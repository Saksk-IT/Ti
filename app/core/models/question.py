# -*- coding: utf-8 -*-
"""
向后兼容桥接模块 — 已迁移至 app.core.services.question_service

请使用新路径导入：
    from app.core.services.question_service import QuestionService
"""
from app.core.services.question_service import QuestionService, Question  # noqa: F401

__all__ = ["Question", "QuestionService"]
