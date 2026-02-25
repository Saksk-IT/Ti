# -*- coding: utf-8 -*-
"""刷题页面路由"""
import json
from app.core.utils.json_helpers import safe_json_load as _safe_json_load
import math
import random
import re
from flask import Blueprint, render_template, request, session, redirect, url_for
from sqlalchemy import text
from app.core.extensions import db
from app.core.utils.options_parser import parse_options
from app.modules.quiz.services.study_service import now_bj, dt_to_str
from app.models.quiz import Favorite, Mistake, UserAnswer, UserProgress
from app.models.subject import Subject, Question
from app.models.user_bank import (
    UserBankQuestion, UserBankFavorite, UserBankMistake, UserBankAnswer,
)
from app.models.study import StudyLearning, StudyReview
from app.models.exam import Exam, ExamQuestion

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


def _apply_pqf_legacy_fields(q: dict, *, scope: str) -> None:
    """把 DB(PQF) 字段转成 quiz 页面历史字段。"""
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


def _build_public_questions(rows, uid):
    q_ids = [int(r['id']) for r in rows] if rows else []
    fav_set = set()
    mis_set = set()
    if uid and q_ids:
        fav_rows = Favorite.query.filter(
            Favorite.user_id == uid,
            Favorite.question_id.in_(q_ids),
        ).all()
        mis_rows = Mistake.query.filter(
            Mistake.user_id == uid,
            Mistake.question_id.in_(q_ids),
        ).all()
        fav_set = {int(r.question_id) for r in fav_rows}
        mis_set = {int(r.question_id) for r in mis_rows}

    questions = []
    for row in rows:
        q = dict(row) if not isinstance(row, dict) else row
        _apply_pqf_legacy_fields(q, scope='question_center')
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


def _build_user_bank_questions(rows, uid, bank_id):
    q_ids = [int(r['id']) for r in rows] if rows else []
    fav_set = set()
    mis_set = set()
    if uid and q_ids:
        fav_rows = UserBankFavorite.query.filter(
            UserBankFavorite.user_id == uid,
            UserBankFavorite.question_id.in_(q_ids),
        ).all()
        mis_rows = UserBankMistake.query.filter(
            UserBankMistake.user_id == uid,
            UserBankMistake.question_id.in_(q_ids),
        ).all()
        fav_set = {int(r.question_id) for r in fav_rows}
        mis_set = {int(r.question_id) for r in mis_rows}

    questions = []
    for row in rows:
        q = dict(row) if not isinstance(row, dict) else row
        _apply_pqf_legacy_fields(q, scope='user_bank')
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


def _orm_to_dict(obj) -> dict:
    """Convert an ORM model instance to a dict (column values only)."""
    if isinstance(obj, dict):
        return obj
    try:
        return {c.key: getattr(obj, c.key) for c in obj.__class__.__mapper__.column_attrs}
    except Exception:
        return dict(obj) if hasattr(obj, "__iter__") else {}


def _row_to_dict(row) -> dict:
    """Convert a SQLAlchemy Row/RowMapping to dict."""
    if isinstance(row, dict):
        return row
    try:
        return dict(row._mapping)
    except Exception:
        pass
    try:
        return {c.key: getattr(row, c.key) for c in row.__class__.__mapper__.column_attrs}
    except Exception:
        return {}


