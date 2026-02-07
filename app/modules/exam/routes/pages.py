# -*- coding: utf-8 -*-
"""考试页面路由"""
import json
from datetime import datetime
from flask import Blueprint, render_template, request, session, redirect, url_for
from app.core.utils.database import get_db
from app.core.utils.validators import parse_int

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


@exam_pages_bp.route('/exams/select')
def page_exams_select():
    """考试：先选题库（公共题库 / 个人题库），再进入题库详情页开始考试。"""
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login_page'))

    conn = get_db()
    from app.core.utils.bank_select import load_bank_select_payload

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
    
    conn = get_db()
    
    # 科目列表（按权限 + 锁定状态过滤）
    from app.core.utils.subject_permissions import get_user_accessible_subjects

    subjects_meta = []
    subjects = []
    subject_q_types = {}

    try:
        accessible_subject_ids = [int(x) for x in (get_user_accessible_subjects(int(uid)) or [])]
    except Exception:
        accessible_subject_ids = []

    if accessible_subject_ids:
        placeholders = ','.join(['?'] * len(accessible_subject_ids))
        rows = conn.execute(
            f"""
            SELECT id, name
            FROM subjects
            WHERE id IN ({placeholders})
              AND (is_locked=0 OR is_locked IS NULL)
            ORDER BY id
            """,
            accessible_subject_ids,
        ).fetchall()
        subjects_meta = [dict(r) for r in rows]
        subjects = [r['name'] for r in subjects_meta]

        subject_ids = [int(r['id']) for r in subjects_meta if r.get('id') is not None]
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            rows = conn.execute(
                f"""
                SELECT s.name as name, GROUP_CONCAT(DISTINCT q.type) as p_types
                FROM subjects s
                LEFT JOIN questions q ON s.id = q.subject_id
                WHERE s.id IN ({placeholders})
                GROUP BY s.name
                ORDER BY s.id
                """,
                subject_ids,
            ).fetchall()
            from app.core.utils.portable_question_format import portable_type_to_q_type

            for row in rows:
                name = row['name']
                types_str = row['p_types']
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

    # 所有题型（备用：全部题库）
    try:
        from app.core.utils.portable_question_format import portable_type_to_q_type

        q_types = [
            portable_type_to_q_type((row[0] or ''))
            for row in conn.execute(
                "SELECT DISTINCT type FROM questions WHERE type IS NOT NULL AND TRIM(type) != '' ORDER BY type"
            ).fetchall()
            if row and row[0]
        ]
        q_types = sorted(list({t for t in q_types if t}))
    except Exception:
        q_types = []

    if subject != 'all' and subject not in subjects:
        subject = 'all'

    # 个人题库列表（用于新建/偏好/筛选）
    from app.core.utils.bank_select import load_user_bank_cards

    banks_meta = load_user_bank_cards(conn, uid)

    bank_q_types: dict[str, list[str]] = {}
    bank_ids = [int(b.get('id')) for b in banks_meta if b.get('id') is not None]
    if bank_ids:
        placeholders = ','.join(['?'] * len(bank_ids))
        rows = conn.execute(
            f"""
            SELECT bank_id, GROUP_CONCAT(DISTINCT type) as p_types
            FROM user_bank_questions
            WHERE bank_id IN ({placeholders})
              AND type IS NOT NULL AND TRIM(type) != ''
            GROUP BY bank_id
            """,
            bank_ids,
        ).fetchall()
        from app.core.utils.portable_question_format import portable_type_to_q_type

        for r in rows:
            bid = r['bank_id']
            types_str = r['p_types']
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

    # 新建考试页：支持 URL 预设范围，并在 lock=1 时锁定到当前题库/科目
    preset_apply = bool(lock_requested or has_source_arg or has_subject_arg or has_bank_arg)

    preset_source = 'public'
    if filter_source in ('public', 'user_bank'):
        preset_source = filter_source
    elif bank_id:
        preset_source = 'user_bank'

    bank_name_by_id = {}
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

    # 进行中的考试：新建页展示全部；记录页按筛选展示
    ongoing_params = [uid]
    ongoing_where = 'WHERE user_id=? AND status="ongoing"'

    if tab == 'records':
        if filter_source == 'user_bank':
            ongoing_where += ' AND (config_json LIKE ? OR config_json LIKE ?)'
            ongoing_params.append('%"source": "user_bank"%')
            ongoing_params.append('%"source":"user_bank"%')
        elif filter_source == 'public':
            ongoing_where += ' AND (config_json IS NULL OR (config_json NOT LIKE ? AND config_json NOT LIKE ?))'
            ongoing_params.append('%"source": "user_bank"%')
            ongoing_params.append('%"source":"user_bank"%')

        if subject != 'all':
            ongoing_where += ' AND subject = ?'
            ongoing_params.append(subject)

        if bank_id:
            ongoing_where += ' AND (config_json LIKE ? OR config_json LIKE ? OR config_json LIKE ? OR config_json LIKE ?)'
            bid_str = str(int(bank_id))
            ongoing_params.append(f'%"bank_id": {bid_str},%')
            ongoing_params.append('%"bank_id": ' + bid_str + '}%')
            ongoing_params.append(f'%"bank_id":{bid_str},%')
            ongoing_params.append('%"bank_id":' + bid_str + '}%')

    ongoing = conn.execute(
        f'SELECT * FROM exams {ongoing_where} ORDER BY started_at DESC',
        ongoing_params,
    ).fetchall()

    # 已提交的考试：仅记录页分页查询
    submitted = []
    total = 0
    if tab == 'records':
        where = 'WHERE user_id=? AND status="submitted"'
        params = [uid]

        if filter_source == 'user_bank':
            where += ' AND (config_json LIKE ? OR config_json LIKE ?)'
            params.append('%"source": "user_bank"%')
            params.append('%"source":"user_bank"%')
        elif filter_source == 'public':
            where += ' AND (config_json IS NULL OR (config_json NOT LIKE ? AND config_json NOT LIKE ?))'
            params.append('%"source": "user_bank"%')
            params.append('%"source":"user_bank"%')

        if subject != 'all':
            where += ' AND subject = ?'
            params.append(subject)

        if bank_id:
            where += ' AND (config_json LIKE ? OR config_json LIKE ? OR config_json LIKE ? OR config_json LIKE ?)'
            bid_str = str(int(bank_id))
            params.append(f'%"bank_id": {bid_str},%')
            params.append('%"bank_id": ' + bid_str + '}%')
            params.append(f'%"bank_id":{bid_str},%')
            params.append('%"bank_id":' + bid_str + '}%')

        total = conn.execute(f'SELECT COUNT(1) FROM exams {where}', params).fetchone()[0]
        offset = (page - 1) * size
        submitted = conn.execute(
            f'SELECT * FROM exams {where} ORDER BY submitted_at DESC LIMIT ? OFFSET ?',
            params + [size, offset],
        ).fetchall()

    # exam_questions 统计（用于列表/最近考试）
    stats_map: dict[int, dict[str, int]] = {}
    stat_exam_ids = [int(r['id']) for r in ongoing] + [int(r['id']) for r in submitted]
    if stat_exam_ids:
        placeholders = ','.join(['?'] * len(stat_exam_ids))
        rows = conn.execute(
            f"""
            SELECT exam_id,
                   COUNT(1) as total,
                   SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END) as correct
            FROM exam_questions
            WHERE exam_id IN ({placeholders})
            GROUP BY exam_id
            """,
            stat_exam_ids,
        ).fetchall()
        for r in rows:
            ex_id = int(r['exam_id'])
            stats_map[ex_id] = {
                'total': int(r['total'] or 0),
                'correct': int(r['correct'] or 0),
            }

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

    ongoing_payload = [_enrich_exam(dict(r)) for r in ongoing]
    submitted_payload = [_enrich_exam(dict(r)) for r in submitted]

    # 数据页
    stats_overview = {
        'submitted_count': 0,
        'avg_score': 0,
        'avg_accuracy': 0,
        'last7_count': 0,
        'last7_avg_accuracy': 0,
    }
    recent_exams = []
    type_dist = []
    score_dist = []
    data_scope_label = ''
    data_tips = []

    if tab == 'data':
        # 统计范围：与「考试记录」筛选语义一致（source/subject/bank_id）
        scope_where = 'WHERE e.user_id=? AND e.status="submitted"'
        scope_params: list = [uid]

        if filter_source == 'user_bank':
            scope_where += ' AND (e.config_json LIKE ? OR e.config_json LIKE ?)'
            scope_params.append('%"source": "user_bank"%')
            scope_params.append('%"source":"user_bank"%')
        elif filter_source == 'public':
            scope_where += ' AND (e.config_json IS NULL OR (e.config_json NOT LIKE ? AND e.config_json NOT LIKE ?))'
            scope_params.append('%"source": "user_bank"%')
            scope_params.append('%"source":"user_bank"%')

        if subject != 'all':
            scope_where += ' AND e.subject = ?'
            scope_params.append(subject)

        if bank_id:
            scope_where += ' AND (e.config_json LIKE ? OR e.config_json LIKE ? OR e.config_json LIKE ? OR e.config_json LIKE ?)'
            bid_str = str(int(bank_id))
            scope_params.append(f'%"bank_id": {bid_str},%')
            scope_params.append('%"bank_id": ' + bid_str + '}%')
            scope_params.append(f'%"bank_id":{bid_str},%')
            scope_params.append('%"bank_id":' + bid_str + '}%')

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

        stats_overview['submitted_count'] = int(
            conn.execute(
                f'SELECT COUNT(1) FROM exams e {scope_where}',
                scope_params,
            ).fetchone()[0]
            or 0
        )

        avg_score = conn.execute(
            f'SELECT AVG(e.total_score) FROM exams e {scope_where}',
            scope_params,
        ).fetchone()[0]
        stats_overview['avg_score'] = round(float(avg_score or 0), 2)

        avg_acc = conn.execute(
            f"""
            SELECT AVG(acc) FROM (
              SELECT e.id as id,
                     CASE WHEN COUNT(eq.id)=0 THEN 0
                          ELSE (SUM(CASE WHEN eq.is_correct=1 THEN 1 ELSE 0 END) * 100.0 / COUNT(eq.id))
                     END as acc
              FROM exams e
              LEFT JOIN exam_questions eq ON eq.exam_id = e.id
              {scope_where}
              GROUP BY e.id
            ) t
            """,
            scope_params,
        ).fetchone()[0]
        stats_overview['avg_accuracy'] = round(float(avg_acc or 0), 1)

        stats_overview['last7_count'] = int(
            conn.execute(
                f'SELECT COUNT(1) FROM exams e {scope_where} AND e.submitted_at >= datetime(\"now\", \"-7 day\")',
                scope_params,
            ).fetchone()[0]
            or 0
        )

        recent_rows = conn.execute(
            f'SELECT * FROM exams e {scope_where} ORDER BY e.submitted_at DESC LIMIT 7',
            scope_params,
        ).fetchall()
        recent_exams = [dict(r) for r in recent_rows]

        recent_ids = [int(r['id']) for r in recent_exams if r.get('id') is not None]
        if recent_ids:
            placeholders = ','.join(['?'] * len(recent_ids))
            rows = conn.execute(
                f"""
                SELECT exam_id,
                       COUNT(1) as total,
                       SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END) as correct
                FROM exam_questions
                WHERE exam_id IN ({placeholders})
                GROUP BY exam_id
                """,
                recent_ids,
            ).fetchall()
            rstats = {int(r['exam_id']): {'total': int(r['total'] or 0), 'correct': int(r['correct'] or 0)} for r in rows}
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

        # 题型分布 + 正确率：最近 30 天（按当前范围统计）
        include_public = (not bank_id) and (filter_source in ('all', 'public'))
        include_bank = (filter_source in ('all', 'user_bank')) or bool(bank_id)

        merged: dict[str, dict[str, int]] = {}
        if include_public:
            where = 'WHERE e.user_id=? AND e.status="submitted" AND e.submitted_at >= datetime("now", "-30 day")'
            params = [uid]
            where += ' AND (e.config_json IS NULL OR (e.config_json NOT LIKE ? AND e.config_json NOT LIKE ?))'
            params.append('%"source": "user_bank"%')
            params.append('%"source":"user_bank"%')
            if subject != 'all':
                where += ' AND e.subject = ?'
                params.append(subject)

            rows = conn.execute(
                f"""
                SELECT q.type as p_type,
                       COUNT(1) as cnt,
                       SUM(CASE WHEN eq.is_correct=1 THEN 1 ELSE 0 END) as correct
                FROM exams e
                JOIN exam_questions eq ON eq.exam_id = e.id
                JOIN questions q ON q.id = eq.question_id
                {where}
                  AND q.type IS NOT NULL AND TRIM(q.type) != ''
                GROUP BY q.type
                """,
                params,
            ).fetchall()
            for r in rows or []:
                pt = (r['p_type'] or '').strip()
                if not pt:
                    continue
                if pt not in merged:
                    merged[pt] = {'count': 0, 'correct': 0}
                merged[pt]['count'] += int(r['cnt'] or 0)
                merged[pt]['correct'] += int(r['correct'] or 0)

        if include_bank:
            where = 'WHERE e.user_id=? AND e.status="submitted" AND e.submitted_at >= datetime("now", "-30 day")'
            params = [uid]
            where += ' AND (e.config_json LIKE ? OR e.config_json LIKE ?)'
            params.append('%"source": "user_bank"%')
            params.append('%"source":"user_bank"%')
            if subject != 'all':
                where += ' AND e.subject = ?'
                params.append(subject)
            if bank_id:
                where += ' AND (e.config_json LIKE ? OR e.config_json LIKE ? OR e.config_json LIKE ? OR e.config_json LIKE ?)'
                bid_str = str(int(bank_id))
                params.append(f'%"bank_id": {bid_str},%')
                params.append('%"bank_id": ' + bid_str + '}%')
                params.append(f'%"bank_id":{bid_str},%')
                params.append('%"bank_id":' + bid_str + '}%')

            rows = conn.execute(
                f"""
                SELECT q.type as p_type,
                       COUNT(1) as cnt,
                       SUM(CASE WHEN eq.is_correct=1 THEN 1 ELSE 0 END) as correct
                FROM exams e
                JOIN exam_questions eq ON eq.exam_id = e.id
                JOIN user_bank_questions q ON q.id = eq.question_id
                {where}
                  AND q.type IS NOT NULL AND TRIM(q.type) != ''
                GROUP BY q.type
                """,
                params,
            ).fetchall()
            for r in rows or []:
                pt = (r['p_type'] or '').strip()
                if not pt:
                    continue
                if pt not in merged:
                    merged[pt] = {'count': 0, 'correct': 0}
                merged[pt]['count'] += int(r['cnt'] or 0)
                merged[pt]['correct'] += int(r['correct'] or 0)

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

        # 得分分布（全量，按当前范围统计）
        try:
            bins = [
                {'label': '0-59', 'count': 0},
                {'label': '60-69', 'count': 0},
                {'label': '70-79', 'count': 0},
                {'label': '80-89', 'count': 0},
                {'label': '90-100', 'count': 0},
            ]
            rows = conn.execute(
                f"SELECT e.total_score as score FROM exams e {scope_where}",
                scope_params,
            ).fetchall()
            for r in rows or []:
                try:
                    score = float(r['score'] or 0.0)
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

        # 建议（基于统计结果）
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
                data_tips.append('平均正确率不错：建议提高“混合题型比例”，并在错题型上做小卷回归。')
            else:
                data_tips.append('平均正确率很高：可以缩短时间限制做“速度训练”，提升稳定性。')

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
    
    conn = get_db()
    exam = conn.execute('SELECT * FROM exams WHERE id=?', (exam_id,)).fetchone()
    
    # 管理员可查看任意用户的考试
    if not exam:
        return "考试不存在或无权限", 403
    if exam['user_id'] != uid and not session.get('is_admin'):
        return "考试不存在或无权限", 403
    
    # 统计每题对错
    cfg = _parse_exam_config(exam['config_json'] if exam else None)
    source = _exam_source_from_cfg(cfg)

    if source == 'user_bank':
        rows = conn.execute(
            """
            SELECT eq.*, q.type, q.content, q.options, q.answer, q.analysis
            FROM exam_questions eq
            JOIN user_bank_questions q ON q.id = eq.question_id
            WHERE eq.exam_id=?
            ORDER BY eq.order_index
            """,
            (exam_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT eq.*, q.type, q.content, q.options, q.answer, q.analysis
            FROM exam_questions eq
            JOIN questions q ON q.id = eq.question_id
            WHERE eq.exam_id=?
            ORDER BY eq.order_index
            """,
            (exam_id,),
        ).fetchall()
    
    total = len(rows)
    correct = sum(1 for r in rows if (r['is_correct'] or 0) == 1)
    acc = round(correct*100.0/total, 1) if total else 0.0
    
    data = {
        'exam': dict(exam),
        'total': total,
        'correct': correct,
        'accuracy': acc,
        'items': [],
        'exam_source': source,
        'exam_bank_id': cfg.get('bank_id') if source == 'user_bank' else None,
    }

    try:
        from app.core.utils.pqf_rows import pqf_row_to_internal

        scope = 'user_bank' if source == 'user_bank' else 'question_center'
        data['items'] = [pqf_row_to_internal(r, scope=scope) for r in rows]
    except Exception:
        data['items'] = [dict(r) for r in rows]
    
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

    conn = get_db()
    exam = conn.execute('SELECT * FROM exams WHERE id=?', (exam_id,)).fetchone()
    if not exam:
        return "考试不存在或无权限", 403
    if exam['user_id'] != uid and not session.get('is_admin'):
        return "考试不存在或无权限", 403

    exam_dict = dict(exam)
    cfg = _parse_exam_config(exam['config_json'] if exam else None)
    source = _exam_source_from_cfg(cfg)
    bank_id_val = cfg.get('bank_id') if source == 'user_bank' else None

    rows = conn.execute(
        """
        SELECT user_answer, is_correct
        FROM exam_questions
        WHERE exam_id=?
        ORDER BY order_index
        """,
        (exam_id,),
    ).fetchall()

    total = len(rows)
    correct = 0
    wrong = 0
    answered = 0

    for r in rows or []:
        ua = (r['user_answer'] or '').strip()
        if ua:
            answered += 1
        ic = r['is_correct']
        if (ic or 0) == 1:
            correct += 1
        else:
            wrong += 1

    unanswered = max(0, total - answered)
    accuracy = round(correct * 100.0 / total, 1) if total else 0.0

    used_sec, used_text = _format_used_seconds(exam_dict.get('started_at'), exam_dict.get('submitted_at'))
    avg_sec = (int(round(used_sec / total)) if used_sec is not None and total else None)

    return render_template(
        'exam/exam_settlement_v2.html',
        exam=exam_dict,
        total=total,
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

