# -*- coding: utf-8 -*-
"""手机短信认证 API 路由"""
from flask import Blueprint, request, jsonify, current_app, session
from app.core.extensions import limiter
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.jwt_utils import generate_jwt_token
from app.modules.auth.schemas import (
    SendPhoneCodeSchema,
    PhoneLoginSchema,
    BindPhoneSchema,
    PhoneResetPasswordSchema,
)
from app.modules.auth.services.sms_auth_service import SmsAuthService
from app.modules.auth.services.web_login_service import set_web_session

sms_api_bp = Blueprint('sms_api', __name__)


@sms_api_bp.route('/send-login-code', methods=['POST'])
@limiter.limit("3 per minute;10 per hour")
def send_login_code():
    """发送登录/注册验证码"""
    data = request.json or {}
    try:
        schema = SendPhoneCodeSchema.model_validate(data)
    except Exception:
        return jsonify({'status': 'error', 'message': '请输入正确的手机号'}), 400

    success, msg = SmsAuthService.send_login_code(schema.phone)
    if not success:
        return jsonify({'status': 'error', 'message': msg}), 400
    return jsonify({'status': 'success', 'message': '验证码已发送'})


@sms_api_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def phone_login():
    """手机验证码登录"""
    data = request.json or {}
    try:
        schema = PhoneLoginSchema.model_validate(data)
    except Exception:
        return jsonify({'status': 'error', 'message': '请求数据格式不正确'}), 400

    success, msg, user_info = SmsAuthService.verify_login_code(schema.phone, schema.code)
    if not success:
        return jsonify({'status': 'error', 'message': msg}), 400

    # 设置 session
    set_web_session(user_info['id'])

    # 生成 JWT
    token = generate_jwt_token(user_info['id'], user_info.get('session_version', 0))

    return jsonify({
        'status': 'success',
        'message': '登录成功',
        'token': token,
        'user': user_info,
    })


@sms_api_bp.route('/send-bind-code', methods=['POST'])
@auth_required
@limiter.limit("1 per minute;5 per hour")
def send_bind_code():
    """发送绑定手机验证码（需登录）"""
    data = request.json or {}
    try:
        schema = SendPhoneCodeSchema.model_validate(data)
    except Exception:
        return jsonify({'status': 'error', 'message': '请输入正确的手机号'}), 400

    user_id = current_user_id()
    success, msg = SmsAuthService.send_bind_code(schema.phone, user_id)
    if not success:
        return jsonify({'status': 'error', 'message': msg}), 400
    return jsonify({'status': 'success', 'message': '验证码已发送'})


@sms_api_bp.route('/bind', methods=['POST'])
@auth_required
@limiter.limit("10 per minute")
def bind_phone():
    """绑定手机号（需登录）"""
    data = request.json or {}
    try:
        schema = BindPhoneSchema.model_validate(data)
    except Exception:
        return jsonify({'status': 'error', 'message': '请求数据格式不正确'}), 400

    user_id = current_user_id()
    success, msg, info = SmsAuthService.bind_phone(schema.phone, schema.code, user_id)
    if not success:
        return jsonify({'status': 'error', 'message': msg}), 400
    return jsonify({'status': 'success', 'message': '手机号绑定成功', 'data': info})


@sms_api_bp.route('/forgot-password/send-code', methods=['POST'])
@limiter.limit("1 per minute;5 per hour")
def send_forgot_password_code():
    """发送重置密码验证码"""
    data = request.json or {}
    try:
        schema = SendPhoneCodeSchema.model_validate(data)
    except Exception:
        return jsonify({'status': 'error', 'message': '请输入正确的手机号'}), 400

    success, msg = SmsAuthService.send_reset_password_code(schema.phone)
    if not success:
        return jsonify({'status': 'error', 'message': msg}), 400
    return jsonify({'status': 'success', 'message': '验证码已发送'})


@sms_api_bp.route('/forgot-password/reset', methods=['POST'])
@limiter.limit("10 per minute")
def reset_password():
    """手机号重置密码"""
    data = request.json or {}
    try:
        schema = PhoneResetPasswordSchema.model_validate(data)
    except Exception:
        return jsonify({'status': 'error', 'message': '请求数据格式不正确'}), 400

    success, msg = SmsAuthService.reset_password(schema.phone, schema.code, schema.new_password)
    if not success:
        return jsonify({'status': 'error', 'message': msg}), 400
    return jsonify({'status': 'success', 'message': '密码重置成功'})
