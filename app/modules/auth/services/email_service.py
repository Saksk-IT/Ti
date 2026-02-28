# -*- coding: utf-8 -*-
"""
邮箱认证业务逻辑服务
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from flask import current_app
from werkzeug.security import generate_password_hash

from app.core.extensions import db
from app.models.user import User, EmailVerificationCode
from app.core.utils.email_service import EmailService
from app.core.utils.time_utils import now_bj


class EmailAuthService:
    """邮箱认证服务类"""
    
    # 验证码有效期（分钟）
    CODE_EXPIRE_MINUTES = 10
    # 验证码错误次数限制
    MAX_VERIFY_ATTEMPTS = 5
    
    @staticmethod
    def send_bind_code(user_id: int, email: str) -> Tuple[bool, Optional[str]]:
        """
        发送绑定邮箱验证码
        
        Args:
            user_id: 用户ID
            email: 邮箱地址
            
        Returns:
            (是否成功, 错误消息) 元组
        """
        # 验证邮箱格式
        if not EmailService.validate_email_format(email):
            return False, '邮箱格式不正确'
        
        # 检查邮箱是否已被其他用户使用
        existing = User.query.filter(User.email == email, User.id != user_id).first()
        if existing:
            return False, '邮箱已被其他用户使用'

        # 检查发送频率（1分钟内只能发送1次）
        one_minute_ago = now_bj() - timedelta(minutes=1)
        recent_count = EmailVerificationCode.query.filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.code_type == 'bind',
            EmailVerificationCode.created_at > one_minute_ago,
        ).count()

        if recent_count > 0:
            return False, '发送验证码过于频繁，请稍后再试'

        # 检查用户发送频率（1小时内最多5次）
        one_hour_ago = now_bj() - timedelta(hours=1)
        user_recent_count = EmailVerificationCode.query.filter(
            EmailVerificationCode.user_id == user_id,
            EmailVerificationCode.code_type == 'bind',
            EmailVerificationCode.created_at > one_hour_ago,
        ).count()

        if user_recent_count >= 5:
            return False, '发送验证码次数过多，请稍后再试'

        # 先存后发：先保存验证码到数据库，再异步发送邮件
        code = EmailService.generate_verification_code()
        try:
            expires_at = now_bj() + timedelta(minutes=EmailAuthService.CODE_EXPIRE_MINUTES)
            record = EmailVerificationCode(
                email=email, code=code, code_type='bind',
                user_id=user_id, expires_at=expires_at,
            )
            db.session.add(record)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'保存验证码失败: {str(e)}', exc_info=True)
            return False, '系统错误，请稍后再试'

        success, sent_code = EmailService.send_verification_code(
            to_email=email,
            code_type='bind',
            code=code
        )

        if not success:
            # 异步发送失败（同步降级也失败），删除刚存的记录
            try:
                db.session.delete(record)
                db.session.commit()
            except Exception:
                db.session.rollback()
            return False, '邮件发送失败，请稍后再试'

        current_app.logger.info(f'绑定邮箱验证码已发送: user_id={user_id}, email={email}')
        return True, None
    
    @staticmethod
    def bind_email(user_id: int, email: str, code: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        绑定邮箱
        
        Args:
            user_id: 用户ID
            email: 邮箱地址
            code: 验证码
            
        Returns:
            (是否成功, 错误消息, 用户信息) 元组
        """
        # 验证邮箱格式
        if not EmailService.validate_email_format(email):
            return False, '邮箱格式不正确', None
        
        # 检查邮箱是否已被其他用户使用
        existing = User.query.filter(User.email == email, User.id != user_id).first()
        if existing:
            return False, '邮箱已被其他用户使用', None

        # 验证验证码
        now = now_bj()

        # 查找有效的验证码
        code_record = EmailVerificationCode.query.filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.code == code,
            EmailVerificationCode.code_type == 'bind',
            EmailVerificationCode.user_id == user_id,
            EmailVerificationCode.is_used == False,
            EmailVerificationCode.expires_at > now,
        ).order_by(EmailVerificationCode.created_at.desc()).first()

        if not code_record:
            # 检查是否验证码错误次数过多
            recent_attempts = EmailVerificationCode.query.filter(
                EmailVerificationCode.email == email,
                EmailVerificationCode.code_type == 'bind',
                EmailVerificationCode.user_id == user_id,
                EmailVerificationCode.created_at > now_bj() - timedelta(minutes=10),
                EmailVerificationCode.is_used == False,
            ).count()

            if recent_attempts >= EmailAuthService.MAX_VERIFY_ATTEMPTS:
                return False, '验证码错误次数过多，请重新发送验证码', None

            return False, '验证码错误或已过期', None

        # 标记验证码为已使用
        try:
            code_record.is_used = True
            code_record.used_at = now

            # 绑定邮箱
            user = User.query.get(user_id)
            if not user:
                db.session.rollback()
                return False, '绑定邮箱失败', None

            # 检查邮箱是否已被其他用户使用（二次检查）
            other = User.query.filter(User.email == email, User.id != user_id).first()
            if other:
                db.session.rollback()
                return False, '邮箱已被其他用户使用', None

            user.email = email
            user.email_verified = True
            user.email_verified_at = now
            db.session.commit()

            current_app.logger.info(f'邮箱绑定成功: user_id={user_id}, email={email}')

            return True, None, {
                'email': user.email,
                'email_verified': bool(user.email_verified),
            }

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'绑定邮箱失败: {str(e)}', exc_info=True)
            return False, '系统错误，请稍后再试', None
    
    @staticmethod
    def send_login_code(email: str) -> Tuple[bool, Optional[str]]:
        """
        发送登录验证码（支持自动注册）
        
        Args:
            email: 邮箱地址
            
        Returns:
            (是否成功, 错误消息) 元组
        """
        # 验证邮箱格式
        if not EmailService.validate_email_format(email):
            return False, '邮箱格式不正确'
        
        # 检查邮箱是否已绑定（未绑定也可以发送验证码，用于自动注册）
        user = User.query.filter_by(email=email).first()
        user_id = user.id if user else None

        # 检查发送频率（1分钟内只能发送1次）
        one_minute_ago = now_bj() - timedelta(minutes=1)
        recent_count = EmailVerificationCode.query.filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.code_type == 'login',
            EmailVerificationCode.created_at > one_minute_ago,
        ).count()

        if recent_count > 0:
            return False, '发送验证码过于频繁，请稍后再试'

        # 先存后发：先保存验证码到数据库，再异步发送邮件
        code = EmailService.generate_verification_code()
        try:
            expires_at = now_bj() + timedelta(minutes=EmailAuthService.CODE_EXPIRE_MINUTES)
            record = EmailVerificationCode(
                email=email, code=code, code_type='login',
                user_id=user_id, expires_at=expires_at,
            )
            db.session.add(record)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'保存验证码失败: {str(e)}', exc_info=True)
            return False, '系统错误，请稍后再试'

        success, sent_code = EmailService.send_verification_code(
            to_email=email,
            code_type='login',
            code=code
        )

        if not success:
            # 异步发送失败（同步降级也失败），删除刚存的记录
            try:
                db.session.delete(record)
                db.session.commit()
            except Exception:
                db.session.rollback()
            return False, '邮件发送失败，请稍后再试'

        if user:
            current_app.logger.info(f'登录验证码已发送: email={email}, user_id={user_id}')
        else:
            current_app.logger.info(f'注册验证码已发送: email={email} (新用户)')
        return True, None
    
    @staticmethod
    def verify_login_code(email: str, code: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        验证登录验证码（支持自动注册）
        
        Args:
            email: 邮箱地址
            code: 验证码
            
        Returns:
            (是否成功, 错误消息, 用户信息) 元组
        """
        # 验证邮箱格式
        if not EmailService.validate_email_format(email):
            return False, '邮箱格式不正确', None
        
        # 验证验证码
        now = now_bj()

        # 查找有效的验证码（user_id可以为None，用于自动注册）
        code_record = EmailVerificationCode.query.filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.code == code,
            EmailVerificationCode.code_type == 'login',
            EmailVerificationCode.is_used == False,
            EmailVerificationCode.expires_at > now,
        ).order_by(EmailVerificationCode.created_at.desc()).first()

        if not code_record:
            # 检查是否验证码错误次数过多
            recent_attempts = EmailVerificationCode.query.filter(
                EmailVerificationCode.email == email,
                EmailVerificationCode.code_type == 'login',
                EmailVerificationCode.created_at > now_bj() - timedelta(minutes=10),
                EmailVerificationCode.is_used == False,
            ).count()

            if recent_attempts >= EmailAuthService.MAX_VERIFY_ATTEMPTS:
                return False, '验证码错误次数过多，请重新发送验证码', None

            return False, '验证码错误或已过期', None

        # 标记验证码为已使用
        try:
            code_record.is_used = True
            code_record.used_at = now

            # 检查用户是否存在
            user = User.query.filter_by(email=email).first()

            if not user:
                # 自动注册：创建新用户
                email_prefix = email.split('@')[0]
                username = email_prefix
                counter = 1

                # 确保用户名唯一
                while User.query.filter_by(username=username).first():
                    username = f"{email_prefix}{counter}"
                    counter += 1

                # 生成随机密码（用户不会用到，但数据库字段需要）
                import secrets
                import string
                random_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

                # 检查是否是第一个用户（自动成为管理员）
                user_count = User.query.count()
                is_first_user = user_count == 0

                password_hash = generate_password_hash(random_password)

                user = User(
                    username=username,
                    password_hash=password_hash,
                    email=email,
                    email_verified=True,
                    email_verified_at=now,
                    is_admin=is_first_user,
                    has_password_set=False,
                )
                db.session.add(user)
                db.session.flush()  # 获取 user.id

                current_app.logger.info(f'自动注册成功: email={email}, username={username}, user_id={user.id}')
            else:
                # 检查账户是否锁定
                if user.is_locked:
                    db.session.rollback()
                    return False, '账户已被锁定，请联系管理员', None

                current_app.logger.info(f'验证码登录成功: email={email}, user_id={user.id}')

            db.session.commit()

            user_info = {
                'id': user.id, 'username': user.username, 'is_admin': user.is_admin,
                'is_locked': user.is_locked, 'session_version': user.session_version,
                'avatar': user.avatar, 'contact': user.contact, 'college': user.college,
                'email': user.email, 'email_verified': user.email_verified,
                'openid': user.openid, 'has_password_set': user.has_password_set,
                'is_subject_admin': user.is_subject_admin,
                'is_notification_admin': user.is_notification_admin,
                'created_at': user.created_at,
            }
            return True, None, user_info

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'验证登录验证码失败: {str(e)}', exc_info=True)
            return False, '系统错误，请稍后再试', None
    
    @staticmethod
    def send_reset_password_code(email: str) -> Tuple[bool, Optional[str]]:
        """
        发送重置密码验证码
        
        Args:
            email: 邮箱地址
            
        Returns:
            (是否成功, 错误消息) 元组
        """
        # 验证邮箱格式
        if not EmailService.validate_email_format(email):
            return False, '邮箱格式不正确'
        
        # 检查邮箱是否已绑定
        user = User.query.filter_by(email=email).first()
        if not user:
            # 防止邮箱枚举攻击：即使邮箱未绑定也返回相同消息
            return True, None

        user_id = user.id

        # 检查发送频率（1分钟内只能发送1次）
        one_minute_ago = now_bj() - timedelta(minutes=1)
        recent_count = EmailVerificationCode.query.filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.code_type == 'reset_password',
            EmailVerificationCode.created_at > one_minute_ago,
        ).count()

        if recent_count > 0:
            return False, '发送验证码过于频繁，请稍后再试'

        # 检查用户发送频率（1小时内最多5次）
        one_hour_ago = now_bj() - timedelta(hours=1)
        user_recent_count = EmailVerificationCode.query.filter(
            EmailVerificationCode.user_id == user_id,
            EmailVerificationCode.code_type == 'reset_password',
            EmailVerificationCode.created_at > one_hour_ago,
        ).count()

        if user_recent_count >= 5:
            return False, '发送验证码次数过多，请稍后再试'

        # 先存后发：先保存验证码到数据库，再异步发送邮件
        code = EmailService.generate_verification_code()
        try:
            expires_at = now_bj() + timedelta(minutes=EmailAuthService.CODE_EXPIRE_MINUTES)
            record = EmailVerificationCode(
                email=email, code=code, code_type='reset_password',
                user_id=user_id, expires_at=expires_at,
            )
            db.session.add(record)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'保存验证码失败: {str(e)}', exc_info=True)
            return False, '系统错误，请稍后再试'

        success, sent_code = EmailService.send_verification_code(
            to_email=email,
            code_type='reset_password',
            code=code
        )

        if not success:
            # 异步发送失败（同步降级也失败），删除刚存的记录
            try:
                db.session.delete(record)
                db.session.commit()
            except Exception:
                db.session.rollback()
            return False, '邮件发送失败，请稍后再试'

        current_app.logger.info(f'重置密码验证码已发送: email={email}, user_id={user_id}')
        return True, None
    
    @staticmethod
    def reset_password(email: str, code: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        重置密码
        
        Args:
            email: 邮箱地址
            code: 验证码
            new_password: 新密码
            
        Returns:
            (是否成功, 错误消息) 元组
        """
        # 验证邮箱格式
        if not EmailService.validate_email_format(email):
            return False, '邮箱格式不正确'
        
        # 检查邮箱是否已绑定
        user = User.query.filter_by(email=email).first()
        if not user:
            # 防止邮箱枚举攻击：即使邮箱未绑定也返回相同消息
            return False, '验证码错误或已过期'

        user_id = user.id

        # 验证验证码
        now = now_bj()

        # 查找有效的验证码
        code_record = EmailVerificationCode.query.filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.code == code,
            EmailVerificationCode.code_type == 'reset_password',
            EmailVerificationCode.user_id == user_id,
            EmailVerificationCode.is_used == False,
            EmailVerificationCode.expires_at > now,
        ).order_by(EmailVerificationCode.created_at.desc()).first()

        if not code_record:
            # 检查是否验证码错误次数过多
            recent_attempts = EmailVerificationCode.query.filter(
                EmailVerificationCode.email == email,
                EmailVerificationCode.code_type == 'reset_password',
                EmailVerificationCode.user_id == user_id,
                EmailVerificationCode.created_at > now_bj() - timedelta(minutes=10),
                EmailVerificationCode.is_used == False,
            ).count()

            if recent_attempts >= EmailAuthService.MAX_VERIFY_ATTEMPTS:
                return False, '验证码错误次数过多，请重新发送验证码'

            return False, '验证码错误或已过期'

        # 标记验证码为已使用并更新密码
        try:
            code_record.is_used = True
            code_record.used_at = now

            # 更新密码
            user.password_hash = generate_password_hash(new_password)

            # 递增 session_version，强制所有旧 JWT / session 失效
            user.session_version = (user.session_version or 0) + 1

            db.session.commit()

            current_app.logger.info(f'密码重置成功: email={email}, user_id={user_id}')
            return True, None

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'重置密码失败: {str(e)}', exc_info=True)
            return False, '系统错误，请稍后再试'
