# -*- coding: utf-8 -*-
"""刷题页面路由"""
import json
import math
import random
import re
from flask import Blueprint, render_template, request, session, redirect, url_for
from app.core.utils.database import get_db
from app.core.utils.options_parser import parse_options
from app.modules.quiz.services.study_service import now_bj, dt_to_str

# 子蓝图需要指定template_folder（Flask子蓝图不会自动继承父蓝图的template_folder）
import os
# __file__ 是 app/modules/quiz/routes/pages.py
# 需要向上两级到quiz模块目录：routes -> quiz
module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(module_dir, 'templates')
quiz_pages_bp = Blueprint('quiz_pages', __name__, template_folder=template_dir)


def _parse_positive_int(val, default=10, min_val=1, max_val=200):
    try:
        num = int(val)
        if num < min_val:
            return min_val
        if num > max_val:
            return max_val
        return num
    except Exception:
        return default


def _parse_id_list(val, max_len=200):
    if not val:
        return []
    raw = str(val)
    parts = re.split(r"[^0-9]+", raw)
    out = []
    seen = set()
    for p in parts:
        if not p:
            continue
        try:
            n = int(p)
        except Exception:
            continue
        if n <= 0 or n in seen:
            continue
        seen.add(n)
        out.append(n)
        if len(out) >= max_len:
            break
    return out


def _build_learn_session(rows, target_n):
    target_n = _parse_positive_int(target_n, default=10)
    extra = max(2, min(10, int(math.ceil(target_n * 0.3))))
    session_size = min(len(rows), target_n + extra)

    in_progress = []
    new_items = []
    for r in rows:
        streak = r.get('streak')
        if streak is None:
            new_items.append(r)
        else:
            in_progress.append(r)

    random.shuffle(in_progress)
    random.shuffle(new_items)

    need_in_progress = min(len(in_progress), max(1, int(math.ceil(target_n * 0.6))))
    selected = list(in_progress[:need_in_progress])

    remaining = session_size - len(selected)
    if remaining > 0:
        selected.extend(new_items[:remaining])

    if len(selected) < session_size:
        rest = in_progress[need_in_progress:] + new_items[remaining:]
        random.shuffle(rest)
        selected.extend(rest[:(session_size - len(selected))])

    ids = [int(r['id']) for r in selected]
    streak_map = {int(r['id']): int(r.get('streak') or 0) for r in selected}
    return ids, streak_map


def _split_review_rows(rows):
    weak = []
    strong = []
    for r in rows:
        level = int(r.get('review_level') or 0)
        last_rating = (r.get('last_rating') or '').lower()
        if level <= 1 or last_rating in ('fuzzy', 'unknown'):
            weak.append(r)
        else:
            strong.append(r)
    return weak, strong


def _build_review_session(rows, target_n):
    target_n = _parse_positive_int(target_n, default=10)
    if not rows:
        return []
    weak, strong = _split_review_rows(rows)
    random.shuffle(weak)
    random.shuffle(strong)
    need_weak = min(len(weak), max(1, int(math.ceil(target_n * 0.8))))
    selected = list(weak[:need_weak])
    remaining = target_n - len(selected)
    if remaining > 0:
        selected.extend(strong[:remaining])
    if len(selected) < target_n:
        rest = weak[need_weak:] + strong[remaining:]
        random.shuffle(rest)
        selected.extend(rest[:(target_n - len(selected))])
    return [int(r['question_id']) for r in selected]


def _progress_key_prefix(mode: str) -> str:
    if mode in ('learn', 'review'):
        return 'study_progress'
    return 'quiz_progress'


def _normalize_answer(q):
    try:
        qtype = str(q.get('q_type') or '')
        ans_raw = str(q.get('answer') or '').strip()
        if qtype in ('选择题', '多选题'):
            q['answer'] = ''.join([c for c in ans_raw if c.isalpha()]).upper()
        elif qtype == '判断题':
            v = ans_raw.lower()
            if v in ('对', '正确', 'true', 't', '1', 'yes', 'y'):
                q['answer'] = '正确'
            elif v in ('错', '错误', 'false', 'f', '0', 'no', 'n'):
                q['answer'] = '错误'
    except Exception:
        pass


def _safe_json_load(raw, default):
    if raw is None:
        return default
    if isinstance(raw, (list, dict, bool, int, float)):
        return raw
    s = str(raw).strip()
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


def _apply_pqf_legacy_fields(q: dict, *, scope: str) -> None:
    """把 DB(PQF) 字段转成 quiz 页面历史字段：q_type/content(__)/answer(str)/explanation(str)/options(list)。"""
    from app.core.utils.portable_question_format import portable_question_to_internal

    portable = {
        "id": q.get("id"),
        "type": q.get("type") or "",
        "content": q.get("content") or "",
        "options": _safe_json_load(q.get("options"), []),
        "answer": _safe_json_load(q.get("answer"), []),
        "analysis": q.get("analysis") or "",
        "tags": _safe_json_load(q.get("tags"), []),
        "difficulty": q.get("difficulty") if q.get("difficulty") is not None else 1,
    }
    internal, _errors = portable_question_to_internal(portable, scope=scope)
    q["q_type"] = internal.get("q_type") or ""
    q["content"] = internal.get("content") or ""
    q["options"] = internal.get("options") or []
    q["answer"] = internal.get("answer") or ""
    q["explanation"] = internal.get("explanation") or ""


