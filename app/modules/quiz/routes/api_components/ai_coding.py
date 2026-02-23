# -*- coding: utf-8 -*-
"""AI 解析与编程执行相关路由。"""

from flask import request, jsonify, session, current_app
from app.core.extensions import limiter
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.redis_utils import redis_get_json, redis_set_json
from app.core.utils.cache_utils import make_cache_key
from app.core.models.question import Question

from ..api_bp import quiz_api_bp

def _ai_explain_rate_key():
    """AI 解析限流：优先按用户，其次按 IP。"""
    try:
        uid = current_user_id()
        if uid:
            return f"user:{int(uid)}"
    except Exception:
        pass
    try:
        from flask_limiter.util import get_remote_address

        return get_remote_address()
    except Exception:
        return 'unknown'

@quiz_api_bp.route('/ai/explain', methods=['POST'])
@auth_required  # 支持session和JWT
@limiter.limit("3 per minute;30 per hour", key_func=_ai_explain_rate_key)
def api_ai_explain():
    """AI 解析接口（阿里云百炼 DashScope OpenAI 兼容接口）。

    环境变量（推荐写入项目根目录 .env）：
    - DASHSCOPE_API_KEY: 百炼 API-KEY
    - DASHSCOPE_BASE_URL: 可选，北京默认 https://dashscope.aliyuncs.com/compatible-mode/v1
    - DASHSCOPE_MODEL: 可选，默认 qwen-plus
    """
    from flask import current_app
    from app.core.utils.subject_permissions import can_user_access_subject
    from app.modules.quiz.services.ai_explain_service import generate_ai_explain

    uid = current_user_id()
    data = request.json or {}

    # 允许前端仅传 question_id；后端优先用库内题目，避免前端篡改
    raw_qid = data.get('question_id')
    qid = None
    try:
        qid = int(raw_qid) if raw_qid is not None and str(raw_qid).strip() else None
    except Exception:
        qid = None

    payload = {
        'question_id': qid,
        'content': (data.get('content') or '').strip(),
        'q_type': (data.get('q_type') or '').strip(),
        'options': data.get('options'),
        'answer': (data.get('answer') or '').strip(),
    }

    if qid:
        q = Question.get_by_id(qid)
        if q:
            subject_id = q.get('subject_id')
            if subject_id and uid and not can_user_access_subject(uid, subject_id):
                return jsonify({'status': 'forbidden', 'message': '无权限访问该题目'}), 403

            payload['content'] = (q.get('content') or '').strip()
            payload['q_type'] = (q.get('q_type') or '').strip()
            payload['options'] = q.get('options')
            payload['answer'] = (q.get('answer') or '').strip()

    if not payload.get('content') and not payload.get('question_id'):
        return jsonify({'status': 'error', 'message': '缺少题目信息'}), 400

    api_key = (current_app.config.get('DASHSCOPE_API_KEY') or '').strip()
    base_url = (current_app.config.get('DASHSCOPE_BASE_URL') or '').strip()
    model = (current_app.config.get('DASHSCOPE_MODEL') or '').strip()
    timeout = int(current_app.config.get('DASHSCOPE_TIMEOUT') or 25)

    # 未配置密钥：保留旧行为，返回“占位解析”，同时提示如何配置
    if not api_key:
        tip = '（未配置 DASHSCOPE_API_KEY，当前为模板解析；配置后将自动使用百炼模型）'
        lines = [tip, '', '建议解题思路：', '1) 先圈出关键词与限定条件。', '2) 把题干转为可验证的结论/公式/步骤。', '3) 对选择题：用排除法 + 代入验证。', '4) 对填空/简答题：列步骤，逐步推导，最后回代检查。']
        return jsonify({'status': 'success', 'data': {'explain': '\n'.join(lines), 'provider': 'placeholder'}})

    # Redis 缓存：避免重复扣费/重复阻塞
    cache_key = None
    cache_ttl = int(current_app.config.get('AI_EXPLAIN_CACHE_TTL_SECONDS') or (30 * 24 * 60 * 60))
    if cache_ttl > 0:
        try:
            cache_key = make_cache_key(
                'quiz:ai_explain',
                {
                    'provider': 'dashscope',
                    'model': model or 'qwen-plus',
                    'base_url': base_url,
                    'payload': payload,
                },
            )
            cached = redis_get_json(cache_key)
            if isinstance(cached, dict) and cached.get('explain'):
                data_out = {
                    'explain': cached.get('explain'),
                    'provider': cached.get('provider') or 'dashscope',
                    'model': cached.get('model') or (model or 'qwen-plus'),
                    'cached': True,
                }
                return jsonify({'status': 'success', 'data': data_out})
        except Exception:
            cache_key = None

    try:
        explain = generate_ai_explain(
            api_key=api_key,
            base_url=base_url,
            model=model or 'qwen-plus',
            payload=payload,
            timeout=timeout,
        )
        data_out = {'explain': explain, 'provider': 'dashscope', 'model': model or 'qwen-plus'}
        if cache_key and cache_ttl > 0:
            try:
                redis_set_json(cache_key, data_out, ttl_seconds=cache_ttl)
            except Exception:
                pass
        return jsonify({'status': 'success', 'data': data_out})
    except Exception as e:
        current_app.logger.error('AI解析失败: %s', str(e), exc_info=True)
        return jsonify({'status': 'error', 'message': 'AI解析失败，请检查 DASHSCOPE_API_KEY / 计费状态 / 地域 Base URL 配置'}), 502


@quiz_api_bp.route('/coding/execute', methods=['POST'])
@limiter.limit("10 per minute")  # 限制执行频率：每分钟最多10次
def api_coding_execute():
    """
    代码执行接口（符合开发文档要求的路径：/api/coding/execute）
    
    Request Body:
    {
        "code": "print('Hello')",
        "language": "python",
        "input": "1\n2",  // 可选
        "time_limit": 5,  // 可选
        "memory_limit": 128  // 可选
    }
    
    Response:
    {
        "status": "success",
        "output": "Hello\n",
        "error": null,
        "execution_time": 0.05,
        "status_code": "success"
    }
    """
    if not session.get('user_id'):
        return jsonify({
            'status': 'unauthorized',
            'message': '请先登录'
        }), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        code = data.get('code', '').strip()
        language = data.get('language', 'python').lower()
        input_data = data.get('input', '')
        time_limit = data.get('time_limit', 5)
        memory_limit = data.get('memory_limit', 128)
        
        # 验证参数
        if not code:
            return jsonify({
                'status': 'error',
                'message': '代码不能为空'
            }), 400
        
        if language not in ['python']:  # 第一阶段只支持 Python
            return jsonify({
                'status': 'error',
                'message': f'不支持的编程语言: {language}'
            }), 400
        
        # 验证时间限制和内存限制
        if not isinstance(time_limit, (int, float)) or time_limit < 1 or time_limit > 30:
            time_limit = 5
        if not isinstance(memory_limit, int) or memory_limit < 64 or memory_limit > 512:
            memory_limit = 128
        
        # 执行代码
        from app.modules.coding.services.code_executor import PythonExecutor
        executor = PythonExecutor(time_limit=int(time_limit), memory_limit=memory_limit)
        result = executor.execute(code, input_data)
        
        # 限制输出长度（避免过长输出）
        if result.get('output') and len(result['output']) > 10000:
            result['output'] = result['output'][:10000] + '\n... (输出过长，已截断)'
        
        return jsonify({
            'status': 'success',
            'output': result.get('output', ''),
            'error': result.get('error'),
            'execution_time': result.get('execution_time', 0),
            'status_code': result.get('status', 'success')
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500
