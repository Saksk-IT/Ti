# -*- coding: utf-8 -*-
"""强化训练路由 — 错题推荐 + 相似题查重

从 core.py 拆分，提供 /reinforce 接口。
"""

from flask import request, jsonify
from sqlalchemy import text

from app.core.extensions import db, limiter
from app.models.subject import Subject, Question
from app.models.quiz import Mistake
from app.models.user_bank import UserBankQuestion, UserBankMistake
from app.modules.quiz.services.reinforcement_service import (
    find_similar_pairs_public,
    find_similar_pairs_user_bank,
    find_similar_training_ids_public,
    find_similar_training_ids_user_bank,
)

from ..api_bp import quiz_api_bp
from ..api_shared import _get_uid_from_request


def _preview_text(s: str, limit: int = 120) -> str:
    """截断预览文本"""
    try:
        s = str(s or '')
    except Exception:
        s = ''
    s = " ".join(s.split())
    if limit > 0 and len(s) > limit:
        return s[:limit] + '…'
    return s


def _build_meta_map_user_bank(bank_id: int, ids: list[int]) -> dict:
    """为用户题库的题目 ID 列表构建 meta 信息映射"""
    if not ids:
        return {}
    meta_map: dict = {}
    try:
        rows = UserBankQuestion.query.filter(
            UserBankQuestion.bank_id == int(bank_id),
            UserBankQuestion.id.in_(ids),
        ).all()
        from app.core.utils.portable_question_format import portable_question_to_internal
        for qr in rows or []:
            try:
                portable = {
                    "id": qr.id,
                    "type": (qr.type or ""),
                    "content": (qr.content or ""),
                    "options": [],
                    "answer": [],
                    "analysis": "",
                    "tags": [],
                    "difficulty": 1,
                }
                internal, _errors = portable_question_to_internal(portable, scope="user_bank")
                meta_map[int(qr.id)] = {
                    'q_type': internal.get("q_type") or "",
                    'content': internal.get("content") or (qr.content or ""),
                }
            except Exception:
                continue
    except Exception:
        pass
    return meta_map


def _build_meta_map_public(subject_id: int, ids: list[int]) -> dict:
    """为公共题库的题目 ID 列表构建 meta 信息映射"""
    if not ids:
        return {}
    meta_map: dict = {}
    try:
        rows = Question.query.filter(
            Question.subject_id == int(subject_id),
            Question.id.in_(ids),
        ).all()
        from app.core.utils.portable_question_format import portable_question_to_internal
        for qr in rows or []:
            try:
                portable = {
                    "id": qr.id,
                    "type": (qr.type or ""),
                    "content": (qr.content or ""),
                    "options": [],
                    "answer": [],
                    "analysis": "",
                    "tags": [],
                    "difficulty": 1,
                }
                internal, _errors = portable_question_to_internal(portable, scope="question_center")
                meta_map[int(qr.id)] = {
                    'q_type': internal.get("q_type") or "",
                    'content': internal.get("content") or (qr.content or ""),
                }
            except Exception:
                continue
    except Exception:
        pass
    return meta_map


def _build_wrong_top(rows, meta_map: dict, wrong_list_n: int) -> list[dict]:
    """从错题行构建 wrong_top 列表"""
    wrong_top = []
    top_rows = list(rows[:wrong_list_n])
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
    return wrong_top


def _build_similar_pairs_display(display_pairs, meta_map: dict) -> list[dict]:
    """从相似题对构建展示列表"""
    similar_pairs = []
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
    return similar_pairs


def _collect_pair_unique_ids(display_pairs) -> list[int]:
    """从相似题对中收集去重后的题目 ID"""
    pair_ids = []
    for a, b, _stem, _opt in display_pairs:
        pair_ids.append(int(a))
        pair_ids.append(int(b))
    uniq_ids = []
    seen: set = set()
    for qid in pair_ids:
        if qid in seen:
            continue
        seen.add(qid)
        uniq_ids.append(qid)
    return uniq_ids


def _parse_int_param(name: str, default: int, lo: int, hi: int) -> int:
    """从 request.args 解析整数参数并 clamp 到 [lo, hi]"""
    try:
        val = int(request.args.get(name) or default)
    except Exception:
        val = default
    return max(lo, min(val, hi))


