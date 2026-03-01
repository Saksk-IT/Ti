# -*- coding: utf-8 -*-
"""
手机号认证业务逻辑服务

验证码由阿里云 DYPNS 托管生成和校验，本地无需存储验证码。
频率限制通过 Redis 实现（Redis 不可用时 fail-closed）。
"""
from __future__ import annotations

import logging
import secrets
import string
from typing import Any, Dict, Optional, Tuple

from flask import current_app
from werkzeug.security import generate_password_hash

from app.core.extensions import db
from app.core.utils.redis_utils import (
    get_redis_connection,
    redis_get_text,
    redis_incr,
    redis_set_text,
)
from app.core.utils.time_utils import now_bj
from app.models.user import User

logger = logging.getLogger(__name__)


class SmsAuthService:
    """手机号认证服务（镜像 EmailAuthService 结构）"""

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _sms_config(template_code: Optional[str] = None) -> Dict[str, Any]:
        """从 Flask config 构建传给 SDK / RQ 的配置字典。"""
        cfg = current_app.config
        return {
            'access_key_id': cfg.get('ALIYUN_ACCESS_KEY_ID') or '',
            'access_key_secret': cfg.get('ALIYUN_ACCESS_KEY_SECRET') or '',
            'sign_name': cfg.get('ALIYUN_SMS_SIGN_NAME') or '',
            'template_code': template_code or cfg.get('ALIYUN_SMS_TEMPLATE_CODE') or '',
            'code_length': cfg.get('ALIYUN_SMS_CODE_LENGTH', 6),
            'valid_time': cfg.get('ALIYUN_SMS_VALID_TIME', 300),
            'interval': cfg.get('ALIYUN_SMS_INTERVAL', 60),
            'console_output': cfg.get('SMS_CONSOLE_OUTPUT', False),
        }

    @staticmethod
    def _check_rate_limit(phone: str) -> Optional[str]:
        """频率检查：1 分钟 1 次 + 1 小时 5 次。返回错误消息或 None。"""
        conn = get_redis_connection()
        if conn is None:
            logger.error("短信限流检查失败: Redis 不可用")
            return '系统繁忙，请稍后再试'
        try:
            conn.ping()
        except Exception:
            logger.error("短信限流检查失败: Redis ping 失败", exc_info=True)
            return '系统繁忙，请稍后再试'

        # 1 分钟限制
        rate_key = f'sms:rate:{phone}'
        if redis_get_text(rate_key):
            return '发送验证码过于频繁，请稍后再试'

        # 1 小时限制
        hour_key = f'sms:rate_hour:{phone}'
        hour_count = redis_get_text(hour_key)
        try:
            over_limit = bool(hour_count) and int(hour_count) >= 5
        except Exception:
            logger.warning("短信限流计数解析失败: phone=%s hour_count=%s", phone, hour_count)
            over_limit = True
        if over_limit:
            return '发送验证码次数过多，请稍后再试'

        return None

    @staticmethod
    def _mark_rate_limit(phone: str) -> bool:
        """标记已发送，更新频率计数。"""
        minute_ok = redis_set_text(f'sms:rate:{phone}', '1', ttl_seconds=60)
        hour_key = f'sms:rate_hour:{phone}'
        val = redis_incr(hour_key)
        if val is None:
            return False

        ttl_ok = True
        if val == 1:
            # 首次，设置 TTL
            conn = get_redis_connection()
            if conn:
                try:
                    conn.expire(hour_key, 3600)
                except Exception:
                    ttl_ok = False
            else:
                ttl_ok = False
        return bool(minute_ok) and ttl_ok

    @staticmethod
    def _do_send(phone: str, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """RQ 异步发送短信，降级同步。返回 (成功, 错误消息)。"""
        try:
            from app.core.utils.rq_utils import get_queue
            q = get_queue()
            if q is not None:
                from app.tasks.sms_tasks import on_sms_task_failure, send_sms_task
                from rq import Retry
                q.enqueue(
                    send_sms_task,
                    kwargs={'phone': phone, 'config': config},
                    retry=Retry(max=2, interval=[10, 30]),
                    on_failure=on_sms_task_failure,
                    job_timeout=30,
                )
                logger.info('短信任务已入队(RQ): phone=%s', phone)
                return True, None
        except Exception as exc:
            logger.warning('RQ 入队失败，降级同步发送: %s', exc)

        # 同步降级
        from app.core.utils.sms_service import send_sms_verify_code
        result = send_sms_verify_code(phone, config)
        if not result.success:
            logger.error('短信同步发送失败: phone=%s, err=%s', phone, result.error_message)
            return False, '短信发送失败，请稍后再试'
        return True, None

    # ------------------------------------------------------------------
    # 登录 / 注册
    # ------------------------------------------------------------------

    @staticmethod
    def send_login_code(phone: str) -> Tuple[bool, Optional[str]]:
        """发送登录/注册验证码。"""
        if not current_app.config.get('SMS_ENABLED', True):
            return False, '短信功能未启用'

        err = SmsAuthService._check_rate_limit(phone)
        if err:
            return False, err

        config = SmsAuthService._sms_config()
        ok, msg = SmsAuthService._do_send(phone, config)
        if not ok:
            return False, msg

        if not SmsAuthService._mark_rate_limit(phone):
            logger.error("短信限流标记失败: phone=%s", phone)
            return False, '系统繁忙，请稍后再试'
        logger.info('登录验证码已发送: phone=%s', phone)
        return True, None

    @staticmethod
    def verify_login_code(phone: str, code: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """校验登录验证码，自动注册不存在的手机号用户。"""
        config = SmsAuthService._sms_config()

        from app.core.utils.sms_service import check_sms_verify_code
        result = check_sms_verify_code(phone, code, config)
        if not result.success:
            msg = '验证码错误或已过期'
            if result.verify_result == 'UNKNOWN':
                msg = '验证码错误或已过期'
            return False, msg, None

        try:
            now = now_bj()
            user = User.query.filter_by(phone=phone).first()

            if not user:
                # 自动注册
                suffix = phone[-4:]
                username = f'手机用户_{suffix}'
                counter = 1
                while User.query.filter_by(username=username).first():
                    username = f'手机用户_{suffix}_{counter}'
                    counter += 1

                random_pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
                user_count = User.query.count()

                user = User(
                    username=username,
                    password_hash=generate_password_hash(random_pw),
                    phone=phone,
                    phone_verified=True,
                    phone_verified_at=now,
                    is_admin=(user_count == 0),
                    has_password_set=False,
                )
                db.session.add(user)
                db.session.flush()
                logger.info('手机号自动注册: phone=%s, username=%s, id=%s', phone, username, user.id)
            else:
                if user.is_locked:
                    return False, '账户已被锁定，请联系管理员', None
                logger.info('手机验证码登录: phone=%s, id=%s', phone, user.id)

            db.session.commit()

            user_info = {
                'id': user.id, 'username': user.username, 'is_admin': user.is_admin,
                'is_locked': user.is_locked, 'session_version': user.session_version,
                'avatar': user.avatar, 'contact': user.contact, 'college': user.college,
                'email': user.email, 'email_verified': user.email_verified,
                'phone': user.phone, 'phone_verified': user.phone_verified,
                'openid': user.openid, 'has_password_set': user.has_password_set,
                'is_subject_admin': user.is_subject_admin,
                'is_notification_admin': user.is_notification_admin,
                'created_at': user.created_at,
            }
            return True, None, user_info

        except Exception as exc:
            db.session.rollback()
            logger.error('手机验证码登录失败: %s', exc, exc_info=True)
            return False, '系统错误，请稍后再试', None

    # ------------------------------------------------------------------
    # 忘记密码
    # ------------------------------------------------------------------

    @staticmethod
    def send_reset_password_code(phone: str) -> Tuple[bool, Optional[str]]:
        """发送重置密码验证码。"""
        if not current_app.config.get('SMS_ENABLED', True):
            return False, '短信功能未启用'

        user = User.query.filter_by(phone=phone).first()
        if not user:
            return True, None  # 防枚举

        err = SmsAuthService._check_rate_limit(phone)
        if err:
            return False, err

        config = SmsAuthService._sms_config(
            template_code=current_app.config.get('ALIYUN_SMS_TEMPLATE_CODE_RESET'),
        )
        ok, msg = SmsAuthService._do_send(phone, config)
        if not ok:
            return False, msg

        if not SmsAuthService._mark_rate_limit(phone):
            logger.error("短信限流标记失败: phone=%s", phone)
            return False, '系统繁忙，请稍后再试'
        logger.info('重置密码验证码已发送: phone=%s', phone)
        return True, None

    @staticmethod
    def reset_password(phone: str, code: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """手机号重置密码。"""
        user = User.query.filter_by(phone=phone).first()
        if not user:
            return False, '验证码错误或已过期'

        config = SmsAuthService._sms_config()
        from app.core.utils.sms_service import check_sms_verify_code
        result = check_sms_verify_code(phone, code, config)
        if not result.success:
            return False, '验证码错误或已过期'

        try:
            user.password_hash = generate_password_hash(new_password)
            user.has_password_set = True
            user.session_version = (user.session_version or 0) + 1
            db.session.commit()
            logger.info('手机号重置密码成功: phone=%s, id=%s', phone, user.id)
            return True, None
        except Exception as exc:
            db.session.rollback()
            logger.error('手机号重置密码失败: %s', exc, exc_info=True)
            return False, '系统错误，请稍后再试'

    # ------------------------------------------------------------------
    # 绑定手机
    # ------------------------------------------------------------------

    @staticmethod
    def send_bind_code(phone: str, user_id: int) -> Tuple[bool, Optional[str]]:
        """发送绑定手机验证码。"""
        if not current_app.config.get('SMS_ENABLED', True):
            return False, '短信功能未启用'

        user = User.query.get(user_id)
        if not user:
            return False, '用户不存在'
        if user.phone and str(user.phone).strip() == phone:
            return False, '新手机号不能与当前绑定手机号一致'

        existing = User.query.filter(User.phone == phone, User.id != user_id).first()
        if existing:
            return False, '该手机号已被其他用户绑定'

        err = SmsAuthService._check_rate_limit(phone)
        if err:
            return False, err

        config = SmsAuthService._sms_config(
            template_code=current_app.config.get('ALIYUN_SMS_TEMPLATE_CODE_BIND'),
        )
        ok, msg = SmsAuthService._do_send(phone, config)
        if not ok:
            return False, msg

        if not SmsAuthService._mark_rate_limit(phone):
            logger.error("短信限流标记失败: phone=%s user_id=%s", phone, user_id)
            return False, '系统繁忙，请稍后再试'
        logger.info('绑定手机验证码已发送: phone=%s, user_id=%s', phone, user_id)
        return True, None

    @staticmethod
    def bind_phone(phone: str, code: str, user_id: int) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """绑定手机号。"""
        user = User.query.get(user_id)
        if not user:
            return False, '用户不存在', None
        if user.phone and str(user.phone).strip() == phone:
            return False, '新手机号不能与当前绑定手机号一致', None

        existing = User.query.filter(User.phone == phone, User.id != user_id).first()
        if existing:
            return False, '该手机号已被其他用户绑定', None

        config = SmsAuthService._sms_config()
        from app.core.utils.sms_service import check_sms_verify_code
        result = check_sms_verify_code(phone, code, config)
        if not result.success:
            return False, '验证码错误或已过期', None

        try:
            # 二次检查占用
            other = User.query.filter(User.phone == phone, User.id != user_id).first()
            if other:
                return False, '该手机号已被其他用户绑定', None

            now = now_bj()
            user.phone = phone
            user.phone_verified = True
            user.phone_verified_at = now
            db.session.commit()

            logger.info('手机号绑定成功: phone=%s, user_id=%s', phone, user_id)
            return True, None, {
                'phone': user.phone,
                'phone_verified': bool(user.phone_verified),
            }
        except Exception as exc:
            db.session.rollback()
            logger.error('绑定手机号失败: %s', exc, exc_info=True)
            return False, '系统错误，请稍后再试', None
