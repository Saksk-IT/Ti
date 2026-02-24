# -*- coding: utf-8 -*-
"""弹窗业务逻辑服务（ORM 版本）"""
import logging
from typing import List, Optional, Dict, Any

from app.core.extensions import db
from app.core.utils.time_utils import now_bj
from app.models.popup import Popup, PopupDismissal, PopupView

logger = logging.getLogger(__name__)


class PopupService:
    """弹窗服务类"""

    @staticmethod
    def get_active_popups_for_user(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """获取用户应显示的活跃弹窗列表（支持轮播/队列）"""
        now = now_bj()

        # 子查询：该用户已关闭的弹窗 ID
        dismissed_ids = (
            db.session.query(PopupDismissal.popup_id)
            .filter(PopupDismissal.user_id == user_id)
            .subquery()
        )

        rows = (
            db.session.query(Popup)
            .filter(
                Popup.is_active == True,  # noqa: E712
                Popup.id.notin_(db.session.query(dismissed_ids.c.popup_id)),
                db.or_(Popup.start_at.is_(None), Popup.start_at <= now),
                db.or_(Popup.end_at.is_(None), Popup.end_at >= now),
            )
            .order_by(Popup.priority.desc(), Popup.created_at.desc(), Popup.id.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                'id': p.id,
                'title': p.title,
                'content': p.content,
                'popup_type': p.popup_type,
                'priority': p.priority,
                'start_at': p.start_at.isoformat() if p.start_at else None,
                'end_at': p.end_at.isoformat() if p.end_at else None,
                'created_at': p.created_at.isoformat() if p.created_at else None,
            }
            for p in rows
        ]
    @staticmethod
    def record_popup_view(popup_id: int, user_id: Optional[int] = None) -> None:
        """记录弹窗显示次数（用于统计）"""
        try:
            view = PopupView(popup_id=popup_id, user_id=user_id)
            db.session.add(view)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error('记录弹窗显示失败: %s', e, exc_info=True)

    @staticmethod
    def dismiss_popup(popup_id: int, user_id: int) -> bool:
        """关闭弹窗（记录到 popup_dismissals，用户将不再看到该弹窗）"""
        try:
            existing = (
                db.session.query(PopupDismissal)
                .filter_by(user_id=user_id, popup_id=popup_id)
                .first()
            )
            if not existing:
                dismissal = PopupDismissal(user_id=user_id, popup_id=popup_id)
                db.session.add(dismissal)
                db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error('关闭弹窗失败: %s', e, exc_info=True)
            return False

    @staticmethod
    def get_popup_stats(popup_id: int) -> Optional[Dict[str, Any]]:
        """获取弹窗统计信息"""
        popup = db.session.get(Popup, popup_id)
        if not popup:
            return None

        view_count = (
            db.session.query(db.func.count(PopupView.id))
            .filter(PopupView.popup_id == popup_id)
            .scalar()
        ) or 0

        dismissal_count = (
            db.session.query(db.func.count(PopupDismissal.id))
            .filter(PopupDismissal.popup_id == popup_id)
            .scalar()
        ) or 0

        dismissal_rate = dismissal_count / view_count if view_count > 0 else 0.0

        return {
            'popup_id': popup_id,
            'total_views': view_count,
            'total_dismissals': dismissal_count,
            'dismissal_rate': round(dismissal_rate, 4),
        }

    @staticmethod
    def get_all_popups_stats() -> List[Dict[str, Any]]:
        """获取所有弹窗的统计信息"""
        popups = (
            db.session.query(Popup.id)
            .order_by(Popup.id.desc())
            .all()
        )

        stats_list = []
        for (pid,) in popups:
            stats = PopupService.get_popup_stats(pid)
            if stats:
                stats_list.append(stats)
        return stats_list
