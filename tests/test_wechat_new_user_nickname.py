# -*- coding: utf-8 -*-
import re

import pytest

from app.core.extensions import db
from app.models.user import User
from app.modules.auth.services.wechat_auth_service import WechatAuthService


NICKNAME_RE = re.compile(r'^[\u4e00-\u9fffA-Za-z0-9]{1,8}$')


def _delete_openid(openid: str) -> None:
    User.query.filter_by(openid=openid).delete(synchronize_session=False)
    db.session.commit()


def test_wechat_new_user_without_nickname_gets_valid_random_nickname(app):
    openid = 'nickname-random-openid-001'
    with app.app_context():
        _delete_openid(openid)
        try:
            user = WechatAuthService.get_or_create_user(openid, {})

            assert user['is_new_user'] is True
            assert NICKNAME_RE.fullmatch(user['username'])
            assert len(user['username']) <= 8
            assert not user['username'].startswith('微信用户_')
        finally:
            _delete_openid(openid)


def test_wechat_new_user_accepts_valid_explicit_nickname(app):
    openid = 'nickname-explicit-openid-001'
    with app.app_context():
        _delete_openid(openid)
        try:
            user = WechatAuthService.get_or_create_user(
                openid,
                {'nickName': '用户A123'},
                strict_nickname=True,
            )

            assert user['username'] == '用户A123'
            assert user['is_new_user'] is True
        finally:
            _delete_openid(openid)


def test_wechat_new_user_rejects_invalid_explicit_nickname(app):
    openid = 'nickname-invalid-openid-001'
    with app.app_context():
        _delete_openid(openid)
        try:
            with pytest.raises(ValueError, match='昵称只能由汉字、字母、数字组成，且不超过8个字符'):
                WechatAuthService.get_or_create_user(
                    openid,
                    {'nickName': '坏昵称_1'},
                    strict_nickname=True,
                )

            assert User.query.filter_by(openid=openid).first() is None
        finally:
            _delete_openid(openid)


def test_wechat_create_rejects_invalid_explicit_nickname(app, client, monkeypatch):
    openid = 'nickname-route-invalid-openid-001'

    def fake_peek(_token):
        return {'openid': openid, 'user_info': {}}

    with app.app_context():
        _delete_openid(openid)
        monkeypatch.setattr(
            'app.modules.auth.routes.api.WechatTempTokenService.peek',
            staticmethod(fake_peek),
        )

        try:
            response = client.post(
                '/api/wechat/create',
                json={
                    'wechat_temp_token': 'test-temp-token',
                    'user_info': {'nickName': '坏昵称_1'},
                },
            )

            assert response.status_code == 400
            payload = response.get_json()
            assert payload['status'] == 'error'
            assert payload['message'] == '昵称只能由汉字、字母、数字组成，且不超过8个字符'
            assert User.query.filter_by(openid=openid).first() is None
        finally:
            _delete_openid(openid)
