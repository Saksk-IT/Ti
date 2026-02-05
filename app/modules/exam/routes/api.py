# -*- coding: utf-8 -*-
"""考试API路由"""
import json
from flask import Blueprint, request, jsonify, session
from app.core.utils.database import get_db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.models.exam import Exam
from app.core.utils.cache_utils import bump_user_quiz_version
from app.core.utils.options_parser import parse_options
from app.core.utils.validators import parse_int
from app.core.errors import BadRequestError

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
        conn = get_db()
        ex = conn.execute('SELECT user_id FROM exams WHERE id=?', (exam_id,)).fetchone()

        if not ex or ex['user_id'] != uid:
            return jsonify({'status': 'error', 'message': '考试不存在或无权限'}), 403

        conn.execute('DELETE FROM exams WHERE id=?', (exam_id,))
        conn.commit()

        return jsonify({'status': 'success'})

    # GET：返回考试详情（含题目）
    data = Exam.get_by_id(exam_id, uid)
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
    
    conn = get_db()
    exam = conn.execute('SELECT user_id, status FROM exams WHERE id=?', (exam_id,)).fetchone()
    
    if not exam or exam['user_id'] != uid:
        return jsonify({'status':'error','message':'考试不存在或无权限'}), 403
    
    if exam['status'] == 'submitted':
        return jsonify({'status':'error','message':'考试已提交，不可保存草稿'}), 400
    
    for a in answers:
        try:
            qid = int(a.get('question_id'))
        except:
            continue
        ua = (a.get('user_answer') or '').strip()
        conn.execute(
            'UPDATE exam_questions SET user_answer=? WHERE exam_id=? AND question_id=?',
            (ua, exam_id, qid)
        )
    
    conn.commit()
    return jsonify({'status':'success'})


@exam_api_bp.route('/exams/<int:exam_id>/mistakes', methods=['POST'])
@auth_required  # 支持session和JWT（小程序）
def api_exam_to_mistakes(exam_id):
    """将考试错题加入错题本"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status':'unauthorized','message':'请先登录'}), 401
    
    conn = get_db()
    exam = conn.execute('SELECT * FROM exams WHERE id=?', (exam_id,)).fetchone()
    
    if not exam or exam['user_id'] != uid:
        return jsonify({'status':'error','message':'考试不存在或无权限'}), 403
    
    if exam['status'] != 'submitted':
        return jsonify({'status':'error','message':'请在提交考试后再加入错题本'}), 400

    cfg = {}
    try:
        cfg = json.loads(exam['config_json'] or '{}')
        if not isinstance(cfg, dict):
            cfg = {}
    except Exception:
        cfg = {}

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
    
    wrongs = conn.execute(
        'SELECT question_id FROM exam_questions WHERE exam_id=? AND (is_correct IS NULL OR is_correct=0)',
        (exam_id,)
    ).fetchall()
    
    count = 0
    for r in wrongs:
        qid = r['question_id']
        if source == 'user_bank':
            conn.execute(
                """
                INSERT INTO user_bank_mistakes (user_id, bank_id, question_id, wrong_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, question_id) DO UPDATE SET
                  wrong_count = wrong_count + 1,
                  bank_id = excluded.bank_id,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (uid, int(bank_id_val), qid),
            )
        else:
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
                    (uid, qid),
                )
            except Exception:
                conn.execute(
                    """
                    INSERT INTO mistakes (user_id, question_id, wrong_count)
                    VALUES (?, ?, 1)
                    ON CONFLICT(user_id, question_id) DO UPDATE SET wrong_count = wrong_count + 1
                    """,
                    (uid, qid),
                )
        count += 1
    
    conn.commit()
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

    conn = get_db()
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

        rows = conn.execute(
            """
            SELECT id, title, config_json, created_at, updated_at
            FROM exam_templates
            WHERE user_id=?
            ORDER BY updated_at DESC, id DESC
            """,
            (uid,),
        ).fetchall()

        templates = []
        for r in rows:
            cfg = {}
            try:
                cfg = json.loads(r['config_json'] or '{}')
                if not isinstance(cfg, dict):
                    cfg = {}
            except Exception:
                cfg = {}

            cfg_source = str(cfg.get('source') or 'public').strip().lower()
            if cfg_source not in ('public', 'user_bank'):
                cfg_source = 'public'

            cfg_subject = str(cfg.get('subject') or 'all').strip()
            cfg_bank_id = parse_int(cfg.get('bank_id'), 0, 0)
            cfg_bank_id = cfg_bank_id if cfg_bank_id > 0 else None

            if filter_source != 'all' and cfg_source != filter_source:
                continue
            if filter_source == 'public' and filter_subject:
                # 允许“通用模板”：subject=all
                if cfg_subject not in (filter_subject, 'all'):
                    continue
            if filter_source == 'user_bank' and filter_bank_id:
                if cfg_bank_id != filter_bank_id:
                    continue

            templates.append({
                'id': r['id'],
                'title': r['title'] or '未命名模板',
                'config': cfg,
                'created_at': r['created_at'],
                'updated_at': r['updated_at'],
            })

        return jsonify({'status': 'success', 'data': templates})

    data = request.json or {}
    title = (data.get('title') or '').strip()
    config = data.get('config') or {}

    if not title:
        return jsonify({'status': 'error', 'message': '模板名称不能为空'}), 400
    if not isinstance(config, dict):
        return jsonify({'status': 'error', 'message': '模板内容不合法'}), 400

    conn.execute(
        'INSERT INTO exam_templates (user_id, title, config_json) VALUES (?, ?, ?)',
        (uid, title, json.dumps(config, ensure_ascii=False)),
    )
    template_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()

    return jsonify({'status': 'success', 'id': template_id})