@quiz_pages_bp.route('/quiz')
def quiz_page():
    """刷题页面"""
    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    mode = request.args.get('mode', 'quiz').lower()
    source = request.args.get('source', '').lower()
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

    from app.core.utils.portable_question_format import any_type_to_portable_type

    portable_type_filter = None
    if q_type and str(q_type).strip().lower() != 'all':
        portable_type_filter = any_type_to_portable_type(q_type)

    # ====================================================
    # 个人题库（user_question_banks / user_bank_questions）
    # 复用共有刷题模板：/quiz?bank_id=<id>
    # ====================================================
    if bank_id and mode != 'exam':
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
            q_objs = UserBankQuestion.query.filter(
                UserBankQuestion.bank_id == int(bank_id),
                UserBankQuestion.id.in_(custom_ids),
            ).all()
            q_map = {obj.id: _orm_to_dict(obj) for obj in (q_objs or [])}
            ordered_rows = [q_map[i] for i in custom_ids if i in q_map]
            questions = _build_user_bank_questions(ordered_rows, uid, int(bank_id))

            ua_map = {}
            try:
                ua_rows = UserBankAnswer.query.filter(
                    UserBankAnswer.user_id == uid,
                    UserBankAnswer.bank_id == int(bank_id),
                    UserBankAnswer.question_id.in_(custom_ids),
                ).all()
                ua_map = {int(r.question_id): (r.user_answer or "") for r in (ua_rows or [])}
            except Exception:
                ua_map = {}

            return render_template(
                "quiz/quiz.html",
                questions=questions,
                mode=mode,
                source=source,
                exam_id=None,
                user_answers_json=ua_map,
                logged_in=True,
                user_id=uid,
                username=session.get("username"),
                is_admin=bool(session.get("is_admin")),
                is_subject_admin=bool(session.get("is_subject_admin")),
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
                q_query = db.session.query(
                    UserBankQuestion.id,
                    StudyLearning.streak,
                ).select_from(UserBankQuestion).outerjoin(
                    StudyLearning,
                    db.and_(StudyLearning.user_id == uid, StudyLearning.source == 'user_bank',
                            StudyLearning.scope_id == int(bank_id), StudyLearning.question_id == UserBankQuestion.id)
                ).outerjoin(
                    StudyReview,
                    db.and_(StudyReview.user_id == uid, StudyReview.source == 'user_bank',
                            StudyReview.scope_id == int(bank_id), StudyReview.question_id == UserBankQuestion.id)
                ).filter(
                    UserBankQuestion.bank_id == int(bank_id),
                    db.or_(StudyLearning.is_learned.is_(None), StudyLearning.is_learned == False),
                    db.or_(StudyReview.is_mastered.is_(None), StudyReview.is_mastered == False),
                )
                if q_type != 'all':
                    q_query = q_query.filter(UserBankQuestion.type == portable_type_filter)
                rows = q_query.all()
                candidates = [{'id': int(r.id), 'streak': r.streak} for r in rows]
                session_ids, streak_map = _build_learn_session(candidates, learn_n)

                if session_ids:
                    q_objs = UserBankQuestion.query.filter(UserBankQuestion.id.in_(session_ids)).all()
                    q_map = {obj.id: _orm_to_dict(obj) for obj in q_objs}
                    ordered_rows = [q_map[i] for i in session_ids if i in q_map]
                else:
                    ordered_rows = []

                questions = _build_user_bank_questions(ordered_rows, uid, int(bank_id))
                study_meta['streak_map'] = streak_map
            else:
                due_rows = db.session.query(
                    StudyReview.question_id,
                    StudyReview.review_level,
                    StudyReview.last_rating,
                ).join(
                    UserBankQuestion, UserBankQuestion.id == StudyReview.question_id
                ).filter(
                    StudyReview.user_id == uid, StudyReview.source == 'user_bank',
                    StudyReview.scope_id == int(bank_id),
                    StudyReview.is_mastered == False,
                    StudyReview.next_due_at.isnot(None),
                    StudyReview.next_due_at <= now_str,
                ).all()

                study_meta['due_count'] = len(due_rows)
                session_ids = _build_review_session(
                    [{'question_id': r.question_id, 'review_level': r.review_level, 'last_rating': r.last_rating} for r in due_rows], review_n)

                if review_extra and len(session_ids) < study_meta['target_n']:
                    extra_rows = db.session.query(
                        StudyReview.question_id,
                        StudyReview.review_level,
                        StudyReview.last_rating,
                    ).join(
                        UserBankQuestion, UserBankQuestion.id == StudyReview.question_id
                    ).filter(
                        StudyReview.user_id == uid, StudyReview.source == 'user_bank',
                        StudyReview.scope_id == int(bank_id),
                        StudyReview.is_mastered == False,
                        db.or_(StudyReview.next_due_at.is_(None), StudyReview.next_due_at > now_str),
                    ).all()

                    extra_ids = _build_review_session(
                        [{'question_id': r.question_id, 'review_level': r.review_level, 'last_rating': r.last_rating} for r in extra_rows],
                        study_meta['target_n'] - len(session_ids))
                    for qid in extra_ids:
                        if qid not in session_ids:
                            session_ids.append(qid)

                if session_ids:
                    q_objs = UserBankQuestion.query.filter(UserBankQuestion.id.in_(session_ids)).all()
                    q_map = {obj.id: _orm_to_dict(obj) for obj in q_objs}
                    ordered_rows = [q_map[i] for i in session_ids if i in q_map]
                else:
                    ordered_rows = []

                questions = _build_user_bank_questions(ordered_rows, uid, int(bank_id))

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
                conn = db.session.connection()
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
        base_q = UserBankQuestion.query.filter(UserBankQuestion.bank_id == int(bank_id))

        if source == 'mistakes':
            base_q = base_q.join(UserBankMistake, db.and_(
                UserBankQuestion.id == UserBankMistake.question_id,
                UserBankMistake.user_id == uid,
            ))
        elif source == 'favorites':
            base_q = base_q.join(UserBankFavorite, db.and_(
                UserBankQuestion.id == UserBankFavorite.question_id,
                UserBankFavorite.user_id == uid,
            ))

        if q_type != 'all':
            base_q = base_q.filter(UserBankQuestion.type == portable_type_filter)

        if tag_question_ids is not None:
            base_q = base_q.filter(UserBankQuestion.id.in_(sorted(set(tag_question_ids))))

        if source == 'mistakes':
            base_q = base_q.order_by(UserBankMistake.wrong_count.desc(), UserBankMistake.updated_at.desc())
        elif source == 'favorites':
            base_q = base_q.order_by(UserBankFavorite.created_at.desc())
        else:
            base_q = base_q.order_by(UserBankQuestion.sort_order.asc(), UserBankQuestion.id.asc())

        q_objs = base_q.all()
        rows = [_orm_to_dict(obj) for obj in q_objs]
        if mode == 'fast' and isinstance(limit, int) and limit > 0:
            if len(rows) > limit:
                rows = random.sample(rows, limit)
            random.shuffle(rows)
        questions = _build_user_bank_questions(rows, uid, int(bank_id))
        q_ids = [int(q.get('id') or 0) for q in (questions or []) if int(q.get('id') or 0) > 0]

        # 历史答案回显
        ua_map = {}
        if q_ids:
            ua_rows = UserBankAnswer.query.filter(
                UserBankAnswer.user_id == uid,
                UserBankAnswer.bank_id == int(bank_id),
                UserBankAnswer.question_id.in_(q_ids),
            ).all()
            ua_map = {int(r.question_id): (r.user_answer or '') for r in ua_rows}

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

        subject_row = Subject.query.filter_by(name=subject).first()
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

        subject_id = subject_row.id
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
            q_query = db.session.query(
                Question.id,
                StudyLearning.streak,
            ).select_from(Question).outerjoin(
                StudyLearning,
                db.and_(StudyLearning.user_id == uid, StudyLearning.source == 'public',
                        StudyLearning.scope_id == subject_id, StudyLearning.question_id == Question.id)
            ).outerjoin(
                StudyReview,
                db.and_(StudyReview.user_id == uid, StudyReview.source == 'public',
                        StudyReview.scope_id == subject_id, StudyReview.question_id == Question.id)
            ).filter(
                Question.subject_id == subject_id,
                db.or_(StudyLearning.is_learned.is_(None), StudyLearning.is_learned == False),
                db.or_(StudyReview.is_mastered.is_(None), StudyReview.is_mastered == False),
            )
            if q_type != 'all':
                q_query = q_query.filter(Question.type == portable_type_filter)
            rows = q_query.all()
            candidates = [{'id': int(r.id), 'streak': r.streak} for r in rows]
            session_ids, streak_map = _build_learn_session(candidates, learn_n)

            if session_ids:
                q_objs = db.session.query(Question, Subject.name.label('subject_name')).outerjoin(
                    Subject, Question.subject_id == Subject.id
                ).filter(Question.id.in_(session_ids)).all()
                q_map = {}
                for qobj, sname in q_objs:
                    d = _orm_to_dict(qobj)
                    d['subject'] = sname
                    q_map[qobj.id] = d
                ordered_rows = [q_map[i] for i in session_ids if i in q_map]
            else:
                ordered_rows = []

            questions = _build_public_questions(ordered_rows, uid)
            study_meta['streak_map'] = streak_map
        else:
            q_filter = db.session.query(
                StudyReview.question_id,
                StudyReview.review_level,
                StudyReview.last_rating,
            ).join(
                Question, Question.id == StudyReview.question_id
            ).filter(
                StudyReview.user_id == uid, StudyReview.source == 'public',
                StudyReview.scope_id == subject_id,
                StudyReview.is_mastered == False,
                StudyReview.next_due_at.isnot(None),
                StudyReview.next_due_at <= now_str,
            )
            if q_type != 'all':
                q_filter = q_filter.filter(Question.type == portable_type_filter)
            due_rows = q_filter.all()

            study_meta['due_count'] = len(due_rows)
            session_ids = _build_review_session(
                [{'question_id': r.question_id, 'review_level': r.review_level, 'last_rating': r.last_rating} for r in due_rows], review_n)

            if review_extra and len(session_ids) < study_meta['target_n']:
                extra_q = db.session.query(
                    StudyReview.question_id,
                    StudyReview.review_level,
                    StudyReview.last_rating,
                ).join(
                    Question, Question.id == StudyReview.question_id
                ).filter(
                    StudyReview.user_id == uid, StudyReview.source == 'public',
                    StudyReview.scope_id == subject_id,
                    StudyReview.is_mastered == False,
                    db.or_(StudyReview.next_due_at.is_(None), StudyReview.next_due_at > now_str),
                )
                if q_type != 'all':
                    extra_q = extra_q.filter(Question.type == portable_type_filter)
                extra_rows = extra_q.all()

                extra_ids = _build_review_session(
                    [{'question_id': r.question_id, 'review_level': r.review_level, 'last_rating': r.last_rating} for r in extra_rows],
                    study_meta['target_n'] - len(session_ids))
                for qid in extra_ids:
                    if qid not in session_ids:
                        session_ids.append(qid)

            if session_ids:
                q_objs = db.session.query(Question, Subject.name.label('subject_name')).outerjoin(
                    Subject, Question.subject_id == Subject.id
                ).filter(Question.id.in_(session_ids)).all()
                q_map = {}
                for qobj, sname in q_objs:
                    d = _orm_to_dict(qobj)
                    d['subject'] = sname
                    q_map[qobj.id] = d
                ordered_rows = [q_map[i] for i in session_ids if i in q_map]
            else:
                ordered_rows = []

            questions = _build_public_questions(ordered_rows, uid)

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
        q_query = db.session.query(Question, Subject.name.label('subject_name')).outerjoin(
            Subject, Question.subject_id == Subject.id
        ).filter(
            Question.id.in_(custom_ids),
            db.or_(Subject.is_locked == False, Subject.is_locked.is_(None)),
        )
        if accessible_subject_ids is not None:
            q_query = q_query.filter(Question.subject_id.in_(accessible_subject_ids))

        result_rows = q_query.all()
        q_map = {}
        for qobj, sname in result_rows:
            d = _orm_to_dict(qobj)
            d['subject'] = sname
            q_map[qobj.id] = d
        ordered_rows = [q_map[i] for i in custom_ids if i in q_map]
        questions = _build_public_questions(ordered_rows, uid if uid != -1 else None)
        question_ids = [int(q['id']) for q in (questions or []) if q and q.get('id') is not None]

        user_answers_json = {}
        real_uid = session.get('user_id')
        if real_uid and question_ids:
            try:
                answer_rows = UserAnswer.query.filter(
                    UserAnswer.user_id == real_uid,
                    UserAnswer.question_id.in_(question_ids),
                ).order_by(UserAnswer.created_at.desc()).all()

                user_answers = {}
                seen_questions = set()
                for row in answer_rows:
                    q_id = row.question_id
                    if q_id not in seen_questions:
                        user_answers[str(q_id)] = {
                            'is_correct': bool(row.is_correct)
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
        exam_meta = db.session.get(Exam, exam_id)
        if not exam_meta:
            return "考试不存在或无权限", 404
        if exam_meta.user_id != uid and not session.get('is_admin'):
            return "考试不存在或无权限", 403

        try:
            cfg = json.loads(exam_meta.config_json or '{}')
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
        # 考试模式：获取考试题目 — 使用 text() 保持复杂 JOIN
        if exam_source == 'user_bank':
            sql = text('''
                SELECT q.*, :subject_name as subject, eq.user_answer, eq.score_val,
                       CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                       CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
                FROM exam_questions eq
                JOIN user_bank_questions q ON eq.question_id = q.id
                LEFT JOIN user_bank_favorites f ON q.id = f.question_id AND f.user_id = :uid
                LEFT JOIN user_bank_mistakes m ON q.id = m.question_id AND m.user_id = :uid2
                WHERE eq.exam_id = :exam_id
                ORDER BY eq.order_index
            ''')
            rows = db.session.execute(sql, {
                'subject_name': exam_meta.subject or '',
                'uid': uid, 'uid2': uid, 'exam_id': exam_id,
            }).fetchall()
            rows = [dict(r._mapping) for r in rows]
        else:
            sql = text('''
                SELECT q.*, s.name as subject, eq.user_answer, eq.score_val,
                       CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                       CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
                FROM exam_questions eq
                JOIN questions q ON eq.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = :uid
                LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = :uid2
                WHERE eq.exam_id = :exam_id
                ORDER BY eq.order_index
            ''')
            rows = db.session.execute(sql, {
                'uid': uid, 'uid2': uid, 'exam_id': exam_id,
            }).fetchall()
            rows = [dict(r._mapping) for r in rows]
    elif target == 'favorites':
        q_query = db.session.query(Question, Subject.name.label('subject_name'),
            Mistake.id.label('mistake_id'),
        ).join(
            Favorite, Favorite.question_id == Question.id
        ).outerjoin(
            Subject, Question.subject_id == Subject.id
        ).outerjoin(
            Mistake, db.and_(Mistake.question_id == Question.id, Mistake.user_id == uid)
        ).filter(
            Favorite.user_id == uid,
            db.or_(Subject.is_locked == False, Subject.is_locked.is_(None)),
        )
        if accessible_subject_ids is not None:
            q_query = q_query.filter(Question.subject_id.in_(accessible_subject_ids))
        if subject != 'all':
            q_query = q_query.filter(Subject.name == subject)
        if q_type != 'all':
            q_query = q_query.filter(Question.type == portable_type_filter)
        result_rows = q_query.all()
        rows = []
        for qobj, sname, mid in result_rows:
            d = _orm_to_dict(qobj)
            d['subject'] = sname
            d['is_fav'] = 1
            d['is_mistake'] = 1 if mid else 0
            rows.append(d)

    elif target == 'mistakes':
        q_query = db.session.query(Question, Subject.name.label('subject_name'),
            Favorite.id.label('fav_id'),
        ).join(
            Mistake, Mistake.question_id == Question.id
        ).outerjoin(
            Subject, Question.subject_id == Subject.id
        ).outerjoin(
            Favorite, db.and_(Favorite.question_id == Question.id, Favorite.user_id == uid)
        ).filter(
            Mistake.user_id == uid,
            db.or_(Subject.is_locked == False, Subject.is_locked.is_(None)),
        )
        if accessible_subject_ids is not None:
            q_query = q_query.filter(Question.subject_id.in_(accessible_subject_ids))
        if subject != 'all':
            q_query = q_query.filter(Subject.name == subject)
        if q_type != 'all':
            q_query = q_query.filter(Question.type == portable_type_filter)
        result_rows = q_query.all()
        rows = []
        for qobj, sname, fid in result_rows:
            d = _orm_to_dict(qobj)
            d['subject'] = sname
            d['is_fav'] = 1 if fid else 0
            d['is_mistake'] = 1
            rows.append(d)

    else:
        q_query = db.session.query(Question, Subject.name.label('subject_name'),
            Favorite.id.label('fav_id'),
            Mistake.id.label('mistake_id'),
        ).outerjoin(
            Subject, Question.subject_id == Subject.id
        ).outerjoin(
            Favorite, db.and_(Favorite.question_id == Question.id, Favorite.user_id == uid)
        ).outerjoin(
            Mistake, db.and_(Mistake.question_id == Question.id, Mistake.user_id == uid)
        ).filter(
            db.or_(Subject.is_locked == False, Subject.is_locked.is_(None)),
        )
        if accessible_subject_ids is not None:
            q_query = q_query.filter(Question.subject_id.in_(accessible_subject_ids))
        elif uid == -1:
            q_query = q_query.filter(db.literal(False))
        if subject != 'all':
            q_query = q_query.filter(Subject.name == subject)
        if q_type != 'all':
            q_query = q_query.filter(Question.type == portable_type_filter)
        result_rows = q_query.all()
        rows = []
        for qobj, sname, fid, mid in result_rows:
            d = _orm_to_dict(qobj)
            d['subject'] = sname
            d['is_fav'] = 1 if fid else 0
            d['is_mistake'] = 1 if mid else 0
            rows.append(d)

    # 标签筛选（仅对当前用户生效）
    if tag and str(tag).lower() != 'all' and uid and uid != -1 and mode != 'exam':
        from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
        conn = db.session.connection()
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
        data_scope = target if target in ('favorites', 'mistakes') else 'all'
        rk_part = None
        if mode == 'reinforce':
            rk_raw = (request.args.get('rk') or '').strip().lower()
            if rk_raw in ('wrong', 'similar'):
                rk_part = f'rk{rk_raw}'
        key_parts = [
            f'{_progress_key_prefix(mode)}_{uid}',
            mode,
            subject,
            q_type,
            data_scope,
            f'tag{tag}' if tag and str(tag).lower() != 'all' else None,
            rk_part,
            f'q{1 if shuffle_questions else 0}',
            f'o{1 if shuffle_options else 0}',
        ]
        p_key = '_'.join([p for p in key_parts if p])
        try:
            saved = UserProgress.query.filter_by(user_id=uid, p_key=p_key).first()
            if saved and saved.data:
                saved_json = json.loads(saved.data)
                if isinstance(saved_json, dict) and isinstance(saved_json.get('order'), list):
                    saved_order = saved_json['order']
        except Exception:
            saved_order = None

    # 处理题目数据
    questions = []
    question_ids = []

    pqf_scope = 'question_center'
    if mode == 'exam' and exam_source == 'user_bank':
        pqf_scope = 'user_bank'
    for row in rows:
        q = dict(row) if not isinstance(row, dict) else row
        _apply_pqf_legacy_fields(q, scope=pqf_scope)
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

                # 打乱选项顺序
                if shuffle_options and q['options'] and q.get('q_type') in ('选择题', '多选题'):
                    orig_answer_keys = str(q.get('answer') or '')
                    correct_texts = []
                    options_map = {opt['key']: opt['value'] for opt in q['options']}
                    for key in orig_answer_keys:
                        if key in options_map:
                            correct_texts.append(options_map[key])

                    shuffle_seed = (uid if uid != -1 else 0) * 1000000 + q['id']
                    rng = random.Random(shuffle_seed)
                    rng.shuffle(q['options'])

                    abcd = 'ABCD'
                    new_answer_keys = []
                    for i, option in enumerate(q['options']):
                        if i < len(abcd):
                            option['key'] = abcd[i]
                            if option['value'] in correct_texts:
                                new_answer_keys.append(option['key'])

                    q['answer'] = ''.join(sorted(new_answer_keys))
            except Exception:
                q['options'] = []
        else:
            q['options'] = []

        _normalize_answer(q)
        questions.append(q)
        question_ids.append(q['id'])

    question_ids_for_template = [q['id'] for q in questions]

    # 打乱题目顺序(考试模式除外)
    if shuffle_questions and mode != 'exam':
        if saved_order:
            q_map = {q['id']: q for q in questions}
            ordered_questions = []
            for qid in saved_order:
                if qid in q_map:
                    ordered_questions.append(q_map.pop(qid))
            if q_map:
                ordered_questions.extend(q_map.values())
            questions = ordered_questions
        else:
            random.shuffle(questions)
            if uid != -1:
                new_order = [q['id'] for q in questions]
                data_scope = target if target in ('favorites', 'mistakes') else 'all'
                rk_part = None
                if mode == 'reinforce':
                    rk_raw = (request.args.get('rk') or '').strip().lower()
                    if rk_raw in ('wrong', 'similar'):
                        rk_part = f'rk{rk_raw}'
                key_parts = [
                    f'{_progress_key_prefix(mode)}_{uid}',
                    mode,
                    subject,
                    q_type,
                    data_scope,
                    f'tag{tag}' if tag and str(tag).lower() != 'all' else None,
                    rk_part,
                    f'q{1 if shuffle_questions else 0}',
                    f'o{1 if shuffle_options else 0}',
                ]
                p_key = '_'.join([p for p in key_parts if p])
                try:
                    existing_prog = UserProgress.query.filter_by(user_id=uid, p_key=p_key).first()
                    if existing_prog and existing_prog.data:
                        progress_json = json.loads(existing_prog.data)
                    else:
                        progress_json = {}
                except Exception:
                    progress_json = {}
                progress_json['order'] = new_order
                progress_json['timestamp'] = progress_json.get('timestamp', 0)
                data_to_save = json.dumps(progress_json, ensure_ascii=False)
                try:
                    existing_prog = UserProgress.query.filter_by(user_id=uid, p_key=p_key).first()
                    if existing_prog:
                        existing_prog.data = data_to_save
                    else:
                        db.session.add(UserProgress(user_id=uid, p_key=p_key, data=data_to_save))
                    db.session.commit()
                except Exception:
                    db.session.rollback()

    # 获取用户的答题记录
    user_answers_json = {}
    uid = session.get('user_id')

    if mode == 'exam' and exam_id:
        user_answers = {}
        for q in questions:
            if q.get('user_answer'):
                user_answers[str(q['id'])] = q['user_answer']
        user_answers_json = user_answers
    elif uid and question_ids:
        try:
            answer_rows = UserAnswer.query.filter(
                UserAnswer.user_id == uid,
                UserAnswer.question_id.in_(question_ids),
            ).order_by(UserAnswer.created_at.desc()).all()

            user_answers = {}
            seen_questions = set()
            for row in answer_rows:
                q_id = row.question_id
                if q_id not in seen_questions:
                    user_answers[str(q_id)] = {
                        'is_correct': bool(row.is_correct)
                    }
                    seen_questions.add(q_id)

            user_answers_json = user_answers
        except Exception:
            user_answers_json = {}

    # 考试模式：获取考试信息
    duration = 0
    submitted = False
    if mode == 'exam' and exam_id:
        if exam_meta:
            duration = exam_meta.duration_minutes
            submitted = (exam_meta.status == 'submitted')
        else:
            exam_obj = db.session.get(Exam, exam_id)
            if exam_obj:
                duration = exam_obj.duration_minutes
                submitted = (exam_obj.status == 'submitted')

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
