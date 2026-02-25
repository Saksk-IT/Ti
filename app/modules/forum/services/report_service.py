# -*- coding: utf-8 -*-
"""举报服务"""
from typing import Optional

from sqlalchemy import text

from app.core.extensions import db


def create_report(reporter_id: int, target_type: str, target_id: int,
                  reason: str, detail: str = '') -> dict:
    """创建举报"""
    # 检查是否已举报过
    existing = db.session.execute(text(
        'SELECT id FROM forum_reports WHERE reporter_id=:uid AND target_type=:tt AND target_id=:tid AND status=:s'
    ), {'uid': reporter_id, 'tt': target_type, 'tid': target_id, 's': 'pending'}).fetchone()
    if existing:
        return {'error': '您已举报过该内容，请等待处理'}

    db.session.execute(text('''
        INSERT INTO forum_reports (reporter_id, target_type, target_id, reason, detail)
        VALUES (:uid, :tt, :tid, :reason, :detail)
    '''), {'uid': reporter_id, 'tt': target_type, 'tid': target_id,
           'reason': reason, 'detail': detail})
    db.session.commit()
    return {'success': True}


def get_reports(status: str = 'pending', page: int = 1, per_page: int = 20) -> dict:
    """获取举报列表（管理后台）"""
    offset = (page - 1) * per_page
    params: dict = {'limit': per_page, 'offset': offset}

    conditions = []
    if status != 'all':
        conditions.append('r.status = :status')
        params['status'] = status
    where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

    total = db.session.execute(text(
        f'SELECT COUNT(*) FROM forum_reports r {where}'
    ), params).scalar()

    rows = db.session.execute(text(f'''
        SELECT r.*, u.username AS reporter_name,
               h.username AS handler_name
        FROM forum_reports r
        JOIN users u ON u.id = r.reporter_id
        LEFT JOIN users h ON h.id = r.handled_by
        {where}
        ORDER BY CASE r.status WHEN 'pending' THEN 0 ELSE 1 END, r.created_at DESC
        LIMIT :limit OFFSET :offset
    '''), params).fetchall()

    return {
        'reports': [dict(r._mapping) for r in rows],
        'total': total, 'page': page, 'per_page': per_page,
    }


def handle_report(report_id: int, handler_id: int, action: str, note: str = '') -> bool:
    """处理举报: action = 'dismiss' | 'delete_content' | 'ban_user'"""
    row = db.session.execute(text(
        'SELECT * FROM forum_reports WHERE id=:rid AND status=:s'
    ), {'rid': report_id, 's': 'pending'}).fetchone()
    if not row:
        return False

    report = dict(row._mapping)
    status = 'resolved'

    if action == 'delete_content':
        # 软删除被举报内容
        table = 'forum_posts' if report['target_type'] == 'post' else 'forum_comments'
        db.session.execute(text(
            f'UPDATE {table} SET is_deleted=true, deleted_by=:uid, deleted_at=NOW() WHERE id=:tid'
        ), {'uid': handler_id, 'tid': report['target_id']})
    elif action == 'dismiss':
        status = 'dismissed'

    db.session.execute(text('''
        UPDATE forum_reports SET status=:status, handled_by=:hid, handled_at=NOW(), handle_note=:note
        WHERE id=:rid
    '''), {'status': status, 'hid': handler_id, 'note': note, 'rid': report_id})
    db.session.commit()
    return True


def get_pending_count() -> int:
    """获取待处理举报数"""
    return db.session.execute(text(
        "SELECT COUNT(*) FROM forum_reports WHERE status='pending'"
    )).scalar() or 0
