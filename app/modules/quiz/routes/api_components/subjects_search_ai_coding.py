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


@quiz_api_bp.route('/subjects', methods=['GET'])
@auth_required  # 支持session和JWT
@limiter.exempt
def api_subjects():
    """获取科目列表（添加权限过滤）"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    
    try:
        user_id = current_user_id()

        cache_key = None
        cache_ttl = 0

        def _ret(payload: dict):
            if cache_key and cache_ttl > 0:
                try:
                    redis_set_json(cache_key, payload, ttl_seconds=cache_ttl)
                except Exception:
                    pass
            return jsonify(payload)

        if user_id and bool(current_app.config.get('QUIZ_API_CACHE_ENABLED', True)):
            try:
                cache_ttl = int(current_app.config.get('QUIZ_CACHE_TTL_SUBJECTS_SECONDS', 60) or 60)
            except Exception:
                cache_ttl = 60
            if cache_ttl > 0:
                try:
                    cache_key = make_cache_key(
                        'quiz:subjects',
                        {
                            'uid': int(user_id),
                            'uv': get_user_quiz_version(int(user_id)),
                            'sv': get_subjects_version(),
                        },
                    )
                    cached = redis_get_json(cache_key)
                    if isinstance(cached, dict) and cached.get('status') == 'success' and 'subjects' in cached:
                        return jsonify(cached)
                except Exception:
                    cache_key = None

        conn = get_db()
        
        if user_id:
            # 获取用户可访问的科目
            accessible_subject_ids = get_user_accessible_subjects(user_id)
            if not accessible_subject_ids:
                return _ret({'status': 'success', 'subjects': []})
            
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            rows = conn.execute(
                f'''SELECT DISTINCT s.name 
                    FROM subjects s 
                    WHERE s.id IN ({placeholders}) AND (s.is_locked=0 OR s.is_locked IS NULL)
                    ORDER BY s.id''',
                accessible_subject_ids
            ).fetchall()
        else:
            # 未登录用户：返回空列表
            rows = []
        
        subjects = [row[0] for row in rows if row and row[0]]
        return _ret({'status': 'success', 'subjects': subjects})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'subjects': []}), 500


@quiz_api_bp.route('/subjects/meta', methods=['GET'])
@auth_required  # 支持 session 和 JWT
@limiter.exempt
def api_subjects_meta():
    """获取科目元信息（id/name/题量），用于跨端对齐 Web「公共题库」页面。"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects

    try:
        uid = current_user_id()
        if not uid:
            return jsonify({'status': 'success', 'data': {'subjects': [], 'quiz_count': 0}})

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
                cache_ttl = int(current_app.config.get('QUIZ_CACHE_TTL_SUBJECTS_META_SECONDS', 60) or 60)
            except Exception:
                cache_ttl = 60
            if cache_ttl > 0:
                try:
                    cache_key = make_cache_key(
                        'quiz:subjects_meta',
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
        accessible_subject_ids = get_user_accessible_subjects(uid)
        if not accessible_subject_ids:
            return _ret({'status': 'success', 'data': {'subjects': [], 'quiz_count': 0}})

        placeholders = ','.join(['?'] * len(accessible_subject_ids))
        subject_rows = conn.execute(
            f"""
            SELECT id, name
            FROM subjects
            WHERE id IN ({placeholders})
              AND (is_locked=0 OR is_locked IS NULL)
            ORDER BY id
            """,
            accessible_subject_ids,
        ).fetchall()

        count_rows = conn.execute(
            f"""
            SELECT q.subject_id as subject_id, COUNT(*) as cnt
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE q.subject_id IN ({placeholders})
              AND (s.is_locked=0 OR s.is_locked IS NULL)
            GROUP BY q.subject_id
            """,
            accessible_subject_ids,
        ).fetchall()

        counts = {}
        for r in (count_rows or []):
            try:
                sid = r['subject_id']
                if sid is None:
                    continue
                counts[int(sid)] = int(r['cnt'] or 0)
            except Exception:
                continue

        subjects = []
        for r in (subject_rows or []):
            if not r or r['id'] is None:
                continue
            sid = int(r['id'])
            name = r['name'] or ''
            if not name:
                continue
            subjects.append({'id': sid, 'name': name, 'question_count': int(counts.get(sid, 0))})

        quiz_count = sum(int(s.get('question_count') or 0) for s in subjects)
        return _ret({'status': 'success', 'data': {'subjects': subjects, 'quiz_count': quiz_count}})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'data': {'subjects': [], 'quiz_count': 0}}), 500


