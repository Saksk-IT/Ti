# -*- coding: utf-8 -*-
"""科目相关路由：科目列表、元信息、详情、统计、题目列表、收藏趋势。"""

from datetime import datetime, timedelta

from flask import request, jsonify, current_app
from app.core.utils.database import get_db, safe_in_clause
from app.core.extensions import limiter
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.redis_utils import redis_get_json, redis_set_json
from app.core.utils.cache_utils import (
    get_questions_version,
    get_subjects_version,
    get_user_quiz_version,
    make_cache_key,
)
from app.core.utils.time_utils import today_bj

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
        tag_cond, tag_params = safe_in_clause('q.id', tag_ids, '', [])

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
        tag_cond, tag_params = safe_in_clause('q.id', tag_ids, '', [])

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

