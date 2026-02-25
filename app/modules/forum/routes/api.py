# -*- coding: utf-8 -*-
"""论坛 API 路由聚合器"""
from flask import Blueprint

forum_api_bp = Blueprint('forum_api', __name__)

from .api_components import boards  # noqa: F401,E402
from .api_components import posts  # noqa: F401,E402
from .api_components import comments  # noqa: F401,E402
from .api_components import interactions  # noqa: F401,E402
from .api_components import uploads  # noqa: F401,E402
