# -*- coding: utf-8 -*-
"""
用户业务服务

原 app/core/models/user.py 的业务逻辑迁移至此。
提供用户 CRUD、密码验证、邮箱绑定等操作。
"""
from typing import Optional
import re
from werkzeug.security import generate_password_hash, check_password_hash
from app.core.extensions import db
from sqlalchemy import text


class UserService:
    """用户业务操作服务（原 core/models/user.User）。"""

    @staticmethod
    def create(username, password, is_admin=False):
        """创建用户"""
        password_hash = generate_password_hash(password)

        # 检查是否是第一个用户（自动成为管理员）
        count = db.session.execute(text('SELECT COUNT(*) FROM users')).scalar()
        if count == 0:
            is_admin = True

        db.session.execute(
            text('INSERT INTO users (username, password_hash, is_admin) VALUES (:username, :password_hash, :is_admin)'),
            {'username': username, 'password_hash': password_hash, 'is_admin': is_admin}
        )
        db.session.commit()
        return UserService.get_by_username(username)

    @staticmethod
    def get_by_id(user_id):
        """通过ID获取用户"""
        row = db.session.execute(
            text('SELECT * FROM users WHERE id = :user_id'), {'user_id': user_id}
        ).fetchone()
        return dict(row._mapping) if row else None

    @staticmethod
    def get_by_username(username):
        """通过用户名获取用户"""
        row = db.session.execute(
            text('SELECT * FROM users WHERE username = :username'), {'username': username}
        ).fetchone()
        return dict(row._mapping) if row else None

    @staticmethod
    def verify_password(identifier: str, password: str) -> Optional[dict]:
        """
        验证密码（支持用户名、邮箱或手机号）

        Args:
            identifier: 用户名、邮箱或手机号
            password: 密码

        Returns:
            用户信息字典，如果验证失败返回None
        """
        if not identifier or not password:
            return None

        identifier = identifier.strip()

        # 判断是邮箱、手机号还是用户名
        if '@' in identifier:
            row = db.session.execute(
                text('SELECT * FROM users WHERE email = :email'), {'email': identifier}
            ).fetchone()
        elif re.fullmatch(r'1[3-9]\d{9}', identifier):
            row = db.session.execute(
                text('SELECT * FROM users WHERE phone = :phone'), {'phone': identifier}
            ).fetchone()
        else:
            row = db.session.execute(
                text('SELECT * FROM users WHERE username = :username'), {'username': identifier}
            ).fetchone()

        if not row:
            return None

        user = dict(row._mapping)
        if not check_password_hash(user['password_hash'], password):
            return None

        # 用户已通过密码认证，修正历史数据中可能残留的 has_password_set=false/null 状态
        if user.get('has_password_set') not in (True, 1):
            if UserService._mark_has_password_set(int(user['id'])):
                user['has_password_set'] = True

        return user

    @staticmethod
    def _mark_has_password_set(user_id: int) -> bool:
        """将 has_password_set 标记为 true（仅在需要时更新）。"""
        try:
            db.session.execute(
                text('''
                    UPDATE users
                    SET has_password_set = true
                    WHERE id = :user_id
                      AND (has_password_set IS NULL OR has_password_set = false)
                '''),
                {'user_id': user_id}
            )
            db.session.commit()
            return True
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
            return False

    @staticmethod
    def update_password(user_id, new_password, set_password=False):
        """
        更新密码

        Args:
            user_id: 用户ID
            new_password: 新密码
            set_password: 是否为设置密码（True表示设置密码，False表示修改密码）
        """
        password_hash = generate_password_hash(new_password)
        db.session.execute(
            text('UPDATE users SET password_hash = :password_hash, has_password_set = true WHERE id = :user_id'),
            {'password_hash': password_hash, 'user_id': user_id}
        )
        db.session.commit()

    @staticmethod
    def has_password_set(user_id: int) -> bool:
        """
        检查用户是否设置了密码

        Args:
            user_id: 用户ID

        Returns:
            是否设置了密码
        """
        try:
            row = db.session.execute(
                text('SELECT has_password_set, password_hash, email, phone, openid FROM users WHERE id = :user_id'),
                {'user_id': user_id}
            ).fetchone()
            if not row:
                return False

            rm = row._mapping
            has_password_hash = bool(str(rm.get('password_hash') or '').strip())
            has_external_binding = any(
                bool(str(rm.get(k) or '').strip())
                for k in ('email', 'phone', 'openid')
            )

            if rm['has_password_set'] is True or rm['has_password_set'] == 1:
                return True

            if rm['has_password_set'] is False or rm['has_password_set'] == 0:
                if has_external_binding:
                    return False
                return has_password_hash

            if rm['has_password_set'] is None:
                if not has_password_hash:
                    return False
                return True

            return False
        except Exception as e:
            import logging
            logging.error(f'检查用户密码设置状态失败: {e}')
            return True

    @staticmethod
    def update_profile(user_id, avatar=None, contact=None, college=None):
        """更新用户资料"""
        updates = []
        params = {'user_id': user_id}

        if avatar is not None:
            updates.append('avatar = :avatar')
            params['avatar'] = avatar
        if contact is not None:
            updates.append('contact = :contact')
            params['contact'] = contact
        if college is not None:
            updates.append('college = :college')
            params['college'] = college

        if updates:
            sql = f"UPDATE users SET {', '.join(updates)} WHERE id = :user_id"
            db.session.execute(text(sql), params)
            db.session.commit()

        return UserService.get_by_id(user_id)

    @staticmethod
    def get_all(search='', page=1, size=10, sort='created_at', order='desc'):
        """获取所有用户（分页）"""
        offset = (page - 1) * size

        where = 'WHERE 1=1'
        params = {}
        if search:
            where += ' AND username LIKE :search'
            params['search'] = f'%{search}%'

        # 验证排序字段
        allowed_sorts = {'created_at', 'username', 'id'}
        if sort not in allowed_sorts:
            sort = 'created_at'
        if order not in ('asc', 'desc'):
            order = 'desc'

        total = db.session.execute(
            text(f'SELECT COUNT(*) FROM users {where}'), params
        ).scalar()

        params['limit'] = size
        params['offset'] = offset
        rows = db.session.execute(
            text(f'SELECT id, username, is_admin, is_locked, created_at FROM users {where} ORDER BY {sort} {order} LIMIT :limit OFFSET :offset'),
            params
        ).fetchall()

        return {
            'data': [dict(row._mapping) for row in rows],
            'total': total
        }

    @staticmethod
    def get_by_email(email: str) -> Optional[dict]:
        """通过邮箱获取用户"""
        if not email:
            return None
        row = db.session.execute(
            text('SELECT * FROM users WHERE email = :email'), {'email': email}
        ).fetchone()
        return dict(row._mapping) if row else None

    @staticmethod
    def bind_email(user_id: int, email: str) -> Optional[dict]:
        """绑定邮箱到用户账户"""
        try:
            existing = db.session.execute(
                text('SELECT id FROM users WHERE email = :email AND id != :user_id'),
                {'email': email, 'user_id': user_id}
            ).fetchone()
            if existing:
                return None

            from app.core.utils.time_utils import now_bj
            db.session.execute(
                text('''UPDATE users
                   SET email = :email, email_verified = true, email_verified_at = :now
                   WHERE id = :user_id'''),
                {'email': email, 'now': now_bj(), 'user_id': user_id}
            )
            db.session.commit()
            return UserService.get_by_id(user_id)
        except Exception:
            db.session.rollback()
            return None

    @staticmethod
    def update_email_verified(user_id: int, verified: bool = True) -> Optional[dict]:
        """更新邮箱验证状态"""
        try:
            from app.core.utils.time_utils import now_bj
            if verified:
                db.session.execute(
                    text('''UPDATE users
                       SET email_verified = true, email_verified_at = :now
                       WHERE id = :user_id'''),
                    {'now': now_bj(), 'user_id': user_id}
                )
            else:
                db.session.execute(
                    text('UPDATE users SET email_verified = false, email_verified_at = NULL WHERE id = :user_id'),
                    {'user_id': user_id}
                )
            db.session.commit()
            return UserService.get_by_id(user_id)
        except Exception:
            db.session.rollback()
            return None

    @staticmethod
    def is_email_available(email: str, exclude_user_id: Optional[int] = None) -> bool:
        """检查邮箱是否可用（未被其他用户使用）"""
        if not email:
            return False
        if exclude_user_id:
            row = db.session.execute(
                text('SELECT id FROM users WHERE email = :email AND id != :user_id'),
                {'email': email, 'user_id': exclude_user_id}
            ).fetchone()
        else:
            row = db.session.execute(
                text('SELECT id FROM users WHERE email = :email'),
                {'email': email}
            ).fetchone()
        return row is None


# 向后兼容别名：旧代码中 `from ... import User` 可继续工作
User = UserService
