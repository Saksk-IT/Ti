# -*- coding: utf-8 -*-
"""
科目权限检查工具函数（黑名单模式）
"""
from typing import List, Tuple, Optional

from app.core.extensions import db
from app.models.user import User
from app.models.subject import Subject
from app.models.system import SystemConfig, UserSubject
from app.models.quiz import UserQuizStats


def is_admin(user_id: int) -> bool:
    """检查用户是否是管理员"""
    user = User.query.get(user_id)
    return bool(user and user.is_admin)


def get_user_restricted_subjects(user_id: int) -> List[int]:
    """获取用户被限制的科目ID列表（黑名单）"""
    if is_admin(user_id):
        return []

    rows = UserSubject.query.filter_by(user_id=user_id).all()
    return [r.subject_id for r in rows]


def can_user_access_subject(user_id: int, subject_id: int) -> bool:
    """检查用户是否可以访问指定科目（黑名单模式）"""
    if is_admin(user_id):
        return True

    restricted = UserSubject.query.filter_by(
        user_id=user_id, subject_id=subject_id
    ).first()
    return restricted is None


def get_user_accessible_subjects(user_id: int) -> List[int]:
    """获取用户可访问的科目ID列表（黑名单模式）"""
    if is_admin(user_id):
        rows = db.session.query(Subject.id).all()
        return [r.id for r in rows]

    all_ids = [r.id for r in db.session.query(Subject.id).all()]
    restricted_ids = set(get_user_restricted_subjects(user_id))
    return [sid for sid in all_ids if sid not in restricted_ids]


def filter_subjects_by_permission(user_id: Optional[int], subject_ids: List[int]) -> List[int]:
    """根据用户权限过滤科目ID列表"""
    if user_id is None:
        return []

    if is_admin(user_id):
        return subject_ids

    restricted_ids = set(get_user_restricted_subjects(user_id))
    return [sid for sid in subject_ids if sid not in restricted_ids]


def is_quiz_limit_enabled() -> bool:
    """检查刷题数限制功能是否开启"""
    try:
        from app.modules.admin.services.system_config_service import SystemConfigService
        cfg = SystemConfigService.get_config('quiz_limit_enabled')
        return bool(cfg and cfg.get('config_value') == '1')
    except Exception:
        row = SystemConfig.query.filter_by(config_key='quiz_limit_enabled').first()
        if not row:
            return False
        return row.config_value == '1'


def get_quiz_limit_count() -> int:
    """获取刷题数限制数量（默认100）"""
    try:
        from app.modules.admin.services.system_config_service import SystemConfigService
        cfg = SystemConfigService.get_config('quiz_limit_count')
        if not cfg:
            return 100
        return int(cfg.get('config_value'))
    except Exception:
        row = SystemConfig.query.filter_by(config_key='quiz_limit_count').first()
        if not row:
            return 100
        try:
            return int(row.config_value)
        except (ValueError, TypeError):
            return 100


def get_user_quiz_count(user_id: int) -> int:
    """获取用户当前刷题数"""
    stats = UserQuizStats.query.filter_by(user_id=user_id).first()
    return stats.total_answered if stats else 0


def check_quiz_limit(user_id: int) -> Tuple[bool, str]:
    """检查用户是否达到刷题限制"""
    if not is_quiz_limit_enabled():
        return False, ""

    if is_admin(user_id):
        return False, ""

    current_count = get_user_quiz_count(user_id)
    limit_count = get_quiz_limit_count()

    if current_count >= limit_count:
        message = f"已达到刷题限制（{limit_count}题），请付费或联系管理员"
        return True, message

    return False, ""


def increment_user_quiz_count(user_id: int) -> None:
    """增加用户刷题数（仅在功能开启时增加）"""
    if not is_quiz_limit_enabled():
        return

    if is_admin(user_id):
        return

    stats = UserQuizStats.query.filter_by(user_id=user_id).first()
    if stats:
        stats.total_answered = (stats.total_answered or 0) + 1
    else:
        stats = UserQuizStats(user_id=user_id, total_answered=1)
        db.session.add(stats)
    db.session.commit()


def reset_user_quiz_count(user_id: int) -> None:
    """重置用户刷题数"""
    from sqlalchemy import func as sa_func

    stats = UserQuizStats.query.filter_by(user_id=user_id).first()
    if stats:
        stats.total_answered = 0
        stats.last_reset_at = sa_func.now()
    else:
        stats = UserQuizStats(user_id=user_id, total_answered=0, last_reset_at=sa_func.now())
        db.session.add(stats)
    db.session.commit()

