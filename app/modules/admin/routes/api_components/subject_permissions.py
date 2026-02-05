# -*- coding: utf-8 -*-
"""Admin API routes - subject permissions/restrictions."""

import datetime
import io
import json
import os
import sqlite3
import zipfile

import pandas as pd
from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from app.core.extensions import limiter
from app.core.utils.database import get_db
from app.core.utils.fill_blank_parser import parse_fill_blank
from app.core.utils.validators import parse_int, validate_password

from ..api_bp import admin_api_bp
from app.core.utils.decorators import admin_required
from app.modules.admin.services.subject_permission_service import SubjectPermissionService
from app.modules.admin.schemas import (
    BatchSubjectActionSchema,
    BatchUserSubjectActionSchema,
    SubjectIdsSchema,
)


@admin_api_bp.route('/users/<int:user_id>/subjects', methods=['GET'])
@admin_required
def get_user_subjects(user_id: int):
    """获取用户科目权限信息"""
    try:
        data = SubjectPermissionService.get_user_subjects(user_id)
        return jsonify({
            'status': 'success',
            'data': data
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取用户科目权限失败: {str(e)}'
        }), 500



@admin_api_bp.route('/users/<int:user_id>/subjects', methods=['POST'])
@admin_required
def restrict_user_subjects(user_id: int):
    """限制用户访问指定科目"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        # 使用Pydantic验证请求数据
        try:
            schema = SubjectIdsSchema.model_validate(data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据验证失败: {str(e)}'
            }), 400
        
        admin_id = session.get('user_id')
        result = SubjectPermissionService.restrict_subjects(
            user_id,
            schema.subject_ids,
            admin_id
        )
        
        return jsonify({
            'status': 'success',
            'message': result['message'],
            'data': {
                'restricted_count': result['restricted_count']
            }
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'限制科目失败: {str(e)}'
        }), 500



@admin_api_bp.route('/users/<int:user_id>/subjects/<int:subject_id>', methods=['DELETE'])
@admin_required
def unrestrict_user_subject(user_id: int, subject_id: int):
    """取消用户对指定科目的限制"""
    try:
        SubjectPermissionService.unrestrict_subject(user_id, subject_id)
        return jsonify({
            'status': 'success',
            'message': '已取消科目限制'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'取消限制失败: {str(e)}'
        }), 500



@admin_api_bp.route('/subjects/<int:subject_id>/restricted_users', methods=['GET'])
@admin_required
def get_subject_restricted_users(subject_id: int):
    """获取某个科目被限制的用户ID列表"""
    try:
        user_ids = SubjectPermissionService.get_subject_restricted_users(subject_id)
        return jsonify({
            'status': 'success',
            'data': {
                'user_ids': user_ids
            }
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取被限制用户列表失败: {str(e)}'
        }), 500



@admin_api_bp.route('/users/<int:user_id>/subjects/batch', methods=['POST'])
@admin_required
def batch_user_subjects(user_id: int):
    """批量限制/取消限制科目"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        try:
            schema = BatchSubjectActionSchema.model_validate(data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据验证失败: {str(e)}'
            }), 400
        
        admin_id = session.get('user_id')
        result = SubjectPermissionService.batch_restrict_subjects(
            user_id,
            schema.subject_ids,
            schema.action,
            admin_id
        )
        
        return jsonify({
            'status': 'success',
            'message': result['message'],
            'data': result
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'批量操作失败: {str(e)}'
        }), 500


# ==================== 批量管理 API ====================


@admin_api_bp.route('/subject_permissions/overview', methods=['GET'])
@admin_required
def get_subject_permissions_overview():
    """获取批量管理页面数据"""
    try:
        page = parse_int(request.args.get('page'), 1, 1)
        # 允许更大的per_page值以支持加载所有用户（最大10000）
        per_page = parse_int(request.args.get('per_page'), 20, 1, 10000)
        search = request.args.get('search', '').strip() or None
        
        data = SubjectPermissionService.get_overview_data(page, per_page, search)
        
        return jsonify({
            'status': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取数据失败: {str(e)}'
        }), 500



@admin_api_bp.route('/subject_permissions/batch', methods=['POST'])
@admin_required
def batch_subject_permissions():
    """批量操作用户科目权限"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        try:
            schema = BatchUserSubjectActionSchema.model_validate(data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据验证失败: {str(e)}'
            }), 400
        
        admin_id = session.get('user_id')
        result = SubjectPermissionService.batch_restrict_users_subjects(
            schema.user_ids,
            schema.subject_ids,
            schema.action,
            admin_id
        )
        
        return jsonify({
            'status': 'success',
            'message': result['message'],
            'data': {
                'affected_users': result['affected_users'],
                'affected_subjects': result['affected_subjects']
            }
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'批量操作失败: {str(e)}'
        }), 500

