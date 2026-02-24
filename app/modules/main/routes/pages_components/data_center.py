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
    subject_ids, base_ctx = compute_data_center_context_base(uid, window_days)
    conn = db.session.connection()
    return compute_data_center_context_extra(conn, uid, window_days, subject_ids, base_ctx)


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
        except Exception:
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
        except Exception:
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
        hero_subtitle = '标签让题目资产结构化：复盘与专项训练更容易“复用”。'
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
@limiter.exempt
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
@limiter.exempt
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
    except Exception:
        days = 30
    if days not in (7, 30, 90):
        days = 30

    if not prompt:
        prompt = '请基于我的学习数据，给出今天最重要的 5 条建议，并按优先级排序。'

    def _pct(a: int, b: int) -> float:
        try:
            a = int(a or 0)
            b = int(b or 0)
            return round(a * 100.0 / b, 1) if b > 0 else 0.0
        except Exception:
            return 0.0

    def _safe_int(x) -> int:
        try:
            return int(x or 0)
        except Exception:
            return 0

    # ===== 公共题库汇总（按科目权限过滤）=====
    subjects_meta = _get_accessible_subject_rows(uid=uid)
    subject_ids = [int(s['id']) for s in (subjects_meta or []) if s and s.get('id') is not None]
    subject_name_map = {int(s['id']): (s.get('name') or '') for s in (subjects_meta or []) if s and s.get('id') is not None}

    total_questions_public = 0
    answered_public = 0
    correct_public = 0
    last_public = None
    favorites_public = 0
    mistakes_public = 0
    mistakes_times_public = 0
    streak_public = 0
    public_streak_dates = []

    try:
        base_sql = """
            SELECT COUNT(*)
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE (s.is_locked=false OR s.is_locked IS NULL)
        """
        params: dict = {}
        if subject_ids:
            in_clause, in_params = _build_named_in('q.subject_id', subject_ids, 'tq')
            base_sql += f" AND {in_clause}"
            params.update(in_params)
        total_questions_public = _safe_int(db.session.execute(text(base_sql), params).fetchone()[0])
    except Exception:
        total_questions_public = 0

    ua_params_base: dict = {'ua_uid': int(uid)}
    ua_from = """
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.id
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE ua.user_id = :ua_uid
          AND (s.is_locked=false OR s.is_locked IS NULL)
    """
    if subject_ids:
        in_clause, in_params = _build_named_in('q.subject_id', subject_ids, 'sid')
        ua_from += f" AND {in_clause}"
        ua_params_base.update(in_params)

    try:
        row = db.session.execute(
            text(f"""
            SELECT
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) AS correct,
              MAX(ua.created_at) AS last_activity
            {ua_from}
            """),
            ua_params_base,
        ).fetchone()
        answered_public = _safe_int(row._mapping['answered'] if row else 0)
        correct_public = _safe_int(row._mapping['correct'] if row else 0)
        last_public = (row._mapping['last_activity'] if row else None) or None
    except Exception:
        answered_public = 0
        correct_public = 0
        last_public = None

    try:
        fav_sql = """
            SELECT COUNT(*)
            FROM favorites f
            JOIN questions q ON f.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE f.user_id = :fav_uid AND (s.is_locked=false OR s.is_locked IS NULL)
        """
        fav_params: dict = {'fav_uid': int(uid)}
        if subject_ids:
            in_clause, in_params = _build_named_in('q.subject_id', subject_ids, 'fav')
            fav_sql += f" AND {in_clause}"
            fav_params.update(in_params)
        favorites_public = _safe_int(db.session.execute(text(fav_sql), fav_params).fetchone()[0])
    except Exception:
        favorites_public = 0

    try:
        mis_sql = """
            SELECT
              COUNT(*) AS cnt,
              SUM(CASE WHEN m.wrong_count IS NULL THEN 1 ELSE m.wrong_count END) AS times
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = :mis_uid AND (s.is_locked=false OR s.is_locked IS NULL)
        """
        mis_params: dict = {'mis_uid': int(uid)}
        if subject_ids:
            in_clause, in_params = _build_named_in('q.subject_id', subject_ids, 'mis')
            mis_sql += f" AND {in_clause}"
            mis_params.update(in_params)
        row = db.session.execute(text(mis_sql), mis_params).fetchone()
        mistakes_public = _safe_int(row._mapping['cnt'] if row else 0)
        mistakes_times_public = _safe_int(row._mapping['times'] if row else 0)
    except Exception:
        mistakes_public = 0
        mistakes_times_public = 0

    try:
        rows = db.session.execute(
            text(f"SELECT DISTINCT DATE(ua.created_at) AS day {ua_from} ORDER BY day DESC LIMIT 120"),
            ua_params_base,
        ).fetchall()
        dates = []
        for r in rows or []:
            d = r._mapping['day']
            if d:
                try:
                    if isinstance(d, str):
                        dates.append(datetime.strptime(d, '%Y-%m-%d').date())
                    else:
                        dates.append(d)
                except Exception:
                    continue
        public_streak_dates = dates
        today = today_bj()
        if dates and dates[0] >= (today - timedelta(days=1)):
            streak_public = 1
            for i in range(1, len(dates)):
                if dates[i - 1] - dates[i] == timedelta(days=1):
                    streak_public += 1
                else:
                    break
    except Exception:
        streak_public = 0
        public_streak_dates = []

    # 公共薄弱科目（按正确率从低到高，至少做过5题）
    weak_subjects = []
    try:
        rows = db.session.execute(
            text(f"""
            SELECT q.subject_id AS subject_id,
                   COUNT(*) AS answered,
                   SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) AS correct
            {ua_from}
            GROUP BY q.subject_id
            """),
            ua_params_base,
        ).fetchall()
        for r in rows or []:
            sid = r._mapping['subject_id']
            if sid is None:
                continue
            answered = _safe_int(r._mapping['answered'])
            correct = _safe_int(r._mapping['correct'])
            if answered < 5:
                continue
            acc = _pct(correct, answered)
            weak_subjects.append({
                'name': subject_name_map.get(int(sid)) or f'科目{sid}',
                'answered': answered,
                'accuracy': acc,
            })
        weak_subjects.sort(key=lambda x: (float(x.get('accuracy') or 0.0), -int(x.get('answered') or 0)))
        weak_subjects = weak_subjects[:3]
    except Exception:
        weak_subjects = []

    # ===== 个人题库（我创建的）=====
    bank_total = 0
    bank_total_questions = 0
    bank_answered = 0
    bank_correct = 0
    bank_favorites = 0
    bank_mistakes = 0
    bank_mistakes_times = 0
    bank_last = None
    bank_streak = 0
    bank_streak_dates = []
    weak_banks = []

    try:
        banks = db.session.execute(
            text("""
            SELECT id, name
            FROM user_question_banks
            WHERE user_id = :bk_uid AND status = 1
            ORDER BY updated_at DESC, id DESC
            """),
            {'bk_uid': int(uid)},
        ).fetchall()
        banks = [dict(b._mapping) for b in (banks or []) if b and b._mapping.get('id') is not None]
        bank_total = len(banks)
        bank_ids = [int(b['id']) for b in banks]
        bank_name_map = {int(b['id']): (b.get('name') or '') for b in banks}

        if bank_ids:
            bk_in_clause, bk_in_params = _build_named_in('bank_id', bank_ids, 'bk')

            try:
                p = {'ba_uid': int(uid)}
                p.update(bk_in_params)
                row = db.session.execute(
                    text(f"SELECT COUNT(*) AS answered, SUM(CASE WHEN is_correct=true THEN 1 ELSE 0 END) AS correct, MAX(created_at) AS last_activity FROM user_bank_answers WHERE user_id=:ba_uid AND {bk_in_clause}"),
                    p,
                ).fetchone()
                bank_answered = _safe_int(row._mapping['answered'] if row else 0)
                bank_correct = _safe_int(row._mapping['correct'] if row else 0)
                bank_last = (row._mapping['last_activity'] if row else None) or None
            except Exception:
                bank_answered = 0
                bank_correct = 0
                bank_last = None

            try:
                p = {'bf_uid': int(uid)}
                p.update(bk_in_params)
                row = db.session.execute(
                    text(f"SELECT COUNT(*) AS cnt FROM user_bank_favorites WHERE user_id=:bf_uid AND {bk_in_clause}"),
                    p,
                ).fetchone()
                bank_favorites = _safe_int(row._mapping['cnt'] if row else 0)
            except Exception:
                bank_favorites = 0

            try:
                p = {'bm_uid': int(uid)}
                p.update(bk_in_params)
                row = db.session.execute(
                    text(f"SELECT COUNT(*) AS cnt, SUM(COALESCE(wrong_count,1)) AS times FROM user_bank_mistakes WHERE user_id=:bm_uid AND {bk_in_clause}"),
                    p,
                ).fetchone()
                bank_mistakes = _safe_int(row._mapping['cnt'] if row else 0)
                bank_mistakes_times = _safe_int(row._mapping['times'] if row else 0)
            except Exception:
                bank_mistakes = 0
                bank_mistakes_times = 0

            try:
                row = db.session.execute(
                    text(f"SELECT COUNT(*) AS cnt FROM user_bank_questions WHERE {bk_in_clause}"),
                    bk_in_params,
                ).fetchone()
                bank_total_questions = _safe_int(row._mapping['cnt'] if row else 0)
            except Exception:
                bank_total_questions = 0

            try:
                p = {'bs_uid': int(uid)}
                p.update(bk_in_params)
                rows = db.session.execute(
                    text(f"""
                    SELECT DISTINCT DATE(created_at) AS day
                    FROM user_bank_answers
                    WHERE user_id = :bs_uid AND {bk_in_clause}
                    ORDER BY day DESC
                    LIMIT 120
                    """),
                    p,
                ).fetchall()
                dates = []
                for r in rows or []:
                    d = r._mapping['day']
                    if d:
                        try:
                            if isinstance(d, str):
                                dates.append(datetime.strptime(d, '%Y-%m-%d').date())
                            else:
                                dates.append(d)
                        except Exception:
                            continue
                bank_streak_dates = dates
                today = today_bj()
                if dates and dates[0] >= (today - timedelta(days=1)):
                    bank_streak = 1
                    for i in range(1, len(dates)):
                        if dates[i - 1] - dates[i] == timedelta(days=1):
                            bank_streak += 1
                        else:
                            break
            except Exception:
                bank_streak = 0
                bank_streak_dates = []

            try:
                p = {'wb_uid': int(uid)}
                p.update(bk_in_params)
                rows = db.session.execute(
                    text(f"""
                    SELECT bank_id,
                           COUNT(*) AS answered,
                           SUM(CASE WHEN is_correct=true THEN 1 ELSE 0 END) AS correct
                    FROM user_bank_answers
                    WHERE user_id = :wb_uid AND {bk_in_clause}
                    GROUP BY bank_id
                    """),
                    p,
                ).fetchall()
                for r in rows or []:
                    bid = r._mapping['bank_id']
                    if bid is None:
                        continue
                    a = _safe_int(r._mapping['answered'])
                    c = _safe_int(r._mapping['correct'])
                    if a < 5:
                        continue
                    weak_banks.append({
                        'name': (bank_name_map.get(int(bid)) or f'题库{bid}').strip(),
                        'answered': a,
                        'accuracy': _pct(c, a),
                    })
                weak_banks.sort(key=lambda x: (float(x.get('accuracy') or 0.0), -int(x.get('answered') or 0)))
                weak_banks = weak_banks[:3]
            except Exception:
                weak_banks = []
    except Exception:
        bank_total = 0

    # ===== 全局（公共 + 个人）=====
    total_questions_all = _safe_int(total_questions_public) + _safe_int(bank_total_questions)
    answered_all = _safe_int(answered_public) + _safe_int(bank_answered)
    correct_all = _safe_int(correct_public) + _safe_int(bank_correct)
    favorites_all = _safe_int(favorites_public) + _safe_int(bank_favorites)
    mistakes_all = _safe_int(mistakes_public) + _safe_int(bank_mistakes)
    mistakes_times_all = _safe_int(mistakes_times_public) + _safe_int(bank_mistakes_times)
    accuracy_all = _pct(correct_all, answered_all)
    completion_all = _pct(answered_all, total_questions_all)

    last_all = None
    try:
        candidates = [x for x in [last_public, bank_last] if x]
        last_all = max(candidates) if candidates else None
    except Exception:
        last_all = None

    streak_all = 0
    try:
        merged_dates = sorted(set(public_streak_dates or []) | set(bank_streak_dates or []), reverse=True)
        today = today_bj()
        if merged_dates and merged_dates[0] >= (today - timedelta(days=1)):
            streak_all = 1
            for i in range(1, len(merged_dates)):
                if merged_dates[i - 1] - merged_dates[i] == timedelta(days=1):
                    streak_all += 1
                else:
                    break
    except Exception:
        streak_all = max(int(streak_public or 0), int(bank_streak or 0))

    summary = {
        'window_days': int(days),
        'all': {
            'total_questions': total_questions_all,
            'answered': answered_all,
            'correct': correct_all,
            'accuracy': accuracy_all,
            'completion': completion_all,
            'favorites': favorites_all,
            'mistakes': mistakes_all,
            'mistakes_times': mistakes_times_all,
            'streak_days': int(streak_all),
            'last_activity': last_all,
        },
        'public': {
            'total_questions': int(total_questions_public),
            'answered': int(answered_public),
            'correct': int(correct_public),
            'accuracy': _pct(correct_public, answered_public),
            'completion': _pct(answered_public, total_questions_public),
            'favorites': int(favorites_public),
            'mistakes': int(mistakes_public),
            'mistakes_times': int(mistakes_times_public),
            'streak_days': int(streak_public),
            'last_activity': last_public,
            'weak_subjects': weak_subjects,
        },
        'banks': {
            'bank_total': int(bank_total),
            'total_questions': int(bank_total_questions),
            'answered': int(bank_answered),
            'correct': int(bank_correct),
            'accuracy': _pct(bank_correct, bank_answered),
            'completion': _pct(bank_answered, bank_total_questions),
            'favorites': int(bank_favorites),
            'mistakes': int(bank_mistakes),
            'mistakes_times': int(bank_mistakes_times),
            'streak_days': int(bank_streak),
            'last_activity': bank_last,
            'weak_banks': weak_banks,
        },
    }

    def _build_placeholder_reply() -> str:
        lines = []
        lines.append('（未配置 DASHSCOPE_API_KEY，以下为模板建议；配置后将自动启用 AI 分析）')
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
            lines.append('2) 优先补“未做题”，把覆盖率先拉到 35%+。')
        if summary['all']['accuracy'] < 65 and summary['all']['answered'] >= 10:
            lines.append('3) 先刷错题并归因（概念/审题/计算/方法），再回到全题库。')
        if weak_subjects:
            lines.append(f"4) 公共题库优先练：{weak_subjects[0]['name']}（先错题，再重练）。")
        if weak_banks:
            lines.append(f"5) 个人题库优先练：{weak_banks[0]['name']}（按题型拆分练）。")
        if summary['all']['streak_days'] <= 1:
            lines.append('补充：设一个“最小计划”（每天 10 题或 8 分钟），先把连续天数做起来。')
        return '\n'.join(lines).strip()

    api_key = (current_app.config.get('DASHSCOPE_API_KEY') or '').strip()
    base_url = (current_app.config.get('DASHSCOPE_BASE_URL') or '').strip()
    model = (current_app.config.get('DASHSCOPE_MODEL') or '').strip() or 'qwen-plus'
    timeout = int(current_app.config.get('DASHSCOPE_TIMEOUT') or 25)

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

