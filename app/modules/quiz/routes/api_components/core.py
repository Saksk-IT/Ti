# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from flask import request, jsonify, session, g, current_app
from app.core.utils.database import get_db
from app.core.extensions import limiter
from app.core.utils.decorators import jwt_required, auth_required, current_user_id
from app.core.utils.redis_utils import redis_get_json, redis_set_json
from app.core.utils.cache_utils import (
    get_questions_version,
    get_subjects_version,
    get_user_quiz_version,
    make_cache_key,
    bump_user_quiz_version,
)
from typing import Optional
from app.core.models.question import Question
from app.core.utils.options_parser import parse_options
from app.core.utils.time_utils import today_bj
from app.modules.quiz.services.study_service import now_bj, dt_to_str, next_4am, calc_next_due, clamp_level
from app.modules.quiz.services.reinforcement_service import (
    find_similar_pairs_public,
    find_similar_pairs_user_bank,
    find_similar_training_ids_public,
    find_similar_training_ids_user_bank,
)

from ..api_bp import quiz_api_bp
from ..api_shared import _get_uid_from_request, _resolve_study_scope, _check_question_scope


@quiz_api_bp.route('/reinforce', methods=['GET'])
@limiter.exempt
def api_reinforce():
    source = (request.args.get('source') or 'public').strip().lower()
    bank_id = request.args.get('bank_id', type=int)
    subject_id = request.args.get('subject_id', type=int)

    try:
        wrong_n = int(request.args.get('wrong_n') or 20)
    except Exception:
        wrong_n = 20
    wrong_n = max(0, min(wrong_n, 200))

    try:
        seed_n = int(request.args.get('seed_n') or 6)
    except Exception:
        seed_n = 6
    seed_n = max(0, min(seed_n, 20))

    try:
        per_seed = int(request.args.get('per_seed') or 3)
    except Exception:
        per_seed = 3
    per_seed = max(0, min(per_seed, 10))

    try:
        similar_n = int(request.args.get('similar_n') or 30)
    except Exception:
        similar_n = 30
    similar_n = max(0, min(similar_n, 200))

    include_raw = (request.args.get('include') or '').strip().lower()
    include_set = set([x.strip() for x in include_raw.split(',') if x.strip()]) if include_raw else set()
    if (not include_set) or ('all' in include_set):
        include_set = {'wrong', 'similar'}
    include_wrong = 'wrong' in include_set
    include_similar = 'similar' in include_set

    try:
        wrong_list_n = int(request.args.get('wrong_list_n') or 30)
    except Exception:
        wrong_list_n = 30
    wrong_list_n = max(0, min(wrong_list_n, 200))

    try:
        pairs_n = int(request.args.get('pairs_n') or 30)
    except Exception:
        pairs_n = 30
    pairs_n = max(0, min(pairs_n, 300))

    uid = _get_uid_from_request()
    conn = get_db()

    def _preview_text(s: str, limit: int = 120) -> str:
        try:
            s = str(s or '')
        except Exception:
            s = ''
        s = " ".join(s.split())
        if limit > 0 and len(s) > limit:
            return s[:limit] + '…'
        return s

    def _time_col(table: str, preferred=('updated_at', 'last_updated', 'created_at')) -> str:
        try:
            cols = [r['name'] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        except Exception:
            cols = []
        colset = set([c for c in cols if c])
        for c in preferred:
            if c in colset:
                return c
        return cols[0] if cols else 'id'

    if source == 'user_bank':
        if not uid:
            return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
        if not bank_id:
            return jsonify({'status': 'error', 'message': 'bank_id 参数错误'}), 400

        from app.modules.user_bank.routes.api import check_bank_access

        has_access, _permission, _access_type = check_bank_access(int(uid), int(bank_id))
        if not has_access:
            return jsonify({'status': 'error', 'message': '无权访问该题库'}), 403

        tcol = _time_col('user_bank_mistakes', preferred=('updated_at', 'created_at'))
        try:
            total_row = conn.execute(
                "SELECT COUNT(1) AS cnt FROM user_bank_mistakes WHERE user_id = ? AND bank_id = ?",
                (int(uid), int(bank_id)),
            ).fetchone()
            wrong_total = int(total_row['cnt'] or 0) if total_row else 0
        except Exception:
            wrong_total = 0

        try:
            rows = conn.execute(
                f"""
                SELECT question_id, COALESCE(wrong_count, 1) AS wrong_count, {tcol} AS t
                FROM user_bank_mistakes
                WHERE user_id = ? AND bank_id = ?
                ORDER BY COALESCE(wrong_count, 1) DESC, {tcol} DESC
                LIMIT ?
                """,
                (int(uid), int(bank_id), int(max(wrong_n, seed_n, wrong_list_n) or 0)),
            ).fetchall()
        except Exception:
            rows = []

        wrong_ids = [int(r['question_id']) for r in (rows or []) if r and r['question_id'] is not None]
        wrong_recommend_ids = wrong_ids[:wrong_n] if wrong_n else []
        wrong_top = []
        if include_wrong and wrong_list_n > 0 and rows:
            top_rows = list(rows[:wrong_list_n])
            top_ids = [int(r['question_id']) for r in top_rows if r and r['question_id'] is not None]
            meta_map = {}
            if top_ids:
                try:
                    placeholders = ",".join(["?"] * len(top_ids))
                    qrows = conn.execute(
                        f"SELECT id, type, content FROM user_bank_questions WHERE bank_id = ? AND id IN ({placeholders})",
                        [int(bank_id)] + top_ids,
                    ).fetchall()
                    from app.core.utils.portable_question_format import portable_question_to_internal
                    for qr in qrows or []:
                        try:
                            portable = {
                                "id": qr["id"],
                                "type": (qr["type"] or ""),
                                "content": (qr["content"] or ""),
                                "options": [],
                                "answer": [],
                                "analysis": "",
                                "tags": [],
                                "difficulty": 1,
                            }
                            internal, _errors = portable_question_to_internal(portable, scope="user_bank")
                            meta_map[int(qr['id'])] = {
                                'q_type': internal.get("q_type") or "",
                                'content': internal.get("content") or (qr["content"] or ""),
                            }
                        except Exception:
                            continue
                except Exception:
                    meta_map = {}
            for r in top_rows:
                try:
                    qid = int(r['question_id'])
                except Exception:
                    continue
                meta = meta_map.get(qid) or {}
                wrong_top.append(
                    {
                        'question_id': qid,
                        'wrong_count': int(r['wrong_count'] or 1),
                        'q_type': meta.get('q_type'),
                        'content_preview': _preview_text(meta.get('content')),
                    }
                )
        similar_mode = (request.args.get('similar_mode') or '').strip().lower()

        # 默认：题库全量“查重”找相似题（题干优先、选项兜底）
        # 兼容：如需按错题种子匹配，可传 ?similar_mode=wrong
        seed_ids = []
        similar_pairs_count = 0
        similar_training_ids = []
        similar_pairs = []
        similar_mode_out = ''

        if include_similar:
            # 默认：题库全量“查重”找相似题（题干优先、选项兜底）
            # 兼容：如需按错题种子匹配，可传 ?similar_mode=wrong
            if similar_mode in ('wrong', 'mistake', 'mistakes', 'wrong_seed', 'seed'):
                seed_ids = wrong_ids[:seed_n] if seed_n else []
                if seed_ids and similar_n > 0:
                    similar_training_ids = find_similar_training_ids_user_bank(
                        conn,
                        int(bank_id),
                        seed_ids=seed_ids,
                        exclude_ids=set(seed_ids),
                        per_seed=per_seed,
                        max_total=similar_n,
                    )
                similar_mode_out = 'wrong_seed'
                similar_pairs_count = 0
                similar_pairs = []
            else:
                seed_ids = []
                if similar_n > 0:
                    pairs_need = pairs_n if pairs_n > 0 else (max(1, (similar_n + 1) // 2) if similar_n > 0 else 0)
                    pairs_need = max(0, min(int(pairs_need or 0), 300))
                    similar_training_ids, similar_pairs_count, pairs_raw = find_similar_pairs_user_bank(
                        conn,
                        int(bank_id),
                        max_total_ids=similar_n,
                        max_pairs=pairs_need,
                    )

                    display_pairs = list(pairs_raw[:pairs_n]) if (pairs_n > 0 and pairs_raw) else []
                    if display_pairs:
                        pair_ids = []
                        for a, b, _stem, _opt in display_pairs:
                            pair_ids.append(int(a))
                            pair_ids.append(int(b))
                        uniq_ids = []
                        seen = set()
                        for qid in pair_ids:
                            if qid in seen:
                                continue
                            seen.add(qid)
                            uniq_ids.append(qid)
                        meta_map = {}
                        try:
                            placeholders = ",".join(["?"] * len(uniq_ids))
                            qrows = conn.execute(
                                f"SELECT id, type, content FROM user_bank_questions WHERE bank_id = ? AND id IN ({placeholders})",
                                [int(bank_id)] + uniq_ids,
                            ).fetchall()
                            from app.core.utils.portable_question_format import portable_question_to_internal
                            for qr in qrows or []:
                                try:
                                    portable = {
                                        "id": qr["id"],
                                        "type": (qr["type"] or ""),
                                        "content": (qr["content"] or ""),
                                        "options": [],
                                        "answer": [],
                                        "analysis": "",
                                        "tags": [],
                                        "difficulty": 1,
                                    }
                                    internal, _errors = portable_question_to_internal(portable, scope="user_bank")
                                    meta_map[int(qr['id'])] = {
                                        'q_type': internal.get("q_type") or "",
                                        'content': internal.get("content") or (qr["content"] or ""),
                                    }
                                except Exception:
                                    continue
                        except Exception:
                            meta_map = {}
                        for a, b, stem_sim, opt_sim in display_pairs:
                            a = int(a)
                            b = int(b)
                            ma = meta_map.get(a) or {}
                            mb = meta_map.get(b) or {}
                            similar_pairs.append(
                                {
                                    'a_id': a,
                                    'b_id': b,
                                    'a_type': ma.get('q_type'),
                                    'b_type': mb.get('q_type'),
                                    'a_preview': _preview_text(ma.get('content')),
                                    'b_preview': _preview_text(mb.get('content')),
                                    'stem_sim': float(stem_sim or 0),
                                    'opt_sim': float(opt_sim or 0),
                                }
                            )
                similar_mode_out = 'bank_dedupe'

        return jsonify(
            {
                'status': 'success',
                'data': {
                    'source': 'user_bank',
                    'bank_id': int(bank_id),
                    'logged_in': True,
                    'wrong_total': wrong_total,
                    'wrong_recommend_ids': wrong_recommend_ids,
                    'wrong_top': wrong_top,
                    'similar_mode': similar_mode_out,
                    'similar_pairs_count': int(similar_pairs_count or 0),
                    'similar_seed_ids': seed_ids,
                    'similar_training_ids': similar_training_ids,
                    'similar_pairs': similar_pairs,
                },
            }
        )

    if not subject_id:
        return jsonify({'status': 'error', 'message': 'subject_id 参数错误'}), 400

    subject_row = conn.execute(
        "SELECT id, name FROM subjects WHERE id = ? AND (is_locked=0 OR is_locked IS NULL)",
        (int(subject_id),),
    ).fetchone()
    if not subject_row:
        return jsonify({'status': 'error', 'message': '科目不存在或已锁定'}), 404

    if uid:
        from app.core.utils.subject_permissions import can_user_access_subject

        if not can_user_access_subject(int(uid), int(subject_id)):
            return jsonify({'status': 'error', 'message': '无权访问该科目'}), 403

    if not uid:
        return jsonify(
            {
                'status': 'success',
                'data': {
                    'source': 'public',
                    'subject_id': int(subject_id),
                    'subject_name': subject_row['name'],
                    'logged_in': False,
                    'wrong_total': 0,
                    'wrong_recommend_ids': [],
                    'wrong_top': [],
                    'similar_mode': '',
                    'similar_pairs_count': 0,
                    'similar_seed_ids': [],
                    'similar_training_ids': [],
                    'similar_pairs': [],
                },
            }
        )

    tcol = _time_col('mistakes', preferred=('updated_at', 'last_updated', 'created_at'))
    try:
        total_row = conn.execute(
            """
            SELECT COUNT(1) AS cnt
            FROM mistakes m
            JOIN questions q ON q.id = m.question_id
            JOIN subjects s ON s.id = q.subject_id
            WHERE m.user_id = ? AND q.subject_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
            """,
            (int(uid), int(subject_id)),
        ).fetchone()
        wrong_total = int(total_row['cnt'] or 0) if total_row else 0
    except Exception:
        wrong_total = 0

    try:
        rows = conn.execute(
            f"""
            SELECT m.question_id, COALESCE(m.wrong_count, 1) AS wrong_count, m.{tcol} AS t
            FROM mistakes m
            JOIN questions q ON q.id = m.question_id
            JOIN subjects s ON s.id = q.subject_id
            WHERE m.user_id = ? AND q.subject_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
            ORDER BY COALESCE(m.wrong_count, 1) DESC, m.{tcol} DESC
            LIMIT ?
            """,
            (int(uid), int(subject_id), int(max(wrong_n, seed_n, wrong_list_n) or 0)),
        ).fetchall()
    except Exception:
        rows = []

    wrong_ids = [int(r['question_id']) for r in (rows or []) if r and r['question_id'] is not None]
    wrong_recommend_ids = wrong_ids[:wrong_n] if wrong_n else []
    wrong_top = []
    if include_wrong and wrong_list_n > 0 and rows:
        top_rows = list(rows[:wrong_list_n])
        top_ids = [int(r['question_id']) for r in top_rows if r and r['question_id'] is not None]
        meta_map = {}
        if top_ids:
            try:
                placeholders = ",".join(["?"] * len(top_ids))
                qrows = conn.execute(
                    f"SELECT id, type, content FROM questions WHERE subject_id = ? AND id IN ({placeholders})",
                    [int(subject_id)] + top_ids,
                ).fetchall()
                from app.core.utils.portable_question_format import portable_question_to_internal
                for qr in qrows or []:
                    try:
                        portable = {
                            "id": qr["id"],
                            "type": (qr["type"] or ""),
                            "content": (qr["content"] or ""),
                            "options": [],
                            "answer": [],
                            "analysis": "",
                            "tags": [],
                            "difficulty": 1,
                        }
                        internal, _errors = portable_question_to_internal(portable, scope="question_center")
                        meta_map[int(qr['id'])] = {
                            'q_type': internal.get("q_type") or "",
                            'content': internal.get("content") or (qr["content"] or ""),
                        }
                    except Exception:
                        continue
            except Exception:
                meta_map = {}
        for r in top_rows:
            try:
                qid = int(r['question_id'])
            except Exception:
                continue
            meta = meta_map.get(qid) or {}
            wrong_top.append(
                {
                    'question_id': qid,
                    'wrong_count': int(r['wrong_count'] or 1),
                    'q_type': meta.get('q_type'),
                    'content_preview': _preview_text(meta.get('content')),
                }
            )
    similar_mode = (request.args.get('similar_mode') or '').strip().lower()

    # 默认：本题库（科目）全量“查重”找相似题（题干优先、选项兜底）
    # 兼容：如需按错题种子匹配，可传 ?similar_mode=wrong
    seed_ids = []
    similar_pairs_count = 0
    similar_training_ids = []
    similar_pairs = []
    similar_mode_out = ''

    if include_similar:
        # 默认：本题库（科目）全量“查重”找相似题（题干优先、选项兜底）
        # 兼容：如需按错题种子匹配，可传 ?similar_mode=wrong
        if similar_mode in ('wrong', 'mistake', 'mistakes', 'wrong_seed', 'seed'):
            seed_ids = wrong_ids[:seed_n] if seed_n else []
            if seed_ids and similar_n > 0:
                similar_training_ids = find_similar_training_ids_public(
                    conn,
                    int(subject_id),
                    seed_ids=seed_ids,
                    exclude_ids=set(seed_ids),
                    per_seed=per_seed,
                    max_total=similar_n,
                )
            similar_mode_out = 'wrong_seed'
            similar_pairs_count = 0
            similar_pairs = []
        else:
            seed_ids = []
            if similar_n > 0:
                pairs_need = pairs_n if pairs_n > 0 else (max(1, (similar_n + 1) // 2) if similar_n > 0 else 0)
                pairs_need = max(0, min(int(pairs_need or 0), 300))
                similar_training_ids, similar_pairs_count, pairs_raw = find_similar_pairs_public(
                    conn,
                    int(subject_id),
                    max_total_ids=similar_n,
                    max_pairs=pairs_need,
                )

                display_pairs = list(pairs_raw[:pairs_n]) if (pairs_n > 0 and pairs_raw) else []
                if display_pairs:
                    pair_ids = []
                    for a, b, _stem, _opt in display_pairs:
                        pair_ids.append(int(a))
                        pair_ids.append(int(b))
                    uniq_ids = []
                    seen = set()
                    for qid in pair_ids:
                        if qid in seen:
                            continue
                        seen.add(qid)
                        uniq_ids.append(qid)
                    meta_map = {}
                    try:
                        placeholders = ",".join(["?"] * len(uniq_ids))
                        qrows = conn.execute(
                            f"SELECT id, type, content FROM questions WHERE subject_id = ? AND id IN ({placeholders})",
                            [int(subject_id)] + uniq_ids,
                        ).fetchall()
                        from app.core.utils.portable_question_format import portable_question_to_internal
                        for qr in qrows or []:
                            try:
                                portable = {
                                    "id": qr["id"],
                                    "type": (qr["type"] or ""),
                                    "content": (qr["content"] or ""),
                                    "options": [],
                                    "answer": [],
                                    "analysis": "",
                                    "tags": [],
                                    "difficulty": 1,
                                }
                                internal, _errors = portable_question_to_internal(portable, scope="question_center")
                                meta_map[int(qr['id'])] = {
                                    'q_type': internal.get("q_type") or "",
                                    'content': internal.get("content") or (qr["content"] or ""),
                                }
                            except Exception:
                                continue
                    except Exception:
                        meta_map = {}
                    for a, b, stem_sim, opt_sim in display_pairs:
                        a = int(a)
                        b = int(b)
                        ma = meta_map.get(a) or {}
                        mb = meta_map.get(b) or {}
                        similar_pairs.append(
                            {
                                'a_id': a,
                                'b_id': b,
                                'a_type': ma.get('q_type'),
                                'b_type': mb.get('q_type'),
                                'a_preview': _preview_text(ma.get('content')),
                                'b_preview': _preview_text(mb.get('content')),
                                'stem_sim': float(stem_sim or 0),
                                'opt_sim': float(opt_sim or 0),
                            }
                        )
            similar_mode_out = 'subject_dedupe'

    return jsonify(
        {
            'status': 'success',
            'data': {
                'source': 'public',
                'subject_id': int(subject_id),
                'subject_name': subject_row['name'],
                'logged_in': True,
                'wrong_total': wrong_total,
                'wrong_recommend_ids': wrong_recommend_ids,
                'wrong_top': wrong_top,
                'similar_mode': similar_mode_out,
                'similar_pairs_count': int(similar_pairs_count or 0),
                'similar_seed_ids': seed_ids,
                'similar_training_ids': similar_training_ids,
                'similar_pairs': similar_pairs,
            },
        }
    )


@quiz_api_bp.route('/favorite', methods=['POST'])
@auth_required  # 支持session和JWT
@limiter.exempt  # 收藏接口不限流
def toggle_favorite():
    """切换收藏状态"""
    data = request.get_json(silent=True) or {}
    q_id = data.get('question_id')
    uid = current_user_id()

    try:
        q_id = int(q_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'question_id 参数错误'}), 400
    
    conn = get_db()
    exists = conn.execute(
        "SELECT id FROM favorites WHERE user_id = ? AND question_id = ?",
        (uid, q_id)
    ).fetchone()
    
    if exists:
        conn.execute("DELETE FROM favorites WHERE user_id = ? AND question_id = ?", (uid, q_id))
        is_favorite = False
    else:
        try:
            conn.execute("INSERT INTO favorites (user_id, question_id) VALUES (?, ?)", (uid, q_id))
        except Exception:
            # 兜底处理：题目不存在 / 外键约束失败 / 并发插入等
            conn.rollback()
            return jsonify({'status': 'error', 'message': '收藏失败：题目不存在或不可收藏'}), 400
        is_favorite = True
    
    conn.commit()
    try:
        bump_user_quiz_version(int(uid))
    except Exception:
        pass
    return jsonify({"status": "success", "data": {"is_favorite": is_favorite}})


@quiz_api_bp.route('/record_result', methods=['POST'])
@auth_required  # 支持session和JWT
@limiter.exempt  # 答题记录接口不限流
def record_result():
    """记录做题结果（添加刷题限制检查）"""
    from app.core.utils.subject_permissions import (
        check_quiz_limit, 
        increment_user_quiz_count,
        get_user_quiz_count,
        get_quiz_limit_count
    )
    
    data = request.json or {}
    q_id = data.get('question_id')
    is_correct = data.get('is_correct')
    clear_mistake_on_correct = data.get('clear_mistake_on_correct', True)
    uid = current_user_id()
    
    if not q_id or is_correct is None:
        return jsonify({'status': 'error', 'message': '参数不完整'}), 400

    # 兼容 clear_mistake_on_correct 可能为 string/int/bool；默认 True（保持旧行为）
    try:
        if isinstance(clear_mistake_on_correct, str):
            v = clear_mistake_on_correct.strip().lower()
            if v in ('0', 'false', 'no', 'off'):
                clear_mistake_on_correct = False
            elif v in ('1', 'true', 'yes', 'on'):
                clear_mistake_on_correct = True
            else:
                clear_mistake_on_correct = True
        elif isinstance(clear_mistake_on_correct, (int, float)):
            clear_mistake_on_correct = bool(clear_mistake_on_correct)
        else:
            clear_mistake_on_correct = bool(clear_mistake_on_correct)
    except Exception:
        clear_mistake_on_correct = True
    
    # 检查刷题限制
    is_limited, limit_message = check_quiz_limit(uid)
    if is_limited:
        return jsonify({
            'status': 'error',
            'message': limit_message,
            'code': 'QUIZ_LIMIT_REACHED',
            'data': {
                'current_count': get_user_quiz_count(uid),
                'limit_count': get_quiz_limit_count(),
            }
        }), 403
    
    conn = get_db()
    try:
        # 更新错题本（只记录错误题目）
        if not is_correct:
            try:
                conn.execute(
                    """
                    INSERT INTO mistakes (user_id, question_id, wrong_count, created_at, updated_at, last_updated)
                    VALUES (?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, question_id) DO UPDATE SET
                      wrong_count = wrong_count + 1,
                      updated_at = CURRENT_TIMESTAMP,
                      last_updated = CURRENT_TIMESTAMP
                    """,
                    (uid, q_id),
                )
            except Exception:
                # 兼容旧库：缺少 created_at/updated_at/last_updated 字段
                conn.execute(
                    "INSERT INTO mistakes (user_id, question_id, wrong_count) VALUES (?, ?, 1) ON CONFLICT(user_id, question_id) DO UPDATE SET wrong_count = wrong_count + 1",
                    (uid, q_id),
                )
            action = "added_mistake"
        else:
            if clear_mistake_on_correct:
                # 答对了，从错题本中移除（默认行为）
                conn.execute("DELETE FROM mistakes WHERE user_id = ? AND question_id = ?", (uid, q_id))
                action = "removed_mistake"
            else:
                # 答对但不清除：保留在错题本
                action = "kept_mistake"
        
        # 记录答题历史（每次答题都记录，用于统计）
        # 先删除旧记录，再插入新记录，确保每个用户对每道题只保留最新的一条记录
        conn.execute(
            'DELETE FROM user_answers WHERE user_id = ? AND question_id = ?',
            (uid, q_id)
        )
        conn.execute(
            """INSERT INTO user_answers 
               (user_id, question_id, is_correct, created_at) 
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
            (uid, q_id, 1 if is_correct else 0)
        )
        
        # 增加刷题数（如果功能开启）
        increment_user_quiz_count(uid)
        
        conn.commit()
        try:
            bump_user_quiz_version(int(uid))
        except Exception:
            pass
        return jsonify({"status": "success", "action": action})
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "msg": str(e)}), 500


@quiz_api_bp.route('/questions/count')
@limiter.exempt  # 题目数量查询不限流
def api_questions_count():
    """获取题目数量（添加权限过滤）"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
    from app.core.utils.portable_question_format import any_type_to_portable_type
    
    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    mode = request.args.get('mode', '').lower()
    source = request.args.get('source', '').lower()  # 兼容背题模式下的来源
    tag = (request.args.get('tag') or '').strip()
    uid = _get_uid_from_request()

    cache_key = None
    cache_ttl = 0

    def _ret(payload: dict):
        if cache_key and cache_ttl > 0:
            try:
                redis_set_json(cache_key, payload, ttl_seconds=cache_ttl)
            except Exception:
                pass
        return jsonify(payload)

    if bool(current_app.config.get('QUIZ_API_CACHE_ENABLED', True)):
        try:
            cache_ttl = int(current_app.config.get('QUIZ_CACHE_TTL_COUNTS_SECONDS', 60) or 60)
        except Exception:
            cache_ttl = 60
        if cache_ttl > 0:
            try:
                uv = get_user_quiz_version(int(uid)) if uid else 0
                cache_key = make_cache_key(
                    'quiz:questions_count',
                    {
                        'uid': int(uid) if uid else 0,
                        'subject': subject,
                        'type': q_type,
                        'mode': mode,
                        'source': source,
                        'tag': tag,
                        'uv': int(uv),
                        'qv': get_questions_version(),
                        'sv': get_subjects_version(),
                    },
                )
                cached = redis_get_json(cache_key)
                if isinstance(cached, dict) and cached.get('status') == 'success' and 'count' in cached:
                    return jsonify(cached)
            except Exception:
                cache_key = None

    conn = get_db()
    
    # 获取用户可访问的科目ID列表（用于权限过滤）
    accessible_subject_ids = None
    if uid:
        accessible_subject_ids = get_user_accessible_subjects(uid)
        if not accessible_subject_ids:
            return _ret({'status': 'success', 'count': 0})

    # 兼容新的 source 参数，优先使用 source，其次 mode
    target = source if source in ('favorites', 'mistakes') else mode
    
    if target == 'favorites':
        if not uid:
            return _ret({'status': 'success', 'count': 0})
        base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id JOIN favorites f ON f.question_id = q.id AND f.user_id = ? WHERE (s.is_locked=0 OR s.is_locked IS NULL)"
        params = [uid]
    elif target == 'mistakes':
        if not uid:
            return _ret({'status': 'success', 'count': 0})
        base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id JOIN mistakes m ON m.question_id = q.id AND m.user_id = ? WHERE (s.is_locked=0 OR s.is_locked IS NULL)"
        params = [uid]
    else:
        base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id WHERE (s.is_locked=0 OR s.is_locked IS NULL)"
        params = []
    
    # 添加权限过滤
    if accessible_subject_ids is not None:
        placeholders = ','.join(['?'] * len(accessible_subject_ids))
        base_sql += f" AND q.subject_id IN ({placeholders})"
        params.extend(accessible_subject_ids)
    # 未登录用户：不添加权限过滤，显示所有未锁定科目的题目数（已在base_sql中过滤了is_locked）
    
    if subject != 'all':
        base_sql += " AND s.name = ?"
        params.append(subject)
    
    if q_type != 'all':
        base_sql += " AND q.type = ?"
        params.append(any_type_to_portable_type(q_type))

    # 标签筛选：无登录 / 无命中直接返回 0（标签是用户私有）
    if tag and str(tag).lower() != 'all':
        if not uid:
            return _ret({'status': 'success', 'count': 0})
        tag_ids = get_question_ids_by_tag(conn, uid, tag)
        if not tag_ids:
            return _ret({'status': 'success', 'count': 0})

        # 变量过多时避免 IN 触发 SQLite 参数上限：回退为取ID后求交集
        if len(tag_ids) > 900:
            id_rows = conn.execute("SELECT q.id " + base_sql, params).fetchall()
            base_ids = {int(r[0]) for r in id_rows if r and r[0] is not None}
            return _ret({'status': 'success', 'count': len(base_ids & set(tag_ids))})

        placeholders = ','.join(['?'] * len(tag_ids))
        sql = "SELECT COUNT(1) " + base_sql + f" AND q.id IN ({placeholders})"
        cnt = conn.execute(sql, params + list(tag_ids)).fetchone()[0]
        return _ret({'status': 'success', 'count': cnt})

    sql = "SELECT COUNT(1) " + base_sql
    cnt = conn.execute(sql, params).fetchone()[0]
    return _ret({'status': 'success', 'count': cnt})


@quiz_api_bp.route('/questions/user_counts')
@limiter.exempt  # 用户计数查询不限流
def api_user_counts():
    """获取用户的收藏和错题数量"""
    from app.core.utils.portable_question_format import any_type_to_portable_type

    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    tag = (request.args.get('tag') or '').strip()
    uid = _get_uid_from_request()
    
    if not uid:
        return jsonify({'status': 'success', 'favorites': 0, 'mistakes': 0})

    cache_key = None
    cache_ttl = 0

    def _ret(payload: dict):
        if cache_key and cache_ttl > 0:
            try:
                redis_set_json(cache_key, payload, ttl_seconds=cache_ttl)
            except Exception:
                pass
        return jsonify(payload)

    if bool(current_app.config.get('QUIZ_API_CACHE_ENABLED', True)):
        try:
            cache_ttl = int(current_app.config.get('QUIZ_CACHE_TTL_USER_COUNTS_SECONDS', 30) or 30)
        except Exception:
            cache_ttl = 30
        if cache_ttl > 0:
            try:
                cache_key = make_cache_key(
                    'quiz:user_counts',
                    {
                        'uid': int(uid),
                        'subject': subject,
                        'type': q_type,
                        'tag': tag,
                        'uv': get_user_quiz_version(int(uid)),
                        'qv': get_questions_version(),
                        'sv': get_subjects_version(),
                    },
                )
                cached = redis_get_json(cache_key)
                if isinstance(cached, dict) and cached.get('status') == 'success':
                    if 'favorites' in cached and 'mistakes' in cached:
                        return jsonify(cached)
            except Exception:
                cache_key = None
    
    conn = get_db()
    
    fav_sql = """
        SELECT COUNT(1)
        FROM favorites f
        JOIN questions q ON q.id = f.question_id
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE f.user_id = ?
    """
    mis_sql = """
        SELECT COUNT(1)
        FROM mistakes m
        JOIN questions q ON q.id = m.question_id
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE m.user_id = ?
    """
    
    fav_params = [uid]
    mis_params = [uid]
    
    if subject != 'all':
        fav_sql += " AND s.name = ?"
        mis_sql += " AND s.name = ?"
        fav_params.append(subject)
        mis_params.append(subject)
    
    if q_type != 'all':
        fav_sql += " AND q.type = ?"
        mis_sql += " AND q.type = ?"
        fav_params.append(any_type_to_portable_type(q_type))
        mis_params.append(any_type_to_portable_type(q_type))

    # 标签筛选：标签为用户私有（存储在 user_progress）
    if tag and str(tag).lower() != 'all':
        from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag

        tag_ids = get_question_ids_by_tag(conn, uid, tag)
        if not tag_ids:
            return _ret({'status': 'success', 'favorites': 0, 'mistakes': 0})

        # 变量过多时避免 IN 触发 SQLite 参数上限：回退为取ID后求交集
        if len(tag_ids) > 900:
            tag_set = set(tag_ids)

            fav_id_rows = conn.execute(
                fav_sql.replace('SELECT COUNT(1)', 'SELECT q.id'),
                fav_params,
            ).fetchall()
            mis_id_rows = conn.execute(
                mis_sql.replace('SELECT COUNT(1)', 'SELECT q.id'),
                mis_params,
            ).fetchall()

            fav_ids = {int(r[0]) for r in fav_id_rows if r and r[0] is not None}
            mis_ids = {int(r[0]) for r in mis_id_rows if r and r[0] is not None}

            return _ret({
                'status': 'success',
                'favorites': len(fav_ids & tag_set),
                'mistakes': len(mis_ids & tag_set),
            })

        placeholders = ','.join(['?'] * len(tag_ids))
        fav_sql += f" AND q.id IN ({placeholders})"
        mis_sql += f" AND q.id IN ({placeholders})"
        fav_params.extend(list(tag_ids))
        mis_params.extend(list(tag_ids))
    
    fav_cnt = conn.execute(fav_sql, fav_params).fetchone()[0]
    mis_cnt = conn.execute(mis_sql, mis_params).fetchone()[0]
    
    return _ret({'status': 'success', 'favorites': fav_cnt, 'mistakes': mis_cnt})


@quiz_api_bp.route('/history', methods=['GET'])
@auth_required  # 支持session和JWT
@limiter.exempt
def api_history_stats():
    """学习统计（与 Web /history 同语义，供小程序 v2 页面使用）"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    from app.core.utils.portable_question_format import portable_type_to_q_type

    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    cache_key = None
    cache_ttl = 0
    if bool(current_app.config.get('QUIZ_API_CACHE_ENABLED', True)):
        try:
            cache_ttl = int(current_app.config.get('QUIZ_CACHE_TTL_HISTORY_SECONDS', 30) or 30)
        except Exception:
            cache_ttl = 30
        if cache_ttl > 0:
            try:
                cache_key = make_cache_key(
                    'quiz:history',
                    {
                        'uid': int(uid),
                        'uv': get_user_quiz_version(int(uid)),
                        'qv': get_questions_version(),
                        'sv': get_subjects_version(),
                    },
                )
                cached = redis_get_json(cache_key)
                if isinstance(cached, dict) and cached.get('status') == 'success' and 'data' in cached:
                    return jsonify(cached)
            except Exception:
                cache_key = None

    conn = get_db()

    def _column_exists(table: str, column: str) -> bool:
        try:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return any(r and r['name'] == column for r in rows)
        except Exception:
            return False

    # 可访问科目（并过滤锁定）
    subject_ids = []
    subjects_meta = []
    try:
        accessible_ids = get_user_accessible_subjects(uid) or []
        if accessible_ids:
            placeholders = ','.join(['?'] * len(accessible_ids))
            rows = conn.execute(
                f"""
                SELECT id, name
                FROM subjects
                WHERE (is_locked=0 OR is_locked IS NULL)
                  AND id IN ({placeholders})
                ORDER BY id
                """,
                accessible_ids,
            ).fetchall()
            subjects_meta = [{'id': int(r['id']), 'name': r['name']} for r in (rows or []) if r and r['id'] is not None]
            subject_ids = [int(r['id']) for r in (rows or []) if r and r['id'] is not None]
    except Exception as e:
        current_app.logger.warning(f"history subjects meta failed: {e}")
        subject_ids = []
        subjects_meta = []

    # 公共题库总题数（按权限与锁定过滤）
    total_questions = 0
    try:
        base_sql = """
            SELECT COUNT(*)
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE (s.is_locked=0 OR s.is_locked IS NULL)
        """
        params = []
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            base_sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(subject_ids)
        total_questions = int(conn.execute(base_sql, params).fetchone()[0] or 0)
    except Exception as e:
        current_app.logger.warning(f"history total_questions failed: {e}")
        total_questions = 0

    # 复用 join + 权限过滤（公共题库）
    ua_from = """
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.id
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE ua.user_id = ?
          AND (s.is_locked=0 OR s.is_locked IS NULL)
    """
    ua_params_base = [uid]
    if subject_ids:
        placeholders = ','.join(['?'] * len(subject_ids))
        ua_from += f" AND q.subject_id IN ({placeholders})"
        ua_params_base.extend(subject_ids)

    # 全局汇总（公共题库）
    answered_count = 0
    correct_count = 0
    last_activity = None
    try:
        row = conn.execute(
            f"""
            SELECT
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
              MAX(ua.created_at) AS last_activity
            {ua_from}
            """,
            ua_params_base,
        ).fetchone()
        answered_count = int(row['answered'] or 0) if row else 0
        correct_count = int(row['correct'] or 0) if row else 0
        last_activity = (row['last_activity'] if row else None) or None
    except Exception as e:
        current_app.logger.warning(f"history summary failed: {e}")
        answered_count = 0
        correct_count = 0
        last_activity = None

    accuracy = round(correct_count * 100 / answered_count, 1) if answered_count > 0 else 0.0
    completion = round(answered_count * 100 / total_questions, 1) if total_questions > 0 else 0.0

    # 收藏/错题（公共题库）
    favorites_count = 0
    mistakes_count = 0
    mistakes_times = 0  # 若存在 wrong_count 则为累计次数，否则退化为 mistakes_count
    try:
        fav_sql = """
            SELECT COUNT(*)
            FROM favorites f
            JOIN questions q ON f.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE f.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        fav_params = [uid]
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            fav_sql += f" AND q.subject_id IN ({placeholders})"
            fav_params.extend(subject_ids)
        favorites_count = int(conn.execute(fav_sql, fav_params).fetchone()[0] or 0)
    except Exception as e:
        current_app.logger.warning(f"history favorites_count failed: {e}")
        favorites_count = 0

    mistakes_has_wrong_count = _column_exists('mistakes', 'wrong_count')
    mistakes_has_updated_at = _column_exists('mistakes', 'updated_at')
    try:
        mis_sql = """
            SELECT
              COUNT(*) AS cnt,
              SUM(CASE WHEN m.wrong_count IS NULL THEN 1 ELSE m.wrong_count END) AS times
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        mis_params = [uid]
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            mis_sql += f" AND q.subject_id IN ({placeholders})"
            mis_params.extend(subject_ids)
        if not mistakes_has_wrong_count:
            mis_sql = mis_sql.replace("m.wrong_count", "NULL")
        row = conn.execute(mis_sql, mis_params).fetchone()
        mistakes_count = int(row['cnt'] or 0) if row else 0
        mistakes_times = int(row['times'] or 0) if row else 0
        if not mistakes_has_wrong_count:
            mistakes_times = mistakes_count
    except Exception as e:
        current_app.logger.warning(f"history mistakes_count failed: {e}")
        mistakes_count = 0
        mistakes_times = 0

    # 连续学习天数（基于 user_answers 的 DATE(created_at)）
    streak_days = 0
    try:
        rows = conn.execute(
            f"SELECT DISTINCT DATE(ua.created_at) AS day {ua_from} ORDER BY day DESC LIMIT 120",
            ua_params_base,
        ).fetchall()
        dates = []
        for r in rows or []:
            if r and r['day']:
                try:
                    dates.append(datetime.strptime(r['day'], '%Y-%m-%d').date())
                except Exception:
                    continue
        today = today_bj()
        if dates and dates[0] >= (today - timedelta(days=1)):
            streak_days = 1
            for i in range(1, len(dates)):
                if dates[i - 1] - dates[i] == timedelta(days=1):
                    streak_days += 1
                else:
                    break
    except Exception as e:
        current_app.logger.warning(f"history streak failed: {e}")
        streak_days = 0

    def _count_since(days: int) -> tuple[int, int]:
        if days <= 0:
            return answered_count, correct_count
        try:
            row = conn.execute(
                f"""
                SELECT
                  COUNT(*) AS answered,
                  SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
                {ua_from}
                  AND ua.created_at >= datetime('now', '+8 hours', ?)
                """,
                ua_params_base + [f'-{days} days'],
            ).fetchone()
            return int(row['answered'] or 0), int(row['correct'] or 0)
        except Exception:
            return 0, 0

    answered_7d, correct_7d = _count_since(7)
    answered_30d, correct_30d = _count_since(30)

    # 趋势窗口（只影响趋势图展示）
    window_days = request.args.get('days', 30, type=int)
    if window_days not in (7, 30, 90):
        window_days = 30

    daily = []
    daily_max = 0
    window_answered = 0
    window_correct = 0
    window_accuracy = 0.0
    try:
        rows = conn.execute(
            f"""
            SELECT
              DATE(ua.created_at) AS day,
              COUNT(*) AS total,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            {ua_from}
              AND ua.created_at >= datetime('now', '+8 hours', ?)
            GROUP BY DATE(ua.created_at)
            ORDER BY day
            """,
            ua_params_base + [f'-{window_days} days'],
        ).fetchall()
        data_map = {r['day']: {'total': int(r['total'] or 0), 'correct': int(r['correct'] or 0)} for r in (rows or []) if r and r['day']}

        today = today_bj()
        start = today - timedelta(days=window_days - 1)
        for i in range(window_days):
            d = start + timedelta(days=i)
            key = d.strftime('%Y-%m-%d')
            total = int((data_map.get(key) or {}).get('total', 0))
            correct = int((data_map.get(key) or {}).get('correct', 0))
            acc = round(correct * 100 / total, 1) if total > 0 else 0.0
            daily_max = max(daily_max, total)
            daily.append({'day': key, 'total': total, 'correct': correct, 'accuracy': acc})

        window_answered = sum(int(x.get('total', 0) or 0) for x in daily)
        window_correct = sum(int(x.get('correct', 0) or 0) for x in daily)
        window_accuracy = round(window_correct * 100 / window_answered, 1) if window_answered > 0 else 0.0
    except Exception as e:
        current_app.logger.warning(f"history daily failed: {e}")
        daily = []
        daily_max = 0
        window_answered = 0
        window_correct = 0
        window_accuracy = 0.0

    # 科目维度（公共题库）
    subject_rows = []
    try:
        total_map = {}
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            rows = conn.execute(
                f"""
                SELECT q.subject_id AS subject_id, COUNT(*) AS total
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                subject_ids,
            ).fetchall()
            total_map = {int(r['subject_id']): int(r['total'] or 0) for r in (rows or []) if r and r['subject_id'] is not None}

        ans_map = {}
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            rows = conn.execute(
                f"""
                SELECT q.subject_id AS subject_id,
                       COUNT(*) AS answered,
                       SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
                FROM user_answers ua
                JOIN questions q ON ua.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE ua.user_id = ?
                  AND (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                [uid] + subject_ids,
            ).fetchall()
            ans_map = {
                int(r['subject_id']): {'answered': int(r['answered'] or 0), 'correct': int(r['correct'] or 0)}
                for r in (rows or [])
                if r and r['subject_id'] is not None
            }

        mis_map = {}
        fav_map = {}
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            rows = conn.execute(
                f"""
                SELECT q.subject_id AS subject_id, COUNT(*) AS cnt
                FROM mistakes m
                JOIN questions q ON m.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                [uid] + subject_ids,
            ).fetchall()
            mis_map = {int(r['subject_id']): int(r['cnt'] or 0) for r in (rows or []) if r and r['subject_id'] is not None}

            rows = conn.execute(
                f"""
                SELECT q.subject_id AS subject_id, COUNT(*) AS cnt
                FROM favorites f
                JOIN questions q ON f.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE f.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                [uid] + subject_ids,
            ).fetchall()
            fav_map = {int(r['subject_id']): int(r['cnt'] or 0) for r in (rows or []) if r and r['subject_id'] is not None}

        for s in subjects_meta or []:
            sid = int(s['id'])
            total = int(total_map.get(sid, 0))
            answered = int((ans_map.get(sid) or {}).get('answered', 0))
            correct = int((ans_map.get(sid) or {}).get('correct', 0))
            acc = round(correct * 100 / answered, 1) if answered > 0 else 0.0
            comp = round(answered * 100 / total, 1) if total > 0 else 0.0
            subject_rows.append({
                'subject_id': sid,
                'subject': s['name'],
                'total': total,
                'answered': answered,
                'correct': correct,
                'accuracy': acc,
                'completion': comp,
                'mistakes': int(mis_map.get(sid, 0)),
                'favorites': int(fav_map.get(sid, 0)),
            })
    except Exception as e:
        current_app.logger.warning(f"history subject rows failed: {e}")
        subject_rows = []

    # 题型维度（公共题库）
    type_rows = []
    try:
        rows = conn.execute(
            f"""
            SELECT
              COALESCE(NULLIF(TRIM(q.type), ''), 'unknown') AS p_type,
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            {ua_from}
            GROUP BY COALESCE(NULLIF(TRIM(q.type), ''), 'unknown')
            ORDER BY answered DESC
            """,
            ua_params_base,
        ).fetchall()
        for r in rows or []:
            p_type = str((r['p_type'] or 'unknown'))
            answered = int(r['answered'] or 0)
            correct = int(r['correct'] or 0)
            type_rows.append({
                'q_type': ('未知' if p_type == 'unknown' else portable_type_to_q_type(p_type)),
                'answered': answered,
                'correct': correct,
                'accuracy': round(correct * 100 / answered, 1) if answered > 0 else 0.0,
            })
    except Exception as e:
        current_app.logger.warning(f"history type rows failed: {e}")
        type_rows = []

    # 难度维度（公共题库）
    difficulty_rows = []
    try:
        rows = conn.execute(
            f"""
            SELECT
              COALESCE(q.difficulty, 1) AS difficulty,
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            {ua_from}
            GROUP BY q.difficulty
            ORDER BY difficulty ASC
            """,
            ua_params_base,
        ).fetchall()
        for r in rows or []:
            diff = int(r['difficulty'] or 1)
            answered = int(r['answered'] or 0)
            correct = int(r['correct'] or 0)
            label = {1: '简单', 2: '中等', 3: '困难'}.get(diff, f'难度{diff}')
            difficulty_rows.append({
                'difficulty': diff,
                'label': label,
                'answered': answered,
                'correct': correct,
                'accuracy': round(correct * 100 / answered, 1) if answered > 0 else 0.0,
            })
    except Exception as e:
        current_app.logger.warning(f"history difficulty rows failed: {e}")
        difficulty_rows = []

    # 薄弱点：科目 × 题型（公共题库）
    weakness_rows = []
    try:
        rows = conn.execute(
            f"""
            SELECT
              COALESCE(s.name, '未分类') AS subject,
              COALESCE(NULLIF(TRIM(q.type), ''), 'unknown') AS p_type,
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            {ua_from}
            GROUP BY s.name, COALESCE(NULLIF(TRIM(q.type), ''), 'unknown')
            HAVING answered >= 5
            ORDER BY (correct * 1.0 / answered) ASC, answered DESC
            LIMIT 8
            """,
            ua_params_base,
        ).fetchall()

        mis_rows = conn.execute(
            f"""
            SELECT
              COALESCE(s.name, '未分类') AS subject,
              COALESCE(NULLIF(TRIM(q.type), ''), 'unknown') AS p_type,
              COUNT(*) AS mistakes
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
            {('AND q.subject_id IN (' + ','.join(['?']*len(subject_ids)) + ')') if subject_ids else ''}
            GROUP BY s.name, COALESCE(NULLIF(TRIM(q.type), ''), 'unknown')
            """,
            [uid] + (subject_ids if subject_ids else []),
        ).fetchall()
        mis_map = {}
        for r in mis_rows or []:
            if not r:
                continue
            subject_name = r['subject'] or '未分类'
            p_type = str((r['p_type'] or 'unknown'))
            q_type_disp = '未知' if p_type == 'unknown' else portable_type_to_q_type(p_type)
            mis_map[(subject_name, q_type_disp)] = int(r['mistakes'] or 0)

        for r in rows or []:
            p_type = str((r['p_type'] or 'unknown'))
            q_type_disp = '未知' if p_type == 'unknown' else portable_type_to_q_type(p_type)
            answered = int(r['answered'] or 0)
            correct = int(r['correct'] or 0)
            acc = round(correct * 100 / answered, 1) if answered > 0 else 0.0
            key = (r['subject'] or '未分类', q_type_disp)
            weakness_rows.append({
                'subject': r['subject'] or '未分类',
                'q_type': q_type_disp,
                'answered': answered,
                'correct': correct,
                'accuracy': acc,
                'mistakes': int(mis_map.get(key, 0)),
            })
    except Exception as e:
        current_app.logger.warning(f"history weakness rows failed: {e}")
        weakness_rows = []

    # 最近错题（公共题库）
    recent_mistakes = []
    try:
        order_by = "m.created_at DESC"
        if mistakes_has_wrong_count:
            order_by = "m.wrong_count DESC, COALESCE(m.updated_at, m.created_at) DESC" if mistakes_has_updated_at else "m.wrong_count DESC, m.created_at DESC"
        sql = f"""
            SELECT
              COALESCE(s.name, '未分类') AS subject,
              COALESCE(NULLIF(TRIM(q.type), ''), 'unknown') AS p_type,
              q.id AS question_id,
              q.content AS content,
              q.difficulty AS difficulty,
              m.created_at AS created_at
              {', m.wrong_count AS wrong_count' if mistakes_has_wrong_count else ''}
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
            {('AND q.subject_id IN (' + ','.join(['?']*len(subject_ids)) + ')') if subject_ids else ''}
            ORDER BY {order_by}
            LIMIT 8
        """
        rows = conn.execute(sql, [uid] + (subject_ids if subject_ids else [])).fetchall()
        for r in rows or []:
            content = (r['content'] or '').strip().replace('\r', ' ').replace('\n', ' ')
            snippet = content[:80] + ('…' if len(content) > 80 else '')
            p_type = str((r['p_type'] or 'unknown'))
            q_type_disp = '未知' if p_type == 'unknown' else portable_type_to_q_type(p_type)
            recent_mistakes.append({
                'subject': r['subject'] or '未分类',
                'q_type': q_type_disp,
                'question_id': int(r['question_id']),
                'snippet': snippet,
                'difficulty': int(r['difficulty'] or 1),
                'wrong_count': int(r['wrong_count'] or 1) if mistakes_has_wrong_count else None,
            })
    except Exception as e:
        current_app.logger.warning(f"history recent mistakes failed: {e}")
        recent_mistakes = []

    next_actions = []
    try:
        for w in (weakness_rows or [])[:3]:
            next_actions.append({
                'title': f"{w['subject']} · {w['q_type']}",
                'meta': f"正确率 {w['accuracy']}%（已做 {w['answered']}）",
                'subject': w['subject'],
                'q_type': w['q_type'],
            })
    except Exception:
        next_actions = []

    payload = {
        'status': 'success',
        'data': {
            'subjects_meta': subjects_meta,
            'total_questions': total_questions,
            'answered_count': answered_count,
            'correct_count': correct_count,
            'accuracy': accuracy,
            'completion': completion,
            'favorites_count': favorites_count,
            'mistakes_count': mistakes_count,
            'mistakes_times': mistakes_times,
            'streak_days': streak_days,
            'last_activity': last_activity,
            'answered_7d': answered_7d,
            'correct_7d': correct_7d,
            'answered_30d': answered_30d,
            'correct_30d': correct_30d,
            'window_days': window_days,
            'daily': daily,
            'daily_max': daily_max or 1,
            'window_answered': window_answered,
            'window_correct': window_correct,
            'window_accuracy': window_accuracy,
            'subject_rows': subject_rows,
            'type_rows': type_rows,
            'difficulty_rows': difficulty_rows,
            'weakness_rows': weakness_rows,
            'recent_mistakes': recent_mistakes,
            'next_actions': next_actions,
        },
    }

    if cache_key and cache_ttl > 0 and bool(current_app.config.get('QUIZ_API_CACHE_ENABLED', True)):
        try:
            redis_set_json(cache_key, payload, ttl_seconds=cache_ttl)
        except Exception:
            pass

    return jsonify(payload)
