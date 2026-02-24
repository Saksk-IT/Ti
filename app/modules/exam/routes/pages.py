# -*- coding: utf-8 -*-
"""考试页面路由"""
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, session, redirect, url_for
from sqlalchemy import func, case, literal_column

from app.core.extensions import db
from app.core.utils.validators import parse_int
from app.models.exam import Exam, ExamQuestion
from app.models.subject import Subject, Question
from app.models.user_bank import UserBankQuestion

exam_pages_bp = Blueprint('exam_pages', __name__)


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


def _parse_dt(val: str) -> datetime | None:
    s = (val or '').strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    except Exception:
        try:
            return datetime.fromisoformat(s.replace(' ', 'T'))
        except Exception:
            return None


def _format_used_seconds(started_at: str | None, submitted_at: str | None) -> tuple[int | None, str]:
    d1 = _parse_dt(started_at or '')
    d2 = _parse_dt(submitted_at or '')
    if not d1 or not d2:
        return None, '—'
    sec = int(max(0, (d2 - d1).total_seconds()))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return sec, f'{h:02d}:{m:02d}:{s:02d}'
    return sec, f'{m:02d}:{s:02d}'


def _exam_to_dict(exam: Exam) -> dict:
    """Convert an Exam ORM instance to a dict matching the old row-dict format."""
    return {
        'id': exam.id,
        'user_id': exam.user_id,
        'subject': exam.subject,
        'duration_minutes': exam.duration_minutes,
        'config_json': exam.config_json,
        'total_score': exam.total_score,
        'status': exam.status,
        'started_at': str(exam.started_at) if exam.started_at else None,
        'submitted_at': str(exam.submitted_at) if exam.submitted_at else None,
    }


def _build_source_filters(filter_source: str, subject: str, bank_id: int | None):
    """Build a list of SQLAlchemy filter conditions for exam source/subject/bank."""
    filters: list = []
    if filter_source == 'user_bank':
        filters.append(db.or_(
            Exam.config_json.like('%"source": "user_bank"%'),
            Exam.config_json.like('%"source":"user_bank"%'),
        ))
    elif filter_source == 'public':
        filters.append(db.or_(
            Exam.config_json.is_(None),
            db.and_(
                Exam.config_json.notlike('%"source": "user_bank"%'),
                Exam.config_json.notlike('%"source":"user_bank"%'),
            ),
        ))

    if subject != 'all':
        filters.append(Exam.subject == subject)

    if bank_id:
        bid_str = str(int(bank_id))
        filters.append(db.or_(
            Exam.config_json.like(f'%"bank_id": {bid_str},%'),
            Exam.config_json.like(f'%"bank_id": {bid_str}' + '}%'),
            Exam.config_json.like(f'%"bank_id":{bid_str},%'),
            Exam.config_json.like(f'%"bank_id":{bid_str}' + '}%'),
        ))

    return filters


def _get_eq_stats(exam_ids: list[int]) -> dict[int, dict[str, int]]:
    """Query exam_questions stats for a list of exam IDs."""
    if not exam_ids:
        return {}
    rows = (
        db.session.query(
            ExamQuestion.exam_id,
            func.count(ExamQuestion.id).label('total'),
            func.sum(case((ExamQuestion.is_correct == True, 1), else_=0)).label('correct'),  # noqa: E712
        )
        .filter(ExamQuestion.exam_id.in_(exam_ids))
        .group_by(ExamQuestion.exam_id)
        .all()
    )
    return {
        int(r.exam_id): {'total': int(r.total or 0), 'correct': int(r.correct or 0)}
        for r in rows
    }