def _build_public_questions(conn, rows, uid):
    q_ids = [int(r['id']) for r in rows] if rows else []
    fav_set = set()
    mis_set = set()
    if uid and q_ids:
        placeholders = ",".join(["?"] * len(q_ids))
        fav_rows = conn.execute(
            f"SELECT question_id FROM favorites WHERE user_id = ? AND question_id IN ({placeholders})",
            [uid] + q_ids,
        ).fetchall()
        mis_rows = conn.execute(
            f"SELECT question_id FROM mistakes WHERE user_id = ? AND question_id IN ({placeholders})",
            [uid] + q_ids,
        ).fetchall()
        fav_set = {int(r['question_id']) for r in fav_rows}
        mis_set = {int(r['question_id']) for r in mis_rows}

    questions = []
    for row in rows:
        q = dict(row)
        _apply_pqf_legacy_fields(q, scope="question_center")
        q['is_fav'] = 1 if int(q.get('id') or 0) in fav_set else 0
        q['is_mistake'] = 1 if int(q.get('id') or 0) in mis_set else 0

        image_path = q.get('image_path')
        image_path_json = '[]'
        if image_path and isinstance(image_path, str):
            if image_path.strip().startswith('[') and image_path.strip().endswith(']'):
                image_path_json = image_path
            else:
                image_path_json = json.dumps([image_path])
        q['image_path_json'] = image_path_json

        if q.get('options'):
            try:
                q['options'] = parse_options(q['options'])
            except Exception:
                q['options'] = []
        else:
            q['options'] = []

        _normalize_answer(q)
        questions.append(q)
    return questions


def _build_user_bank_questions(conn, rows, uid, bank_id):
    q_ids = [int(r['id']) for r in rows] if rows else []
    fav_set = set()
    mis_set = set()
    if uid and q_ids:
        placeholders = ",".join(["?"] * len(q_ids))
        fav_rows = conn.execute(
            f"SELECT question_id FROM user_bank_favorites WHERE user_id = ? AND question_id IN ({placeholders})",
            [uid] + q_ids,
        ).fetchall()
        mis_rows = conn.execute(
            f"SELECT question_id FROM user_bank_mistakes WHERE user_id = ? AND question_id IN ({placeholders})",
            [uid] + q_ids,
        ).fetchall()
        fav_set = {int(r['question_id']) for r in fav_rows}
        mis_set = {int(r['question_id']) for r in mis_rows}

    questions = []
    for row in rows:
        q = dict(row)
        _apply_pqf_legacy_fields(q, scope="user_bank")
        q['is_fav'] = 1 if int(q.get('id') or 0) in fav_set else 0
        q['is_mistake'] = 1 if int(q.get('id') or 0) in mis_set else 0

        image_path = q.get('image_path')
        image_path_json = '[]'
        if image_path and isinstance(image_path, str):
            if image_path.strip().startswith('[') and image_path.strip().endswith(']'):
                image_path_json = image_path
            else:
                image_path_json = json.dumps([image_path])
        q['image_path_json'] = image_path_json

        if q.get('options'):
            try:
                q['options'] = parse_options(q['options'])
            except Exception:
                q['options'] = []
        else:
            q['options'] = []

        _normalize_answer(q)
        questions.append(q)
    return questions


