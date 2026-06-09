# -*- coding: utf-8 -*-
from sqlalchemy import text

from app.core.extensions import db
from app.models.system import SystemConfig
from app.modules.admin.services.system_config_service import SystemConfigService


AUTH_LOGIN_KEYS = [
    'auth_phone_login_enabled',
    'auth_wechat_login_enabled',
]


def _clear_auth_login_configs():
    SystemConfig.query.filter(SystemConfig.config_key.in_(AUTH_LOGIN_KEYS)).delete(synchronize_session=False)
    db.session.commit()


def _set_auth_login_config(*, phone: bool = True, wechat: bool = True):
    SystemConfigService.update_config('auth_phone_login_enabled', 'true' if phone else 'false', admin_id=1)
    SystemConfigService.update_config('auth_wechat_login_enabled', 'true' if wechat else 'false', admin_id=1)


def _make_admin_client(app, seed_user):
    with app.app_context():
        db.session.execute(
            text("UPDATE users SET is_admin = 1 WHERE id = :uid"),
            {'uid': seed_user['id']},
        )
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = seed_user['id']
        sess['username'] = seed_user['username']
        sess['is_admin'] = True
    return client


def test_auth_login_methods_default_enabled(app):
    with app.app_context():
        _clear_auth_login_configs()
        try:
            cfg = SystemConfigService.get_auth_login_methods_config()
            assert cfg['phone_login_enabled'] is True
            assert cfg['wechat_login_enabled'] is True
            assert cfg['default_mode'] == 'phone'
        finally:
            _clear_auth_login_configs()


def test_admin_auth_login_settings_roundtrip(app, seed_user):
    client = _make_admin_client(app, seed_user)
    with app.app_context():
        _clear_auth_login_configs()

    try:
        response = client.post(
            '/admin/api/settings/auth-login',
            json={
                'auth_phone_login_enabled': False,
                'auth_wechat_login_enabled': True,
            },
        )
        assert response.status_code == 200
        assert response.get_json()['status'] == 'success'

        response = client.get('/admin/api/settings/auth-login')
        assert response.status_code == 200
        data = response.get_json()['data']
        assert data == {
            'auth_phone_login_enabled': 'false',
            'auth_wechat_login_enabled': 'true',
        }

        with app.app_context():
            cfg = SystemConfigService.get_auth_login_methods_config()
            assert cfg['phone_login_enabled'] is False
            assert cfg['wechat_login_enabled'] is True
            assert cfg['default_mode'] == 'qr'
    finally:
        with app.app_context():
            _clear_auth_login_configs()
            db.session.execute(
                text("UPDATE users SET is_admin = 0 WHERE id = :uid"),
                {'uid': seed_user['id']},
            )
            db.session.commit()


def test_login_page_hides_phone_and_wechat_when_disabled(app, client):
    with app.app_context():
        _clear_auth_login_configs()
        _set_auth_login_config(phone=False, wechat=False)

    try:
        response = client.get('/login')
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'data-default-login-mode="password"' in html
        assert 'id="phone-form"' not in html
        assert 'id="wechat-login-btn"' not in html
        assert 'data-mode="phone"' not in html
        assert 'data-mode="qr"' not in html
        assert '密码登录' in html
        assert '邮箱登录' in html
    finally:
        with app.app_context():
            _clear_auth_login_configs()


def test_login_page_keeps_phone_password_login_when_phone_code_disabled(app, client):
    with app.app_context():
        _clear_auth_login_configs()
        _set_auth_login_config(phone=False, wechat=True)

    try:
        response = client.get('/login')
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'data-default-login-mode="qr"' in html
        assert 'id="phone-form"' not in html
        assert 'data-mode="phone"' not in html
        assert 'id="wechat-login-btn"' in html
        assert 'data-mode="password"' in html
        assert 'data-mode="code"' in html
        assert '邮箱 / 手机号' in html
        assert '请输入已绑定邮箱或手机号' in html
    finally:
        with app.app_context():
            _clear_auth_login_configs()


def test_disabled_phone_code_login_rejects_only_sms_login_paths(app, client):
    with app.app_context():
        _clear_auth_login_configs()
        _set_auth_login_config(phone=False, wechat=True)

    try:
        response = client.post('/api/sms/send-login-code', json={'phone': '13573028533'})
        assert response.status_code == 403
        assert response.get_json()['status'] == 'error'
        assert response.get_json()['message'] == '手机号验证码登录已关闭，请使用其他登录方式'

        response = client.post('/api/sms/login', json={'phone': '13573028533', 'code': '123456'})
        assert response.status_code == 403

        response = client.post('/api/login', json={'username': '13573028533', 'password': 'wrong'})
        assert response.status_code != 403
        assert response.get_json()['message'] != '手机号验证码登录已关闭，请使用其他登录方式'

        response = client.post('/api/mini/login', json={'account': '13573028533', 'password': 'wrong'})
        assert response.status_code == 403
        assert response.get_json()['message'] != '手机号验证码登录已关闭，请使用其他登录方式'
    finally:
        with app.app_context():
            _clear_auth_login_configs()


def test_disabled_wechat_login_rejects_wechat_paths(app, client):
    with app.app_context():
        _clear_auth_login_configs()
        _set_auth_login_config(phone=True, wechat=False)

    try:
        response = client.get('/api/auth/login-methods')
        assert response.status_code == 200
        assert response.get_json()['data']['wechat_login_enabled'] is False

        response = client.post('/api/wechat/login', json={'code': 'test-code'})
        assert response.status_code == 403

        response = client.post(
            '/api/web_login/qrcode',
            json={},
            headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        assert response.status_code == 403
    finally:
        with app.app_context():
            _clear_auth_login_configs()
