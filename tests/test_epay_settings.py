# -*- coding: utf-8 -*-
from sqlalchemy import text

from app.core.extensions import db
from app.models.system import SystemConfig
from app.modules.payment.services.epay_service import EpayService


EPAY_KEYS = [
    'epay_enabled',
    'epay_api_base_url',
    'epay_pid',
    'epay_key',
    'epay_sitename',
    'epay_notify_url',
    'epay_return_url',
    'epay_default_type',
    'epay_timeout',
]


def _clear_system_configs(keys):
    SystemConfig.query.filter(SystemConfig.config_key.in_(keys)).delete(synchronize_session=False)
    db.session.commit()


def test_admin_epay_settings_roundtrip(app, seed_user):
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
        _clear_system_configs(EPAY_KEYS)

    payload = {
        'epay_enabled': True,
        'epay_api_base_url': 'https://z-pay.cn',
        'epay_pid': '10001',
        'epay_key': 'secret-key-123456',
        'epay_sitename': '题库系统',
        'epay_notify_url': 'https://example.com/api/payment/epay/notify',
        'epay_return_url': 'https://example.com/payment/result',
        'epay_default_type': 'wxpay',
        'epay_timeout': 12,
    }

    try:
        response = client.post('/admin/api/settings/payment/epay', json=payload)
        assert response.status_code == 200
        assert response.get_json()['status'] == 'success'

        response = client.get('/admin/api/settings/payment/epay')
        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['epay_enabled'] is True
        assert data['epay_pid'] == '10001'
        assert '****' in data['epay_key']
        assert data['epay_default_type'] == 'wxpay'

        with app.app_context():
            cfg = EpayService.get_config()
            assert cfg['enabled'] is True
            assert cfg['pid'] == '10001'
            assert cfg['key'] == 'secret-key-123456'
            assert cfg['timeout'] == 12
    finally:
        with app.app_context():
            _clear_system_configs(EPAY_KEYS)
            db.session.execute(
                text("UPDATE users SET is_admin = 0 WHERE id = :uid"),
                {'uid': seed_user['id']},
            )
            db.session.commit()


def test_epay_payment_url_uses_md5_signature():
    request_data = EpayService.build_payment_request(
        money='0.01',
        name='测试订单',
        out_trade_no='T202606080001',
        config={
            'api_base_url': 'https://z-pay.cn',
            'pid': '10001',
            'key': 'secret',
            'sitename': '题库系统',
            'notify_url': 'https://example.com/notify',
            'return_url': 'https://example.com/return',
            'default_type': 'alipay',
            'timeout': 10,
        },
    )

    assert request_data['sign_base'] == (
        'money=0.01&name=测试订单&notify_url=https://example.com/notify&'
        'out_trade_no=T202606080001&pid=10001&return_url=https://example.com/return&'
        'sitename=题库系统&type=alipay'
    )
    assert request_data['params']['sign'] == '803d453efadc65bfc5fd85cd49850b9f'
    assert request_data['url'].startswith('https://z-pay.cn/submit.php?')
