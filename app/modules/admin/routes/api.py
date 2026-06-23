# -*- coding: utf-8 -*-
"""Admin API routes (split aggregator).

This module exposes `admin_api_bp` and imports component route modules to
register endpoints.
"""

from .api_bp import ALLOWED_EXTENSIONS, admin_api_bp, allowed_file

# Import component routes (imports register @admin_api_bp.route handlers)
from .api_components import chat  # noqa: F401
from .api_components import auth_login_settings  # noqa: F401
from .api_components import coding_questions  # noqa: F401
from .api_components import mail_settings  # noqa: F401
from .api_components import notifications  # noqa: F401
from .api_components import payment_settings  # noqa: F401
from .api_components import popups  # noqa: F401
from .api_components import questions  # noqa: F401
from .api_components import questions_io  # noqa: F401
from .api_components import sms_settings  # noqa: F401
from .api_components import subject_permissions  # noqa: F401
from .api_components import subjects  # noqa: F401
from .api_components import system_config  # noqa: F401
from .api_components import user_banks  # noqa: F401
from .api_components import users  # noqa: F401
from .api_components import wechat_miniprogram_settings  # noqa: F401
from .api_components import edu_schedule_settings  # noqa: F401
from .api_components import forum  # noqa: F401

__all__ = ['admin_api_bp', 'ALLOWED_EXTENSIONS', 'allowed_file']
