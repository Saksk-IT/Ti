# -*- coding: utf-8 -*-
"""
桥接模块 — 保持向后兼容

实际实现已迁移至 app.modules.exam.services.exam_legacy_service。
本文件仅做重导出，避免其他模块的旧导入路径报错。
"""
from app.modules.exam.services.exam_legacy_service import ExamLegacyService, Exam

__all__ = ['Exam', 'ExamLegacyService']
