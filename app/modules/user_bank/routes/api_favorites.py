# -*- coding: utf-8 -*-

"""用户题库：收藏 API"""

from flask import request, jsonify

from app.core.utils.database import get_db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.time_utils import today_bj

from .api_base import user_bank_api_bp, check_bank_access


@user_bank_api_bp.route('/<int:bank_id>/favorites/trend', methods=['GET'])
@auth_required
def get_bank_favorites_trend(bank_id: int):
    """收藏趋势：按收藏创建时间聚合（用于收藏数据面板）。"""
    from datetime import datetime, timedelta

    user_id = current_user_id()
    has_access, _permission, _access_type = check_bank_access(user_id, bank_id)
    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    window_days = request.args.get('days', 30, type=int)
    if window_days not in (7, 14, 30, 90):
        window_days = 30

    days_back = max(1, int(window_days)) - 1

    conn = get_db()

    def _table_exists(table: str) -> bool:
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            return bool(row and (row['name'] or '').lower() == table.lower())
        except Exception:
            return False

    def _column_exists(table: str, column: str) -> bool:
        if not _table_exists(table):
            return False
        try:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return any(r and r['name'] == column for r in rows)
        except Exception:
            return False

    total = 0
    rows = []
    if _table_exists('user_bank_favorites') and _column_exists('user_bank_favorites', 'question_id') and _column_exists('user_bank_favorites', 'created_at'):
        fav_has_user = _column_exists('user_bank_favorites', 'user_id')
        fav_has_bank = _column_exists('user_bank_favorites', 'bank_id')
        try:
            if fav_has_bank:
                where_parts = ['bank_id = ?']
                params = [int(bank_id)]
                if fav_has_user:
                    where_parts.insert(0, 'user_id = ?')
                    params.insert(0, int(user_id))

                total = int(
                    conn.execute(
                        "SELECT COUNT(1) AS cnt FROM user_bank_favorites WHERE " + " AND ".join(where_parts),
                        params,
                    ).fetchone()['cnt']
                    or 0
                )

                rows = conn.execute(
                    """
                    SELECT DATE(created_at) AS day, COUNT(*) AS added
                    FROM user_bank_favorites
                    WHERE """
                    + " AND ".join(where_parts)
                    + """
                      AND created_at >= datetime('now', '+8 hours', ?)
                    GROUP BY day
                    ORDER BY day ASC
                    """,
                    params + [f'-{days_back} days'],
                ).fetchall()
            else:
                where_parts = ['q.bank_id = ?']
                params = [int(bank_id)]
                if fav_has_user:
                    where_parts.append('f.user_id = ?')
                    params.append(int(user_id))

                total = int(
                    conn.execute(
                        """
                        SELECT COUNT(1) AS cnt
                        FROM user_bank_favorites f
                        JOIN user_bank_questions q ON q.id = f.question_id
                        WHERE """
                        + " AND ".join(where_parts),
                        params,
                    ).fetchone()['cnt']
                    or 0
                )

                rows = conn.execute(
                    """
                    SELECT DATE(f.created_at) AS day, COUNT(*) AS added
                    FROM user_bank_favorites f
                    JOIN user_bank_questions q ON q.id = f.question_id
                    WHERE """
                    + " AND ".join(where_parts)
                    + """
                      AND f.created_at >= datetime('now', '+8 hours', ?)
                    GROUP BY day
                    ORDER BY day ASC
                    """,
                    params + [f'-{days_back} days'],
                ).fetchall()
        except Exception:
            total = 0
            rows = []

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
        'code': 0,
        'data': {
            'bank_id': int(bank_id),
            'days': int(window_days),
            'favorites_total': total,
            'total_added': total_added,
            'trend': trend,
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/questions/<int:question_id>/favorite', methods=['POST'])
@auth_required
def toggle_favorite(bank_id, question_id):
    """切换题目收藏状态"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()

    # 检查题目是否存在
    question = conn.execute(
        'SELECT id FROM user_bank_questions WHERE id = ? AND bank_id = ?',
        (question_id, bank_id)
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    # 检查是否已收藏
    existing = conn.execute(
        'SELECT id FROM user_bank_favorites WHERE user_id = ? AND question_id = ?',
        (user_id, question_id)
    ).fetchone()

    if existing:
        # 取消收藏
        conn.execute(
            'DELETE FROM user_bank_favorites WHERE user_id = ? AND question_id = ?',
            (user_id, question_id)
        )
        conn.commit()
        return jsonify({
            'code': 0,
            'message': '已取消收藏',
            'is_favorite': False
        })
    else:
        # 添加收藏
        conn.execute(
            '''INSERT INTO user_bank_favorites (user_id, bank_id, question_id)
               VALUES (?, ?, ?)''',
            (user_id, bank_id, question_id)
        )
        conn.commit()
        return jsonify({
            'code': 0,
            'message': '已收藏',
            'is_favorite': True
        })