@quiz_api_bp.route('/subjects/<subject>/info', methods=['GET'])
@auth_required  # 支持session和JWT
@limiter.exempt
def api_subject_info(subject):
    """获取科目详情信息"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    
    try:
        user_id = current_user_id()

        cache_key = None
        cache_ttl = 0
        if user_id and bool(current_app.config.get('QUIZ_API_CACHE_ENABLED', True)):
            try:
                cache_ttl = int(current_app.config.get('QUIZ_CACHE_TTL_SUBJECTS_META_SECONDS', 60) or 60)
            except Exception:
                cache_ttl = 60
            if cache_ttl > 0:
                try:
                    cache_key = make_cache_key(
                        'quiz:subject_info',
                        {
                            'uid': int(user_id),
                            'subject': str(subject),
                            'uv': get_user_quiz_version(int(user_id)),
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
        
        # 获取科目信息
        subject_row = conn.execute(
            'SELECT id, name FROM subjects WHERE name = ? AND (is_locked=0 OR is_locked IS NULL)',
            (subject,)
        ).fetchone()
        
        if not subject_row:
            return jsonify({'status': 'error', 'message': '科目不存在'}), 404
        
        subject_id = subject_row['id']
        
        # 检查用户权限
        if user_id:
            accessible_subject_ids = get_user_accessible_subjects(user_id)
            if not accessible_subject_ids or subject_id not in accessible_subject_ids:
                return jsonify({'status': 'error', 'message': '无权限访问该科目'}), 403
        
        # 获取题目总数
        total_count = conn.execute(
            'SELECT COUNT(*) FROM questions WHERE subject_id = ?',
            (subject_id,)
        ).fetchone()[0]

        # 获取该科目实际拥有的题型（用于小程序动态渲染）
        from app.core.utils.portable_question_format import portable_type_to_q_type

        type_rows = conn.execute(
            "SELECT DISTINCT type AS p_type FROM questions WHERE subject_id = ? AND type IS NOT NULL AND TRIM(type) != '' ORDER BY type",
            (subject_id,)
        ).fetchall()
        available_types = [
            portable_type_to_q_type(r['p_type'])
            for r in type_rows
            if r and r['p_type']
        ]
        
        # 获取作者信息（暂时设为空，后续可以从其他表获取）
        author = ''
        
        # 获取用户统计信息
        user_stats = {
            'done_count': 0,
            'wrong_count': 0,
            'favorite_count': 0,
            'note_count': 0,
            'last_activity': None
        }
        
        if user_id:
            # 已做题数（从user_answers表统计）
            done_count = conn.execute(
                'SELECT COUNT(DISTINCT question_id) FROM user_answers ua JOIN questions q ON ua.question_id = q.id WHERE ua.user_id = ? AND q.subject_id = ?',
                (user_id, subject_id)
            ).fetchone()[0]
            
            # 错题数
            wrong_count = conn.execute(
                'SELECT COUNT(*) FROM mistakes m JOIN questions q ON m.question_id = q.id WHERE m.user_id = ? AND q.subject_id = ?',
                (user_id, subject_id)
            ).fetchone()[0]
            
            # 收藏数
            favorite_count = conn.execute(
                'SELECT COUNT(*) FROM favorites f JOIN questions q ON f.question_id = q.id WHERE f.user_id = ? AND q.subject_id = ?',
                (user_id, subject_id)
            ).fetchone()[0]
            
            # 最后活动时间（从user_answers表获取最新的created_at）
            last_activity_row = conn.execute(
                'SELECT MAX(ua.created_at) as last_activity FROM user_answers ua JOIN questions q ON ua.question_id = q.id WHERE ua.user_id = ? AND q.subject_id = ?',
                (user_id, subject_id)
            ).fetchone()
            
            last_activity = last_activity_row['last_activity'] if last_activity_row and last_activity_row['last_activity'] else None
            
            user_stats = {
                'done_count': done_count,
                'wrong_count': wrong_count,
                'favorite_count': favorite_count,
                'note_count': 0,  # 笔记功能暂未实现
                'last_activity': last_activity
            }
        
        payload = {
            'status': 'success',
            'data': {
                'subject': subject,
                'total_count': total_count,
                'author': author,
                'available_types': available_types,
                'user_stats': user_stats
            }
        }

        if cache_key and cache_ttl > 0 and bool(current_app.config.get('QUIZ_API_CACHE_ENABLED', True)):
            try:
                redis_set_json(cache_key, payload, ttl_seconds=cache_ttl)
            except Exception:
                pass

        return jsonify(payload)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@quiz_api_bp.route('/subjects/<subject>/stats', methods=['GET'])
@auth_required  # 支持session和JWT
@limiter.exempt
def api_subject_stats_detail(subject):
    """科目统计详情（用于题库详情页-统计子页面）"""
    from datetime import datetime, timedelta
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
    from app.core.utils.portable_question_format import any_type_to_portable_type, portable_type_to_q_type

    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    window_days = request.args.get('days', 14, type=int)
    if window_days not in (7, 14, 30, 90):
        window_days = 14

    # 可选筛选：用于“错题/收藏/标签中心”的数据子页面（不传则按全题库统计）
    source = (request.args.get('source') or '').strip().lower()
    if source not in ('favorites', 'mistakes'):
        source = 'all'

    q_type_filter = (request.args.get('q_type') or request.args.get('type') or 'all')
    q_type_filter = (q_type_filter or '').strip()
    if q_type_filter.lower() == 'all':
        q_type_filter = ''
    portable_type_filter = any_type_to_portable_type(q_type_filter) if q_type_filter else ''

    tag = (request.args.get('tag') or '').strip()
    if tag and str(tag).lower() == 'all':
        tag = ''

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
            cache_ttl = int(current_app.config.get('QUIZ_CACHE_TTL_HISTORY_SECONDS', 30) or 30)
        except Exception:
            cache_ttl = 30
        if cache_ttl > 0:
            try:
                cache_key = make_cache_key(
                    'quiz:subject_stats_detail',
                    {
                        'uid': int(uid),
                        'subject': str(subject),
                        'days': int(window_days),
                        'source': source,
                        'type': q_type_filter,
                        'tag': tag,
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

    # 科目 + 权限
    subject_row = conn.execute(
        'SELECT id, name FROM subjects WHERE name = ? AND (is_locked=0 OR is_locked IS NULL)',
        (subject,),
    ).fetchone()
    if not subject_row:
        return jsonify({'status': 'error', 'message': '科目不存在'}), 404

    subject_id = int(subject_row['id'])
    accessible_subject_ids = get_user_accessible_subjects(uid) or []
    if subject_id not in accessible_subject_ids:
        return jsonify({'status': 'error', 'message': '无权限访问该科目'}), 403

    # window_days/source/q_type_filter/tag 已在函数开头解析（用于缓存 key 与业务逻辑一致）

    tag_cond = ''
    tag_params: list = []
    if tag:
        tag_ids = get_question_ids_by_tag(conn, uid, tag)
        if not tag_ids:
            return _ret({
                'status': 'success',
                'data': {
                    'subject': subject_row['name'] or subject,
                    'subject_id': subject_id,
                    'total_count': 0,
                    'answered': 0,
                    'correct': 0,
                    'wrong': 0,
                    'favorites': 0,
                    'mistakes': 0,
                    'mistakes_times': 0,
                    'accuracy': 0.0,
                    'completion': 0.0,
                    'streak_days': 0,
                    'last_activity': None,
                    'trend_days': window_days,
                    'trend': [],
                    'by_type': [],
                    'by_difficulty': [],
                    'advice': [],
                }
            })

        tag_ids = sorted({int(x) for x in tag_ids})
        if len(tag_ids) <= 900:
            placeholders = ','.join(['?'] * len(tag_ids))
            tag_cond = f' AND q.id IN ({placeholders})'
            tag_params = tag_ids
        else:
            # 避免 SQLite 参数上限（tag_ids 已强制 int 转换）
            tag_cond = ' AND q.id IN ({})'.format(','.join(str(i) for i in tag_ids))
            tag_params = []

    # 基于题目集合做统计：subject + (source/tag/q_type) 组合筛选
    base_from = """
    FROM questions q
    LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
    LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
    WHERE q.subject_id = ?
    """
    base_params: list = [uid, uid, subject_id]
    if q_type_filter:
        base_from += " AND q.type = ?"
        base_params.append(portable_type_filter)
    if tag_cond:
        base_from += tag_cond
        base_params.extend(tag_params)
    if source == 'favorites':
        base_from += " AND f.id IS NOT NULL"
    elif source == 'mistakes':
        base_from += " AND m.id IS NOT NULL"

    total_count = int(conn.execute("SELECT COUNT(1) " + base_from, base_params).fetchone()[0] or 0)

    # 已做/正确/最后活动
    row = conn.execute(
        """
        SELECT
          COUNT(*) AS answered,
          SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
          MAX(ua.created_at) AS last_activity
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.id
        LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
        LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
        WHERE ua.user_id = ? AND q.subject_id = ?
        """
        + (" AND q.type = ?" if q_type_filter else "")
        + tag_cond
        + (" AND f.id IS NOT NULL" if source == "favorites" else "")
        + (" AND m.id IS NOT NULL" if source == "mistakes" else ""),
        ([uid, uid, uid, subject_id] + ([portable_type_filter] if q_type_filter else []) + tag_params),
    ).fetchone()

    answered = int(row['answered'] or 0) if row else 0
    correct = int(row['correct'] or 0) if row else 0
    wrong = max(0, answered - correct)
    last_activity = (row['last_activity'] if row else None) or None

    favorites = int(conn.execute("SELECT COUNT(1) " + base_from + " AND f.id IS NOT NULL", base_params).fetchone()[0] or 0)

    mistakes_has_wrong_count = _column_exists('mistakes', 'wrong_count')
    try:
        if mistakes_has_wrong_count:
            m_row = conn.execute(
                "SELECT COUNT(1) AS cnt, SUM(COALESCE(m.wrong_count, 1)) AS times " + base_from + " AND m.id IS NOT NULL",
                base_params,
            ).fetchone()
            mistakes = int(m_row['cnt'] or 0) if m_row else 0
            mistakes_times = int(m_row['times'] or 0) if m_row else 0
        else:
            mistakes = int(
                conn.execute("SELECT COUNT(1) " + base_from + " AND m.id IS NOT NULL", base_params).fetchone()[0] or 0
            )
            mistakes_times = mistakes
    except Exception:
        mistakes = 0
        mistakes_times = 0

    accuracy = round(correct * 100 / answered, 1) if answered > 0 else 0.0
    completion = round(answered * 100 / total_count, 1) if total_count > 0 else 0.0

    # streak（注：基于 user_answers 的最新记录，属于“近似活跃”）
    streak_days = 0
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT DATE(ua.created_at) AS day
            FROM user_answers ua
            JOIN questions q ON ua.question_id = q.id
            LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
            LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
            WHERE ua.user_id = ? AND q.subject_id = ?
            """
            + (" AND q.type = ?" if q_type_filter else "")
            + tag_cond
            + (" AND f.id IS NOT NULL" if source == "favorites" else "")
            + (" AND m.id IS NOT NULL" if source == "mistakes" else "")
            + """
            ORDER BY day DESC
            LIMIT 120
            """,
            ([uid, uid, uid, subject_id] + ([portable_type_filter] if q_type_filter else []) + tag_params),
        ).fetchall()

        dates = []
        for r in rows or []:
            if not r or not r['day']:
                continue
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
    except Exception:
        streak_days = 0

    # trend：最近 N 天（基于 user_answers 的最新记录）
    trend = []
    try:
        days_back = max(1, window_days) - 1
        rows = conn.execute(
            """
            SELECT
              DATE(ua.created_at) AS day,
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            FROM user_answers ua
            JOIN questions q ON ua.question_id = q.id
            LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
            LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
            WHERE ua.user_id = ? AND q.subject_id = ?
              AND ua.created_at >= datetime('now', '+8 hours', ?)
            """
            + (" AND q.type = ?" if q_type_filter else "")
            + tag_cond
            + (" AND f.id IS NOT NULL" if source == "favorites" else "")
            + (" AND m.id IS NOT NULL" if source == "mistakes" else "")
            + """
            GROUP BY day
            ORDER BY day ASC
            """,
            ([uid, uid, uid, subject_id, f'-{days_back} days'] + ([portable_type_filter] if q_type_filter else []) + tag_params),
        ).fetchall()

        by_day = {}
        for r in rows or []:
            if not r or not r['day']:
                continue
            by_day[str(r['day'])] = {
                'answered': int(r['answered'] or 0),
                'correct': int(r['correct'] or 0),
            }

        start_day = today_bj() - timedelta(days=days_back)
        for i in range(0, days_back + 1):
            d = (start_day + timedelta(days=i)).strftime('%Y-%m-%d')
            item = by_day.get(d) or {'answered': 0, 'correct': 0}
            a = int(item.get('answered') or 0)
            c = int(item.get('correct') or 0)
            trend.append({'day': d, 'answered': a, 'correct': c, 'wrong': max(0, a - c)})
    except Exception:
        trend = []

    # by_type：总题/已做/正确率/覆盖率 + 收藏/错题
    by_type = []
    try:
        total_rows = conn.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(q.type), ''), 'unknown') AS p_type, COUNT(*) AS total
            """
            + base_from
            + """
            GROUP BY COALESCE(NULLIF(TRIM(q.type), ''), 'unknown')
            ORDER BY total DESC
            """,
            base_params,
        ).fetchall()
        total_map = {str(r['p_type']): int(r['total'] or 0) for r in (total_rows or []) if r}

        answered_rows = conn.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(q.type), ''), 'unknown') AS p_type,
                   COUNT(*) AS answered,
                   SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            FROM user_answers ua
            JOIN questions q ON ua.question_id = q.id
            LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
            LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
            WHERE ua.user_id = ? AND q.subject_id = ?
            """
            + (" AND q.type = ?" if q_type_filter else "")
            + tag_cond
            + (" AND f.id IS NOT NULL" if source == "favorites" else "")
            + (" AND m.id IS NOT NULL" if source == "mistakes" else "")
            + """
            GROUP BY COALESCE(NULLIF(TRIM(q.type), ''), 'unknown')
            """,
            ([uid, uid, uid, subject_id] + ([portable_type_filter] if q_type_filter else []) + tag_params),
        ).fetchall()
        answered_map = {
            str(r['p_type']): {'answered': int(r['answered'] or 0), 'correct': int(r['correct'] or 0)}
            for r in (answered_rows or [])
            if r
        }

        fav_rows = conn.execute(
            "SELECT COALESCE(NULLIF(TRIM(q.type), ''), 'unknown') AS p_type, COUNT(*) AS cnt "
            + base_from
            + " AND f.id IS NOT NULL GROUP BY COALESCE(NULLIF(TRIM(q.type), ''), 'unknown')",
            base_params,
        ).fetchall()
        fav_map = {str(r['p_type']): int(r['cnt'] or 0) for r in (fav_rows or []) if r}

        mis_rows = conn.execute(
            "SELECT COALESCE(NULLIF(TRIM(q.type), ''), 'unknown') AS p_type, COUNT(*) AS cnt "
            + base_from
            + " AND m.id IS NOT NULL GROUP BY COALESCE(NULLIF(TRIM(q.type), ''), 'unknown')",
            base_params,
        ).fetchall()
        mis_map = {str(r['p_type']): int(r['cnt'] or 0) for r in (mis_rows or []) if r}

        keys = set(total_map.keys()) | set(answered_map.keys()) | set(fav_map.keys()) | set(mis_map.keys())
        for k in keys:
            q_type_disp = '未知' if str(k) in ('unknown', '') else portable_type_to_q_type(k)
            total = int(total_map.get(k, 0))
            a = int((answered_map.get(k) or {}).get('answered', 0))
            c = int((answered_map.get(k) or {}).get('correct', 0))
            w = max(0, a - c)
            by_type.append({
                'q_type': q_type_disp,
                'total': total,
                'answered': a,
                'correct': c,
                'wrong': w,
                'accuracy': round(c * 100 / a, 1) if a > 0 else 0.0,
                'completion': round(a * 100 / total, 1) if total > 0 else 0.0,
                'favorites': int(fav_map.get(k, 0)),
                'mistakes': int(mis_map.get(k, 0)),
            })

        by_type.sort(key=lambda x: (-int(x.get('answered') or 0), str(x.get('q_type') or '')))
    except Exception:
        by_type = []

    # by_difficulty（可选）
    by_difficulty = []
    if _column_exists('questions', 'difficulty'):
        try:
            total_rows = conn.execute(
                "SELECT COALESCE(q.difficulty, 1) AS difficulty, COUNT(*) AS total " + base_from + " GROUP BY difficulty ORDER BY difficulty ASC",
                base_params,
            ).fetchall()
            total_map = {int(r['difficulty'] or 1): int(r['total'] or 0) for r in (total_rows or []) if r}

            ans_rows = conn.execute(
                """
                SELECT COALESCE(q.difficulty, 1) AS difficulty,
                       COUNT(*) AS answered,
                       SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
                FROM user_answers ua
                JOIN questions q ON ua.question_id = q.id
                LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
                LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
                WHERE ua.user_id = ? AND q.subject_id = ?
                """
                + (" AND q.type = ?" if q_type_filter else "")
                + tag_cond
                + (" AND f.id IS NOT NULL" if source == "favorites" else "")
                + (" AND m.id IS NOT NULL" if source == "mistakes" else "")
                + """
                GROUP BY q.difficulty
                ORDER BY difficulty ASC
                """,
                ([uid, uid, uid, subject_id] + ([portable_type_filter] if q_type_filter else []) + tag_params),
            ).fetchall()
            ans_map = {
                int(r['difficulty'] or 1): {'answered': int(r['answered'] or 0), 'correct': int(r['correct'] or 0)}
                for r in (ans_rows or [])
                if r
            }

            def _diff_label(d: int) -> str:
                return {1: '简单', 2: '中等', 3: '困难'}.get(d, f'难度{d}')

            keys = sorted(set(total_map.keys()) | set(ans_map.keys()))
            for d in keys:
                total = int(total_map.get(d, 0))
                a = int((ans_map.get(d) or {}).get('answered', 0))
                c = int((ans_map.get(d) or {}).get('correct', 0))
                by_difficulty.append({
                    'difficulty': int(d),
                    'label': _diff_label(int(d)),
                    'total': total,
                    'answered': a,
                    'correct': c,
                    'wrong': max(0, a - c),
                    'accuracy': round(c * 100 / a, 1) if a > 0 else 0.0,
                    'completion': round(a * 100 / total, 1) if total > 0 else 0.0,
                })
        except Exception:
            by_difficulty = []

    # advice（尽量短、可执行）
    advice = []
    try:
        if total_count <= 0:
            advice = [{'title': '暂无题目', 'content': '该题库目前没有可练习的题目。'}]
        else:
            if answered < 10:
                advice.append({'title': '先建立手感', 'content': '建议先从“练习-全题库”开始，连续做 20~30 题快速熟悉题型与知识点。'})
            if completion < 35:
                advice.append({'title': '提高完成度', 'content': '当前覆盖率偏低，建议每天固定一段时间刷题，优先把“未做”题补齐。'})
            if accuracy < 65 and answered >= 10:
                advice.append({'title': '聚焦薄弱点', 'content': '正确率偏低，建议先做“错题”复盘，再回到练习巩固。'})
            if mistakes_times >= 20:
                advice.append({'title': '错题要闭环', 'content': '错题次数较多，建议用“背题”模式强化记忆，并在错因处做一次总结。'})

            weak = [r for r in (by_type or []) if int(r.get('answered') or 0) >= 5]
            weak.sort(key=lambda x: (float(x.get('accuracy') or 0.0), -int(x.get('answered') or 0)))
            if weak[:2]:
                names = '、'.join([str(x.get('q_type')) for x in weak[:2]])
                advice.append({'title': '优先攻克题型', 'content': f'你在「{names}」上的正确率相对更低，建议优先针对性练习并复盘。'})
    except Exception:
        advice = []

    return _ret({
        'status': 'success',
        'data': {
            'subject': subject_row['name'] or subject,
            'subject_id': subject_id,
            'total_count': total_count,
            'answered': answered,
            'correct': correct,
            'wrong': wrong,
            'favorites': favorites,
            'mistakes': mistakes,
            'mistakes_times': mistakes_times,
            'accuracy': accuracy,
            'completion': completion,
            'streak_days': streak_days,
            'last_activity': last_activity,
            'trend_days': window_days,
            'trend': trend,
            'by_type': by_type,
            'by_difficulty': by_difficulty,
            'advice': advice,
        }
    })


