# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta

from flask import current_app, jsonify, redirect, render_template, request, session
from sqlalchemy import text

from app.core.extensions import db, limiter
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.time_utils import today_bj

from .bp import main_pages_bp
from .common import _get_accessible_subject_rows
from .data_center_context_base import compute_data_center_context_base, _build_named_in
from .data_center_context_extra import compute_data_center_context_extra


def _compute_data_center_context(uid: int, window_days: int) -> dict:
    from app.core.utils.cache_utils import make_cache_key, get_user_quiz_version
    from app.core.utils.redis_utils import redis_get_json, redis_set_json

    # 尝试从缓存读取
    cache_key = None
    try:
        cache_key = make_cache_key('data_center', {
            'uid': int(uid),
            'days': int(window_days),
            'ver': get_user_quiz_version(int(uid)),
        })
        cached = redis_get_json(cache_key)
        if isinstance(cached, dict) and cached:
            return cached
    except Exception:
        cache_key = None

    # 缓存未命中，执行原始计算
    subject_ids, base_ctx = compute_data_center_context_base(uid, window_days)
    conn = db.session.connection()
    result = compute_data_center_context_extra(conn, uid, window_days, subject_ids, base_ctx)

    # 写入缓存（TTL 120 秒）
    if cache_key:
        try:
            redis_set_json(cache_key, result, ttl_seconds=120)
        except Exception:
            pass

    return result


