# -*- coding: utf-8 -*-
"""User bank API routes (aggregator).

Note:
- The original api.py was split into multiple api_*.py modules under the same folder.
- Backward-compatible re-exports are preserved: user_bank_api_bp / check_bank_access / _load_bank_tag_store.
"""

from .api_base import (
    user_bank_api_bp,
    check_bank_access,
    generate_share_code,
    get_bank_category_name,
)

from .api_tags import _load_bank_tag_store

# Import submodules to register routes on the shared blueprint.
from . import api_categories  # noqa: F401
from . import api_banks  # noqa: F401
from . import api_questions  # noqa: F401
from . import api_duplicate_check  # noqa: F401
from . import api_transfer  # noqa: F401
from . import api_shares  # noqa: F401
from . import api_quiz  # noqa: F401
from . import api_favorites  # noqa: F401
from . import api_tags  # noqa: F401
from . import api_uploads  # noqa: F401


__all__ = [
    "user_bank_api_bp",
    "check_bank_access",
    "generate_share_code",
    "get_bank_category_name",
    "_load_bank_tag_store",
]
