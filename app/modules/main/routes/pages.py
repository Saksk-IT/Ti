# -*- coding: utf-8 -*-
"""Main pages route aggregator (implemented in pages_components)."""

from .pages_components.bp import main_pages_bp

# Import submodules to register routes (keep legacy endpoints/URLs).
from .pages_components import account_settings as _account_settings  # noqa: F401
from .pages_components import dashboard_utility as _dashboard_utility  # noqa: F401
from .pages_components import data_center as _data_center  # noqa: F401
from .pages_components import hub as _hub  # noqa: F401
from .pages_components import misc as _misc  # noqa: F401
from .pages_components import resources as _resources  # noqa: F401
from .pages_components import review_center as _review_center  # noqa: F401
from .pages_components import search as _search  # noqa: F401
from .pages_components import subjects as _subjects  # noqa: F401