@quiz_pages_bp.route('/quiz')
def quiz_page():
    """刷题页面"""
    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    mode = request.args.get('mode', 'quiz').lower()
    source = request.args.get('source', '').lower()  # 兼容背题来源（收藏/错题）
    tag = (request.args.get('tag') or '').strip()
    exam_id = request.args.get('exam_id', type=int)
    bank_id = request.args.get('bank_id', type=int)
    limit = request.args.get('limit', type=int)
    learn_n = request.args.get('learn_n', type=int) or request.args.get('group_size', type=int)
    review_n = request.args.get('review_n', type=int) or request.args.get('group_size', type=int)
    review_extra = (request.args.get('review_extra') or '0') == '1'
    custom_ids = _parse_id_list(request.args.get('ids') or request.args.get('question_ids'))
    
    # 获取打乱设置
    shuffle_questions = request.args.get('shuffle_questions', '0') == '1'
    shuffle_options = request.args.get('shuffle_options', '0') == '1'
    
    uid = session.get('user_id') or -1
    if mode in ('learn', 'review') and uid == -1:
        return redirect(url_for('auth.auth_pages.login_page'))
    conn = get_db()

    from app.core.utils.portable_question_format import any_type_to_portable_type

    portable_type_filter = None
    if q_type and str(q_type).strip().lower() != 'all':
        portable_type_filter = any_type_to_portable_type(q_type)

    # ====================================================
    # 个人题库（user_question_banks / user_bank_questions）
    # 复用共有刷题模板：/quiz?bank_id=<id>
    # ====================================================
    if bank_id and mode != 'exam':
        # 个人题库不支持未登录访问
        if uid == -1:
            return redirect(url_for('auth.auth_pages.login_page'))

        from app.modules.user_bank.routes.api import check_bank_access, _load_bank_tag_store

        has_access, _permission, _access_type = check_bank_access(uid, int(bank_id))
        if not has_access:
            return render_template(
                'quiz/quiz.html',
                questions=[],
                mode=mode,
                source=source,
                exam_id=None,
                user_answers_json='{}',
                logged_in=True,
                user_id=uid,
                username=session.get('username'),
                is_admin=bool(session.get('is_admin')),
                is_subject_admin=bool(session.get('is_subject_admin')),
                duration=0,
                submitted=False,
            )


        if custom_ids:
            placeholders = ",".join(["?"] * len(custom_ids))
            rows = conn.execute(
                f"SELECT * FROM user_bank_questions WHERE bank_id = ? AND id IN ({placeholders})",
                [int(bank_id)] + custom_ids,
            ).fetchall()
            q_map = {int(r['id']): r for r in (rows or []) if r and r['id'] is not None}
            ordered_rows = [q_map[i] for i in custom_ids if i in q_map]
            questions = _build_user_bank_questions(conn, ordered_rows, uid, int(bank_id))

            ua_map = {}
            try:
                ua_rows = conn.execute(
                    f"SELECT question_id, user_answer FROM user_bank_answers WHERE user_id = ? AND bank_id = ? AND question_id IN ({placeholders})",
                    [uid, int(bank_id)] + custom_ids,
                ).fetchall()
                ua_map = {int(r['question_id']): (r['user_answer'] or '') for r in (ua_rows or []) if r and r['question_id'] is not None}
            except Exception:
                ua_map = {}

            return render_template(
                'quiz/quiz.html',
                questions=questions,
                mode=mode,
                source=source,
                exam_id=None,
                user_answers_json=ua_map,
                logged_in=True,
                user_id=uid,
                username=session.get('username'),
                is_admin=bool(session.get('is_admin')),
                is_subject_admin=bool(session.get('is_subject_admin')),
                duration=0,
                submitted=False,
            )

        if mode in ('learn', 'review'):
            now_str = dt_to_str(now_bj())
            study_meta = {
                'mode': mode,
                'source': 'user_bank',
                'bank_id': int(bank_id),
                'target_n': _parse_positive_int(learn_n if mode == 'learn' else review_n, default=10),
                'review_extra': bool(review_extra),
                'due_count': 0,
            }

            if mode == 'learn':
                sql = """
                    SELECT q.id, lp.streak
                    FROM user_bank_questions q
                    LEFT JOIN study_learning lp
                      ON lp.user_id = ? AND lp.source = 'user_bank' AND lp.scope_id = ? AND lp.question_id = q.id
                    LEFT JOIN study_review rs
                      ON rs.user_id = ? AND rs.source = 'user_bank' AND rs.scope_id = ? AND rs.question_id = q.id
                    WHERE q.bank_id = ?
                      AND (lp.is_learned IS NULL OR lp.is_learned = 0)
                      AND (rs.is_mastered IS NULL OR rs.is_mastered = 0)
                """
                params = [uid, int(bank_id), uid, int(bank_id), int(bank_id)]
                if q_type != 'all':
                    sql += " AND q.type = ?"
                    params.append(portable_type_filter)
                rows = conn.execute(sql, params).fetchall()
                candidates = [{'id': int(r['id']), 'streak': r['streak']} for r in rows]
                session_ids, streak_map = _build_learn_session(candidates, learn_n)

                if session_ids:
                    placeholders = ",".join(["?"] * len(session_ids))
                    q_rows = conn.execute(
                        f"SELECT * FROM user_bank_questions WHERE id IN ({placeholders})",
                        session_ids,
                    ).fetchall()
                    q_map = {int(r['id']): r for r in q_rows}
                    ordered_rows = [q_map[i] for i in session_ids if i in q_map]
                else:
                    ordered_rows = []

                questions = _build_user_bank_questions(conn, ordered_rows, uid, int(bank_id))
                study_meta['streak_map'] = streak_map
            else:
                due_rows = conn.execute(
                    """
                    SELECT r.question_id, r.review_level, r.last_rating
                    FROM study_review r
                    JOIN user_bank_questions q ON q.id = r.question_id
                    WHERE r.user_id = ? AND r.source = 'user_bank' AND r.scope_id = ?
                      AND r.is_mastered = 0
                      AND r.next_due_at IS NOT NULL
                      AND r.next_due_at <= ?
                    """,
                    (uid, int(bank_id), now_str),
                ).fetchall()

                study_meta['due_count'] = len(due_rows)
                session_ids = _build_review_session([dict(r) for r in due_rows], review_n)

                if review_extra and len(session_ids) < study_meta['target_n']:
                    extra_rows = conn.execute(
                        """
                        SELECT r.question_id, r.review_level, r.last_rating
                        FROM study_review r
                        JOIN user_bank_questions q ON q.id = r.question_id
                        WHERE r.user_id = ? AND r.source = 'user_bank' AND r.scope_id = ?
                          AND r.is_mastered = 0
                          AND (r.next_due_at IS NULL OR r.next_due_at > ?)
                        """,
                        (uid, int(bank_id), now_str),
                    ).fetchall()

                    extra_ids = _build_review_session([dict(r) for r in extra_rows], study_meta['target_n'] - len(session_ids))
                    for qid in extra_ids:
                        if qid not in session_ids:
                            session_ids.append(qid)

                if session_ids:
                    placeholders = ",".join(["?"] * len(session_ids))
                    q_rows = conn.execute(
                        f"SELECT * FROM user_bank_questions WHERE id IN ({placeholders})",
                        session_ids,
                    ).fetchall()
                    q_map = {int(r['id']): r for r in q_rows}
                    ordered_rows = [q_map[i] for i in session_ids if i in q_map]
                else:
                    ordered_rows = []

                questions = _build_user_bank_questions(conn, ordered_rows, uid, int(bank_id))

            return render_template(
                'quiz/quiz.html',
                questions=questions,
                mode=mode,
                source='user_bank',
                exam_id=None,
                user_answers_json='{}',
                logged_in=True,
                user_id=uid,
                username=session.get('username'),
                is_admin=bool(session.get('is_admin')),
                is_subject_admin=bool(session.get('is_subject_admin')),
                duration=0,
                submitted=False,
                study_meta_json=study_meta,
            )

        # tag 过滤：bank_<bank_id>_tags 存储在 user_progress
        tag_question_ids = None
        if tag and str(tag).lower() != 'all':
            try:
                store = _load_bank_tag_store(conn, int(bank_id), uid)
                question_tags = store.get('question_tags', {}) or {}
                tag_question_ids = []
                for q_id, tags in question_tags.items():
                    if not isinstance(tags, list):
                        continue
                    if tag in tags:
                        try:
                            tag_question_ids.append(int(q_id))
                        except Exception:
                            continue
            except Exception:
                tag_question_ids = []

            if not tag_question_ids:
                return render_template(
                    'quiz/quiz.html',
                    questions=[],
                    mode=mode,
                    source=source,
                    exam_id=None,
                    user_answers_json='{}',
                    logged_in=True,
                    user_id=uid,
                    username=session.get('username'),
                    is_admin=bool(session.get('is_admin')),
                    is_subject_admin=bool(session.get('is_subject_admin')),
                    duration=0,
                    submitted=False,
                )

        # scope：复用 source=favorites/mistakes
        sql = "SELECT q.* FROM user_bank_questions q"
        params = []
        if source == 'mistakes':
            sql += " JOIN user_bank_mistakes m ON q.id = m.question_id AND m.user_id = ?"
            params.append(uid)
        elif source == 'favorites':
            sql += " JOIN user_bank_favorites f ON q.id = f.question_id AND f.user_id = ?"
            params.append(uid)

        sql += " WHERE q.bank_id = ?"
        params.append(int(bank_id))

        if q_type != 'all':
            sql += " AND q.type = ?"
            params.append(portable_type_filter)

        if tag_question_ids is not None:
            tag_question_ids = sorted(set(tag_question_ids))
            if len(tag_question_ids) <= 900:
                placeholders = ",".join(["?"] * len(tag_question_ids))
                sql += f" AND q.id IN ({placeholders})"
                params.extend(tag_question_ids)
            else:
                sql += " AND q.id IN ({})".format(",".join(str(i) for i in tag_question_ids))

        if source == 'mistakes':
            sql += " ORDER BY m.wrong_count DESC, m.updated_at DESC"
        elif source == 'favorites':
            sql += " ORDER BY f.created_at DESC"
        else:
            sql += " ORDER BY q.sort_order ASC, q.id ASC"

        rows = conn.execute(sql, params).fetchall()
        if mode == 'fast' and isinstance(limit, int) and limit > 0:
            if len(rows) > limit:
                rows = random.sample(list(rows), limit)
            random.shuffle(rows)
        questions = _build_user_bank_questions(conn, rows, uid, int(bank_id))
        q_ids = [int(q.get('id') or 0) for q in (questions or []) if int(q.get('id') or 0) > 0]

        # 历史答案回显
        ua_map = {}
        if q_ids:
            placeholders = ",".join(["?"] * len(q_ids))
            ua_rows = conn.execute(
                f"SELECT question_id, user_answer FROM user_bank_answers WHERE user_id = ? AND bank_id = ? AND question_id IN ({placeholders})",
                [uid, int(bank_id)] + q_ids,
            ).fetchall()
            ua_map = {int(r['question_id']): (r['user_answer'] or '') for r in ua_rows}

        return render_template(
            'quiz/quiz.html',
            questions=questions,
            mode=mode,
            source=source,
            exam_id=None,
            user_answers_json=ua_map,
            logged_in=True,
            user_id=uid,
            username=session.get('username'),
            is_admin=bool(session.get('is_admin')),
            is_subject_admin=bool(session.get('is_subject_admin')),
            duration=0,
            submitted=False,
        )
    


    if mode in ('learn', 'review'):
        if subject == 'all':
            return render_template(
                'quiz/quiz.html',
                questions=[],
                mode=mode,
                source='public',
                exam_id=None,
                user_answers_json='{}',
                logged_in=bool(uid),
                user_id=uid,
                username=session.get('username'),
                is_admin=bool(session.get('is_admin')),
                is_subject_admin=bool(session.get('is_subject_admin')),
                duration=0,
                submitted=False,
                study_meta_json={'mode': mode, 'source': 'public', 'subject': subject, 'target_n': _parse_positive_int(learn_n if mode == 'learn' else review_n, default=10), 'review_extra': bool(review_extra), 'due_count': 0},
            )

        subject_row = conn.execute('SELECT id FROM subjects WHERE name = ?', (subject,)).fetchone()
        if not subject_row:
            return render_template(
                'quiz/quiz.html',
                questions=[],
                mode=mode,
                source='public',
                exam_id=None,
                user_answers_json='{}',
                logged_in=bool(uid),
                user_id=uid,
                username=session.get('username'),
                is_admin=bool(session.get('is_admin')),
                is_subject_admin=bool(session.get('is_subject_admin')),
                duration=0,
                submitted=False,
                study_meta_json={'mode': mode, 'source': 'public', 'subject': subject, 'target_n': _parse_positive_int(learn_n if mode == 'learn' else review_n, default=10), 'review_extra': bool(review_extra), 'due_count': 0},
            )

        subject_id = int(subject_row['id'])
        now_str = dt_to_str(now_bj())
        study_meta = {
            'mode': mode,
            'source': 'public',
            'subject': subject,
            'target_n': _parse_positive_int(learn_n if mode == 'learn' else review_n, default=10),
            'review_extra': bool(review_extra),
            'due_count': 0,
        }

        if mode == 'learn':
            sql = """
                SELECT q.id, lp.streak
                FROM questions q
                LEFT JOIN study_learning lp
                  ON lp.user_id = ? AND lp.source = 'public' AND lp.scope_id = ? AND lp.question_id = q.id
                LEFT JOIN study_review rs
                  ON rs.user_id = ? AND rs.source = 'public' AND rs.scope_id = ? AND rs.question_id = q.id
                WHERE q.subject_id = ?
                  AND (lp.is_learned IS NULL OR lp.is_learned = 0)
                  AND (rs.is_mastered IS NULL OR rs.is_mastered = 0)
            """
            params = [uid, subject_id, uid, subject_id, subject_id]
            if q_type != 'all':
                sql += " AND q.type = ?"
                params.append(portable_type_filter)
            rows = conn.execute(sql, params).fetchall()
            candidates = [{'id': int(r['id']), 'streak': r['streak']} for r in rows]
            session_ids, streak_map = _build_learn_session(candidates, learn_n)

            if session_ids:
                placeholders = ",".join(["?"] * len(session_ids))
                q_rows = conn.execute(
                    f"SELECT q.*, s.name as subject FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id WHERE q.id IN ({placeholders})",
                    session_ids,
                ).fetchall()
                q_map = {int(r['id']): r for r in q_rows}
                ordered_rows = [q_map[i] for i in session_ids if i in q_map]
            else:
                ordered_rows = []

            questions = _build_public_questions(conn, ordered_rows, uid)
            study_meta['streak_map'] = streak_map
        else:
            sql = """
                SELECT r.question_id, r.review_level, r.last_rating
                FROM study_review r
                JOIN questions q ON q.id = r.question_id
                WHERE r.user_id = ? AND r.source = 'public' AND r.scope_id = ?
                  AND r.is_mastered = 0
                  AND r.next_due_at IS NOT NULL
                  AND r.next_due_at <= ?
            """
            params = [uid, subject_id, now_str]
            if q_type != 'all':
                sql += " AND q.type = ?"
                params.append(portable_type_filter)
            due_rows = conn.execute(sql, params).fetchall()

            study_meta['due_count'] = len(due_rows)
            session_ids = _build_review_session([dict(r) for r in due_rows], review_n)

            if review_extra and len(session_ids) < study_meta['target_n']:
                sql = """
                    SELECT r.question_id, r.review_level, r.last_rating
                    FROM study_review r
                    JOIN questions q ON q.id = r.question_id
                    WHERE r.user_id = ? AND r.source = 'public' AND r.scope_id = ?
                      AND r.is_mastered = 0
                      AND (r.next_due_at IS NULL OR r.next_due_at > ?)
                """
                params = [uid, subject_id, now_str]
                if q_type != 'all':
                    sql += " AND q.type = ?"
                    params.append(portable_type_filter)
                extra_rows = conn.execute(sql, params).fetchall()

                extra_ids = _build_review_session([dict(r) for r in extra_rows], study_meta['target_n'] - len(session_ids))
                for qid in extra_ids:
                    if qid not in session_ids:
                        session_ids.append(qid)

            if session_ids:
                placeholders = ",".join(["?"] * len(session_ids))
                q_rows = conn.execute(
                    f"SELECT q.*, s.name as subject FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id WHERE q.id IN ({placeholders})",
                    session_ids,
                ).fetchall()
                q_map = {int(r['id']): r for r in q_rows}
                ordered_rows = [q_map[i] for i in session_ids if i in q_map]
            else:
                ordered_rows = []

            questions = _build_public_questions(conn, ordered_rows, uid)

        return render_template(
            'quiz/quiz.html',
            questions=questions,
            mode=mode,
            source='public',
            exam_id=None,
            user_answers_json='{}',
            logged_in=bool(uid),
            user_id=uid,
            username=session.get('username'),
            is_admin=bool(session.get('is_admin')),
            is_subject_admin=bool(session.get('is_subject_admin')),
            duration=0,
            submitted=False,
            study_meta_json=study_meta,
        )
    # 获取用户可访问的科目ID列表（用于权限过滤）
    accessible_subject_ids = None
    if uid and uid != -1 and mode != 'exam':
        from app.core.utils.subject_permissions import get_user_accessible_subjects
        accessible_subject_ids = get_user_accessible_subjects(uid)
        # 如果没有可访问的科目，直接返回空题目列表
        if not accessible_subject_ids:
            return render_template('quiz/quiz.html',
                                 questions=[],
                                 mode=mode,
                                 source=source,
                                 exam_id=exam_id,
                                 user_answers_json='{}',
                                 logged_in=bool(uid),
                                 user_id=uid,
                                 username=session.get('username'),
                                 is_admin=bool(session.get('is_admin')),
                                 is_subject_admin=bool(session.get('is_subject_admin')),
                                 duration=0,
                                 submitted=False)
    
    if custom_ids and mode != 'exam':
        placeholders = ",".join(["?"] * len(custom_ids))
        sql = f"""
            SELECT q.*, s.name as subject
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE q.id IN ({placeholders}) AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        params = list(custom_ids)
        if accessible_subject_ids is not None:
            placeholders2 = ','.join(['?'] * len(accessible_subject_ids))
            sql += f" AND q.subject_id IN ({placeholders2})"
            params.extend(accessible_subject_ids)

        rows = conn.execute(sql, params).fetchall()
        q_map = {int(r['id']): r for r in (rows or []) if r and r['id'] is not None}
        ordered_rows = [q_map[i] for i in custom_ids if i in q_map]
        questions = _build_public_questions(conn, ordered_rows, uid if uid != -1 else None)
        question_ids = [int(q['id']) for q in (questions or []) if q and q.get('id') is not None]

        user_answers_json = {}
        real_uid = session.get('user_id')
        if real_uid and question_ids:
            try:
                placeholders3 = ','.join(['?'] * len(question_ids))
                answer_rows = conn.execute(
                    f'''SELECT question_id, is_correct 
                       FROM user_answers 
                       WHERE user_id = ? AND question_id IN ({placeholders3})
                       ORDER BY created_at DESC''',
                    [real_uid] + question_ids
                ).fetchall()

                user_answers = {}
                seen_questions = set()
                for row in answer_rows:
                    q_id = row['question_id']
                    if q_id not in seen_questions:
                        user_answers[str(q_id)] = {
                            'is_correct': bool(row['is_correct'])
                        }
                        seen_questions.add(q_id)

                user_answers_json = user_answers
            except Exception:
                user_answers_json = {}

        return render_template(
            'quiz/quiz.html',
            questions=questions,
            mode=mode,
            source=source,
            exam_id=None,
            user_answers_json=user_answers_json,
            logged_in=bool(real_uid),
            user_id=real_uid,
            username=session.get('username'),
            is_admin=bool(session.get('is_admin')),
            is_subject_admin=bool(session.get('is_subject_admin')),
            duration=0,
            submitted=False,
        )

    exam_meta = None
    exam_source = 'public'
    if mode == 'exam' and exam_id:
        exam_meta = conn.execute('SELECT * FROM exams WHERE id=?', (exam_id,)).fetchone()
        if not exam_meta:
            return "考试不存在或无权限", 404
        if exam_meta['user_id'] != uid and not session.get('is_admin'):
            return "考试不存在或无权限", 403

        try:
            cfg = json.loads(exam_meta['config_json'] or '{}')
            if not isinstance(cfg, dict):
                cfg = {}
        except Exception:
            cfg = {}

        exam_source = (cfg.get('source') or 'public').strip().lower()
        if exam_source not in ('public', 'user_bank'):
            exam_source = 'public'

    # 根据不同模式获取题目
    target = source if source in ('favorites', 'mistakes') else mode
    if mode == 'exam' and exam_id:
        # 考试模式：获取考试题目
        if exam_source == 'user_bank':
            sql = """
                SELECT q.*, ? as subject, eq.user_answer, eq.score_val,
                       CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                       CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
                FROM exam_questions eq
                JOIN user_bank_questions q ON eq.question_id = q.id
                LEFT JOIN user_bank_favorites f ON q.id = f.question_id AND f.user_id = ?
                LEFT JOIN user_bank_mistakes m ON q.id = m.question_id AND m.user_id = ?
                WHERE eq.exam_id = ?
                ORDER BY eq.order_index
            """
            rows = conn.execute(sql, (exam_meta['subject'] or '', uid, uid, exam_id)).fetchall()
        else:
            sql = """
                SELECT q.*, s.name as subject, eq.user_answer, eq.score_val,
                       CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                       CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
                FROM exam_questions eq
                JOIN questions q ON eq.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
                LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
                WHERE eq.exam_id = ?
                ORDER BY eq.order_index
            """
            rows = conn.execute(sql, (uid, uid, exam_id)).fetchall()
    elif target == 'favorites':
        # 收藏模式（过滤掉锁定科目和被限制科目的题目）
        sql = """
            SELECT q.*, s.name as subject,
                   1 as is_fav,
                   CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
            FROM favorites f
            JOIN questions q ON f.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
            WHERE f.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        params = [uid, uid]
        
        # 添加权限过滤
        if accessible_subject_ids is not None:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(accessible_subject_ids)
        
        if subject != 'all':
            sql += " AND s.name = ?"
            params.append(subject)
        
        if q_type != 'all':
            sql += " AND q.type = ?"
            params.append(portable_type_filter)
        
        rows = conn.execute(sql, params).fetchall()

    elif target == 'mistakes':
        # 错题模式（过滤掉锁定科目和被限制科目的题目）
        sql = """
            SELECT q.*, s.name as subject,
                   CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                   1 as is_mistake
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
            WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        params = [uid, uid]
        
        # 添加权限过滤
        if accessible_subject_ids is not None:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(accessible_subject_ids)
        
        if subject != 'all':
            sql += " AND s.name = ?"
            params.append(subject)
        
        if q_type != 'all':
            sql += " AND q.type = ?"
            params.append(portable_type_filter)
        
        rows = conn.execute(sql, params).fetchall()
    else:
        # 普通刷题/背题模式（过滤掉锁定科目和被限制科目的题目）
        sql = """
            SELECT q.*, s.name as subject,
                   CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                   CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
            LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
            WHERE (s.is_locked=0 OR s.is_locked IS NULL)
        """
        params = [uid, uid]
        
        # 添加权限过滤
        if accessible_subject_ids is not None:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(accessible_subject_ids)
        elif uid == -1:
            # 未登录用户：返回空结果
            sql += " AND 1=0"
        
        if subject != 'all':
            sql += " AND s.name = ?"
            params.append(subject)
        
        if q_type != 'all':
            sql += " AND q.type = ?"
            params.append(portable_type_filter)
        
        rows = conn.execute(sql, params).fetchall()

    # 标签筛选（仅对当前用户生效）
    if tag and str(tag).lower() != 'all' and uid and uid != -1 and mode != 'exam':
        from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
        tag_ids = get_question_ids_by_tag(conn, uid, tag)
        if not tag_ids:
            rows = []
        else:
            rows = [r for r in rows if int(r['id']) in tag_ids]
    


    if mode == 'fast' and isinstance(limit, int) and limit > 0:
        if len(rows) > limit:
            rows = random.sample(list(rows), limit)
        random.shuffle(rows)
    # 读取已保存的做题顺序（如果是打乱题目模式且已保存）
    saved_order = None
    if shuffle_questions and mode != 'exam' and uid != -1:
        # 生成进度key，与前端 progressKey 保持一致
        data_scope = target if target in ('favorites', 'mistakes') else 'all'
        rk_part = None
        if mode == 'reinforce':
            rk_raw = (request.args.get('rk') or '').strip().lower()
            if rk_raw in ('wrong', 'similar'):
                rk_part = f"rk{rk_raw}"
        key_parts = [
            f"{_progress_key_prefix(mode)}_{uid}",
            mode,
            subject,
            q_type,
            data_scope,
            f"tag{tag}" if tag and str(tag).lower() != 'all' else None,
            rk_part,
            f"q{1 if shuffle_questions else 0}",
            f"o{1 if shuffle_options else 0}"
        ]
        p_key = "_".join([p for p in key_parts if p])
        try:
            saved = conn.execute('SELECT data FROM user_progress WHERE user_id=? AND p_key=?', (uid, p_key)).fetchone()
            if saved and saved['data']:
                saved_json = json.loads(saved['data'])
                if isinstance(saved_json, dict) and isinstance(saved_json.get('order'), list):
                    saved_order = saved_json['order']
        except Exception:
            saved_order = None

    # 处理题目数据
    questions = []
    question_ids = []

    pqf_scope = "question_center"
    if mode == "exam" and exam_source == "user_bank":
        pqf_scope = "user_bank"
    for row in rows:
        q = dict(row)
        _apply_pqf_legacy_fields(q, scope=pqf_scope)
        image_path = q.get('image_path')
        image_path_json = '[]'
        if image_path and isinstance(image_path, str):
            # Check if it's already a JSON array string
            if image_path.strip().startswith('[') and image_path.strip().endswith(']'):
                image_path_json = image_path
            else:
                # It's a single path string, wrap it in an array
                image_path_json = json.dumps([image_path])
        q['image_path_json'] = image_path_json

        if q.get('options'):
            try:
                # 统一 options 解析（兼容有/无 A/B 前缀、数字列表、结构化等）
                q['options'] = parse_options(q['options'])

                # 打乱选项顺序（使用确定性随机，确保同一用户同一题目的选项顺序一致）
                if shuffle_options and q['options'] and q.get('q_type') in ('选择题', '多选题'):
                    # 1. 保存原始正确答案的文本
                    orig_answer_keys = str(q.get('answer') or '')
                    correct_texts = []
                    options_map = {opt['key']: opt['value'] for opt in q['options']}
                    for key in orig_answer_keys:
                        if key in options_map:
                            correct_texts.append(options_map[key])
                    
                    # 2. 使用确定性随机打乱选项
                    # 种子 = 用户ID + 题目ID，确保同一用户同一题目的选项顺序永远一致
                    shuffle_seed = (uid if uid != -1 else 0) * 1000000 + q['id']
                    rng = random.Random(shuffle_seed)
                    rng.shuffle(q['options'])
                    
                    # 3. 根据打乱后的顺序，重新分配 A,B,C,D 并找到新答案
                    abcd = 'ABCD'
                    new_answer_keys = []
                    for i, option in enumerate(q['options']):
                        if i < len(abcd):
                            option['key'] = abcd[i]  # 重新分配key
                            if option['value'] in correct_texts:
                                new_answer_keys.append(option['key'])
                    
                    # 4. 更新答案
                    q['answer'] = ''.join(sorted(new_answer_keys))
            except Exception:
                q['options'] = []
        else:
            q['options'] = []

        _normalize_answer(q)
        questions.append(q)
        question_ids.append(q['id'])
    
    # 打乱题目顺序后，生成最终的题目ID列表，用于传递给前端
    question_ids_for_template = [q['id'] for q in questions]

    # 打乱题目顺序(考试模式除外,考试模式需要保持order_index顺序)
    if shuffle_questions and mode != 'exam':
        if saved_order:
            # 如果有已保存的顺序，则按此顺序排序
            q_map = {q['id']: q for q in questions}
            ordered_questions = []
            for qid in saved_order:
                if qid in q_map:
                    ordered_questions.append(q_map.pop(qid))
            # 追加剩余的题目（如果有新增题目）
            if q_map:
                ordered_questions.extend(q_map.values())
            questions = ordered_questions
        else:
            # 否则，随机打乱并保存新的顺序
            random.shuffle(questions)
            if uid != -1:
                new_order = [q['id'] for q in questions]
                # 生成进度key
                data_scope = target if target in ('favorites', 'mistakes') else 'all'
                rk_part = None
                if mode == 'reinforce':
                    rk_raw = (request.args.get('rk') or '').strip().lower()
                    if rk_raw in ('wrong', 'similar'):
                        rk_part = f"rk{rk_raw}"
                key_parts = [
                    f"{_progress_key_prefix(mode)}_{uid}",
                    mode,
                    subject,
                    q_type,
                    data_scope,
                    f"tag{tag}" if tag and str(tag).lower() != 'all' else None,
                    rk_part,
                    f"q{1 if shuffle_questions else 0}",
                    f"o{1 if shuffle_options else 0}"
                ]
                p_key = "_".join([p for p in key_parts if p])
                # 尝试获取现有进度数据
                try:
                    existing_data = conn.execute('SELECT data FROM user_progress WHERE user_id=? AND p_key=?', (uid, p_key)).fetchone()
                    if existing_data and existing_data['data']:
                        progress_json = json.loads(existing_data['data'])
                    else:
                        progress_json = {}
                except Exception:
                    progress_json = {}
                # 更新顺序并写回数据库
                progress_json['order'] = new_order
                progress_json['timestamp'] = progress_json.get('timestamp', 0) # 保留原有时间戳
                data_to_save = json.dumps(progress_json, ensure_ascii=False)
                conn.execute(
                    "INSERT INTO user_progress (user_id, p_key, data) VALUES (?, ?, ?) ON CONFLICT(user_id, p_key) DO UPDATE SET data = excluded.data",
                    (uid, p_key, data_to_save)
                )
                conn.commit()
    
    # 获取用户的答题记录（用于恢复答题状态）
    user_answers_json = {}
    uid = session.get('user_id')

    # 考试模式：从 exam_questions 表获取用户答案
    if mode == 'exam' and exam_id:
        user_answers = {}
        for q in questions:
            if q.get('user_answer'):
                user_answers[str(q['id'])] = q['user_answer']
        user_answers_json = user_answers
    # 其他模式：从 user_answers 表获取答题记录
    elif uid and question_ids:
        try:
            # 获取用户对这些题目的最新答题记录
            placeholders = ','.join(['?'] * len(question_ids))
            answer_rows = conn.execute(
                f'''SELECT question_id, is_correct
                   FROM user_answers
                   WHERE user_id = ? AND question_id IN ({placeholders})
                   ORDER BY created_at DESC''',
                [uid] + question_ids
            ).fetchall()

            # 构建答题记录字典（每道题只保留最新的一条记录）
            user_answers = {}
            seen_questions = set()
            for row in answer_rows:
                q_id = row['question_id']
                if q_id not in seen_questions:
                    user_answers[str(q_id)] = {
                        'is_correct': bool(row['is_correct'])
                    }
                    seen_questions.add(q_id)

            user_answers_json = user_answers
        except Exception as e:
            # 如果出错，使用空字典
            user_answers_json = {}

    # 考试模式：获取考试信息(时长、状态等)
    duration = 0
    submitted = False
    if mode == 'exam' and exam_id:
        if exam_meta:
            duration = exam_meta['duration_minutes']
            submitted = (exam_meta['status'] == 'submitted')
        else:
            exam_row = conn.execute('SELECT duration_minutes, status FROM exams WHERE id=?', (exam_id,)).fetchone()
            if exam_row:
                duration = exam_row['duration_minutes']
                submitted = (exam_row['status'] == 'submitted')
    
    return render_template('quiz/quiz.html',
                         questions=questions,
                         mode=mode,
                         source=source,
                         exam_id=exam_id,
                         user_answers_json=user_answers_json,
                         logged_in=bool(uid),
                         user_id=uid,
                         username=session.get('username'),
                         is_admin=bool(session.get('is_admin')),
                         is_subject_admin=bool(session.get('is_subject_admin')),
                         duration=duration,
                         submitted=submitted)


@quiz_pages_bp.route('/quiz/settlement')
def quiz_settlement_page():
    """刷题/背题/加强结算页（前端使用本地结算数据渲染）"""
    return render_template('quiz/quiz_settlement_v2.html')