def _api_subject_guard(conn, uid: int, subject: str):
    """复用 subject 校验 + 权限校验（供 subject 统计/列表类接口使用）。"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects

    subject_row = conn.execute(
        'SELECT id, name FROM subjects WHERE name = ? AND (is_locked=0 OR is_locked IS NULL)',
        (subject,),
    ).fetchone()
    if not subject_row:
        return None, None, (jsonify({'status': 'error', 'message': '科目不存在'}), 404)

    subject_id = int(subject_row['id'])
    accessible_subject_ids = get_user_accessible_subjects(uid) or []
    if subject_id not in accessible_subject_ids:
        return None, None, (jsonify({'status': 'error', 'message': '无权限访问该科目'}), 403)

    return subject_row, subject_id, None


@quiz_api_bp.route('/subjects/<subject>/questions', methods=['GET'])
@auth_required  # 支持session和JWT
@limiter.exempt
def api_subject_questions(subject):
    """科目题目列表（用于统计页：错题/收藏列表与图表）。"""
    from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
    from app.core.utils.portable_question_format import any_type_to_portable_type, portable_question_to_internal

    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    conn = get_db()
    subject_row, subject_id, err = _api_subject_guard(conn, int(uid), subject)
    if err:
        return err

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 1000)
    source = (request.args.get('source') or 'all').strip().lower()  # all/favorites/mistakes
    q_type = (request.args.get('q_type') or request.args.get('type') or '').strip()
    if q_type.lower() == 'all':
        q_type = ''
    portable_type_filter = any_type_to_portable_type(q_type) if q_type else ''
    tag = (request.args.get('tag') or '').strip()
    if tag.lower() == 'all':
        tag = ''

    tag_cond = ''
    tag_params: list = []
    if tag:
        tag_ids = get_question_ids_by_tag(conn, int(uid), tag)
        if not tag_ids:
            return jsonify({
                'status': 'success',
                'data': {
                    'subject': subject_row['name'] or subject,
                    'subject_id': subject_id,
                    'questions': [],
                    'total': 0,
                    'page': page,
                    'per_page': per_page,
                }
            })

        tag_ids = sorted({int(x) for x in tag_ids})
        if len(tag_ids) <= 900:
            placeholders = ','.join(['?'] * len(tag_ids))
            tag_cond = f' AND q.id IN ({placeholders})'
            tag_params = tag_ids
        else:
            tag_cond = ' AND q.id IN ({})'.format(','.join(str(i) for i in tag_ids))
            tag_params = []

    def _column_exists(table: str, column: str) -> bool:
        try:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return any(r and r['name'] == column for r in rows)
        except Exception:
            return False

    # joins / order / select extras
    joins = ''
    join_params = []
    order_by = 'q.id DESC'
    select_extras = []

    if source == 'favorites':
        joins += ' JOIN favorites f ON q.id = f.question_id AND f.user_id = ?'
        join_params.append(int(uid))
        order_by = 'f.created_at DESC, q.id DESC'
        select_extras.append('f.created_at AS favorite_created_at')
    elif source == 'mistakes':
        joins += ' JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?'
        join_params.append(int(uid))

        m_cols = []
        if _column_exists('mistakes', 'updated_at'):
            m_cols.append('m.updated_at')
        if _column_exists('mistakes', 'last_updated'):
            m_cols.append('m.last_updated')
        if _column_exists('mistakes', 'created_at'):
            m_cols.append('m.created_at')
        if not m_cols:
            m_cols = ['NULL']
        m_time_expr = 'COALESCE({})'.format(','.join(m_cols)) if len(m_cols) >= 2 else m_cols[0]

        select_extras.extend([
            'm.wrong_count AS mistake_wrong_count',
            ('m.created_at' if _column_exists('mistakes', 'created_at') else m_time_expr) + ' AS mistake_created_at',
            m_time_expr + ' AS mistake_updated_at',
        ])
        order_by = f'm.wrong_count DESC, {m_time_expr} DESC, q.id DESC'
    else:
        source = 'all'

    where = ' WHERE q.subject_id = ?'
    where_params = [int(subject_id)]
    if q_type:
        where += ' AND q.type = ?'
        where_params.append(portable_type_filter)
    if tag_cond:
        where += tag_cond
        where_params.extend(tag_params)

    count_sql = f'SELECT COUNT(*) as cnt FROM questions q{joins}{where}'
    total = conn.execute(count_sql, join_params + where_params).fetchone()['cnt']

    if page < 1:
        page = 1
    offset = (page - 1) * per_page

    # last answer join（取该用户每题最后一次作答）
    answer_join = """
        LEFT JOIN (
            SELECT ua1.question_id,
                   ua1.is_correct AS last_is_correct,
                   ua1.created_at AS last_answered_at
            FROM user_answers ua1
            JOIN (
                SELECT question_id, MAX(created_at) AS max_created_at
                FROM user_answers
                WHERE user_id = ?
                GROUP BY question_id
            ) t
              ON t.question_id = ua1.question_id AND t.max_created_at = ua1.created_at
            WHERE ua1.user_id = ?
        ) a ON a.question_id = q.id
    """

    query_joins = joins + answer_join
    query_params = join_params + [int(uid), int(uid)]
    select_extras.extend([
        'a.last_is_correct AS last_is_correct',
        'a.last_answered_at AS last_answered_at',
    ])

    select_sql = 'q.*'
    if select_extras:
        select_sql += ', ' + ', '.join(select_extras)

    query_sql = f'SELECT {select_sql} FROM questions q{query_joins}{where} ORDER BY {order_by} LIMIT ? OFFSET ?'
    rows = conn.execute(query_sql, query_params + where_params + [per_page, offset]).fetchall()

    q_ids = [int(r['id']) for r in rows] if rows else []
    fav_set = set()
    mis_set = set()
    if q_ids:
        placeholders = ','.join('?' * len(q_ids))
        fav_rows = conn.execute(
            f'SELECT question_id FROM favorites WHERE user_id = ? AND question_id IN ({placeholders})',
            [int(uid)] + q_ids,
        ).fetchall()
        fav_set = {int(r['question_id']) for r in (fav_rows or []) if r and r['question_id'] is not None}

        mis_rows = conn.execute(
            f'SELECT question_id FROM mistakes WHERE user_id = ? AND question_id IN ({placeholders})',
            [int(uid)] + q_ids,
        ).fetchall()
        mis_set = {int(r['question_id']) for r in (mis_rows or []) if r and r['question_id'] is not None}

    def _preview(content: str) -> str:
        try:
            import re as _re
            text = _re.sub(r'<[^>]+>', '', content or '').replace('\n', ' ').strip()
        except Exception:
            text = (content or '').replace('\n', ' ').strip()
        return text[:80] + '...' if len(text) > 80 else text

    questions = []
    for r in rows or []:
        q = dict(r)
        qid = int(q.get('id') or 0)
        q['is_fav'] = 1 if qid in fav_set else 0
        q['is_mistake'] = 1 if qid in mis_set else 0
        # 兼容旧字段：q_type/answer/explanation/填空 __
        try:
            import json as _json
            portable = {
                "id": qid,
                "type": q.get("type") or "",
                "content": q.get("content") or "",
                "options": (_json.loads(q.get("options") or "[]") if isinstance(q.get("options"), str) else (q.get("options") or [])),
                "answer": (_json.loads(q.get("answer") or "[]") if isinstance(q.get("answer"), str) else (q.get("answer") or [])),
                "analysis": q.get("analysis") or "",
                "tags": (_json.loads(q.get("tags") or "[]") if isinstance(q.get("tags"), str) else (q.get("tags") or [])),
                "difficulty": q.get("difficulty") if q.get("difficulty") is not None else 1,
            }
            internal, _errors = portable_question_to_internal(portable, scope="question_center")
            q["q_type"] = internal.get("q_type") or ""
            q["content"] = internal.get("content") or q.get("content") or ""
            q["answer"] = internal.get("answer") or ""
            q["explanation"] = internal.get("explanation") or ""
        except Exception:
            q["q_type"] = ""
        q['content_preview'] = _preview(str(q.get('content') or ''))
        questions.append(q)

    return jsonify({
        'status': 'success',
        'data': {
            'subject': subject_row['name'] or subject,
            'subject_id': subject_id,
            'source': source,
            'questions': questions,
            'total': int(total or 0),
            'page': page,
            'per_page': per_page,
        }
    })


@quiz_api_bp.route('/subjects/<subject>/favorites/trend', methods=['GET'])
@auth_required  # 支持session和JWT
@limiter.exempt
def api_subject_favorites_trend(subject):
    """科目收藏趋势：按收藏创建时间聚合（用于收藏数据面板）。"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    window_days = request.args.get('days', 30, type=int)
    if window_days not in (7, 14, 30, 90):
        window_days = 30
    days_back = max(1, int(window_days)) - 1

    conn = get_db()
    subject_row, subject_id, err = _api_subject_guard(conn, int(uid), subject)
    if err:
        return err

    try:
        total = int(
            conn.execute(
                """
                SELECT COUNT(1) AS cnt
                FROM favorites f
                JOIN questions q ON q.id = f.question_id
                WHERE f.user_id = ? AND q.subject_id = ?
                """,
                (int(uid), int(subject_id)),
            ).fetchone()['cnt']
            or 0
        )
    except Exception:
        total = 0

    rows = conn.execute(
        """
        SELECT DATE(f.created_at) AS day, COUNT(*) AS added
        FROM favorites f
        JOIN questions q ON q.id = f.question_id
        WHERE f.user_id = ? AND q.subject_id = ?
          AND f.created_at >= datetime('now', '+8 hours', ?)
        GROUP BY day
        ORDER BY day ASC
        """,
        (int(uid), int(subject_id), f'-{days_back} days'),
    ).fetchall()

    by_day = {}
    for r in rows or []:
        day = (r['day'] if r else None) or None
        if not day:
            continue
        by_day[str(day)] = int((r['added'] if r else 0) or 0)

    start_day = today_bj() - timedelta(days=days_back)
    trend = []
    total_added = 0
    for i in range(0, days_back + 1):
        d = (start_day + timedelta(days=i)).strftime('%Y-%m-%d')
        added = int(by_day.get(d) or 0)
        total_added += added
        trend.append({'day': d, 'added': added})

    return jsonify({
        'status': 'success',
        'data': {
            'subject': subject_row['name'] or subject,
            'subject_id': int(subject_id),
            'days': int(window_days),
            'favorites_total': total,
            'total_added': total_added,
            'trend': trend,
        }
    })


