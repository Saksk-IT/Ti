# -*- coding: utf-8 -*-
"""管理后台页面路由"""
from flask import Blueprint, render_template, session, request
from sqlalchemy import text

from app.core.extensions import db

admin_pages_bp = Blueprint('admin_pages', __name__)


@admin_pages_bp.route('/')
@admin_pages_bp.route('/dashboard')
def admin_dashboard():
    """管理后台首页"""
    from app.core.utils.portable_question_format import portable_question_to_internal

    q_count = db.session.execute(text('SELECT COUNT(1) FROM questions')).scalar()
    s_count = db.session.execute(text('SELECT COUNT(1) FROM user_question_banks WHERE status = 1')).scalar()
    u_count = db.session.execute(text('SELECT COUNT(1) FROM users')).scalar()
    admin_count = db.session.execute(text('SELECT COUNT(1) FROM users WHERE is_admin = true')).scalar()

    recent_rows = db.session.execute(
        text('SELECT id, type, content FROM questions ORDER BY id DESC LIMIT 5')
    ).fetchall()
    recent_q = []
    for r in recent_rows or []:
        d = dict(r._mapping)
        try:
            portable = {
                'id': d.get('id'),
                'type': d.get('type') or '',
                'content': d.get('content') or '',
                'options': [],
                'answer': [],
                'analysis': '',
                'tags': [],
                'difficulty': 1,
            }
            internal, _errors = portable_question_to_internal(portable, scope='question_center')
            d['q_type'] = internal.get('q_type') or ''
            d['content'] = internal.get('content') or d.get('content') or ''
        except Exception:
            d['q_type'] = ''
        recent_q.append(d)

    subject_dist = db.session.execute(text('''
        SELECT s.name, COUNT(q.id) as count
        FROM subjects s
        LEFT JOIN questions q ON s.id = q.subject_id
        GROUP BY s.id
        ORDER BY count DESC
    ''')).fetchall()

    return render_template('admin/dashboard/index.html',
        stats={'q_count': q_count, 's_count': s_count, 'u_count': u_count, 'admin_count': admin_count},
        recent_questions=recent_q,
        subject_distribution=[dict(row._mapping) for row in subject_dist]
    )


@admin_pages_bp.route('/users')
def admin_users_page():
    """用户管理页面"""
    users = db.session.execute(text('SELECT id, username, created_at, is_admin FROM users ORDER BY id')).fetchall()
    return render_template('admin/users/index.html', users=[dict(row._mapping) for row in users])


@admin_pages_bp.route('/subjects')
def admin_subjects_page():
    """题库管理页面"""
    return render_template('admin/subjects/index.html')


@admin_pages_bp.route('/legacy-subjects')
def admin_legacy_subjects_page():
    """旧公共科目管理入口。"""
    return render_template('admin/subjects/legacy.html')


@admin_pages_bp.route('/subjects/<int:subject_id>/questions')
def admin_questions_page(subject_id):
    """题集管理页面"""
    # 获取科目信息（使用subjects表，题库中心模式）
    subject = db.session.execute(text('SELECT id, name FROM subjects WHERE id=:sid'), {'sid': subject_id}).fetchone()

    if not subject:
        return "科目不存在", 404

    return render_template('admin/subjects/questions.html', subject_id=subject_id, subject=dict(subject._mapping))


@admin_pages_bp.route('/subjects/<int:subject_id>/questions/duplicate-check')
def admin_duplicate_check_page(subject_id):
    """题集查重结果页面"""
    # 获取科目信息
    subject = db.session.execute(text('SELECT id, name FROM subjects WHERE id=:sid'), {'sid': subject_id}).fetchone()

    if not subject:
        return "科目不存在", 404

    return render_template('admin/subjects/duplicate_check.html', subject_id=subject_id, subject=dict(subject._mapping))


@admin_pages_bp.route('/users/<int:user_id>')
def admin_user_detail_page(user_id):
    """用户详情页面"""
    u = db.session.execute(
        text('SELECT id, username, is_admin, is_locked, created_at, avatar, contact, college, email, email_verified, email_verified_at FROM users WHERE id=:uid'),
        {'uid': user_id}
    ).fetchone()

    if not u:
        return "用户不存在", 404

    # 收藏/错题
    fav = db.session.execute(text('SELECT COUNT(1) FROM favorites WHERE user_id=:uid'), {'uid': user_id}).scalar()
    mis = db.session.execute(text('SELECT COUNT(1) FROM mistakes WHERE user_id=:uid'), {'uid': user_id}).scalar()

    # 答题统计
    r = db.session.execute(
        text('SELECT COUNT(1) AS total, SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) AS correct FROM user_answers WHERE user_id=:uid'),
        {'uid': user_id}
    ).fetchone()
    total = r._mapping['total'] or 0
    correct = r._mapping['correct'] or 0
    acc = round(correct * 100.0 / total, 1) if total else 0.0

    # 考试统计
    ex_ongoing = db.session.execute(text("SELECT COUNT(1) FROM exams WHERE user_id=:uid AND status='ongoing'"), {'uid': user_id}).scalar()
    ex_submitted = db.session.execute(text("SELECT COUNT(1) FROM exams WHERE user_id=:uid AND status='submitted'"), {'uid': user_id}).scalar()

    recent = db.session.execute(
        text("SELECT id, subject, total_score, started_at, submitted_at FROM exams WHERE user_id=:uid AND status='submitted' ORDER BY submitted_at DESC LIMIT 5"),
        {'uid': user_id}
    ).fetchall()

    return render_template('admin/users/detail.html',
        user=dict(u._mapping),
        stats={
            'favorites': fav,
            'mistakes': mis,
            'total_answers': total,
            'accuracy': acc,
            'exams_ongoing': ex_ongoing,
            'exams_submitted': ex_submitted
        },
        recent_exams=[dict(x._mapping) for x in recent]
    )