@exam_pages_bp.route('/exams/select')
def page_exams_select():
    """考试：先选题库（公共题库 / 个人题库），再进入题库详情页开始考试。"""
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login_page'))

    from app.core.utils.bank_select import load_bank_select_payload

    conn = db.session.connection()
    payload = load_bank_select_payload(conn, uid)

    return render_template(
        'main/bank/bank_select_entry.html',
        entry_key='exam',
        entry_title='考试',
        entry_subtitle='先选择题库，再进入考试中心。',
        public_cards=payload.get('public_cards') or [],
        bank_cards=payload.get('bank_cards') or [],
        public_total=payload.get('public_total') or 0,
        bank_total=payload.get('bank_total') or 0,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@exam_pages_bp.route('/exams')
def page_exams():
    """考试列表页面"""
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login_page'))

    lock_requested = parse_int(request.args.get('lock'), 0, 0, 1) == 1
    has_source_arg = request.args.get('source') is not None
    has_subject_arg = request.args.get('subject') is not None
    has_bank_arg = request.args.get('bank_id') is not None

    tab = (request.args.get('tab') or 'new').strip().lower()
    if tab not in ('new', 'templates', 'records', 'data', 'settings'):
        tab = 'new'

    filter_source = (request.args.get('source') or 'all').strip().lower()
    if filter_source not in ('all', 'public', 'user_bank'):
        filter_source = 'all'

    subject = request.args.get('subject', 'all')
    page = parse_int(request.args.get('page'), 1, 1)
    size = parse_int(request.args.get('size'), 10, 5, 50)

    bank_id = parse_int(request.args.get('bank_id'), 0, 0)
    if bank_id <= 0:
        bank_id = None

    # ── 科目列表（按权限 + 锁定状态过滤）──
    from app.core.utils.subject_permissions import get_user_accessible_subjects

    subjects_meta: list[dict] = []
    subjects: list[str] = []
    subject_q_types: dict[str, list[str]] = {}

    try:
        accessible_subject_ids = [int(x) for x in (get_user_accessible_subjects(int(uid)) or [])]
    except Exception:
        accessible_subject_ids = []

    if accessible_subject_ids:
        rows = (
            Subject.query
            .filter(
                Subject.id.in_(accessible_subject_ids),
                db.or_(Subject.is_locked == False, Subject.is_locked.is_(None)),  # noqa: E712
            )
            .order_by(Subject.id)
            .all()
        )
        subjects_meta = [{'id': r.id, 'name': r.name} for r in rows]
        subjects = [r.name for r in rows]

        subject_ids = [r.id for r in rows]
        if subject_ids:
            from app.core.utils.portable_question_format import portable_type_to_q_type

            sq_rows = (
                db.session.query(
                    Subject.name.label('name'),
                    func.string_agg(func.distinct(Question.type), literal_column("','")).label('p_types'),
                )
                .outerjoin(Question, Subject.id == Question.subject_id)
                .filter(Subject.id.in_(subject_ids))
                .group_by(Subject.name, Subject.id)
                .order_by(Subject.id)
                .all()
            )
            for row in sq_rows:
                name = row.name
                types_str = row.p_types
                if not name:
                    continue
                if not types_str:
                    subject_q_types[name] = []
                    continue
                types = [
                    portable_type_to_q_type(t)
                    for t in (types_str or '').split(',')
                    if t and t.strip()
                ]
                subject_q_types[name] = sorted(list({t for t in types if t}))

    # ── 所有题型（备用：全部题库）──
    try:
        from app.core.utils.portable_question_format import portable_type_to_q_type

        qt_rows = (
            db.session.query(Question.type)
            .filter(Question.type.isnot(None), func.trim(Question.type) != '')
            .distinct()
            .order_by(Question.type)
            .all()
        )
        q_types = [
            portable_type_to_q_type(row[0] or '')
            for row in qt_rows
            if row and row[0]
        ]
        q_types = sorted(list({t for t in q_types if t}))
    except Exception:
        q_types = []

    if subject != 'all' and subject not in subjects:
        subject = 'all'

    # ── 个人题库列表 ──
    from app.core.utils.bank_select import load_user_bank_cards

    conn = db.session.connection()
    banks_meta = load_user_bank_cards(conn, uid)

    # ── 个人题库题型映射 ──
    bank_q_types: dict[str, list[str]] = {}
    bank_ids = [int(b.get('id')) for b in banks_meta if b.get('id') is not None]
    if bank_ids:
        from app.core.utils.portable_question_format import portable_type_to_q_type

        bq_rows = (
            db.session.query(
                UserBankQuestion.bank_id,
                func.string_agg(func.distinct(UserBankQuestion.type), literal_column("','")).label('p_types'),
            )
            .filter(
                UserBankQuestion.bank_id.in_(bank_ids),
                UserBankQuestion.type.isnot(None),
                func.trim(UserBankQuestion.type) != '',
            )
            .group_by(UserBankQuestion.bank_id)
            .all()
        )
        for r in bq_rows:
            bid = r.bank_id
            types_str = r.p_types
            if bid is None:
                continue
            if not types_str:
                bank_q_types[str(int(bid))] = []
                continue
            types = [
                portable_type_to_q_type(t, essay_q_type="简答题")
                for t in (types_str or '').split(',')
                if t and t.strip()
            ]
            bank_q_types[str(int(bid))] = sorted(list({t for t in types if t}))

    # ── 新建考试页：支持 URL 预设范围 ──
    preset_apply = bool(lock_requested or has_source_arg or has_subject_arg or has_bank_arg)

    preset_source = 'public'
    if filter_source in ('public', 'user_bank'):
        preset_source = filter_source
    elif bank_id:
        preset_source = 'user_bank'

    bank_name_by_id: dict[int, str] = {}
    for b in (banks_meta or []):
        try:
            bid = int(b.get('id') or 0)
        except Exception:
            continue
        if bid > 0:
            bank_name_by_id[bid] = str(b.get('name') or '').strip()

    scope_locked = False
    scope_locked_label = ''
    if lock_requested:
        if preset_source == 'user_bank' and bank_id:
            scope_locked = True
            bank_name = bank_name_by_id.get(int(bank_id), '').strip()
            scope_locked_label = f'个人题库 · {bank_name or ("题库#" + str(int(bank_id)))}'
        elif preset_source == 'public' and subject != 'all':
            scope_locked = True
            scope_locked_label = f'公共题库 · {subject}'

    nav_source = filter_source if filter_source != 'all' else None
    nav_subject = subject if subject != 'all' else None
    nav_bank_id = bank_id if bank_id else None
    nav_lock = 1 if lock_requested else None

    # ── 进行中的考试 ──
    ongoing_filters = [Exam.user_id == uid, Exam.status == 'ongoing']

    if tab == 'records':
        ongoing_filters.extend(_build_source_filters(filter_source, subject, bank_id))

    ongoing_exams = (
        Exam.query
        .filter(*ongoing_filters)
        .order_by(Exam.started_at.desc())
        .all()
    )
    ongoing = [_exam_to_dict(e) for e in ongoing_exams]

    # ── 已提交的考试（仅记录页分页查询）──
    submitted: list[dict] = []
    total = 0
    if tab == 'records':
        sub_filters = [Exam.user_id == uid, Exam.status == 'submitted']
        sub_filters.extend(_build_source_filters(filter_source, subject, bank_id))

        total = Exam.query.filter(*sub_filters).count()
        offset = (page - 1) * size
        submitted_exams = (
            Exam.query
            .filter(*sub_filters)
            .order_by(Exam.submitted_at.desc())
            .limit(size)
            .offset(offset)
            .all()
        )
        submitted = [_exam_to_dict(e) for e in submitted_exams]

    # ── exam_questions 统计 ──
    stat_exam_ids = [int(r['id']) for r in ongoing] + [int(r['id']) for r in submitted]
    stats_map = _get_eq_stats(stat_exam_ids)

    def _enrich_exam(row_dict: dict) -> dict:
        cfg = _parse_exam_config(row_dict.get('config_json'))
        source_val = _exam_source_from_cfg(cfg)
        ex_id = int(row_dict.get('id') or 0)
        st = stats_map.get(ex_id, {'total': 0, 'correct': 0})
        total_q = int(st.get('total') or 0)
        correct_q = int(st.get('correct') or 0)
        acc = round(correct_q * 100.0 / total_q, 1) if total_q else 0.0
        row_dict['source'] = source_val
        row_dict['bank_id'] = cfg.get('bank_id') if source_val == 'user_bank' else None
        row_dict['q_total'] = total_q
        row_dict['q_correct'] = correct_q
        row_dict['accuracy'] = acc
        return row_dict

    ongoing_payload = [_enrich_exam(r) for r in ongoing]
    submitted_payload = [_enrich_exam(r) for r in submitted]

    # ── 数据页 ──
    stats_overview = {
        'submitted_count': 0,
        'avg_score': 0,
        'avg_accuracy': 0,
        'last7_count': 0,
        'last7_avg_accuracy': 0,
    }
    recent_exams: list[dict] = []
    type_dist: list[dict] = []
    score_dist: list[dict] = []
    data_scope_label = ''
    data_tips: list[str] = []

    if tab == 'data':
        # 统计范围：与「考试记录」筛选语义一致
        scope_filters = [Exam.user_id == uid, Exam.status == 'submitted']
        scope_filters.extend(_build_source_filters(filter_source, subject, bank_id))

        if bank_id:
            bank_name = bank_name_by_id.get(int(bank_id), '').strip()
            data_scope_label = f'个人题库 · {bank_name or ("题库#" + str(int(bank_id)))}'
        elif filter_source == 'user_bank':
            data_scope_label = '个人题库 · 全部'
        elif subject != 'all':
            data_scope_label = f'公共题库 · {subject}'
        elif filter_source == 'public':
            data_scope_label = '公共题库 · 全部科目'
        else:
            data_scope_label = '全部题库'

        # submitted_count
        stats_overview['submitted_count'] = Exam.query.filter(*scope_filters).count()

        # avg_score
        avg_score_val = db.session.query(func.avg(Exam.total_score)).filter(*scope_filters).scalar()
        stats_overview['avg_score'] = round(float(avg_score_val or 0), 2)

        # avg_accuracy (per-exam accuracy then averaged)
        eq_sub = (
            db.session.query(
                Exam.id.label('eid'),
                case(
                    (func.count(ExamQuestion.id) == 0, 0),
                    else_=(
                        func.sum(case((ExamQuestion.is_correct == True, 1), else_=0)) * 100.0  # noqa: E712
                        / func.count(ExamQuestion.id)
                    ),
                ).label('acc'),
            )
            .outerjoin(ExamQuestion, ExamQuestion.exam_id == Exam.id)
            .filter(*scope_filters)
            .group_by(Exam.id)
            .subquery()
        )
        avg_acc_val = db.session.query(func.avg(eq_sub.c.acc)).scalar()
        stats_overview['avg_accuracy'] = round(float(avg_acc_val or 0), 1)

        # last7_count
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        last7_filters = scope_filters + [Exam.submitted_at >= seven_days_ago]
        stats_overview['last7_count'] = Exam.query.filter(*last7_filters).count()

        # recent_exams (last 7 submitted)
        recent_exam_objs = (
            Exam.query
            .filter(*scope_filters)
            .order_by(Exam.submitted_at.desc())
            .limit(7)
            .all()
        )
        recent_exams = [_exam_to_dict(e) for e in recent_exam_objs]

        recent_ids = [int(r['id']) for r in recent_exams if r.get('id') is not None]
        if recent_ids:
            rstats = _get_eq_stats(recent_ids)
            for e in recent_exams:
                ex_id = int(e.get('id') or 0)
                cfg = _parse_exam_config(e.get('config_json'))
                src = _exam_source_from_cfg(cfg)
                st = rstats.get(ex_id, {'total': 0, 'correct': 0})
                total_q = int(st.get('total') or 0)
                correct_q = int(st.get('correct') or 0)
                e['source'] = src
                e['q_total'] = total_q
                e['q_correct'] = correct_q
                e['accuracy'] = round(correct_q * 100.0 / total_q, 1) if total_q else 0.0

            if recent_exams:
                stats_overview['last7_avg_accuracy'] = round(
                    sum(float(e.get('accuracy') or 0) for e in recent_exams) / len(recent_exams),
                    1,
                )

        # ── 题型分布 + 正确率：最近 30 天 ──
        include_public = (not bank_id) and (filter_source in ('all', 'public'))
        include_bank = (filter_source in ('all', 'user_bank')) or bool(bank_id)

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        merged: dict[str, dict[str, int]] = {}

        if include_public:
            pub_filters = [
                Exam.user_id == uid,
                Exam.status == 'submitted',
                Exam.submitted_at >= thirty_days_ago,
                db.or_(
                    Exam.config_json.is_(None),
                    db.and_(
                        Exam.config_json.notlike('%"source": "user_bank"%'),
                        Exam.config_json.notlike('%"source":"user_bank"%'),
                    ),
                ),
            ]
            if subject != 'all':
                pub_filters.append(Exam.subject == subject)

            pub_rows = (
                db.session.query(
                    Question.type.label('p_type'),
                    func.count(literal_column('1')).label('cnt'),
                    func.sum(case((ExamQuestion.is_correct == True, 1), else_=0)).label('correct'),  # noqa: E712
                )
                .select_from(Exam)
                .join(ExamQuestion, ExamQuestion.exam_id == Exam.id)
                .join(Question, Question.id == ExamQuestion.question_id)
                .filter(
                    *pub_filters,
                    Question.type.isnot(None),
                    func.trim(Question.type) != '',
                )
                .group_by(Question.type)
                .all()
            )
            for r in pub_rows:
                pt = (r.p_type or '').strip()
                if not pt:
                    continue
                if pt not in merged:
                    merged[pt] = {'count': 0, 'correct': 0}
                merged[pt]['count'] += int(r.cnt or 0)
                merged[pt]['correct'] += int(r.correct or 0)

        if include_bank:
            bank_filters = [
                Exam.user_id == uid,
                Exam.status == 'submitted',
                Exam.submitted_at >= thirty_days_ago,
                db.or_(
                    Exam.config_json.like('%"source": "user_bank"%'),
                    Exam.config_json.like('%"source":"user_bank"%'),
                ),
            ]
            if subject != 'all':
                bank_filters.append(Exam.subject == subject)
            if bank_id:
                bid_str = str(int(bank_id))
                bank_filters.append(db.or_(
                    Exam.config_json.like(f'%"bank_id": {bid_str},%'),
                    Exam.config_json.like(f'%"bank_id": {bid_str}' + '}%'),
                    Exam.config_json.like(f'%"bank_id":{bid_str},%'),
                    Exam.config_json.like(f'%"bank_id":{bid_str}' + '}%'),
                ))

            bank_rows = (
                db.session.query(
                    UserBankQuestion.type.label('p_type'),
                    func.count(literal_column('1')).label('cnt'),
                    func.sum(case((ExamQuestion.is_correct == True, 1), else_=0)).label('correct'),  # noqa: E712
                )
                .select_from(Exam)
                .join(ExamQuestion, ExamQuestion.exam_id == Exam.id)
                .join(UserBankQuestion, UserBankQuestion.id == ExamQuestion.question_id)
                .filter(
                    *bank_filters,
                    UserBankQuestion.type.isnot(None),
                    func.trim(UserBankQuestion.type) != '',
                )
                .group_by(UserBankQuestion.type)
                .all()
            )
            for r in bank_rows:
                pt = (r.p_type or '').strip()
                if not pt:
                    continue
                if pt not in merged:
                    merged[pt] = {'count': 0, 'correct': 0}
                merged[pt]['count'] += int(r.cnt or 0)
                merged[pt]['correct'] += int(r.correct or 0)

        if merged:
            max_cnt = max((v.get('count') or 0) for v in merged.values()) if merged else 0
            from app.core.utils.portable_question_format import portable_type_to_q_type

            type_dist = []
            for pt, val in sorted(merged.items(), key=lambda kv: int((kv[1] or {}).get('count') or 0), reverse=True):
                cnt = int((val or {}).get('count') or 0)
                cor = int((val or {}).get('correct') or 0)
                acc = round((cor * 100.0 / cnt), 1) if cnt else 0.0
                type_dist.append(
                    {
                        'q_type': portable_type_to_q_type(pt),
                        'count': cnt,
                        'pct': round((float(cnt) * 100.0 / float(max_cnt)) if max_cnt else 0.0, 1),
                        'accuracy': acc,
                    }
                )

        # ── 得分分布（全量，按当前范围统计）──
        try:
            bins = [
                {'label': '0-59', 'count': 0},
                {'label': '60-69', 'count': 0},
                {'label': '70-79', 'count': 0},
                {'label': '80-89', 'count': 0},
                {'label': '90-100', 'count': 0},
            ]
            score_rows = (
                db.session.query(Exam.total_score)
                .filter(*scope_filters)
                .all()
            )
            for r in score_rows:
                try:
                    score = float(r[0] or 0.0)
                except Exception:
                    score = 0.0
                if score < 60:
                    bins[0]['count'] += 1
                elif score < 70:
                    bins[1]['count'] += 1
                elif score < 80:
                    bins[2]['count'] += 1
                elif score < 90:
                    bins[3]['count'] += 1
                else:
                    bins[4]['count'] += 1

            max_bin = max((int(b.get('count') or 0) for b in bins), default=0)
            score_dist = [
                {
                    'label': b['label'],
                    'count': int(b.get('count') or 0),
                    'pct': round((float(b.get('count') or 0) * 100.0 / float(max_bin)) if max_bin else 0.0, 1),
                }
                for b in bins
            ]
        except Exception:
            score_dist = []

        # ── 建议（基于统计结果）──
        if int(stats_overview.get('submitted_count') or 0) <= 0:
            data_tips.append('当前范围下还没有提交过考试：去「新建考试」做一次模拟，数据页会更有参考价值。')
        else:
            avg_a = float(stats_overview.get('avg_accuracy') or 0.0)
            last7 = int(stats_overview.get('last7_count') or 0)
            if last7 <= 0:
                data_tips.append('近 7 天未提交考试：建议每周至少做 1 套小卷，保持手感与节奏。')
            if avg_a < 60:
                data_tips.append('平均正确率偏低：先把高频题型拆出来做专项（背题 → 刷题 → 再考试）。')
            elif avg_a < 80:
                data_tips.append('平均正确率不错：建议提高"混合题型比例"，并在错题型上做小卷回归。')
            else:
                data_tips.append('平均正确率很高：可以缩短时间限制做"速度训练"，提升稳定性。')

            weak = [t for t in (type_dist or []) if int(t.get('count') or 0) >= 10]
            weak = sorted(weak, key=lambda x: float(x.get('accuracy') or 0.0))
            if weak:
                t0 = weak[0]
                if float(t0.get('accuracy') or 0.0) < 70:
                    data_tips.append(f"薄弱题型：{t0.get('q_type')}（近30天 {t0.get('count')} 题，正确率 {t0.get('accuracy')}%）。建议优先专项突破。")
            if not type_dist:
                data_tips.append('当前范围下近 30 天暂无题型数据：先完成并提交一套考试，再回来查看趋势与分布。')

    return render_template(
        'exam/exams_v3.html',
        tab=tab,
        ongoing=ongoing_payload,
        submitted=submitted_payload,
        subjects=subjects,
        subjects_meta=subjects_meta,
        q_types=q_types,
        subject_q_types_json=subject_q_types,
        filter_subject=subject,
        filter_source=filter_source,
        filter_bank_id=bank_id,
        banks_meta=banks_meta,
        bank_q_types_json=bank_q_types,
        stats_overview=stats_overview,
        recent_exams=recent_exams,
        type_dist=type_dist,
        score_dist=score_dist,
        data_scope_label=data_scope_label,
        data_tips=data_tips,
        page=page,
        size=size,
        total=total,
        preset_apply=preset_apply,
        preset_source=preset_source,
        preset_subject=subject,
        preset_bank_id=bank_id,
        scope_locked=scope_locked,
        scope_locked_label=scope_locked_label,
        nav_source=nav_source,
        nav_subject=nav_subject,
        nav_bank_id=nav_bank_id,
        nav_lock=nav_lock,
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
    )


@exam_pages_bp.route('/exams/<int:exam_id>')
def page_exam_detail(exam_id):
    """考试详情页面"""
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login_page'))

    exam = Exam.query.get(exam_id)

    if not exam:
        return "考试不存在或无权限", 403
    if exam.user_id != uid and not session.get('is_admin'):
        return "考试不存在或无权限", 403

    cfg = _parse_exam_config(exam.config_json)
    source = _exam_source_from_cfg(cfg)

    if source == 'user_bank':
        rows = (
            db.session.query(ExamQuestion, UserBankQuestion)
            .join(UserBankQuestion, UserBankQuestion.id == ExamQuestion.question_id)
            .filter(ExamQuestion.exam_id == exam_id)
            .order_by(ExamQuestion.order_index)
            .all()
        )
        merged_rows = []
        for eq, q in rows:
            merged_rows.append({
                'id': eq.id,
                'exam_id': eq.exam_id,
                'question_id': eq.question_id,
                'order_index': eq.order_index,
                'score_val': eq.score_val,
                'user_answer': eq.user_answer,
                'is_correct': eq.is_correct,
                'answered_at': str(eq.answered_at) if eq.answered_at else None,
                'type': q.type,
                'content': q.content,
                'options': q.options,
                'answer': q.answer,
                'analysis': q.analysis,
            })
    else:
        rows = (
            db.session.query(ExamQuestion, Question)
            .join(Question, Question.id == ExamQuestion.question_id)
            .filter(ExamQuestion.exam_id == exam_id)
            .order_by(ExamQuestion.order_index)
            .all()
        )
        merged_rows = []
        for eq, q in rows:
            merged_rows.append({
                'id': eq.id,
                'exam_id': eq.exam_id,
                'question_id': eq.question_id,
                'order_index': eq.order_index,
                'score_val': eq.score_val,
                'user_answer': eq.user_answer,
                'is_correct': eq.is_correct,
                'answered_at': str(eq.answered_at) if eq.answered_at else None,
                'type': q.type,
                'content': q.content,
                'options': q.options,
                'answer': q.answer,
                'analysis': q.analysis,
            })

    total_count = len(merged_rows)
    correct = sum(1 for r in merged_rows if (r.get('is_correct') or 0) == 1)
    acc = round(correct * 100.0 / total_count, 1) if total_count else 0.0

    exam_dict = _exam_to_dict(exam)
    data = {
        'exam': exam_dict,
        'total': total_count,
        'correct': correct,
        'accuracy': acc,
        'items': [],
        'exam_source': source,
        'exam_bank_id': cfg.get('bank_id') if source == 'user_bank' else None,
    }

    try:
        from app.core.utils.pqf_rows import pqf_row_to_internal

        scope = 'user_bank' if source == 'user_bank' else 'question_center'
        data['items'] = [pqf_row_to_internal(r, scope=scope) for r in merged_rows]
    except Exception:
        data['items'] = merged_rows

    return render_template(
        'exam/exam_detail_v2.html',
        **data,
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
    )


@exam_pages_bp.route('/exams/<int:exam_id>/settlement')
def page_exam_settlement(exam_id):
    """考试结算页（用于交卷后落地页）"""
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login_page'))

    exam = Exam.query.get(exam_id)
    if not exam:
        return "考试不存在或无权限", 403
    if exam.user_id != uid and not session.get('is_admin'):
        return "考试不存在或无权限", 403

    exam_dict = _exam_to_dict(exam)
    cfg = _parse_exam_config(exam.config_json)
    source = _exam_source_from_cfg(cfg)
    bank_id_val = cfg.get('bank_id') if source == 'user_bank' else None

    eq_rows = (
        ExamQuestion.query
        .filter(ExamQuestion.exam_id == exam_id)
        .order_by(ExamQuestion.order_index)
        .all()
    )

    total_count = len(eq_rows)
    correct = 0
    wrong = 0
    answered = 0

    for r in eq_rows:
        ua = (r.user_answer or '').strip()
        if ua:
            answered += 1
        if (r.is_correct or 0) == 1:
            correct += 1
        else:
            wrong += 1

    unanswered = max(0, total_count - answered)
    accuracy = round(correct * 100.0 / total_count, 1) if total_count else 0.0

    used_sec, used_text = _format_used_seconds(exam_dict.get('started_at'), exam_dict.get('submitted_at'))
    avg_sec = (int(round(used_sec / total_count)) if used_sec is not None and total_count else None)

    return render_template(
        'exam/exam_settlement_v2.html',
        exam=exam_dict,
        total=total_count,
        correct=correct,
        wrong=wrong,
        answered=answered,
        unanswered=unanswered,
        accuracy=accuracy,
        used_text=used_text,
        avg_sec=avg_sec,
        exam_source=source,
        exam_bank_id=bank_id_val,
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
    )