@quiz_api_bp.route('/search', methods=['GET'])
@auth_required  # 支持session和JWT
@limiter.exempt
def api_search_questions():
    """题目搜索（JSON，用于小程序）

    Query:
    - keyword: 搜索关键词（必填）
    - subject: 科目名称（可选，默认 all）
    - q_type/type: 题型（可选，默认 all）
    - source: 数据范围（all/favorites/mistakes，可选）
    - tag: 标签筛选（用户私有，可选）
    - page/per_page: 分页
    """
    import re
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
    from app.core.utils.portable_question_format import any_type_to_portable_type, portable_type_to_q_type

    keyword = (request.args.get('keyword', '') or '').strip()
    subject = (request.args.get('subject', 'all') or 'all').strip()
    q_type = (request.args.get('q_type') or request.args.get('type') or 'all').strip()
    source = (request.args.get('source') or '').strip().lower()
    tag = (request.args.get('tag') or '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)

    uid = current_user_id()
    conn = get_db()

    # 无关键词：直接返回空结果（前端可做实时输入）
    if not keyword:
        return jsonify({
            'status': 'success',
            'data': {'questions': [], 'total': 0, 'page': page, 'per_page': per_page}
        })

    # 权限过滤：仅搜索可访问科目
    accessible_subject_ids = get_user_accessible_subjects(uid) if uid else []
    if not accessible_subject_ids:
        return jsonify({
            'status': 'success',
            'data': {'questions': [], 'total': 0, 'page': page, 'per_page': per_page}
        })

    search_term = f'%{keyword}%'
    sql_base = """
        SELECT q.id, q.content, q.type, s.name as subject,
               CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
               CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
        LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
        WHERE (s.is_locked=0 OR s.is_locked IS NULL)
          AND (q.content LIKE ? OR q.analysis LIKE ? OR q.options LIKE ? OR q.answer LIKE ?)
    """
    params = [uid, uid, search_term, search_term, search_term, search_term]

    placeholders = ','.join(['?'] * len(accessible_subject_ids))
    sql_base += f" AND q.subject_id IN ({placeholders})"
    params.extend(accessible_subject_ids)

    if subject and subject != 'all':
        sql_base += " AND s.name = ?"
        params.append(subject)

    if q_type and q_type != 'all':
        sql_base += " AND q.type = ?"
        params.append(any_type_to_portable_type(q_type))

    if source == 'favorites':
        sql_base += " AND f.id IS NOT NULL"
    elif source == 'mistakes':
        sql_base += " AND m.id IS NOT NULL"

    # 标签筛选：标签为用户私有（存储于 user_progress）
    if tag and str(tag).lower() != 'all':
        tag_ids = get_question_ids_by_tag(conn, uid, tag)
        if not tag_ids:
            return jsonify({
                'status': 'success',
                'data': {'questions': [], 'total': 0, 'page': page, 'per_page': per_page}
            })

        tag_ids = sorted({int(x) for x in tag_ids})
        if len(tag_ids) <= 900:
            placeholders = ','.join(['?'] * len(tag_ids))
            sql_base += f" AND q.id IN ({placeholders})"
            params.extend(tag_ids)
        else:
            # 避免 SQLite 参数上限（已强制 int 转换）
            sql_base += " AND q.id IN ({})".format(','.join(str(i) for i in tag_ids))

    # 统计总数
    count_sql = f"SELECT COUNT(*) FROM ({sql_base})"
    total = conn.execute(count_sql, params).fetchone()[0]

    if page < 1:
        page = 1
    offset = (page - 1) * per_page

    sql = sql_base + " ORDER BY q.id DESC LIMIT ? OFFSET ?"
    rows = conn.execute(sql, params + [per_page, offset]).fetchall()

    questions = []
    for row in rows:
        q = dict(row)
        content = q.get('content') or ''
        try:
            text = re.sub(r'<[^>]+>', '', str(content)).replace('\n', ' ').strip()
        except Exception:
            text = str(content).replace('\n', ' ').strip()
        if len(text) > 80:
            text = text[:80] + '...'
        questions.append({
            'id': q.get('id'),
            'content': q.get('content', ''),
            'content_preview': text,
            'q_type': portable_type_to_q_type(q.get('type', '')) if q.get('type') else '',
            'subject': q.get('subject', ''),
            'is_fav': q.get('is_fav', 0),
            'is_mistake': q.get('is_mistake', 0)
        })

    return jsonify({
        'status': 'success',
        'data': {
            'questions': questions,
            'total': total,
            'page': page,
            'per_page': per_page
        }
    })


def _ai_explain_rate_key():
    """AI 解析限流：优先按用户，其次按 IP。"""
    try:
        uid = current_user_id()
        if uid:
            return f"user:{int(uid)}"
    except Exception:
        pass
    try:
        from flask_limiter.util import get_remote_address

        return get_remote_address()
    except Exception:
        return 'unknown'

@quiz_api_bp.route('/ai/explain', methods=['POST'])
@auth_required  # 支持session和JWT
@limiter.limit("3 per minute;30 per hour", key_func=_ai_explain_rate_key)
def api_ai_explain():
    """AI 解析接口（阿里云百炼 DashScope OpenAI 兼容接口）。

    环境变量（推荐写入项目根目录 .env）：
    - DASHSCOPE_API_KEY: 百炼 API-KEY
    - DASHSCOPE_BASE_URL: 可选，北京默认 https://dashscope.aliyuncs.com/compatible-mode/v1
    - DASHSCOPE_MODEL: 可选，默认 qwen-plus
    """
    from flask import current_app
    from app.core.utils.subject_permissions import can_user_access_subject
    from app.modules.quiz.services.ai_explain_service import generate_ai_explain

    uid = current_user_id()
    data = request.json or {}

    # 允许前端仅传 question_id；后端优先用库内题目，避免前端篡改
    raw_qid = data.get('question_id')
    qid = None
    try:
        qid = int(raw_qid) if raw_qid is not None and str(raw_qid).strip() else None
    except Exception:
        qid = None

    payload = {
        'question_id': qid,
        'content': (data.get('content') or '').strip(),
        'q_type': (data.get('q_type') or '').strip(),
        'options': data.get('options'),
        'answer': (data.get('answer') or '').strip(),
    }

    if qid:
        q = Question.get_by_id(qid)
        if q:
            subject_id = q.get('subject_id')
            if subject_id and uid and not can_user_access_subject(uid, subject_id):
                return jsonify({'status': 'forbidden', 'message': '无权限访问该题目'}), 403

            payload['content'] = (q.get('content') or '').strip()
            payload['q_type'] = (q.get('q_type') or '').strip()
            payload['options'] = q.get('options')
            payload['answer'] = (q.get('answer') or '').strip()

    if not payload.get('content') and not payload.get('question_id'):
        return jsonify({'status': 'error', 'message': '缺少题目信息'}), 400

    api_key = (current_app.config.get('DASHSCOPE_API_KEY') or '').strip()
    base_url = (current_app.config.get('DASHSCOPE_BASE_URL') or '').strip()
    model = (current_app.config.get('DASHSCOPE_MODEL') or '').strip()
    timeout = int(current_app.config.get('DASHSCOPE_TIMEOUT') or 25)

    # 未配置密钥：保留旧行为，返回“占位解析”，同时提示如何配置
    if not api_key:
        tip = '（未配置 DASHSCOPE_API_KEY，当前为模板解析；配置后将自动使用百炼模型）'
        lines = [tip, '', '建议解题思路：', '1) 先圈出关键词与限定条件。', '2) 把题干转为可验证的结论/公式/步骤。', '3) 对选择题：用排除法 + 代入验证。', '4) 对填空/简答题：列步骤，逐步推导，最后回代检查。']
        return jsonify({'status': 'success', 'data': {'explain': '\n'.join(lines), 'provider': 'placeholder'}})

    # Redis 缓存：避免重复扣费/重复阻塞
    cache_key = None
    cache_ttl = int(current_app.config.get('AI_EXPLAIN_CACHE_TTL_SECONDS') or (30 * 24 * 60 * 60))
    if cache_ttl > 0:
        try:
            cache_key = make_cache_key(
                'quiz:ai_explain',
                {
                    'provider': 'dashscope',
                    'model': model or 'qwen-plus',
                    'base_url': base_url,
                    'payload': payload,
                },
            )
            cached = redis_get_json(cache_key)
            if isinstance(cached, dict) and cached.get('explain'):
                data_out = {
                    'explain': cached.get('explain'),
                    'provider': cached.get('provider') or 'dashscope',
                    'model': cached.get('model') or (model or 'qwen-plus'),
                    'cached': True,
                }
                return jsonify({'status': 'success', 'data': data_out})
        except Exception:
            cache_key = None

    try:
        explain = generate_ai_explain(
            api_key=api_key,
            base_url=base_url,
            model=model or 'qwen-plus',
            payload=payload,
            timeout=timeout,
        )
        data_out = {'explain': explain, 'provider': 'dashscope', 'model': model or 'qwen-plus'}
        if cache_key and cache_ttl > 0:
            try:
                redis_set_json(cache_key, data_out, ttl_seconds=cache_ttl)
            except Exception:
                pass
        return jsonify({'status': 'success', 'data': data_out})
    except Exception as e:
        current_app.logger.error('AI解析失败: %s', str(e), exc_info=True)
        return jsonify({'status': 'error', 'message': 'AI解析失败，请检查 DASHSCOPE_API_KEY / 计费状态 / 地域 Base URL 配置'}), 502


@quiz_api_bp.route('/coding/execute', methods=['POST'])
@limiter.limit("10 per minute")  # 限制执行频率：每分钟最多10次
def api_coding_execute():
    """
    代码执行接口（符合开发文档要求的路径：/api/coding/execute）
    
    Request Body:
    {
        "code": "print('Hello')",
        "language": "python",
        "input": "1\n2",  // 可选
        "time_limit": 5,  // 可选
        "memory_limit": 128  // 可选
    }
    
    Response:
    {
        "status": "success",
        "output": "Hello\n",
        "error": null,
        "execution_time": 0.05,
        "status_code": "success"
    }
    """
    if not session.get('user_id'):
        return jsonify({
            'status': 'unauthorized',
            'message': '请先登录'
        }), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        code = data.get('code', '').strip()
        language = data.get('language', 'python').lower()
        input_data = data.get('input', '')
        time_limit = data.get('time_limit', 5)
        memory_limit = data.get('memory_limit', 128)
        
        # 验证参数
        if not code:
            return jsonify({
                'status': 'error',
                'message': '代码不能为空'
            }), 400
        
        if language not in ['python']:  # 第一阶段只支持 Python
            return jsonify({
                'status': 'error',
                'message': f'不支持的编程语言: {language}'
            }), 400
        
        # 验证时间限制和内存限制
        if not isinstance(time_limit, (int, float)) or time_limit < 1 or time_limit > 30:
            time_limit = 5
        if not isinstance(memory_limit, int) or memory_limit < 64 or memory_limit > 512:
            memory_limit = 128
        
        # 执行代码
        from app.modules.coding.services.code_executor import PythonExecutor
        executor = PythonExecutor(time_limit=int(time_limit), memory_limit=memory_limit)
        result = executor.execute(code, input_data)
        
        # 限制输出长度（避免过长输出）
        if result.get('output') and len(result['output']) > 10000:
            result['output'] = result['output'][:10000] + '\n... (输出过长，已截断)'
        
        return jsonify({
            'status': 'success',
            'output': result.get('output', ''),
            'error': result.get('error'),
            'execution_time': result.get('execution_time', 0),
            'status_code': result.get('status', 'success')
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500