@main_pages_bp.route('/data')
@main_pages_bp.route('/data/global')
@main_pages_bp.route('/data/banks')
@main_pages_bp.route('/data/mistakes')
@main_pages_bp.route('/data/favorites')
@main_pages_bp.route('/data/tags')
@main_pages_bp.route('/data/trend')  # legacy
@main_pages_bp.route('/data/ai')  # legacy
@main_pages_bp.route('/history')
def history_page():
    """数据中心：概览/题库/趋势/AI 四子页面"""
    uid = session.get('user_id')
    if not uid:
        return redirect('/login')

    window_days = request.args.get('days', 30, type=int)
    if window_days not in (7, 30, 90):
        window_days = 30

    ctx = _compute_data_center_context(int(uid), int(window_days))

    path = (request.path or '').lower()
    # legacy：趋势/AI 合并进全局页（仍保留旧链接可访问）
    if path.startswith('/data/trend') or path.startswith('/data/ai'):
        return redirect(f"/data/global?days={window_days}")

    if path.startswith('/data/banks'):
        active_tab = 'banks'
    elif path.startswith('/data/mistakes'):
        active_tab = 'mistakes'
    elif path.startswith('/data/favorites'):
        active_tab = 'favorites'
    elif path.startswith('/data/tags'):
        active_tab = 'tags'
    else:
        active_tab = 'global'

    template_map = {
        'global': 'main/data/data_v2_global.html',
        'banks': 'main/data/data_v2_banks.html',
        'mistakes': 'main/data/data_v2_mistakes.html',
        'favorites': 'main/data/data_v2_favorites.html',
        'tags': 'main/data/data_v2_tags.html',
    }

    # Hero：按页面给出更聚焦的 KPI（移动端也能一眼看懂）
    hero_title = '数据中心 · 全局'
    hero_subtitle = '全局视角：覆盖、正确、连续与复盘资产，一屏把握你的学习系统。'
    hero_kpis = [
        {'k': '已做题', 'v': (ctx.get('all_summary') or {}).get('answered', 0)},
        {'k': '正确率', 'v': f"{(ctx.get('all_summary') or {}).get('accuracy', 0)}%"},
        {'k': '完成度', 'v': f"{(ctx.get('all_summary') or {}).get('completion', 0)}%"},
        {'k': '健康分', 'v': ctx.get('health_score', 0)},
    ]

    if active_tab == 'banks':
        hero_title = '数据中心 · 题库'
        hero_subtitle = '题库全景：规模×覆盖×质量，把投入方向选得更聪明。'
        hero_kpis = [
            {'k': '个人题库', 'v': (ctx.get('bank_summary') or {}).get('bank_total', 0)},
            {'k': '公共规模', 'v': ctx.get('total_questions', 0)},
            {'k': '近窗已做', 'v': ctx.get('window_answered', 0)},
            {'k': '正确率', 'v': f"{(ctx.get('all_summary') or {}).get('accuracy', 0)}%"},
        ]
    elif active_tab == 'mistakes':
        hero_title = '数据中心 · 错题'
        hero_subtitle = '错题是最有杠杆的提升入口：高频先闭环，薄弱再专项。'
        try:
            recent_new = sum(int(x.get('all') or 0) for x in (ctx.get('mistakes_daily') or []))
        except Exception as e:
            current_app.logger.warning(f'计算近期错题新增数失败: {e}')
            recent_new = 0
        hero_kpis = [
            {'k': '错题数', 'v': (ctx.get('all_summary') or {}).get('mistakes', 0)},
            {'k': '错题次数', 'v': (ctx.get('all_summary') or {}).get('mistakes_times', 0)},
            {'k': f'近{window_days}天新增', 'v': recent_new},
            {'k': '健康分', 'v': ctx.get('health_score', 0)},
        ]
    elif active_tab == 'favorites':
        hero_title = '数据中心 · 收藏'
        hero_subtitle = '收藏是高价值题库：复习、背题、冲刺都能复用。'
        try:
            recent_new = sum(int(x.get('all') or 0) for x in (ctx.get('favorites_daily') or []))
        except Exception as e:
            current_app.logger.warning(f'计算近期收藏新增数失败: {e}')
            recent_new = 0
        answered_all = int((ctx.get('all_summary') or {}).get('answered') or 0)
        fav_all = int((ctx.get('all_summary') or {}).get('favorites') or 0)
        fav_rate = round(fav_all * 100.0 / answered_all, 1) if answered_all > 0 else 0.0
        hero_kpis = [
            {'k': '收藏数', 'v': fav_all},
            {'k': f'近{window_days}天新增', 'v': recent_new},
            {'k': '收藏密度', 'v': f'{fav_rate}%'},
            {'k': '健康分', 'v': ctx.get('health_score', 0)},
        ]
    elif active_tab == 'tags':
        hero_title = '数据中心 · 标签'
        hero_subtitle = '标签让题目资产结构化：复盘与专项训练更容易"复用"。'
        kpi = ctx.get('tags_kpis') or {}
        hero_kpis = [
            {'k': '标签总数', 'v': int(kpi.get('all_tag_count') or 0)},
            {'k': '已打标签题', 'v': int(kpi.get('all_tagged_questions') or 0)},
            {'k': '覆盖率', 'v': f"{float(kpi.get('tagged_answered_coverage') or 0)}%"},
            {'k': '健康分', 'v': ctx.get('health_score', 0)},
        ]

    # data_center.js 兼容层：保持旧版 payload 字段名可用（避免图表数据为空）
    data_payload = dict(ctx)
    data_payload.update({
        'active_tab': active_tab,
        'subjects': ctx.get('subject_rows') or [],
        'types': ctx.get('type_rows') or [],
        'difficulty': ctx.get('difficulty_rows') or [],
        'weakness': ctx.get('weakness_rows') or [],
        'banks': ctx.get('bank_rows') or [],
        'bank_categories': ctx.get('bank_category_rows') or [],
        'public_summary': {
            'total_questions': ctx.get('total_questions', 0),
            'answered': ctx.get('answered_count', 0),
            'correct': ctx.get('correct_count', 0),
            'accuracy': ctx.get('accuracy', 0),
            'completion': ctx.get('completion', 0),
            'favorites': ctx.get('favorites_count', 0),
            'mistakes': ctx.get('mistakes_count', 0),
            'mistakes_times': ctx.get('mistakes_times', 0),
            'streak_days': ctx.get('streak_days', 0),
            'last_activity': ctx.get('last_activity'),
            'answered_7d': ctx.get('answered_7d', 0),
            'correct_7d': ctx.get('correct_7d', 0),
            'answered_30d': ctx.get('answered_30d', 0),
            'correct_30d': ctx.get('correct_30d', 0),
            'window_answered': ctx.get('window_answered', 0),
            'window_correct': ctx.get('window_correct', 0),
            'window_accuracy': ctx.get('window_accuracy', 0),
        },
    })

    return render_template(
        template_map.get(active_tab, 'main/data/data_v2_global.html'),
        **ctx,
        active_tab=active_tab,
        hero_title=hero_title,
        hero_subtitle=hero_subtitle,
        hero_kpis=hero_kpis,
        data_payload=data_payload,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=int(uid),
    )


