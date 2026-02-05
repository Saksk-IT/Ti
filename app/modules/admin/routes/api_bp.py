# -*- coding: utf-8 -*-
"""Admin API blueprint (shared for split routes)."""

from flask import Blueprint

admin_api_bp = Blueprint('admin_api', __name__)

ALLOWED_EXTENSIONS = {'json'}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
