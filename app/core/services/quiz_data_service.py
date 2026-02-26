# -*- coding: utf-8 -*-
"""统一数据访问服务 — 双表架构抽象层

根据 source 参数路由到公共题库表或用户题库表，
消除路由层直接操作双表的重复逻辑。

本次仅迁移 toggle_favorite 和 record_result 使用的操作，
后续逐步将 review_center_data / data_center_context_base 等迁移到此 Service。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.core.extensions import db
from app.models.quiz import Favorite, Mistake, UserAnswer
from app.models.user_bank import UserBankFavorite, UserBankMistake

logger = logging.getLogger(__name__)


class QuizDataService:
    """统一的刷题数据访问层，按 source 路由到不同表。"""

    # ------------------------------------------------------------------
    # 收藏
    # ------------------------------------------------------------------

    @staticmethod
    def get_favorite(user_id: int, question_id: int, source: str = 'public', scope_id: Optional[int] = None):
        """查询收藏记录，返回 ORM 对象或 None"""
        if source == 'user_bank':
            return UserBankFavorite.query.filter_by(
                user_id=user_id, question_id=question_id,
            ).first()
        return Favorite.query.filter_by(
            user_id=user_id, question_id=question_id,
        ).first()

    @staticmethod
    def toggle_favorite(user_id: int, question_id: int, source: str = 'public', scope_id: Optional[int] = None) -> bool:
        """切换收藏状态，返回切换后是否已收藏。"""
        if source == 'user_bank':
            existing = UserBankFavorite.query.filter_by(
                user_id=user_id, question_id=question_id,
            ).first()
            if existing:
                db.session.delete(existing)
                return False
            db.session.add(UserBankFavorite(
                user_id=user_id,
                question_id=question_id,
                bank_id=scope_id,
            ))
            return True

        existing = Favorite.query.filter_by(
            user_id=user_id, question_id=question_id,
        ).first()
        if existing:
            Favorite.query.filter_by(
                user_id=user_id, question_id=question_id,
            ).delete()
            return False
        db.session.add(Favorite(
            user_id=user_id, question_id=question_id,
        ))
        return True

    # ------------------------------------------------------------------
    # 错题
    # ------------------------------------------------------------------

    @staticmethod
    def record_mistake(user_id: int, question_id: int, source: str = 'public', scope_id: Optional[int] = None) -> None:
        """记录错题（wrong_count + 1）"""
        if source == 'user_bank':
            existing = UserBankMistake.query.filter_by(
                user_id=user_id, question_id=question_id,
            ).first()
            if existing:
                existing.wrong_count = (existing.wrong_count or 0) + 1
            else:
                db.session.add(UserBankMistake(
                    user_id=user_id,
                    bank_id=scope_id,
                    question_id=question_id,
                    wrong_count=1,
                ))
            return

        existing = Mistake.query.filter_by(
            user_id=user_id, question_id=question_id,
        ).first()
        if existing:
            existing.wrong_count = (existing.wrong_count or 0) + 1
            existing.updated_at = db.func.now()
            existing.last_updated = db.func.now()
        else:
            db.session.add(Mistake(
                user_id=user_id,
                question_id=question_id,
                wrong_count=1,
            ))

    @staticmethod
    def remove_mistake(user_id: int, question_id: int, source: str = 'public') -> None:
        """移除错题记录"""
        if source == 'user_bank':
            UserBankMistake.query.filter_by(
                user_id=user_id, question_id=question_id,
            ).delete()
        else:
            Mistake.query.filter_by(
                user_id=user_id, question_id=question_id,
            ).delete()

    # ------------------------------------------------------------------
    # 答题记录
    # ------------------------------------------------------------------

    @staticmethod
    def record_answer(user_id: int, question_id: int, is_correct: bool, source: str = 'public') -> None:
        """记录答题历史（公共题库专用，每题保留最新一条）"""
        if source == 'user_bank':
            # 用户题库暂无独立答题历史表，跳过
            return
        UserAnswer.query.filter_by(
            user_id=user_id, question_id=question_id,
        ).delete()
        db.session.add(UserAnswer(
            user_id=user_id,
            question_id=question_id,
            is_correct=bool(is_correct),
        ))
