# -*- coding: utf-8 -*-
"""
科目权限管理服务
"""
from typing import List, Dict, Any, Optional

from sqlalchemy import func as sa_func

from app.core.extensions import db
from app.models.user import User
from app.models.subject import Subject, Question
from app.models.system import UserSubject
from app.core.utils.subject_permissions import is_admin
from app.core.utils.cache_utils import bump_user_quiz_version


class SubjectPermissionService:
    """科目权限管理服务类"""

    @staticmethod
    def get_user_subjects(user_id: int) -> Dict[str, Any]:
        """获取用户的科目权限信息"""
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")

        # 所有科目及题目数量
        all_subjects = (
            db.session.query(
                Subject.id, Subject.name,
                sa_func.count(Question.id).label('question_count')
            )
            .outerjoin(Question, Subject.id == Question.subject_id)
            .group_by(Subject.id, Subject.name)
            .order_by(Subject.id)
            .all()
        )

        # 用户被限制的科目
        restricted_rows = UserSubject.query.filter_by(user_id=user_id).all()
        restricted_dict = {r.subject_id: r.restricted_at for r in restricted_rows}

        subjects_list = []
        restricted_count = 0
        for s in all_subjects:
            is_restricted = s.id in restricted_dict
            subjects_list.append({
                'id': s.id,
                'name': s.name,
                'question_count': s.question_count,
                'is_restricted': is_restricted,
                'restricted_at': restricted_dict.get(s.id),
            })
            if is_restricted:
                restricted_count += 1

        return {
            'user': {'id': user.id, 'username': user.username},
            'all_subjects': subjects_list,
            'restricted_count': restricted_count,
            'total_count': len(subjects_list),
        }

    @staticmethod
    def restrict_subjects(user_id: int, subject_ids: List[int], admin_id: int) -> Dict[str, Any]:
        """限制用户访问指定科目（添加到黑名单）"""
        if not subject_ids:
            raise ValueError("科目ID列表不能为空")

        success_count = 0
        try:
            for subject_id in subject_ids:
                if not Subject.query.get(subject_id):
                    continue
                existing = UserSubject.query.filter_by(
                    user_id=user_id, subject_id=subject_id
                ).first()
                if not existing:
                    db.session.add(UserSubject(
                        user_id=user_id, subject_id=subject_id, restricted_by=admin_id
                    ))
                    success_count += 1

            db.session.commit()
            try:
                bump_user_quiz_version(int(user_id))
            except Exception:
                pass

            return {
                'restricted_count': success_count,
                'message': f'成功限制 {success_count} 个科目',
            }
        except Exception as e:
            db.session.rollback()
            raise Exception(f"限制科目失败: {str(e)}")

    @staticmethod
    def unrestrict_subject(user_id: int, subject_id: int) -> None:
        """取消用户对指定科目的限制"""
        UserSubject.query.filter_by(user_id=user_id, subject_id=subject_id).delete()
        db.session.commit()
        try:
            bump_user_quiz_version(int(user_id))
        except Exception:
            pass
    
    @staticmethod
    def batch_restrict_subjects(
        user_id: int,
        subject_ids: List[int],
        action: str,
        admin_id: int
    ) -> Dict[str, Any]:
        """批量限制/取消限制科目"""
        if action == 'restrict':
            return SubjectPermissionService.restrict_subjects(user_id, subject_ids, admin_id)
        elif action == 'unrestrict':
            success_count = 0
            try:
                for subject_id in subject_ids:
                    deleted = UserSubject.query.filter_by(
                        user_id=user_id, subject_id=subject_id
                    ).delete()
                    if deleted > 0:
                        success_count += 1

                db.session.commit()
                try:
                    bump_user_quiz_version(int(user_id))
                except Exception:
                    pass

                return {
                    'unrestricted_count': success_count,
                    'message': f'成功取消限制 {success_count} 个科目',
                }
            except Exception as e:
                db.session.rollback()
                raise Exception(f"取消限制失败: {str(e)}")
        else:
            raise ValueError(f"不支持的操作类型: {action}")

    @staticmethod
    def batch_restrict_users_subjects(
        user_ids: List[int],
        subject_ids: List[int],
        action: str,
        admin_id: int
    ) -> Dict[str, Any]:
        """批量为多个用户限制/取消限制多个科目"""
        if not user_ids or not subject_ids:
            raise ValueError("用户ID列表和科目ID列表不能为空")

        affected_users = 0
        affected_subjects = len(subject_ids)

        try:
            for user_id in user_ids:
                if is_admin(user_id):
                    continue

                if action == 'restrict':
                    for subject_id in subject_ids:
                        existing = UserSubject.query.filter_by(
                            user_id=user_id, subject_id=subject_id
                        ).first()
                        if not existing:
                            db.session.add(UserSubject(
                                user_id=user_id, subject_id=subject_id, restricted_by=admin_id
                            ))
                elif action == 'unrestrict':
                    for subject_id in subject_ids:
                        UserSubject.query.filter_by(
                            user_id=user_id, subject_id=subject_id
                        ).delete()

                affected_users += 1

            db.session.commit()
            try:
                for uid in (user_ids or []):
                    try:
                        bump_user_quiz_version(int(uid))
                    except Exception:
                        continue
            except Exception:
                pass

            return {
                'affected_users': affected_users,
                'affected_subjects': affected_subjects,
                'message': f'成功为 {affected_users} 个用户{action} {affected_subjects} 个科目',
            }
        except Exception as e:
            db.session.rollback()
            raise Exception(f"批量操作失败: {str(e)}")

    @staticmethod
    def get_overview_data(
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取批量管理页面所需的数据"""
        offset = (page - 1) * per_page

        # 用户查询
        user_query = db.session.query(User.id, User.username)
        if search:
            user_query = user_query.filter(User.username.ilike(f'%{search}%'))

        total_users = user_query.count()

        # 用户列表（带限制科目统计）
        users_with_stats = (
            db.session.query(
                User.id, User.username,
                sa_func.count(sa_func.distinct(UserSubject.subject_id)).label('restricted_subjects_count')
            )
            .outerjoin(UserSubject, User.id == UserSubject.user_id)
        )
        if search:
            users_with_stats = users_with_stats.filter(User.username.ilike(f'%{search}%'))
        users_with_stats = (
            users_with_stats
            .group_by(User.id, User.username)
            .order_by(User.id)
            .limit(per_page).offset(offset)
            .all()
        )

        total_subjects = Subject.query.count()

        # 科目列表（带限制用户统计）
        subjects_with_stats = (
            db.session.query(
                Subject.id, Subject.name,
                sa_func.count(sa_func.distinct(Question.id)).label('question_count'),
                sa_func.count(sa_func.distinct(UserSubject.user_id)).label('restricted_users_count')
            )
            .outerjoin(Question, Subject.id == Question.subject_id)
            .outerjoin(UserSubject, Subject.id == UserSubject.subject_id)
            .group_by(Subject.id, Subject.name)
            .order_by(Subject.id)
            .all()
        )

        total_restrictions = UserSubject.query.count()

        return {
            'users': [
                {
                    'id': u.id,
                    'username': u.username,
                    'restricted_subjects_count': u.restricted_subjects_count or 0,
                    'total_subjects_count': total_subjects,
                }
                for u in users_with_stats
            ],
            'subjects': [
                {
                    'id': s.id,
                    'name': s.name,
                    'question_count': s.question_count,
                    'restricted_users_count': s.restricted_users_count or 0,
                }
                for s in subjects_with_stats
            ],
            'stats': {
                'total_users': total_users,
                'total_subjects': total_subjects,
                'total_restrictions': total_restrictions,
            },
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_users,
                'pages': (total_users + per_page - 1) // per_page,
            },
        }

    @staticmethod
    def get_subject_restricted_users(subject_id: int) -> List[int]:
        """获取某个科目被限制的用户ID列表"""
        subject = Subject.query.get(subject_id)
        if not subject:
            raise ValueError(f"科目 {subject_id} 不存在")

        rows = UserSubject.query.filter_by(subject_id=subject_id).all()
        return [r.user_id for r in rows]


