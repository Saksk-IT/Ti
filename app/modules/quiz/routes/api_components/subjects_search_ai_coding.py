# -*- coding: utf-8 -*-
"""科目 / 搜索 / AI解析 & 编程执行 —— 聚合 re-export 模块。

原始实现已拆分至：
  - subjects.py   科目列表、元信息、详情、统计、题目列表、收藏趋势
  - search.py     题目搜索
  - ai_coding.py  AI 解析、代码执行

本文件仅做 re-export，确保所有外部 ``from ...subjects_search_ai_coding import xxx``
的引用继续正常工作。
"""

# 导入子模块以触发路由注册（@quiz_api_bp.route 装饰器）
from . import subjects as _subjects  # noqa: F401
from . import search as _search  # noqa: F401
from . import ai_coding as _ai_coding  # noqa: F401

# 显式 re-export 被外部引用的符号
from .subjects import (  # noqa: F401
    api_subjects,
    api_subjects_meta,
    api_subject_info,
    api_subject_stats_detail,
    api_subject_questions,
    api_subject_favorites_trend,
)
from .search import api_search_questions  # noqa: F401
from .ai_coding import (  # noqa: F401
    api_ai_explain,
    api_coding_execute,
)

__all__ = [
    # subjects
    'api_subjects',
    'api_subjects_meta',
    'api_subject_info',
    'api_subject_stats_detail',
    'api_subject_questions',
    'api_subject_favorites_trend',
    # search
    'api_search_questions',
    # ai_coding
    'api_ai_explain',
    'api_coding_execute',
]
