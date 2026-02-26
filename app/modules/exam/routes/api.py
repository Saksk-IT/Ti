# -*- coding: utf-8 -*-
"""考试API路由"""
import json
from datetime import timedelta

from flask import Blueprint, request, jsonify, session

from app.core.extensions import db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.models.exam import Exam as LegacyExam
from app.core.utils.cache_utils import bump_user_quiz_version
from app.core.utils.options_parser import parse_options
from app.core.utils.validators import parse_int
from app.core.errors import BadRequestError
from app.core.utils.time_utils import now_bj
from app.models.exam import Exam as ExamModel, ExamQuestion, ExamTemplate
from app.models.subject import Subject, Question
from app.models.quiz import Mistake
from app.models.user_bank import UserBankQuestion, UserBankMistake

exam_api_bp = Blueprint('exam_api', __name__)


def _parse_exam_config(config_json: str) -> dict:
    try:
        cfg = json.loads(config_json or '{}')
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def _exam_source_from_cfg(cfg: dict) -> str:
    src = (cfg or {}).get('source') or 'public'
    src = str(src).strip().lower()
    return src if src in ('public', 'user_bank') else 'public'


def _enrich_exam_row(row: dict, stats_map: dict) -> dict:
    cfg = _parse_exam_config(row.get('config_json'))
    source_val = _exam_source_from_cfg(cfg)
    ex_id = int(row.get('id') or 0)

    st = stats_map.get(ex_id, {'total': 0, 'correct': 0})
    total_q = int(st.get('total') or 0)
    correct_q = int(st.get('correct') or 0)
    acc = round(correct_q * 100.0 / total_q, 1) if total_q else 0.0

    row['source'] = source_val
    row['bank_id'] = cfg.get('bank_id') if source_val == 'user_bank' else None
    row['q_total'] = total_q
    row['q_correct'] = correct_q
    row['accuracy'] = acc
    row.pop('config_json', None)
    return row


def _exam_to_dict(exam: ExamModel) -> dict:
    """ORM ExamModel -> dict (compatible with _enrich_exam_row)."""
    return {
        'id': exam.id,
        'user_id': exam.user_id,
        'subject': exam.subject,
        'duration_minutes': exam.duration_minutes,
        'config_json': exam.config_json,
        'total_score': exam.total_score,
        'status': exam.status,
        'started_at': exam.started_at.isoformat() if exam.started_at else None,
        'submitted_at': exam.submitted_at.isoformat() if exam.submitted_at else None,
    }


@exam_api_bp.route('/exams/create', methods=['POST'])
@auth_required  # 支持session和JWT（小程序）
def api_exams_create():
    """创建考试API（添加科目权限检查）"""
    from pydantic import ValidationError

    from app.modules.exam.schemas.create import CreateExamSchema
    from app.modules.exam.services.exam_create_service import ExamCreateService
    
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    data = request.get_json(silent=True) or {}
    try:
        schema = CreateExamSchema.model_validate(data)
    except ValidationError as e:
        raise BadRequestError(message='参数校验失败', payload={'errors': e.errors()})

    exam_id = ExamCreateService.create(user_id=int(uid), payload=schema)
    return jsonify({'status': 'success', 'exam_id': exam_id})


@exam_api_bp.route('/exams/submit', methods=['POST'])
@auth_required  # 支持session和JWT（小程序）
def api_exams_submit():
    """提交考试API"""
    from pydantic import ValidationError

    from app.modules.exam.schemas.submit import SubmitExamSchema
    from app.modules.exam.services.exam_submit_service import ExamSubmitService

    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    data = request.get_json(silent=True) or {}
    try:
        schema = SubmitExamSchema.model_validate(data)
    except ValidationError as e:
        raise BadRequestError(message='参数校验失败', payload={'errors': e.errors()})

    result = ExamSubmitService.submit(user_id=int(uid), payload=schema)

    return jsonify({
        'status': 'success',
        **result,
    })


