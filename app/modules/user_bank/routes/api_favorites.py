# -*- coding: utf-8 -*-

"""用户题库：收藏 API"""

from flask import request, jsonify
from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.time_utils import today_bj, now_bj

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
    cutoff = now_bj() - timedelta(days=days_back)

    # PostgreSQL: 直接查询，不需要检查表/列是否存在
    total = 0
    rows = []
    try:
        total_row = db.session.execute(
            text("""SELECT COUNT(1) AS cnt FROM user_bank_favorites
                    WHERE user_id = :user_id AND bank_id = :bank_id"""),
            {'user_id': int(user_id), 'bank_id': int(bank_id)}
        ).fetchone()
        total = int(total_row._mapping['cnt'] or 0) if total_row else 0

        rows = db.session.execute(
            text("""SELECT DATE(created_at) AS day, COUNT(*) AS added
                    FROM user_bank_favorites
                    WHERE user_id = :user_id AND bank_id = :bank_id
                      AND created_at >= :cutoff
                    GROUP BY day
                    ORDER BY day ASC"""),
            {'user_id': int(user_id), 'bank_id': int(bank_id), 'cutoff': cutoff}
        ).fetchall()
    except Exception:
        total = 0
        rows = []

    by_day = {}
    for r in rows or []:
        m = r._mapping
        day = m['day']
        if not day:
            continue
        by_day[str(day)] = int(m['added'] or 0)

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

    # 检查题目是否存在
    question = db.session.execute(
        text('SELECT id FROM user_bank_questions WHERE id = :qid AND bank_id = :bank_id'),
        {'qid': question_id, 'bank_id': bank_id}
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    # 检查是否已收藏
    existing = db.session.execute(
        text('SELECT id FROM user_bank_favorites WHERE user_id = :user_id AND question_id = :qid'),
        {'user_id': user_id, 'qid': question_id}
    ).fetchone()

    if existing:
        # 取消收藏
        db.session.execute(
            text('DELETE FROM user_bank_favorites WHERE user_id = :user_id AND question_id = :qid'),
            {'user_id': user_id, 'qid': question_id}
        )
        db.session.commit()
        return jsonify({
            'code': 0,
            'message': '已取消收藏',
            'is_favorite': False
        })
    else:
        # 添加收藏
        db.session.execute(
            text('''INSERT INTO user_bank_favorites (user_id, bank_id, question_id)
               VALUES (:user_id, :bank_id, :qid)'''),
            {'user_id': user_id, 'bank_id': bank_id, 'qid': question_id}
        )
        db.session.commit()
        return jsonify({
            'code': 0,
            'message': '已收藏',
            'is_favorite': True
        })
