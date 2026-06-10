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
        assert '通知栏管理' in html
        assert '弹窗管理' in html
        assert 'id="notificationsTab"' in html
        assert 'id="popupsTab"' in html
    finally:
        with app.app_context():
            db.session.execute(
                text("UPDATE users SET is_notification_admin = 0 WHERE id = :uid"),
                {'uid': seed_user['id']},
            )
            db.session.commit()