@main_pages_bp.route('/api/data/center', methods=['GET'])
@auth_required  # 支持 session / JWT
@limiter.limit("20 per minute;200 per hour")
def api_data_center():
    """数据中心聚合数据（供小程序与 Web 子页复用）。"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    window_days = request.args.get('days', 30, type=int)
    if window_days not in (7, 30, 90):
        window_days = 30

    ctx = _compute_data_center_context(int(uid), int(window_days))
    return jsonify({'status': 'success', 'data': ctx})


@main_pages_bp.route('/api/data/tags', methods=['GET'])
@auth_required  # 支持 session / JWT
@limiter.limit("20 per minute;200 per hour")
def api_data_tags():
    """数据中心：标签聚合统计（供小程序与 Web 复用）。"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    window_days = request.args.get('days', 30, type=int)
    if window_days not in (7, 30, 90):
        window_days = 30

    conn = db.session.connection()
    from app.modules.main.services.data_tags_service import compute_data_tags_context

    ctx = compute_data_tags_context(conn, int(uid), int(window_days))
    return jsonify({'status': 'success', 'data': ctx})


@main_pages_bp.route('/api/data/ai-advice', methods=['POST'])
@auth_required  # 支持 session / JWT
@limiter.limit("30 per hour")
def api_data_ai_advice():
    """数据中心 AI 助手：基于用户数据生成建议。"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    payload = request.get_json(silent=True) or {}
    prompt = (payload.get('prompt') or payload.get('question') or '').strip()
    days = payload.get('days', 30)
    try:
        days = int(days)
    except Exception as e:
        current_app.logger.warning(f'解析 days 参数失败: {e}')
        days = 30
    if days not in (7, 30, 90):
        days = 30

    if not prompt:
        prompt = '请基于我的学习数据，给出今天最重要的 5 条建议，并按优先级排序。'

    # ===== 复用 _compute_data_center_context 缓存 =====
    ctx = _compute_data_center_context(int(uid), days)

    all_summary = ctx.get('all_summary') or {}
    public_summary = ctx.get('public_summary') or {}
    bank_summary = ctx.get('bank_summary') or {}

    summary = {
        'window_days': int(days),
        'all': {
            'total_questions': int(all_summary.get('total_questions') or 0),
            'answered': int(all_summary.get('answered') or 0),
            'correct': int(all_summary.get('correct') or 0),
            'accuracy': float(all_summary.get('accuracy') or 0),
            'completion': float(all_summary.get('completion') or 0),
            'favorites': int(all_summary.get('favorites') or 0),
            'mistakes': int(all_summary.get('mistakes') or 0),
            'mistakes_times': int(all_summary.get('mistakes_times') or 0),
            'streak_days': int(all_summary.get('streak_days') or 0),
            'last_activity': all_summary.get('last_activity'),
        },
        'public': {
            'total_questions': int(public_summary.get('total_questions') or ctx.get('total_questions') or 0),
            'answered': int(public_summary.get('answered') or ctx.get('answered_count') or 0),
            'correct': int(public_summary.get('correct') or ctx.get('correct_count') or 0),
            'accuracy': float(public_summary.get('accuracy') or ctx.get('accuracy') or 0),
            'completion': float(public_summary.get('completion') or ctx.get('completion') or 0),
            'favorites': int(public_summary.get('favorites') or ctx.get('favorites_count') or 0),
            'mistakes': int(public_summary.get('mistakes') or ctx.get('mistakes_count') or 0),
            'mistakes_times': int(public_summary.get('mistakes_times') or ctx.get('mistakes_times') or 0),
            'streak_days': int(public_summary.get('streak_days') or ctx.get('streak_days') or 0),
            'last_activity': public_summary.get('last_activity') or ctx.get('last_activity'),
            'weak_subjects': public_summary.get('weak_subjects') or ctx.get('weakness_rows') or [],
        },
        'banks': {
            'bank_total': int(bank_summary.get('bank_total') or 0),
            'total_questions': int(bank_summary.get('total_questions') or 0),
            'answered': int(bank_summary.get('answered') or 0),
            'correct': int(bank_summary.get('correct') or 0),
            'accuracy': float(bank_summary.get('accuracy') or 0),
            'completion': float(bank_summary.get('completion') or 0),
            'favorites': int(bank_summary.get('favorites') or 0),
            'mistakes': int(bank_summary.get('mistakes') or 0),
            'mistakes_times': int(bank_summary.get('mistakes_times') or 0),
            'streak_days': int(bank_summary.get('streak_days') or 0),
            'last_activity': bank_summary.get('last_activity'),
            'weak_banks': bank_summary.get('weak_banks') or [],
        },
    }
    weak_subjects = summary['public'].get('weak_subjects') or []
    weak_banks = summary['banks'].get('weak_banks') or []


    def _build_placeholder_reply() -> str:
        lines = []
        lines.append('（未配置 AI 服务，以下为模板建议；可在后台管理系统 → 系统设置 → AI 配置中启用）')
        lines.append('')
        lines.append('你的概览：')
        lines.append(f"- 全局：已做 {summary['all']['answered']} / {summary['all']['total_questions']}（完成度 {summary['all']['completion']}%），正确率 {summary['all']['accuracy']}%")
        lines.append(f"- 公共题库：已做 {summary['public']['answered']}（正确率 {summary['public']['accuracy']}%）")
        lines.append(f"- 个人题库：已做 {summary['banks']['answered']}（正确率 {summary['banks']['accuracy']}%），题库数 {summary['banks']['bank_total']}")
        if weak_subjects:
            s = '、'.join([f"{x['name']}({x['accuracy']}%)" for x in weak_subjects])
            lines.append(f"- 公共薄弱科目：{s}")
        if weak_banks:
            s = '、'.join([f"{x['name']}({x['accuracy']}%)" for x in weak_banks])
            lines.append(f"- 个人薄弱题库：{s}")
        lines.append('')
        lines.append('建议（按优先级）：')
        if summary['all']['answered'] < 10:
            lines.append('1) 先连续做 20 题建立手感（不要断档）。')
        if summary['all']['completion'] < 35:
            lines.append('2) 优先补"未做题"，把覆盖率先拉到 35%+。')
        if summary['all']['accuracy'] < 65 and summary['all']['answered'] >= 10:
            lines.append('3) 先刷错题并归因（概念/审题/计算/方法），再回到全题库。')
        if weak_subjects:
            lines.append(f"4) 公共题库优先练：{weak_subjects[0]['name']}（先错题，再重练）。")
        if weak_banks:
            lines.append(f"5) 个人题库优先练：{weak_banks[0]['name']}（按题型拆分练）。")
        if summary['all']['streak_days'] <= 1:
            lines.append('补充：设一个"最小计划"（每天 10 题或 8 分钟），先把连续天数做起来。')
        return '\n'.join(lines).strip()

    from app.modules.admin.services.system_config_service import SystemConfigService

    dashscope_cfg = SystemConfigService.get_dashscope_config()
    api_key = (dashscope_cfg.get('api_key') or '').strip()
    base_url = (dashscope_cfg.get('base_url') or '').strip()
    model = (dashscope_cfg.get('model') or '').strip() or 'qwen-plus'
    timeout = int(dashscope_cfg.get('timeout') or 25)

    if not api_key:
        return jsonify({'status': 'success', 'data': {'reply': _build_placeholder_reply(), 'provider': 'placeholder', 'summary': summary}})

    try:
        from app.modules.quiz.services.dashscope_client import DashScopeClient

        system_prompt = (
            "你是一名专业的学习数据分析与训练规划教练。"
            "你将基于用户的学习数据（答题、正确率、覆盖率、错题、收藏、连续学习天数、薄弱题库/科目）给出建议。"
            "请用中文输出，要求："
            "1) 先给 1 句总结；"
            "2) 给 5 条以内建议，按优先级排序；"
            "3) 每条建议都要可执行（包含动作与频率/数量/时间）；"
            "4) 同时给出公共题库与个人题库的侧重点；"
            "5) 不要输出任何与用户无关的免责声明。"
        )

        user_prompt = (
            "这是我的数据（JSON）：\n"
            + json.dumps(summary, ensure_ascii=False)
            + "\n\n我的问题：\n"
            + prompt
            + "\n\n请直接给建议。"
        )

        client = DashScopeClient(api_key=api_key, base_url=base_url)
        reply = client.chat_completions(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            temperature=0.3,
            top_p=0.8,
            max_tokens=900,
            timeout=timeout,
        )
        return jsonify({'status': 'success', 'data': {'reply': reply, 'provider': 'dashscope', 'model': model, 'summary': summary}})
    except Exception as e:
        current_app.logger.error('AI数据建议失败: %s', str(e), exc_info=True)
        return jsonify({'status': 'success', 'data': {'reply': _build_placeholder_reply(), 'provider': 'placeholder', 'note': 'AI调用失败，已返回模板建议', 'summary': summary}})
