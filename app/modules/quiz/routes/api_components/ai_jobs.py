# -*- coding: utf-8 -*-
"""AI 解析异步接口（RQ + Redis，可选）"""

import hashlib
import json
from typing import Any, Dict, Optional, Tuple

from flask import current_app, jsonify, request
from flask_limiter.util import get_remote_address

from app.core.extensions import limiter
from app.core.services.question_service import QuestionService as Question
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.redis_utils import redis_get_json, redis_get_text, redis_set_text
from app.core.utils.rq_utils import fetch_job, get_queue

from ..api_bp import quiz_api_bp


def _rate_key() -> str:
    uid = current_user_id()
    if uid:
        return f'uid:{uid}'
    return get_remote_address()


def _build_payload(uid: int, data: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[int]]:
    """构建 AI 解析 payload；优先以 question_id 为准，避免前端篡改题干/答案。"""
    from app.core.utils.subject_permissions import can_user_access_subject

    raw_qid = data.get('question_id')
    qid = None
    try:
        qid = int(raw_qid) if raw_qid is not None and str(raw_qid).strip() else None
    except Exception:
        qid = None

    payload: Dict[str, Any] = {
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
                return {'__forbidden__': True}, qid

            payload['content'] = (q.get('content') or '').strip()
            payload['q_type'] = (q.get('q_type') or '').strip()
            payload['options'] = q.get('options')
            payload['answer'] = (q.get('answer') or '').strip()

    return payload, qid


def _payload_hash(payload: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    stable = {
        'question_id': payload.get('question_id'),
        'content': payload.get('content') or '',
        'q_type': payload.get('q_type') or '',
        'options': payload.get('options') or [],
        'answer': payload.get('answer') or '',
        'provider': cfg.get('provider') or '',
        'api_type': cfg.get('api_type') or '',
        'model': cfg.get('model') or '',
    }
    s = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:32]


def _cache_keys(payload: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[str, str]:
    h = _payload_hash(payload, cfg)
    return f'ai_explain:result:{h}', f'ai_explain:job:{h}'


def _placeholder_explain() -> Dict[str, Any]:
    tip = '（未配置 AI 服务，当前返回模板解析；可在后台管理系统 → 系统设置 → AI 配置中启用）'
    lines = [tip, '', '建议解题思路：', '1) 先圈出关键词与限定条件。', '2) 把题干转为可验证的结论/公式/步骤。', '3) 对选择题：用排除法 + 代入验证。', '4) 对填空/简答题：列步骤，逐步推导，最后回代检查。']
    return {'provider': 'placeholder', 'explain': '\n'.join(lines)}


@quiz_api_bp.route('/ai/explain_async', methods=['POST'])
@auth_required  # 支持 session + JWT
@limiter.limit('30 per minute', key_func=_rate_key)
def api_ai_explain_async():
    """AI 解析（异步版）：返回 job_id，前端轮询 /jobs/<job_id> 获取结果。"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    data = request.json or {}
    payload, _qid = _build_payload(uid, data)
    if payload.get('__forbidden__'):
        return jsonify({'status': 'forbidden', 'message': '无权限访问该题目'}), 403

    if not payload.get('content') and not payload.get('question_id'):
        return jsonify({'status': 'error', 'message': '缺少题目信息'}), 400

    from app.modules.admin.services.system_config_service import SystemConfigService
    ai_cfg = SystemConfigService.get_ai_config()

    model = ai_cfg['model']
    timeout = ai_cfg['timeout']
    cache_ttl = int(current_app.config.get('AI_EXPLAIN_CACHE_TTL_SECONDS') or (30 * 24 * 60 * 60))

    result_key, job_key = _cache_keys(payload, ai_cfg)

    # 1) 先查缓存（命中直接返回，避免重复排队/扣费）
    cached = redis_get_json(result_key)
    if isinstance(cached, dict) and cached.get('explain'):
        return jsonify({'status': 'success', 'data': {**cached, 'cached': True}})

    # 2) 防重复：同 payload 若已有 job，直接复用 job_id
    exist_job_id = redis_get_text(job_key)
    if exist_job_id:
        return jsonify({'status': 'success', 'data': {'job_id': exist_job_id, 'cached': False}})

    # 3) 尝试入队（RQ + Redis）。若不可用则降级为同步模式
    queue = get_queue()
    if queue is None:
        api_key = ai_cfg['api_key']
        if not api_key:
            return jsonify({'status': 'success', 'data': {**_placeholder_explain(), 'cached': False}})

        from app.modules.quiz.services.ai_explain_service import generate_ai_explain

        try:
            explain = generate_ai_explain(
                api_key=api_key,
                base_url=ai_cfg['base_url'],
                model=model,
                payload=payload,
                timeout=timeout,
                provider=ai_cfg.get('provider') or 'custom',
                api_type=ai_cfg.get('api_type') or 'chat_completions',
            )
            result = {
                'provider': ai_cfg.get('provider') or 'custom',
                'api_type': ai_cfg.get('api_type') or 'chat_completions',
                'model': model,
                'explain': explain,
                'cached': False,
            }
            return jsonify({'status': 'success', 'data': result})
        except Exception:
            current_app.logger.exception('AI异步降级同步调用失败')
            return jsonify({'status': 'error', 'message': 'AI解析失败，请稍后重试'}), 502

    try:
        from app.tasks.ai_explain_tasks import ai_explain_task

        job = queue.enqueue(
            ai_explain_task,
            kwargs={
                'payload': payload,
                'model': model,
                'timeout': timeout,
                'ai_config': ai_cfg,
                'cache_key': result_key,
                'cache_ttl_seconds': cache_ttl,
            },
            job_timeout=120,
            result_ttl=24 * 60 * 60,
            failure_ttl=24 * 60 * 60,
        )
        job.meta['user_id'] = int(uid)
        job.meta['result_key'] = result_key
        job.save_meta()

        # 记录 job_id，短 TTL 防止短时间内重复入队
        redis_set_text(job_key, job.id, ttl_seconds=10 * 60, nx=True)

        return jsonify({'status': 'success', 'data': {'job_id': job.id, 'cached': False}})
    except Exception:
        current_app.logger.exception('AI解析入队失败')
        return jsonify({'status': 'error', 'message': '任务入队失败，请稍后重试'}), 500


@quiz_api_bp.route('/jobs/<job_id>', methods=['GET'])
@auth_required  # 支持 session + JWT
def api_job_status(job_id: str):
    """查询任务状态（当前仅用于 AI 解析）。"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    job = fetch_job(str(job_id).strip())
    if job is None:
        return jsonify({'status': 'error', 'message': '任务不存在或已过期'}), 404

    owner_id = job.meta.get('user_id')
    if owner_id is not None and int(owner_id) != int(uid):
        return jsonify({'status': 'forbidden', 'message': '无权限访问该任务'}), 403

    status = job.get_status()  # queued/started/finished/failed...
    data: Dict[str, Any] = {
        'job_id': job.id,
        'status': status,
        'enqueued_at': job.enqueued_at.isoformat() if getattr(job, 'enqueued_at', None) else None,
        'started_at': job.started_at.isoformat() if getattr(job, 'started_at', None) else None,
        'ended_at': job.ended_at.isoformat() if getattr(job, 'ended_at', None) else None,
    }

    if status == 'finished':
        res = job.result
        if isinstance(res, dict):
            data['result'] = res
        else:
            data['result'] = {'explain': str(res) if res is not None else ''}
    elif status == 'failed':
        data['error'] = '任务执行失败'

    return jsonify({'status': 'success', 'data': data})
