# -*- coding: utf-8 -*-
"""刷题 API 路由（聚合入口）

路由实现已按功能拆分到 `api_components/*`，此文件仅负责导入注册与对外兼容导出。
"""

from .api_bp import quiz_api_bp

# 共享工具函数（供组件模块与历史兼容使用）
from .api_shared import _get_uid_from_request, _resolve_study_scope, _check_question_scope  # noqa: F401

# 导入组件模块以完成路由注册
from .api_components import core as _core  # noqa: F401
from .api_components import progress_tags_notifications as _ptn  # noqa: F401
from .api_components import subjects_search_ai_coding as _subjects  # noqa: F401
from .api_components import questions_study as _qs  # noqa: F401
from .api_components import ai_jobs as _ai_jobs  # noqa: F401
from .api_components import core_grading as _core_grading  # noqa: F401

# 兼容：app/modules/quiz/__init__.py 仍需从此处导出 /api/* 旧入口
from .api_components.core import toggle_favorite, record_result, api_questions_count, api_user_counts  # noqa: F401
from .api_components.core_grading import api_grade_subjective  # noqa: F401
from .api_components.progress_tags_notifications import progress_api  # noqa: F401
from .api_components.subjects_search_ai_coding import api_ai_explain  # noqa: F401
from .api_components.ai_jobs import api_ai_explain_async, api_job_status  # noqa: F401

__all__ = [
    'quiz_api_bp',
    'toggle_favorite',
    'record_result',
    'progress_api',
    'api_questions_count',
    'api_user_counts',
    'api_ai_explain',
    'api_ai_explain_async',
    'api_job_status',
    'api_grade_subjective',
]