@exam_api_bp.route('/exams/<int:exam_id>', methods=['GET', 'DELETE'])
@auth_required  # 支持session和JWT（小程序）
def api_exam_detail_or_delete(exam_id):
    """获取/删除考试（JSON）"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    if request.method == 'DELETE':
        exam = db.session.get(ExamModel, exam_id)

        if not exam or exam.user_id != uid:
            return jsonify({'status': 'error', 'message': '考试不存在或无权限'}), 403

        db.session.delete(exam)
        db.session.commit()

        return jsonify({'status': 'success'})

    # GET：返回考试详情（含题目）
    data = LegacyExam.get_by_id(exam_id, uid)
    if not data:
        return jsonify({'status': 'error', 'message': '考试不存在或无权限'}), 404

    exam = data.get('exam') or {}
    questions = data.get('questions') or []

    formatted_questions = []
    for q in questions:
        q_type_val = q.get('q_type', '')
        options = parse_options(q.get('options'))
        if q_type_val == '判断题' and not options:
            options = [
                {'key': '正确', 'value': '正确'},
                {'key': '错误', 'value': '错误'},
            ]

        formatted_questions.append({
            'id': q.get('id'),
            'content': q.get('content', ''),
            'q_type': q_type_val,
            'options': options,
            'answer': q.get('answer', ''),
            'explanation': q.get('explanation', ''),
            'image_path': q.get('image_path'),
            'subject': q.get('subject', ''),
            'score_val': q.get('score_val', 1),
            'order_index': q.get('order_index', 0),
            'user_answer': q.get('user_answer', ''),
            'is_correct': q.get('is_correct')
        })

    # 降噪返回（避免把 config_json 原封不动传太大）
    exam_info = {
        'id': exam.get('id'),
        'subject': exam.get('subject'),
        'duration_minutes': exam.get('duration_minutes'),
        'status': exam.get('status'),
        'started_at': exam.get('started_at'),
        'submitted_at': exam.get('submitted_at'),
        'total_score': exam.get('total_score', 0)
    }

    return jsonify({'status': 'success', 'data': {'exam': exam_info, 'questions': formatted_questions}})


@exam_api_bp.route('/exams/save_draft', methods=['POST'])
@auth_required  # 支持session和JWT（小程序）
def api_save_exam_draft():
    """保存考试草稿"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status':'unauthorized','message':'请先登录'}), 401
    
    data = request.json or {}
    exam_id = data.get('exam_id')
    answers = data.get('answers') or []
    
    if not exam_id:
        return jsonify({'status':'error','message':'缺少 exam_id'}), 400
    
    exam = db.session.get(ExamModel, exam_id)

    if not exam or exam.user_id != uid:
        return jsonify({'status':'error','message':'考试不存在或无权限'}), 403

    if exam.status == 'submitted':
        return jsonify({'status':'error','message':'考试已提交，不可保存草稿'}), 400

    for a in answers:
        try:
            qid = int(a.get('question_id'))
        except Exception:
            continue
        ua = (a.get('user_answer') or '').strip()
        eq = db.session.query(ExamQuestion).filter_by(exam_id=exam_id, question_id=qid).first()
        if eq:
            eq.user_answer = ua

    db.session.commit()
    return jsonify({'status':'success'})


