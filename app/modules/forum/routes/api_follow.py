# -*- coding: utf-8 -*-
"""关注 API — 独立蓝图，url_prefix=/api（由 forum 模块注册）"""
from flask import Blueprint, jsonify, request, session, current_app

from app.modules.forum.services import follow_service
from app.modules.forum.services import interaction_service

forum_user_api_bp = Blueprint('forum_user_api', __name__)


@forum_user_api_bp.route('/user/follow', methods=['POST'])
def api_follow_user():
    """关注用户"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session['user_id'])
    data = request.get_json(silent=True) or {}
    try:
        target_id = int(data.get('target_id') or 0)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': '参数错误'}), 400

    if target_id <= 0:
        return jsonify({'status': 'error', 'message': '参数错误'}), 400

    result = follow_service.follow_user(uid, target_id)
    if 'error' in result:
        return jsonify({'status': 'error', 'message': result['error']}), 400

    # 触发互动通知
    try:
        interaction_service.create_notification(
            user_id=target_id, actor_id=uid,
            action_type=interaction_service.ACTION_FOLLOW,
            target_type='user', target_id=uid,
        )
    except Exception as e:
        current_app.logger.warning("关注通知失败: %s", e)

    status = follow_service.get_follow_status(uid, target_id)
    return jsonify({'status': 'success', 'data': status})


@forum_user_api_bp.route('/user/unfollow', methods=['POST'])
def api_unfollow_user():
    """取消关注"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session['user_id'])
    data = request.get_json(silent=True) or {}
    try:
        target_id = int(data.get('target_id') or 0)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': '参数错误'}), 400

    if target_id <= 0:
        return jsonify({'status': 'error', 'message': '参数错误'}), 400

    follow_service.unfollow_user(uid, target_id)
    status = follow_service.get_follow_status(uid, target_id)
    return jsonify({'status': 'success', 'data': status})


@forum_user_api_bp.route('/user/<int:user_id>/follow_status')
def api_follow_status(user_id: int):
    """获取关注状态"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session['user_id'])
    status = follow_service.get_follow_status(uid, user_id)
    return jsonify({'status': 'success', 'data': status})


@forum_user_api_bp.route('/user/<int:user_id>/followers')
def api_followers(user_id: int):
    """粉丝列表"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)
    data = follow_service.get_followers(user_id, page, per_page)
    return jsonify({'status': 'success', 'data': data})


@forum_user_api_bp.route('/user/<int:user_id>/following')
def api_following(user_id: int):
    """关注列表"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)
    data = follow_service.get_following(user_id, page, per_page)
    return jsonify({'status': 'success', 'data': data})
