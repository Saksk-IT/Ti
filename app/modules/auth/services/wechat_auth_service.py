# -*- coding: utf-8 -*-
"""
微信认证服务
负责微信登录相关的业务逻辑
"""
import requests
import json
import hashlib
import re
import secrets
from typing import Dict, Any, Optional
from flask import current_app

from app.core.extensions import db
from app.models.user import User


WECHAT_NICKNAME_ERROR = '昵称只能由汉字、字母、数字组成，且不超过8个字符'
WECHAT_NICKNAME_DUPLICATE_ERROR = '昵称已被使用，请换一个'
WECHAT_NICKNAME_RE = re.compile(r'^[\u4e00-\u9fffA-Za-z0-9]{1,8}$')
RANDOM_NICKNAME_PREFIXES = ('题友', '学友', '考友', '小题')


class WechatAuthService:
    """微信认证服务"""

    @staticmethod
    def normalize_nickname(value: Any) -> Optional[str]:
        """规范化小程序新用户昵称；非法时返回 None。"""
        if value is None:
            return None
        nickname = str(value).strip()
        if not nickname:
            return None
        if not WECHAT_NICKNAME_RE.fullmatch(nickname):
            return None
        return nickname

    @staticmethod
    def _nickname_exists(nickname: str, exclude_user_id: Optional[int] = None) -> bool:
        query = User.query.filter(User.username == nickname)
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        return query.first() is not None

    @staticmethod
    def _generate_random_nickname(openid: str) -> str:
        for _ in range(32):
            prefix = secrets.choice(RANDOM_NICKNAME_PREFIXES)
            suffix_len = 8 - len(prefix)
            suffix = f'{secrets.randbelow(10 ** suffix_len):0{suffix_len}d}'
            nickname = f'{prefix}{suffix}'
            if not WechatAuthService._nickname_exists(nickname):
                return nickname

        seed = int(hashlib.sha256(openid.encode('utf-8')).hexdigest()[:12], 16)
        for offset in range(1000000):
            prefix = RANDOM_NICKNAME_PREFIXES[offset % len(RANDOM_NICKNAME_PREFIXES)]
            suffix_len = 8 - len(prefix)
            suffix = f'{(seed + offset) % (10 ** suffix_len):0{suffix_len}d}'
            nickname = f'{prefix}{suffix}'
            if not WechatAuthService._nickname_exists(nickname):
                return nickname

        raise RuntimeError('无法生成可用昵称')

    @staticmethod
    def _resolve_new_user_nickname(openid: str, user_info: Optional[Dict[str, Any]], strict_nickname: bool) -> str:
        raw_nickname = user_info.get('nickName') if user_info else None
        nickname = WechatAuthService.normalize_nickname(raw_nickname)

        if raw_nickname is not None and nickname is None:
            if strict_nickname:
                raise ValueError(WECHAT_NICKNAME_ERROR)
            return WechatAuthService._generate_random_nickname(openid)

        if nickname:
            if WechatAuthService._nickname_exists(nickname):
                if strict_nickname:
                    raise ValueError(WECHAT_NICKNAME_DUPLICATE_ERROR)
                return WechatAuthService._generate_random_nickname(openid)
            return nickname

        return WechatAuthService._generate_random_nickname(openid)

    @staticmethod
    def verify_code(code: str) -> Dict[str, Any]:
        """验证微信code，返回openid和session_key"""
        from app.modules.admin.services.system_config_service import SystemConfigService

        cfg = SystemConfigService.get_wechat_miniprogram_config()
        appid = cfg.get('appid')
        secret = cfg.get('secret')

        if not appid or not secret:
            current_app.logger.error('微信小程序配置缺失：WECHAT_APPID 或 WECHAT_SECRET')
            return {'error': '微信小程序配置缺失'}

        url = 'https://api.weixin.qq.com/sns/jscode2session'
        params = {
            'appid': appid,
            'secret': secret,
            'js_code': code,
            'grant_type': 'authorization_code'
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if 'errcode' in data:
                current_app.logger.warning(f'微信登录失败: {data.get("errmsg", "未知错误")}, errcode: {data.get("errcode")}')
                return {'error': data.get('errmsg', '微信登录失败')}

            return {
                'openid': data.get('openid'),
                'session_key': data.get('session_key'),
                'unionid': data.get('unionid')
            }
        except requests.RequestException as e:
            current_app.logger.error(f'微信API请求失败: {str(e)}')
            return {'error': '网络请求失败，请稍后重试'}
        except Exception as e:
            current_app.logger.error(f'微信登录异常: {str(e)}')
            return {'error': '微信登录失败'}

    @staticmethod
    def get_or_create_user(
        openid: str,
        user_info: Optional[Dict[str, Any]] = None,
        *,
        strict_nickname: bool = False,
    ) -> Dict[str, Any]:
        """根据openid获取或创建用户"""
        if not openid:
            raise ValueError('openid不能为空')

        user = User.query.filter_by(openid=openid).first()

        if user:
            is_new_user = False

            if user_info:
                changed = False
                if user_info.get('avatarUrl') and not user.avatar:
                    user.avatar = user_info.get('avatarUrl')
                    changed = True

                raw_nickname = user_info.get('nickName')
                nickname = WechatAuthService.normalize_nickname(raw_nickname)
                if raw_nickname is not None and nickname is None and strict_nickname:
                    raise ValueError(WECHAT_NICKNAME_ERROR)

                has_legacy_username = not WechatAuthService.normalize_nickname(user.username)
                if nickname and (not user.username or user.username.startswith('微信用户_') or has_legacy_username):
                    existing = User.query.filter(
                        User.username == nickname,
                        User.id != user.id
                    ).first()
                    if existing and strict_nickname:
                        raise ValueError(WECHAT_NICKNAME_DUPLICATE_ERROR)
                    if not existing:
                        user.username = nickname
                        changed = True

                if changed:
                    db.session.commit()

            result = {
                'id': user.id, 'username': user.username, 'is_admin': user.is_admin,
                'is_locked': user.is_locked, 'session_version': user.session_version,
                'avatar': user.avatar, 'contact': user.contact, 'college': user.college,
                'email': user.email, 'email_verified': user.email_verified,
                'openid': user.openid, 'has_password_set': user.has_password_set,
                'is_subject_admin': user.is_subject_admin,
                'is_notification_admin': user.is_notification_admin,
                'created_at': user.created_at, 'is_new_user': False,
            }
            return result
        else:
            username = WechatAuthService._resolve_new_user_nickname(openid, user_info, strict_nickname)

            avatar = user_info.get('avatarUrl') if user_info else None

            new_user = User(
                username=username, openid=openid, avatar=avatar,
                password_hash='', has_password_set=False,
            )
            db.session.add(new_user)
            db.session.commit()

            current_app.logger.info(f'新用户注册: {username} (openid: {openid})')

            result = {
                'id': new_user.id, 'username': new_user.username, 'is_admin': new_user.is_admin,
                'is_locked': new_user.is_locked, 'session_version': new_user.session_version,
                'avatar': new_user.avatar, 'contact': new_user.contact, 'college': new_user.college,
                'email': new_user.email, 'email_verified': new_user.email_verified,
                'openid': new_user.openid, 'has_password_set': new_user.has_password_set,
                'is_subject_admin': new_user.is_subject_admin,
                'is_notification_admin': new_user.is_notification_admin,
                'created_at': new_user.created_at, 'is_new_user': True,
            }
            return result