@exam_api_bp.route('/exams/<int:exam_id>/mistakes', methods=['POST'])
@auth_required  # 支持session和JWT（小程序）
def api_exam_to_mistakes(exam_id):
    """将考试错题加入错题本"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status':'unauthorized','message':'请先登录'}), 401
    
    exam = db.session.get(ExamModel, exam_id)

    if not exam or exam.user_id != uid:
        return jsonify({'status':'error','message':'考试不存在或无权限'}), 403

    if exam.status != 'submitted':
        return jsonify({'status':'error','message':'请在提交考试后再加入错题本'}), 400

    cfg = _parse_exam_config(exam.config_json)

    source = (cfg.get('source') or 'public').strip().lower()
    if source not in ('public', 'user_bank'):
        source = 'public'

    bank_id_val = None
    if source == 'user_bank':
        try:
            bank_id_val = int(cfg.get('bank_id') or 0)
        except Exception:
            bank_id_val = 0
        if not bank_id_val:
            return jsonify({'status': 'error', 'message': '该考试缺少题库信息，无法加入错题本'}), 400

    wrongs = (
        db.session.query(ExamQuestion)
        .filter(
            ExamQuestion.exam_id == exam_id,
            db.or_(ExamQuestion.is_correct.is_(None), ExamQuestion.is_correct == 0),
        )
        .all()
    )

    ts = now_bj()
    count = 0
    for eq in wrongs:
        qid = eq.question_id
        if source == 'user_bank':
            existing = db.session.query(UserBankMistake).filter_by(user_id=uid, question_id=qid).first()
            if existing:
                existing.wrong_count = (existing.wrong_count or 0) + 1
                existing.bank_id = int(bank_id_val)
                existing.updated_at = ts
            else:
                db.session.add(UserBankMistake(
                    user_id=uid, bank_id=int(bank_id_val), question_id=qid, wrong_count=1,
                ))
        else:
            existing = db.session.query(Mistake).filter_by(user_id=uid, question_id=qid).first()
            if existing:
                existing.wrong_count = (existing.wrong_count or 0) + 1
                existing.updated_at = ts
                existing.last_updated = ts
            else:
                db.session.add(Mistake(
                    user_id=uid, question_id=qid, wrong_count=1,
                    created_at=ts, updated_at=ts, last_updated=ts,
                ))
        count += 1

    db.session.commit()
    try:
        bump_user_quiz_version(int(uid))
    except Exception:
        pass
    return jsonify({'status':'success','count': count})


@exam_api_bp.route('/exams/templates', methods=['GET', 'POST'])
@auth_required
def api_exam_templates():
    """Exam templates API."""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    if request.method == 'GET':
        filter_source = (request.args.get('source') or 'all').strip().lower()
        if filter_source not in ('all', 'public', 'user_bank'):
            filter_source = 'all'

        filter_subject = (request.args.get('subject') or '').strip()
        if filter_subject.lower() == 'all':
            filter_subject = ''

        filter_bank_id = parse_int(request.args.get('bank_id'), 0, 0)
        if filter_bank_id <= 0:
            filter_bank_id = None

        rows = (
            db.session.query(ExamTemplate)
            .filter_by(user_id=uid)
            .order_by(ExamTemplate.updated_at.desc(), ExamTemplate.id.desc())
            .all()
        )

        templates = []
        for r in rows:
            cfg = _parse_exam_config(r.config_json)

            cfg_source = str(cfg.get('source') or 'public').strip().lower()
            if cfg_source not in ('public', 'user_bank'):
                cfg_source = 'public'

            cfg_subject = str(cfg.get('subject') or 'all').strip()
            cfg_bank_id = parse_int(cfg.get('bank_id'), 0, 0)
            cfg_bank_id = cfg_bank_id if cfg_bank_id > 0 else None

            if filter_source != 'all' and cfg_source != filter_source:
                continue
            if filter_source == 'public' and filter_subject:
                # 允许"通用模板"：subject=all
                if cfg_subject not in (filter_subject, 'all'):
                    continue
            if filter_source == 'user_bank' and filter_bank_id:
                if cfg_bank_id != filter_bank_id:
                    continue

            templates.append({
                'id': r.id,
                'title': r.title or '未命名模板',
                'config': cfg,
                'created_at': r.created_at.isoformat() if r.created_at else None,
                'updated_at': r.updated_at.isoformat() if r.updated_at else None,
            })

        return jsonify({'status': 'success', 'data': templates})

    data = request.json or {}
    title = (data.get('title') or '').strip()
    config = data.get('config') or {}

    if not title:
        return jsonify({'status': 'error', 'message': '模板名称不能为空'}), 400
    if not isinstance(config, dict):
        return jsonify({'status': 'error', 'message': '模板内容不合法'}), 400

    t = ExamTemplate(
        user_id=uid,
        title=title,
        config_json=json.dumps(config, ensure_ascii=False),
    )
    db.session.add(t)
    db.session.flush()
    template_id = t.id
    db.session.commit()

    return jsonify({'status': 'success', 'id': template_id})


@exam_api_bp.route('/exams/templates/<int:template_id>', methods=['DELETE'])
@auth_required
def api_exam_template_delete(template_id):
    """Delete exam template."""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    t = db.session.get(ExamTemplate, template_id)

    if not t or t.user_id != uid:
        return jsonify({'status': 'error', 'message': '模板不存在或无权限'}), 403

    db.session.delete(t)
    db.session.commit()
    return jsonify({'status': 'success'})


@exam_api_bp.route('/exams/records', methods=['GET'])
@auth_required  # 支持 session 和 JWT（小程序）
def api_exams_records():
    """考试记录数据（对齐 Web /exams?tab=records）。"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    uid = int(uid)

    filter_source = (request.args.get('source') or 'all').strip().lower()
    if filter_source not in ('all', 'public', 'user_bank'):
        filter_source = 'all'

    subject = (request.args.get('subject') or 'all').strip()
    page = parse_int(request.args.get('page'), 1, 1)
    size = parse_int(request.args.get('size'), 10, 5, 50)

    bank_id = parse_int(request.args.get('bank_id'), 0, 0)
    if bank_id <= 0:
        bank_id = None

    # 科目白名单（按权限+锁定过滤）：用于校验 subject 参数
    from app.core.utils.subject_permissions import get_user_accessible_subjects

    subjects: list[str] = []
    try:
        accessible_subject_ids = [int(x) for x in (get_user_accessible_subjects(uid) or [])]
    except Exception:
        accessible_subject_ids = []

    if accessible_subject_ids:
        subj_rows = (
            db.session.query(Subject)
            .filter(
                Subject.id.in_(accessible_subject_ids),
                db.or_(Subject.is_locked == 0, Subject.is_locked.is_(None)),
            )
            .order_by(Subject.id)
            .all()
        )
        subjects = [str(s.name).strip() for s in subj_rows if s and s.name]

    # Web 行为：个人题库时隐藏/禁用科目筛选
    if filter_source == 'user_bank':
        subject = 'all'

    if subject != 'all' and subject not in subjects:
        subject = 'all'

    # Web 行为：公共题库时禁用题库筛选
    if filter_source == 'public':
        bank_id = None

    def _build_source_filters(base_filters: list, fs: str, bk_id: int | None, subj: str) -> list:
        """Append source/subject/bank_id filters to base_filters list."""
        if fs == 'user_bank':
            base_filters.append(ExamModel.config_json.like('%"source": "user_bank"%'))
        elif fs == 'public':
            base_filters.append(
                db.or_(ExamModel.config_json.is_(None), ~ExamModel.config_json.like('%"source": "user_bank"%'))
            )
        if subj != 'all':
            base_filters.append(ExamModel.subject == subj)
        if bk_id:
            base_filters.append(db.or_(
                ExamModel.config_json.like(f'%"bank_id": {int(bk_id)},%'),
                ExamModel.config_json.like(f'%"bank_id": {int(bk_id)}' + '}%'),
            ))
        return base_filters

    # ongoing exams
    ongoing_filters = [ExamModel.user_id == uid, ExamModel.status == 'ongoing']
    _build_source_filters(ongoing_filters, filter_source, bank_id, subject)
    ongoing = (
        db.session.query(ExamModel)
        .filter(*ongoing_filters)
        .order_by(ExamModel.started_at.desc())
        .all()
    )

    # submitted exams (paginated)
    sub_filters = [ExamModel.user_id == uid, ExamModel.status == 'submitted']
    _build_source_filters(sub_filters, filter_source, bank_id, subject)
    total = db.session.query(db.func.count(ExamModel.id)).filter(*sub_filters).scalar() or 0
    offset = (page - 1) * size
    submitted = (
        db.session.query(ExamModel)
        .filter(*sub_filters)
        .order_by(ExamModel.submitted_at.desc())
        .limit(size)
        .offset(offset)
        .all()
    )

    # exam_questions 统计：total/correct/accuracy
    stats_map: dict[int, dict[str, int]] = {}
    stat_exam_ids = [e.id for e in ongoing] + [e.id for e in submitted]
    if stat_exam_ids:
        stat_rows = (
            db.session.query(
                ExamQuestion.exam_id,
                db.func.count(ExamQuestion.id).label('total'),
                db.func.sum(db.case((ExamQuestion.is_correct == 1, 1), else_=0)).label('correct'),
            )
            .filter(ExamQuestion.exam_id.in_(stat_exam_ids))
            .group_by(ExamQuestion.exam_id)
            .all()
        )
        for r in stat_rows:
            stats_map[int(r.exam_id)] = {'total': int(r.total or 0), 'correct': int(r.correct or 0)}

    ongoing_payload = [_enrich_exam_row(_exam_to_dict(e), stats_map) for e in ongoing]
    submitted_payload = [_enrich_exam_row(_exam_to_dict(e), stats_map) for e in submitted]

    return jsonify(
        {
            'status': 'success',
            'data': {
                'filter': {'source': filter_source, 'subject': subject, 'bank_id': bank_id},
                'page': page,
                'size': size,
                'total': total,
                'ongoing': ongoing_payload,
                'submitted': submitted_payload,
            },
        }
    )


