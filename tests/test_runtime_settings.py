# -*- coding: utf-8 -*-
from sqlalchemy import text

from app.core.extensions import db
from app.models.system import SystemConfig
from app.modules.admin.services.system_config_service import SystemConfigService
from app.tasks.ai_explain_tasks import ai_explain_task


MAIL_KEYS = [
    'mail_server',
    'mail_port',
    'mail_use_tls',
    'mail_use_ssl',
    'mail_username',
    'mail_password',
    'mail_default_sender',
    'mail_default_sender_name',
    'mail_enabled',
    'mail_console_output',
]

SMS_KEYS = [
    'sms_access_key_id',
    'sms_access_key_secret',
    'sms_sign_name',
    'sms_template_code',
    'sms_template_code_bind',
    'sms_template_code_reset',
    'sms_code_length',
    'sms_valid_time',
    'sms_interval',
    'sms_enabled',
    'sms_console_output',
]


def _clear_system_configs(keys):
    SystemConfig.query.filter(SystemConfig.config_key.in_(keys)).delete(synchronize_session=False)
    db.session.commit()


def test_mail_config_prefers_system_settings(app):
    with app.app_context():
        _clear_system_configs(MAIL_KEYS)
        try:
            SystemConfigService.update_config('mail_server', 'smtp.db.example.com', admin_id=1)
            SystemConfigService.update_config('mail_port', '2525', admin_id=1)
            SystemConfigService.update_config('mail_use_tls', 'false', admin_id=1)
            SystemConfigService.update_config('mail_username', 'db-user@example.com', admin_id=1)
            SystemConfigService.update_config('mail_password', 'db-password', admin_id=1)
            SystemConfigService.update_config('mail_default_sender', 'noreply@example.com', admin_id=1)
            SystemConfigService.update_config('mail_enabled', 'true', admin_id=1)

            cfg = SystemConfigService.get_mail_config()

            assert cfg['server'] == 'smtp.db.example.com'
            assert cfg['port'] == 2525
            assert cfg['use_tls'] is False
            assert cfg['username'] == 'db-user@example.com'
            assert cfg['password'] == 'db-password'
            assert cfg['sender'] == 'noreply@example.com'
            assert cfg['enabled'] is True
        finally:
            _clear_system_configs(MAIL_KEYS)


def test_admin_sms_settings_roundtrip(app, seed_user):
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

    with app.app_context():
        _clear_system_configs(SMS_KEYS)

    payload = {
        'sms_access_key_id': 'LTAI123456789',
        'sms_access_key_secret': 'secret987654321',
        'sms_sign_name': '速通互联验证码',
        'sms_template_code': '100001',
        'sms_template_code_bind': '100004',
        'sms_template_code_reset': '100003',
        'sms_code_length': 6,
        'sms_valid_time': 300,
        'sms_interval': 60,
        'sms_enabled': True,
        'sms_console_output': True,
    }

    try:
        response = client.post('/admin/api/settings/sms', json=payload)
        assert response.status_code == 200
        assert response.get_json()['status'] == 'success'

        response = client.get('/admin/api/settings/sms')
        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['sms_sign_name'] == '速通互联验证码'
        assert '****' in data['sms_access_key_id']
        assert '****' in data['sms_access_key_secret']

        with app.app_context():
            cfg = SystemConfigService.get_sms_config()
            assert cfg['access_key_id'] == 'LTAI123456789'
            assert cfg['access_key_secret'] == 'secret987654321'
            assert cfg['template_code_bind'] == '100004'
            assert cfg['enabled'] is True
            assert cfg['console_output'] is True
    finally:
        with app.app_context():
            _clear_system_configs(SMS_KEYS)
            db.session.execute(
                text("UPDATE users SET is_admin = 0 WHERE id = :uid"),
                {'uid': seed_user['id']},
            )
            db.session.commit()


def test_ai_explain_task_prefers_explicit_dashscope_config(monkeypatch):
    captured = {}

    def fake_generate_ai_explain(*, api_key, base_url, model, payload, timeout):
        captured['api_key'] = api_key
        captured['base_url'] = base_url
        captured['model'] = model
        captured['payload'] = payload
        captured['timeout'] = timeout
        return 'AI 解析结果'

    monkeypatch.setattr('app.tasks.ai_explain_tasks.generate_ai_explain', fake_generate_ai_explain)

    result = ai_explain_task(
        payload={'content': '示例题目'},
        model='qwen-max',
        timeout=18,
        dashscope_config={
            'api_key': 'db-runtime-key',
            'base_url': 'https://dashscope.example.com/v1',
            'model': 'qwen-plus',
            'timeout': 25,
        },
    )

    assert result['provider'] == 'dashscope'
    assert result['model'] == 'qwen-max'
    assert result['explain'] == 'AI 解析结果'
    assert captured == {
        'api_key': 'db-runtime-key',
        'base_url': 'https://dashscope.example.com/v1',
        'model': 'qwen-max',
        'payload': {'content': '示例题目'},
        'timeout': 18,
    }
