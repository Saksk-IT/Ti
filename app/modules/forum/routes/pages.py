# -*- coding: utf-8 -*-
"""论坛页面路由"""
from flask import Blueprint, render_template, request, session

from app.core.utils.decorators import login_required

forum_pages_bp = Blueprint('forum_pages', __name__)


@forum_pages_bp.route('/community')
@login_required
def community_home():
    """社区首页"""
    return render_template('forum/community.html')


@forum_pages_bp.route('/community/board/<int:board_id>')
@login_required
def board_detail(board_id: int):
    """版块帖子列表"""
    return render_template('forum/board.html', board_id=board_id)


@forum_pages_bp.route('/community/post/<int:post_id>')
@login_required
def post_detail(post_id: int):
    """帖子详情"""
    return render_template('forum/post_detail.html', post_id=post_id)


@forum_pages_bp.route('/community/new')
@login_required
def post_create():
    """发帖页"""
    board_id = request.args.get('board_id', type=int)
    return render_template('forum/post_create.html', board_id=board_id)


@forum_pages_bp.route('/community/post/<int:post_id>/edit')
@login_required
def post_edit(post_id: int):
    """编辑帖子"""
    return render_template('forum/post_create.html', post_id=post_id, editing=True)


@forum_pages_bp.route('/community/favorites')
@login_required
def my_favorites():
    """我的收藏"""
    return render_template('forum/my_favorites.html')