@exam_api_bp.route('/exams/templates/<int:template_id>', methods=['DELETE'])
@auth_required
def api_exam_template_delete(template_id):
    """Delete exam template."""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    conn = get_db()
    row = conn.execute(
        'SELECT user_id FROM exam_templates WHERE id=?',
        (template_id,),
    ).fetchone()

    if not row or row['user_id'] != uid:
        return jsonify({'status': 'error', 'message': '模板不存在或无权限'}), 403

    conn.execute('DELETE FROM exam_templates WHERE id=?', (template_id,))
    conn.commit()
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

    conn = get_db()

    # 科目白名单（按权限+锁定过滤）：用于校验 subject 参数
    from app.core.utils.subject_permissions import get_user_accessible_subjects

    subjects: list[str] = []
    try:
        accessible_subject_ids = [int(x) for x in (get_user_accessible_subjects(uid) or [])]
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
        subjects = [str(r['name']).strip() for r in (rows or []) if r and r['name']]

    # Web 行为：个人题库时隐藏/禁用科目筛选
    if filter_source == 'user_bank':
        subject = 'all'

    if subject != 'all' and subject not in subjects:
        subject = 'all'

    # Web 行为：公共题库时禁用题库筛选
    if filter_source == 'public':
        bank_id = None

    ongoing_params = [uid]
    ongoing_where = 'WHERE user_id=? AND status="ongoing"'

    if filter_source == 'user_bank':
        ongoing_where += ' AND config_json LIKE ?'
        ongoing_params.append('%"source": "user_bank"%')
    elif filter_source == 'public':
        ongoing_where += ' AND (config_json IS NULL OR config_json NOT LIKE ?)'
        ongoing_params.append('%"source": "user_bank"%')

    if subject != 'all':
        ongoing_where += ' AND subject = ?'
        ongoing_params.append(subject)

    if bank_id:
        ongoing_where += ' AND (config_json LIKE ? OR config_json LIKE ?)'
        ongoing_params.append(f'%"bank_id": {int(bank_id)},%')
        ongoing_params.append('%"bank_id": ' + str(int(bank_id)) + '}%')

    ongoing = conn.execute(
        f'SELECT * FROM exams {ongoing_where} ORDER BY started_at DESC',
        ongoing_params,
    ).fetchall()

    where = 'WHERE user_id=? AND status="submitted"'
    params = [uid]

    if filter_source == 'user_bank':
        where += ' AND config_json LIKE ?'
        params.append('%"source": "user_bank"%')
    elif filter_source == 'public':
        where += ' AND (config_json IS NULL OR config_json NOT LIKE ?)'
        params.append('%"source": "user_bank"%')

    if subject != 'all':
        where += ' AND subject = ?'
        params.append(subject)

    if bank_id:
        where += ' AND (config_json LIKE ? OR config_json LIKE ?)'
        params.append(f'%"bank_id": {int(bank_id)},%')
        params.append('%"bank_id": ' + str(int(bank_id)) + '}%')

    total = int(conn.execute(f'SELECT COUNT(1) FROM exams {where}', params).fetchone()[0] or 0)
    offset = (page - 1) * size
    submitted = conn.execute(
        f'SELECT * FROM exams {where} ORDER BY submitted_at DESC LIMIT ? OFFSET ?',
        params + [size, offset],
    ).fetchall()

    # exam_questions 统计：total/correct/accuracy
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
            stats_map[ex_id] = {'total': int(r['total'] or 0), 'correct': int(r['correct'] or 0)}

    ongoing_payload = [_enrich_exam_row(dict(r), stats_map) for r in ongoing]
    submitted_payload = [_enrich_exam_row(dict(r), stats_map) for r in submitted]

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

    conn = get_db()

    # 可选筛选：与 /exams/records 对齐（便于小程序按“所选题库/科目”查看数据）
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
        subjects = [str(r['name']).strip() for r in (rows or []) if r and r['name']]

    # 个人题库时隐藏/禁用科目筛选
    if filter_source == 'user_bank':
        subject = 'all'

    if subject != 'all' and subject not in subjects:
        subject = 'all'

    # 公共题库时禁用题库筛选
    if filter_source == 'public':
        bank_id = None

    where = 'WHERE e.user_id=? AND e.status="submitted"'
    params: list = [uid]

    if filter_source == 'user_bank':
        where += ' AND e.config_json LIKE ?'
        params.append('%"source": "user_bank"%')
    elif filter_source == 'public':
        where += ' AND (e.config_json IS NULL OR e.config_json NOT LIKE ?)'
        params.append('%"source": "user_bank"%')

    if subject != 'all':
        where += ' AND e.subject = ?'
        params.append(subject)

    if bank_id:
        where += ' AND (e.config_json LIKE ? OR e.config_json LIKE ?)'
        params.append(f'%"bank_id": {int(bank_id)},%')
        params.append('%"bank_id": ' + str(int(bank_id)) + '}%')

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

    stats_overview['submitted_count'] = int(conn.execute(f'SELECT COUNT(1) FROM exams e {where}', params).fetchone()[0] or 0)

    avg_score = conn.execute(f'SELECT AVG(e.total_score) FROM exams e {where}', params).fetchone()[0]
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
          {where}
          GROUP BY e.id
        ) t
        """,
        params,
    ).fetchone()[0]
    stats_overview['avg_accuracy'] = round(float(avg_acc or 0), 1)

    stats_overview['last7_count'] = int(
        conn.execute(
            f'SELECT COUNT(1) FROM exams e {where} AND e.submitted_at >= datetime("now", "-7 day")',
            params,
        ).fetchone()[0]
        or 0
    )

    recent_rows = conn.execute(
        f'SELECT * FROM exams e {where} ORDER BY e.submitted_at DESC LIMIT 7',
        params,
    ).fetchall()
    recent_exams = [dict(r) for r in recent_rows]

    # 近期考试统计（准确率 + bank_id/source）
    stats_map: dict[int, dict[str, int]] = {}
    recent_ids = [int(r['id']) for r in recent_exams if r and r.get('id') is not None]
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
        for r in rows:
            ex_id = int(r['exam_id'])
            stats_map[ex_id] = {'total': int(r['total'] or 0), 'correct': int(r['correct'] or 0)}

        recent_exams = [_enrich_exam_row(e, stats_map) for e in recent_exams]
        if recent_exams:
            stats_overview['last7_avg_accuracy'] = round(
                sum(float(e.get('accuracy') or 0) for e in recent_exams) / len(recent_exams),
                1,
            )

    # 题型分布：最近 30 天（可按 source/subject/bank_id 筛选）
    merged: dict[str, int] = {}

    if filter_source in ('all', 'public'):
        pub_where = where
        pub_params = list(params)
        if filter_source == 'all':
            pub_where += ' AND (e.config_json IS NULL OR e.config_json NOT LIKE ?)'
            pub_params.append('%"source": "user_bank"%')

        rows = conn.execute(
            f"""
            SELECT q.type as p_type, COUNT(1) as cnt
            FROM exams e
            JOIN exam_questions eq ON eq.exam_id = e.id
            JOIN questions q ON q.id = eq.question_id
            {pub_where}
              AND e.submitted_at >= datetime("now", "-30 day")
              AND q.type IS NOT NULL AND TRIM(q.type) != ''
            GROUP BY q.type
            """,
            pub_params,
        ).fetchall()
        for r in rows or []:
            pt = (r['p_type'] or '').strip()
            if not pt:
                continue
            merged[pt] = merged.get(pt, 0) + int(r['cnt'] or 0)

    if filter_source in ('all', 'user_bank'):
        bank_where = where
        bank_params = list(params)
        if filter_source == 'all':
            bank_where += ' AND e.config_json LIKE ?'
            bank_params.append('%"source": "user_bank"%')

        rows = conn.execute(
            f"""
            SELECT q.type as p_type, COUNT(1) as cnt
            FROM exams e
            JOIN exam_questions eq ON eq.exam_id = e.id
            JOIN user_bank_questions q ON q.id = eq.question_id
            {bank_where}
              AND e.submitted_at >= datetime("now", "-30 day")
              AND q.type IS NOT NULL AND TRIM(q.type) != ''
            GROUP BY q.type
            """,
            bank_params,
        ).fetchall()
        for r in rows or []:
            pt = (r['p_type'] or '').strip()
            if not pt:
                continue
            merged[pt] = merged.get(pt, 0) + int(r['cnt'] or 0)

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
