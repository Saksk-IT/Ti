# -*- coding: utf-8 -*-
from flask import Blueprint, session

from app.core.extensions import db
from app.models.user import User as UserModel

main_pages_bp = Blueprint('main_pages', __name__)


@main_pages_bp.before_request
def sync_session_username():
    """页面请求前同步昵称，确保首页与侧边栏展示用户自定义昵称。"""
    uid = session.get('user_id')
    if not uid:
        return None

    try:
        db_username = (
            db.session.query(UserModel.username)
            .filter(UserModel.id == int(uid))
            .scalar()
        )
        if isinstance(db_username, str):
            db_username = db_username.strip()
        if db_username and db_username != session.get('username'):
            session['username'] = db_username
    except Exception:
        # 同步失败不影响主流程
        pass

    return None