@quiz_api_bp.route('/reinforce', methods=['GET'])
@limiter.exempt
def api_reinforce():
    source = (request.args.get('source') or 'public').strip().lower()
    bank_id = request.args.get('bank_id', type=int)
    subject_id = request.args.get('subject_id', type=int)

    wrong_n = _parse_int_param('wrong_n', 20, 0, 200)
    seed_n = _parse_int_param('seed_n', 6, 0, 20)
    per_seed = _parse_int_param('per_seed', 3, 0, 10)
    similar_n = _parse_int_param('similar_n', 30, 0, 200)
    wrong_list_n = _parse_int_param('wrong_list_n', 30, 0, 200)
    pairs_n = _parse_int_param('pairs_n', 30, 0, 300)

    include_raw = (request.args.get('include') or '').strip().lower()
    include_set = set([x.strip() for x in include_raw.split(',') if x.strip()]) if include_raw else set()
    if (not include_set) or ('all' in include_set):
        include_set = {'wrong', 'similar'}
    include_wrong = 'wrong' in include_set
    include_similar = 'similar' in include_set

    uid = _get_uid_from_request()
    conn = db.session.connection()

    if source == 'user_bank':
        return _reinforce_user_bank(
            conn, uid, bank_id,
            wrong_n=wrong_n, seed_n=seed_n, per_seed=per_seed,
            similar_n=similar_n, wrong_list_n=wrong_list_n, pairs_n=pairs_n,
            include_wrong=include_wrong, include_similar=include_similar,
        )

    return _reinforce_public(
        conn, uid, subject_id,
        wrong_n=wrong_n, seed_n=seed_n, per_seed=per_seed,
        similar_n=similar_n, wrong_list_n=wrong_list_n, pairs_n=pairs_n,
        include_wrong=include_wrong, include_similar=include_similar,
    )


def _reinforce_user_bank(
    conn, uid, bank_id,
    *, wrong_n, seed_n, per_seed, similar_n, wrong_list_n, pairs_n,
    include_wrong, include_similar,
):
    """强化训练 — 用户题库分支"""
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    if not bank_id:
        return jsonify({'status': 'error', 'message': 'bank_id 参数错误'}), 400

    from app.modules.user_bank.routes.api import check_bank_access

    has_access, _permission, _access_type = check_bank_access(int(uid), int(bank_id))
    if not has_access:
        return jsonify({'status': 'error', 'message': '无权访问该题库'}), 403

    try:
        wrong_total = UserBankMistake.query.filter_by(
            user_id=int(uid), bank_id=int(bank_id)
        ).count()
    except Exception:
        wrong_total = 0

    try:
        limit_n = int(max(wrong_n, seed_n, wrong_list_n) or 0)
        rows = db.session.query(
            UserBankMistake.question_id,
            db.func.coalesce(UserBankMistake.wrong_count, 1).label("wrong_count"),
            UserBankMistake.updated_at.label("t"),
        ).filter(
            UserBankMistake.user_id == int(uid),
            UserBankMistake.bank_id == int(bank_id),
        ).order_by(
            db.func.coalesce(UserBankMistake.wrong_count, 1).desc(),
            UserBankMistake.updated_at.desc(),
        ).limit(limit_n).all()
    except Exception:
        rows = []

    wrong_ids = [int(r.question_id) for r in (rows or []) if r and r.question_id is not None]
    wrong_recommend_ids = wrong_ids[:wrong_n] if wrong_n else []

    # 错题 top 列表
    wrong_top = []
    if include_wrong and wrong_list_n > 0 and rows:
        top_ids = [int(r.question_id) for r in list(rows[:wrong_list_n]) if r and r.question_id is not None]
        meta_map = _build_meta_map_user_bank(int(bank_id), top_ids)
        row_dicts = [{'question_id': r.question_id, 'wrong_count': r.wrong_count} for r in rows]
        wrong_top = _build_wrong_top(row_dicts, meta_map, wrong_list_n)

    # 相似题
    similar_mode = (request.args.get('similar_mode') or '').strip().lower()
    result = _compute_similar_user_bank(
        conn, int(bank_id), wrong_ids,
        similar_mode=similar_mode, include_similar=include_similar,
        seed_n=seed_n, similar_n=similar_n, per_seed=per_seed, pairs_n=pairs_n,
    )

    return jsonify({
        'status': 'success',
        'data': {
            'source': 'user_bank',
            'bank_id': int(bank_id),
            'logged_in': True,
            'wrong_total': wrong_total,
            'wrong_recommend_ids': wrong_recommend_ids,
            'wrong_top': wrong_top,
            **result,
        },
    })