@exam_api_bp.route('/exams/stats', methods=['GET'])
@auth_required  # 支持 session 和 JWT（小程序）
def api_exams_stats():
    """考试数据分析（对齐 Web /exams?tab=data）。"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    uid = int(uid)

    # 可选筛选：与 /exams/records 对齐（便于小程序按"所选题库/科目"查看数据）
    filter_source = (request.args.get('source') or 'all').strip().lower()
    if filter_source not in ('all', 'public', 'user_bank'):
        filter_source = 'all'

    subject = (request.args.get('subject') or 'all').strip()
    if not subject:
        subject = 'all'

    bank_id = parse_int(request.args.get('bank_id'), 0, 0)
    if bank_id <= 0:
        bank_id = None

    # subject 白名单（按权限+锁定过滤）：用于校验 subject 参数
    from app.core.utils.subject_permissions import get_user_accessible_subjects

    subjects: list[str] = []
    try:
        accessible_subject_ids = [int(x) for x in (get_user_accessible_subjects(uid) or [])]
    except Exception:
        accessible_subject_ids = []

    if accessible_subject_ids:
        subj_rows = (
            db.session.query(Subject)
            .filter(
                Subject.id.in_(accessible_subject_ids),
                db.or_(Subject.is_locked == 0, Subject.is_locked.is_(None)),
            )
            .order_by(Subject.id)
            .all()
        )
        subjects = [str(s.name).strip() for s in subj_rows if s and s.name]

    # 个人题库时隐藏/禁用科目筛选
    if filter_source == 'user_bank':
        subject = 'all'

    if subject != 'all' and subject not in subjects:
        subject = 'all'

    # 公共题库时禁用题库筛选
    if filter_source == 'public':
        bank_id = None

    # -- ORM filter chain (replaces raw SQL WHERE builder) --
    base_filters = [ExamModel.user_id == uid, ExamModel.status == 'submitted']

    if filter_source == 'user_bank':
        base_filters.append(ExamModel.config_json.like('%"source": "user_bank"%'))
    elif filter_source == 'public':
        base_filters.append(
            db.or_(ExamModel.config_json.is_(None), ~ExamModel.config_json.like('%"source": "user_bank"%'))
        )

    if subject != 'all':
        base_filters.append(ExamModel.subject == subject)

    if bank_id:
        base_filters.append(db.or_(
            ExamModel.config_json.like(f'%"bank_id": {int(bank_id)},%'),
            ExamModel.config_json.like(f'%"bank_id": {int(bank_id)}' + '}%'),
        ))

    stats_overview = {
        'submitted_count': 0,
        'avg_score': 0,
        'avg_accuracy': 0,
        'last7_count': 0,
        'last7_avg_accuracy': 0,
    }
    recent_exams: list[dict] = []
    type_dist: list[dict] = []
    advice: list[dict] = []

    # submitted_count
    stats_overview['submitted_count'] = (
        db.session.query(db.func.count(ExamModel.id))
        .filter(*base_filters)
        .scalar() or 0
    )

    # avg_score
    avg_score = (
        db.session.query(db.func.avg(ExamModel.total_score))
        .filter(*base_filters)
        .scalar()
    )
    stats_overview['avg_score'] = round(float(avg_score or 0), 2)

    # avg_accuracy (subquery: per-exam accuracy, then AVG)
    eq_sub = (
        db.session.query(
            ExamModel.id.label('eid'),
            db.case(
                (db.func.count(ExamQuestion.id) == 0, 0),
                else_=(
                    db.func.sum(db.case((ExamQuestion.is_correct == 1, 1), else_=0))
                    * 100.0
                    / db.func.count(ExamQuestion.id)
                ),
            ).label('acc'),
        )
        .outerjoin(ExamQuestion, ExamQuestion.exam_id == ExamModel.id)
        .filter(*base_filters)
        .group_by(ExamModel.id)
        .subquery()
    )
    avg_acc = db.session.query(db.func.avg(eq_sub.c.acc)).scalar()
    stats_overview['avg_accuracy'] = round(float(avg_acc or 0), 1)

    # last7_count
    cutoff_7d = now_bj() - timedelta(days=7)
    stats_overview['last7_count'] = (
        db.session.query(db.func.count(ExamModel.id))
        .filter(*base_filters, ExamModel.submitted_at >= cutoff_7d)
        .scalar() or 0
    )

    # recent exams (last 7 submitted)
    recent_models = (
        db.session.query(ExamModel)
        .filter(*base_filters)
        .order_by(ExamModel.submitted_at.desc())
        .limit(7)
        .all()
    )
    recent_exams = [_exam_to_dict(e) for e in recent_models]

    # 近期考试统计（准确率 + bank_id/source）
    stats_map: dict[int, dict[str, int]] = {}
    recent_ids = [int(e['id']) for e in recent_exams if e and e.get('id') is not None]
    if recent_ids:
        stat_rows = (
            db.session.query(
                ExamQuestion.exam_id,
                db.func.count(ExamQuestion.id).label('total'),
                db.func.sum(db.case((ExamQuestion.is_correct == 1, 1), else_=0)).label('correct'),
            )
            .filter(ExamQuestion.exam_id.in_(recent_ids))
            .group_by(ExamQuestion.exam_id)
            .all()
        )
        for r in stat_rows:
            stats_map[int(r.exam_id)] = {'total': int(r.total or 0), 'correct': int(r.correct or 0)}

        recent_exams = [_enrich_exam_row(e, stats_map) for e in recent_exams]
        if recent_exams:
            stats_overview['last7_avg_accuracy'] = round(
                sum(float(e.get('accuracy') or 0) for e in recent_exams) / len(recent_exams),
                1,
            )

    # 题型分布：最近 30 天（可按 source/subject/bank_id 筛选）
    cutoff_30d = now_bj() - timedelta(days=30)
    merged: dict[str, int] = {}

    if filter_source in ('all', 'public'):
        pub_filters = list(base_filters)
        if filter_source == 'all':
            pub_filters.append(
                db.or_(ExamModel.config_json.is_(None), ~ExamModel.config_json.like('%"source": "user_bank"%'))
            )
        pub_rows = (
            db.session.query(
                Question.type.label('p_type'),
                db.func.count(ExamQuestion.id).label('cnt'),
            )
            .join(ExamQuestion, ExamQuestion.exam_id == ExamModel.id)
            .join(Question, Question.id == ExamQuestion.question_id)
            .filter(
                *pub_filters,
                ExamModel.submitted_at >= cutoff_30d,
                Question.type.isnot(None),
                db.func.trim(Question.type) != '',
            )
            .group_by(Question.type)
            .all()
        )
        for r in pub_rows:
            pt = (r.p_type or '').strip()
            if pt:
                merged[pt] = merged.get(pt, 0) + int(r.cnt or 0)

    if filter_source in ('all', 'user_bank'):
        bank_filters = list(base_filters)
        if filter_source == 'all':
            bank_filters.append(ExamModel.config_json.like('%"source": "user_bank"%'))
        bank_rows = (
            db.session.query(
                UserBankQuestion.type.label('p_type'),
                db.func.count(ExamQuestion.id).label('cnt'),
            )
            .join(ExamQuestion, ExamQuestion.exam_id == ExamModel.id)
            .join(UserBankQuestion, UserBankQuestion.id == ExamQuestion.question_id)
            .filter(
                *bank_filters,
                ExamModel.submitted_at >= cutoff_30d,
                UserBankQuestion.type.isnot(None),
                db.func.trim(UserBankQuestion.type) != '',
            )
            .group_by(UserBankQuestion.type)
            .all()
        )
        for r in bank_rows:
            pt = (r.p_type or '').strip()
            if pt:
                merged[pt] = merged.get(pt, 0) + int(r.cnt or 0)

    if merged:
        max_cnt = max(merged.values()) if merged else 0
        from app.core.utils.portable_question_format import portable_type_to_q_type

        type_dist = [
            {
                'q_type': portable_type_to_q_type(k),
                'count': int(v),
                'pct': round((float(v) * 100.0 / float(max_cnt)) if max_cnt else 0.0, 1),
            }
            for k, v in sorted(merged.items(), key=lambda kv: kv[1], reverse=True)
        ]

    # 建议（尽量短、可执行）
    try:
        submitted_count = int(stats_overview.get('submitted_count') or 0)
        avg_accuracy = float(stats_overview.get('avg_accuracy') or 0)
        last7_count = int(stats_overview.get('last7_count') or 0)

        if submitted_count <= 0:
            advice = [{'title': '先做一次小测', 'content': '先创建一场 10~20 题的考试，用于快速定位薄弱点。'}]
        else:
            if last7_count <= 0:
                advice.append({'title': '保持频率', 'content': '近 7 天没有提交记录，建议每周至少完成 1 次考试巩固。'})
            if avg_accuracy < 65:
                advice.append({'title': '先复盘再刷题', 'content': '平均正确率偏低，建议优先把本次错题加入错题中心，按题型逐个击破。'})
            if avg_accuracy >= 85 and submitted_count >= 3:
                advice.append({'title': '提高难度或覆盖面', 'content': '整体表现不错，建议增加题量或补齐未覆盖题型，保持稳定输出。'})
            if type_dist:
                top = type_dist[0]
                advice.append({'title': '关注高频题型', 'content': f"近 30 天考试中「{top.get('q_type')}」出现最多（{top.get('count')} 题），建议围绕该题型做专项练习。"})
    except Exception:
        advice = []

    return jsonify(
        {
            'status': 'success',
            'data': {
                'filter': {'source': filter_source, 'subject': subject, 'bank_id': bank_id},
                'stats_overview': stats_overview,
                'recent_exams': recent_exams,
                'type_dist': type_dist,
                'advice': advice,
            },
        }
    )
