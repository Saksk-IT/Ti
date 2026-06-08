# -*- coding: utf-8 -*-
"""Admin API routes - system config & quiz stats."""

from flask import (
    current_app,
    jsonify,
    request,
    session,
)

from app.core.utils.validators import parse_int

from ..api_bp import admin_api_bp
from app.core.utils.decorators import admin_required
from app.core.utils.api_response import error_response, success_response
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
                # API Key 脱敏
                if SystemConfigService.is_secret_config_key(config_key) and config.get('config_value'):
                    config = {**config, 'config_value': SystemConfigService.mask_api_key(config['config_value'])}
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

        # API Key 脱敏值跳过覆盖（含 **** 表示未修改）
        if SystemConfigService.is_secret_config_key(config_key) and SystemConfigService.is_masked_secret(schema.config_value or ''):
            return jsonify({
                'status': 'success',
                'message': '配置未变更（API Key 未修改）',
                'data': {'config_key': config_key}
            })

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


@admin_api_bp.route('/ai/models', methods=['POST'])
@admin_required
def list_ai_models():
    """从当前配置或表单临时值拉取上游模型列表。"""
    try:
        data = request.get_json(silent=True) or {}
        saved = SystemConfigService.get_ai_config()

        api_key = str(data.get('api_key') or '').strip()
        if not api_key or SystemConfigService.is_masked_secret(api_key):
            api_key = saved.get('api_key') or ''

        provider = str(data.get('provider') or saved.get('provider') or 'custom').strip().lower()
        api_type = str(data.get('api_type') or saved.get('api_type') or 'chat_completions').strip().lower()
        base_url = str(data.get('base_url') or saved.get('base_url') or '').strip().rstrip('/')
        timeout = parse_int(data.get('timeout'), saved.get('timeout') or 25, min_val=5, max_val=120)

        if provider not in {'dashscope', 'openai', 'custom'}:
            return error_response('服务商类型无效', status_code=400)
        if api_type not in {'chat_completions', 'responses'}:
            return error_response('接口类型无效', status_code=400)
        if not api_key:
            return error_response('请先填写 API Key 后再拉取模型', status_code=400)
        if not base_url.startswith(('https://', 'http://')):
            return error_response('API Base URL 必须以 http:// 或 https:// 开头', status_code=400)

        from app.modules.quiz.services.ai_client import AIClient

        client = AIClient(
            api_key=api_key,
            base_url=base_url,
            api_type=api_type,
            provider=provider,
        )
        models = client.list_models(timeout=timeout)
        return success_response(
            data={
                'models': models,
                'provider': provider,
                'base_url': base_url,
            },
            message='模型列表拉取成功',
        )
    except ValueError as e:
        return error_response(str(e), status_code=400)
    except Exception as e:
        current_app.logger.warning('AI模型列表拉取失败: %s', str(e), exc_info=True)
        return error_response('模型列表拉取失败，请检查 API Key、Base URL 与上游网络', status_code=502)



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