def _compute_similar_user_bank(
    conn, bank_id: int, wrong_ids: list[int],
    *, similar_mode: str, include_similar: bool,
    seed_n: int, similar_n: int, per_seed: int, pairs_n: int,
) -> dict:
    """计算用户题库的相似题结果"""
    seed_ids: list[int] = []
    similar_pairs_count = 0
    similar_training_ids: list[int] = []
    similar_pairs: list[dict] = []
    similar_mode_out = ''

    if not include_similar:
        return {
            'similar_mode': similar_mode_out,
            'similar_pairs_count': 0,
            'similar_seed_ids': seed_ids,
            'similar_training_ids': similar_training_ids,
            'similar_pairs': similar_pairs,
        }

    if similar_mode in ('wrong', 'mistake', 'mistakes', 'wrong_seed', 'seed'):
        seed_ids = wrong_ids[:seed_n] if seed_n else []
        if seed_ids and similar_n > 0:
            similar_training_ids = find_similar_training_ids_user_bank(
                conn, bank_id,
                seed_ids=seed_ids,
                exclude_ids=set(seed_ids),
                per_seed=per_seed,
                max_total=similar_n,
            )
        similar_mode_out = 'wrong_seed'
    else:
        if similar_n > 0:
            pairs_need = pairs_n if pairs_n > 0 else (max(1, (similar_n + 1) // 2) if similar_n > 0 else 0)
            pairs_need = max(0, min(int(pairs_need or 0), 300))
            similar_training_ids, similar_pairs_count, pairs_raw = find_similar_pairs_user_bank(
                conn, bank_id,
                max_total_ids=similar_n,
                max_pairs=pairs_need,
            )
            display_pairs = list(pairs_raw[:pairs_n]) if (pairs_n > 0 and pairs_raw) else []
            if display_pairs:
                uniq_ids = _collect_pair_unique_ids(display_pairs)
                meta_map = _build_meta_map_user_bank(bank_id, uniq_ids)
                similar_pairs = _build_similar_pairs_display(display_pairs, meta_map)
        similar_mode_out = 'bank_dedupe'

    return {
        'similar_mode': similar_mode_out,
        'similar_pairs_count': int(similar_pairs_count or 0),
        'similar_seed_ids': seed_ids,
        'similar_training_ids': similar_training_ids,
        'similar_pairs': similar_pairs,
    }


def _reinforce_public(
    conn, uid, subject_id,
    *, wrong_n, seed_n, per_seed, similar_n, wrong_list_n, pairs_n,
    include_wrong, include_similar,
):
    """强化训练 — 公共题库分支"""
    if not subject_id:
        return jsonify({'status': 'error', 'message': 'subject_id 参数错误'}), 400

    subject_row = Subject.query.filter(
        Subject.id == int(subject_id),
        db.or_(Subject.is_locked == False, Subject.is_locked.is_(None)),
    ).first()
    if not subject_row:
        return jsonify({'status': 'error', 'message': '科目不存在或已锁定'}), 404

    if uid:
        from app.core.utils.subject_permissions import can_user_access_subject
        if not can_user_access_subject(int(uid), int(subject_id)):
            return jsonify({'status': 'error', 'message': '无权访问该科目'}), 403

    if not uid:
        return jsonify({
            'status': 'success',
            'data': {
                'source': 'public',
                'subject_id': int(subject_id),
                'subject_name': subject_row.name,
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
        })

    try:
        wrong_total = db.session.query(Mistake).join(
            Question, Question.id == Mistake.question_id
        ).join(
            Subject, Subject.id == Question.subject_id
        ).filter(
            Mistake.user_id == int(uid),
            Question.subject_id == int(subject_id),
            db.or_(Subject.is_locked == False, Subject.is_locked.is_(None)),
        ).count()
    except Exception:
        wrong_total = 0

    try:
        limit_n = int(max(wrong_n, seed_n, wrong_list_n) or 0)
        rows = db.session.query(
            Mistake.question_id,
            db.func.coalesce(Mistake.wrong_count, 1).label("wrong_count"),
            Mistake.updated_at.label("t"),
        ).join(
            Question, Question.id == Mistake.question_id
        ).join(
            Subject, Subject.id == Question.subject_id
        ).filter(
            Mistake.user_id == int(uid),
            Question.subject_id == int(subject_id),
            db.or_(Subject.is_locked == False, Subject.is_locked.is_(None)),
        ).order_by(
            db.func.coalesce(Mistake.wrong_count, 1).desc(),
            Mistake.updated_at.desc(),
        ).limit(limit_n).all()
    except Exception:
        rows = []

    wrong_ids = [int(r.question_id) for r in (rows or []) if r and r.question_id is not None]
    wrong_recommend_ids = wrong_ids[:wrong_n] if wrong_n else []

    # 错题 top 列表
    wrong_top = []
    if include_wrong and wrong_list_n > 0 and rows:
        top_ids = [int(r.question_id) for r in list(rows[:wrong_list_n]) if r and r.question_id is not None]
        meta_map = _build_meta_map_public(int(subject_id), top_ids)
        row_dicts = [{'question_id': r.question_id, 'wrong_count': r.wrong_count} for r in rows]
        wrong_top = _build_wrong_top(row_dicts, meta_map, wrong_list_n)

    # 相似题
    similar_mode = (request.args.get('similar_mode') or '').strip().lower()
    result = _compute_similar_public(
        conn, int(subject_id), wrong_ids,
        similar_mode=similar_mode, include_similar=include_similar,
        seed_n=seed_n, similar_n=similar_n, per_seed=per_seed, pairs_n=pairs_n,
    )

    return jsonify({
        'status': 'success',
        'data': {
            'source': 'public',
            'subject_id': int(subject_id),
            'subject_name': subject_row.name,
            'logged_in': True,
            'wrong_total': wrong_total,
            'wrong_recommend_ids': wrong_recommend_ids,
            'wrong_top': wrong_top,
            **result,
        },
    })


def _compute_similar_public(
    conn, subject_id: int, wrong_ids: list[int],
    *, similar_mode: str, include_similar: bool,
    seed_n: int, similar_n: int, per_seed: int, pairs_n: int,
) -> dict:
    """计算公共题库的相似题结果"""
    seed_ids: list[int] = []
    similar_pairs_count = 0
    similar_training_ids: list[int] = []
    similar_pairs: list[dict] = []
    similar_mode_out = ''

    if not include_similar:
        return {
            'similar_mode': similar_mode_out,
            'similar_pairs_count': 0,
            'similar_seed_ids': seed_ids,
            'similar_training_ids': similar_training_ids,
            'similar_pairs': similar_pairs,
        }

    if similar_mode in ('wrong', 'mistake', 'mistakes', 'wrong_seed', 'seed'):
        seed_ids = wrong_ids[:seed_n] if seed_n else []
        if seed_ids and similar_n > 0:
            similar_training_ids = find_similar_training_ids_public(
                conn, subject_id,
                seed_ids=seed_ids,
                exclude_ids=set(seed_ids),
                per_seed=per_seed,
                max_total=similar_n,
            )
        similar_mode_out = 'wrong_seed'
    else:
        if similar_n > 0:
            pairs_need = pairs_n if pairs_n > 0 else (max(1, (similar_n + 1) // 2) if similar_n > 0 else 0)
            pairs_need = max(0, min(int(pairs_need or 0), 300))
            similar_training_ids, similar_pairs_count, pairs_raw = find_similar_pairs_public(
                conn, subject_id,
                max_total_ids=similar_n,
                max_pairs=pairs_need,
            )
            display_pairs = list(pairs_raw[:pairs_n]) if (pairs_n > 0 and pairs_raw) else []
            if display_pairs:
                uniq_ids = _collect_pair_unique_ids(display_pairs)
                meta_map = _build_meta_map_public(subject_id, uniq_ids)
                similar_pairs = _build_similar_pairs_display(display_pairs, meta_map)
        similar_mode_out = 'subject_dedupe'

    return {
        'similar_mode': similar_mode_out,
        'similar_pairs_count': int(similar_pairs_count or 0),
        'similar_seed_ids': seed_ids,
        'similar_training_ids': similar_training_ids,
        'similar_pairs': similar_pairs,
    }