@admin_pages_bp.route('/notifications')
def admin_notifications_page():
    """通知管理页面"""
    return render_template('admin/notifications/index.html')


@admin_pages_bp.route('/chat')
def admin_chat_page():
    """聊天管理页面"""
    return render_template('admin/chat/index.html')


@admin_pages_bp.route('/subject_permissions')
def admin_subject_permissions_page():
    """题库管理页面（批量操作）"""
    return render_template('admin/permissions/subject_permissions.html')


@admin_pages_bp.route('/settings')
def admin_settings_page():
    """系统设置页面"""
    return render_template('admin/settings/index.html')


@admin_pages_bp.route('/settings/mail')
def admin_mail_settings_page():
    """邮件配置页面"""
    from app.modules.admin.services.system_config_service import SystemConfigService

    cfg = SystemConfigService.get_mail_config_masked()
    mail_config = {
        'mail_server': cfg.get('server', ''),
        'mail_port': cfg.get('port', 587),
        'mail_use_tls': 'true' if cfg.get('use_tls', True) else 'false',
        'mail_use_ssl': 'true' if cfg.get('use_ssl', False) else 'false',
        'mail_username': cfg.get('username', ''),
        'mail_password': cfg.get('password', ''),
        'mail_default_sender': cfg.get('sender', ''),
        'mail_default_sender_name': cfg.get('sender_name', '系统通知'),
        'mail_enabled': 'true' if cfg.get('enabled', True) else 'false',
        'mail_console_output': 'true' if cfg.get('console_output', False) else 'false',
    }
    return render_template('admin/settings/mail.html', mail_config=mail_config)


@admin_pages_bp.route('/settings/limits')
def admin_limit_settings_page():
    """限制设置页面"""
    return render_template('admin/settings/limits.html')


@admin_pages_bp.route('/settings/ai')
def admin_ai_settings_page():
    """AI 配置页面"""
    from app.modules.admin.services.system_config_service import SystemConfigService
    cfg = SystemConfigService.get_ai_config_masked()
    return render_template('admin/settings/ai.html', ai_config=cfg)


@admin_pages_bp.route('/settings/payment')
def admin_payment_settings_page():
    """支付配置页面"""
    from app.modules.payment.services.epay_service import EpayService

    cfg = EpayService.get_config(masked=True)
    return render_template('admin/settings/payment.html', epay_config=cfg)


@admin_pages_bp.route('/settings/sms')
def admin_sms_settings_page():
    """短信配置页面"""
    from app.modules.admin.services.system_config_service import SystemConfigService

    cfg = SystemConfigService.get_sms_config_masked()
    return render_template('admin/settings/sms.html', sms_config=cfg)


@admin_pages_bp.route('/settings/auth-login')
def admin_auth_login_settings_page():
    """登录方式配置页面"""
    from app.modules.admin.services.system_config_service import SystemConfigService

    cfg = SystemConfigService.get_auth_login_methods_form_config()
    return render_template('admin/settings/auth_login.html', auth_login_config=cfg)


@admin_pages_bp.route('/settings/wechat-miniprogram')
def admin_wechat_miniprogram_settings_page():
    """微信小程序配置页面"""
    from app.modules.admin.services.system_config_service import SystemConfigService

    cfg = SystemConfigService.get_wechat_miniprogram_form_config()
    return render_template('admin/settings/wechat_miniprogram.html', wechat_config=cfg)


@admin_pages_bp.route('/settings/edu-schedule')
def admin_edu_schedule_settings_page():
    """教务课表配置页面"""
    from app.modules.admin.services.system_config_service import SystemConfigService

    cfg = SystemConfigService.get_edu_schedule_config_masked()
    return render_template('admin/settings/edu_schedule.html', schedule_config=cfg)


@admin_pages_bp.route('/permissions')
def admin_permissions_page():
    """权限管理页面"""
    return render_template('admin/permissions/index.html')


@admin_pages_bp.route('/forum')
def admin_forum_page():
    """论坛管理页面"""
    return render_template('admin/forum/index.html')
