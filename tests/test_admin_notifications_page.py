# -*- coding: utf-8 -*-
from sqlalchemy import text

from app.core.extensions import db


def _make_notification_admin_client(app, seed_user):
    with app.app_context():
        db.session.execute(
            text("UPDATE users SET is_notification_admin = 1 WHERE id = :uid"),
            {'uid': seed_user['id']},
        )
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = seed_user['id']
        sess['username'] = seed_user['username']
        sess['is_notification_admin'] = True
    return client


def test_admin_notifications_page_renders(app, seed_user):
    client = _make_notification_admin_client(app, seed_user)

    try:
        response = client.get('/admin/notifications')
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert '通知管理' in html
        assert '弹窗管理' not in html
        assert '通知类型' not in html
        assert 'id="popupsTab"' not in html
        assert 'id="typeSelector"' not in html
    finally:
        with app.app_context():
            db.session.execute(
                text("UPDATE users SET is_notification_admin = 0 WHERE id = :uid"),
                {'uid': seed_user['id']},
            )
            db.session.commit()


def test_admin_notification_create_ignores_message_type(app, seed_user):
    client = _make_notification_admin_client(app, seed_user)
    notification_id = None

    try:
        response = client.post(
            '/admin/api/notifications',
            json={
                'title': '测试通知',
                'content': '用于验证消息类型已移除',
                'n_type': 'warning',
                'priority': 8,
                'is_active': True,
            },
        )
        data = response.get_json()

        assert response.status_code == 200
        assert data['status'] == 'success'
        notification_id = data['id']

        with app.app_context():
            row = db.session.execute(
                text('SELECT n_type FROM notifications WHERE id = :nid'),
                {'nid': notification_id},
            ).fetchone()
            assert row is not None
            assert row._mapping['n_type'] == 'info'
    finally:
        with app.app_context():
            if notification_id:
                db.session.execute(
                    text('DELETE FROM notification_dismissals WHERE notification_id = :nid'),
                    {'nid': notification_id},
                )
                db.session.execute(
                    text('DELETE FROM notifications WHERE id = :nid'),
                    {'nid': notification_id},
                )
            db.session.execute(
                text("UPDATE users SET is_notification_admin = 0 WHERE id = :uid"),
                {'uid': seed_user['id']},
            )
            db.session.commit()


def test_notification_read_removes_item_from_unread_list(app, client, jwt_headers, seed_user):
    notification_id = None

    try:
        with app.app_context():
            result = db.session.execute(
                text(
                    "INSERT INTO notifications (title, content, n_type, priority, is_active) "
                    "VALUES (:title, :content, 'info', 10, 1) RETURNING id"
                ),
                {'title': '弹窗通知', 'content': '确认已读后不再弹出'},
            )
            notification_id = result.scalar()
            db.session.commit()

        unread_response = client.get('/api/notifications', headers=jwt_headers)
        unread_data = unread_response.get_json()
        assert unread_response.status_code == 200
        assert any(item['id'] == notification_id for item in unread_data['data'])

        read_response = client.post(f'/api/notifications/{notification_id}/read', headers=jwt_headers)
        read_data = read_response.get_json()
        assert read_response.status_code == 200
        assert read_data['status'] == 'success'

        unread_after = client.get('/api/notifications', headers=jwt_headers).get_json()
        assert all(item['id'] != notification_id for item in unread_after['data'])

        all_after = client.get('/api/notifications?include_dismissed=1', headers=jwt_headers).get_json()
        target = next(item for item in all_after['data'] if item['id'] == notification_id)
        assert target['is_read'] == 1
    finally:
        with app.app_context():
            if notification_id:
                db.session.execute(
                    text('DELETE FROM notification_dismissals WHERE notification_id = :nid'),
                    {'nid': notification_id},
                )
                db.session.execute(
                    text('DELETE FROM notifications WHERE id = :nid'),
                    {'nid': notification_id},
                )
            db.session.commit()


def test_notifications_page_includes_global_popup_dialog(auth_client):
    response = auth_client.get('/notifications')
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="appNotificationDialog"' in html
    assert 'id="appNotificationRead"' in html
    assert 'fetchNotifDialogQueue' in html
