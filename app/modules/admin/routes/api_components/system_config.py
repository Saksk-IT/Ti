# -*- coding: utf-8 -*-
"""Admin API routes - system config & quiz stats."""

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
from app.modules.admin.schemas import BatchResetQuizCountSchema, SystemConfigUpdateSchema
from app.modules.admin.services.quiz_stats_service import QuizStatsService
from app.modules.admin.services.system_config_service import SystemConfigService


@admin_api_bp.route('/system_config', methods=['GET'])
@admin_required
def get_system_configs():
    """获取所有系统配置"""
    try:
        configs = SystemConfigService.get_all_configs()
        return jsonify({
            'status': 'success',
            'data': configs
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取配置失败: {str(e)}'
        }), 500



@admin_api_bp.route('/system_config/<config_key>', methods=['GET', 'PUT'])
@admin_required
def get_or_update_system_config(config_key: str):
    """获取或更新系统配置"""
    if request.method == 'GET':
        try:
            config = SystemConfigService.get_config(config_key)
            if config:
                return jsonify({
                    'status': 'success',
                    'data': config
                })
            else:
                # 如果配置不存在，返回默认值（用于向后兼容）
                return jsonify({
                    'status': 'success',
                    'data': {
                        'config_key': config_key,
                        'config_value': '1' if config_key == 'email_bind_required' else '',
                        'description': ''
                    }
                })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'获取配置失败: {str(e)}'
            }), 500
    
    # PUT 方法（更新配置）
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        try:
            schema = SystemConfigUpdateSchema.model_validate(data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据验证失败: {str(e)}'
            }), 400
        
        admin_id = session.get('user_id')
        config = SystemConfigService.update_config(
            config_key,
            schema.config_value,
            schema.description,
            admin_id
        )
        
        return jsonify({
            'status': 'success',
            'message': '配置更新成功',
            'data': config
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'更新配置失败: {str(e)}'
        }), 500
    """更新系统配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        try:
            schema = SystemConfigUpdateSchema.model_validate(data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据验证失败: {str(e)}'
            }), 400
        
        admin_id = session.get('user_id')
        config = SystemConfigService.update_config(
            config_key,
            schema.config_value,
            schema.description,
            admin_id
        )
        
        return jsonify({
            'status': 'success',
            'message': '配置更新成功',
            'data': config
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'更新配置失败: {str(e)}'
        }), 500



@admin_api_bp.route('/system_config/quiz_limit', methods=['GET'])
@admin_required
def get_quiz_limit_config():
    """获取刷题限制配置"""
    try:
        config = SystemConfigService.get_quiz_limit_config()
        return jsonify({
            'status': 'success',
            'data': config
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取配置失败: {str(e)}'
        }), 500


# ==================== 用户刷题数管理 API ====================


@admin_api_bp.route('/users/<int:user_id>/quiz_stats', methods=['GET'])
@admin_required
def get_user_quiz_stats(user_id: int):
    """获取用户刷题统计"""
    try:
        data = QuizStatsService.get_user_quiz_stats(user_id)
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
            'message': f'获取统计失败: {str(e)}'
        }), 500



@admin_api_bp.route('/users/<int:user_id>/reset_quiz_count', methods=['POST'])
@admin_required
def reset_user_quiz_count(user_id: int):
    """重置用户刷题数"""
    try:
        QuizStatsService.reset_user_quiz_count(user_id)
        return jsonify({
            'status': 'success',
            'message': '刷题数重置成功'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'重置失败: {str(e)}'
        }), 500



@admin_api_bp.route('/users/batch_reset_quiz_count', methods=['POST'])
@admin_required
def batch_reset_quiz_count():
    """批量重置用户刷题数"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        try:
            schema = BatchResetQuizCountSchema.model_validate(data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据验证失败: {str(e)}'
            }), 400
        
        result = QuizStatsService.batch_reset_quiz_count(schema.user_ids)
        
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
            'message': f'批量重置失败: {str(e)}'
        }), 500


