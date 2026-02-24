# -*- coding: utf-8 -*-
"""
应用工厂模块
"""
import json
import os
import logging
import threading
import time
from logging.handlers import RotatingFileHandler
from flask import Flask

# 加载.env文件（如果存在）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv未安装时忽略

from .core.config import config
from .core.extensions import init_extensions
from markupsafe import Markup, escape as _escape


_LAST_ACTIVE_LOCK = threading.Lock()
_LAST_ACTIVE_TS = {}


def _should_update_last_active(user_id: int, interval_seconds: int) -> bool:
    if interval_seconds <= 0:
        return True
    now = time.monotonic()
    uid = int(user_id)
    with _LAST_ACTIVE_LOCK:
        last = _LAST_ACTIVE_TS.get(uid)
        if last is None or (now - float(last)) >= float(interval_seconds):
            _LAST_ACTIVE_TS[uid] = now
            return True
    return False


def create_app(config_name=None):
    """
    应用工厂函数
    
    Args:
        config_name: 配置名称 ('development', 'production', 'testing')
        
    Returns:
        Flask: Flask应用实例
    """
    # 如果没有指定配置，从环境变量获取
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # 创建Flask应用
    # 显式指定 static_folder，避免在某些运行方式/工作目录下出现 /static 404
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'), static_url_path='/static')
    
    # 加载配置
    app.config.from_object(config[config_name])

    # 响应压缩（减少 HTML/CSS/JS/JSON 体积，提升移动端加载体验）
    _setup_response_compression(app)

    # 反向代理头支持（Nginx -> gunicorn 场景）：获取真实 IP / scheme
    _setup_proxy_fix(app)
    
    # 确保必要的目录存在
    _ensure_directories(app)
    
    # 初始化扩展
    init_extensions(app)

    # 注册自定义 Jinja2 过滤器
    def _nl2br(value):
        """将换行符转为 <br>，同时转义 HTML（防止 XSS）"""
        if value is None:
            return ''
        return Markup(_escape(value).replace('\n', Markup('<br>')))

    app.jinja_env.filters['nl2br'] = _nl2br
    
    # 配置日志
    _setup_logging(app)
    
    # 注册蓝图
    _register_blueprints(app)

    # CSRF 豁免：所有 API 蓝图使用 JWT 认证，不需要 CSRF token
    _csrf_exempt_api_blueprints(app)
    
    # 注册上下文处理器
    _register_context_processors(app)
    
    # 注册请求钩子
    _register_before_request(app)

    # 注册健康检查接口（便于小程序真机连通性测试）
    _register_health_endpoints(app)
    
    # 注册错误处理器
    _register_error_handlers(app)
    
    # 初始化 ORM 模型（确保 Flask-Migrate 能发现所有表定义）
    with app.app_context():
        from app import models as _models  # noqa: F401
    
    # 启动后台任务
    _start_background_tasks(app)
    
    app.logger.info('应用启动完成')
    
    return app


def _setup_response_compression(app: Flask) -> None:
    """启用可选的 Gzip 压缩（直连 Flask 场景尤为重要）。"""
    if app.testing:
        return

    if not app.config.get('ENABLE_GZIP', True):
        return

    try:
        from .core.utils.gzip_middleware import GzipMiddleware

        minimum_size = int(app.config.get('GZIP_MINIMUM_SIZE', 500) or 500)
        app.wsgi_app = GzipMiddleware(app.wsgi_app, compresslevel=6, minimum_size=minimum_size)
        app.logger.info('GzipMiddleware 已启用 (minimum_size=%s)', minimum_size)
    except Exception as e:
        app.logger.warning('GzipMiddleware 启用失败：%s', e)


def _setup_proxy_fix(app: Flask) -> None:
    """在 Nginx 反代场景下启用 ProxyFix（获取真实 IP / scheme / host）。"""
    if app.testing:
        return

    if not app.config.get('PROXY_FIX_ENABLED'):
        return

    try:
        from werkzeug.middleware.proxy_fix import ProxyFix

        x_for = int(app.config.get('PROXY_FIX_X_FOR', 1) or 1)
        x_proto = int(app.config.get('PROXY_FIX_X_PROTO', 1) or 1)
        x_host = int(app.config.get('PROXY_FIX_X_HOST', 0) or 0)
        x_prefix = int(app.config.get('PROXY_FIX_X_PREFIX', 0) or 0)

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=x_for, x_proto=x_proto, x_host=x_host, x_prefix=x_prefix)
        app.logger.info('ProxyFix 已启用 (x_for=%s x_proto=%s x_host=%s x_prefix=%s)', x_for, x_proto, x_host, x_prefix)
    except Exception as e:
        app.logger.warning('ProxyFix 启用失败：%s', e)


def _ensure_directories(app):
    """确保必要的目录存在"""
    dirs = [
        app.config['LOG_DIR'],
        app.config['UPLOAD_FOLDER'],
        os.path.join(app.config['UPLOAD_FOLDER'], 'avatars'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'question_images'),
        os.path.dirname(app.config['DATABASE_PATH'])
    ]
    
    for dir_path in dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)


def _setup_logging(app):
    """配置日志系统"""
    import re

    # 敏感信息脱敏模式
    _SENSITIVE_PATTERNS = [
        (re.compile(r'(SECRET_KEY|WECHAT_SECRET|DASHSCOPE_API_KEY|MAIL_PASSWORD|password|token|secret)[=:]\s*["\']?([^\s"\']{4})[^\s"\']*', re.IGNORECASE), r'\1=\2****'),
        (re.compile(r'(sk-)[a-zA-Z0-9]{4}[a-zA-Z0-9]+', re.IGNORECASE), r'\1****'),
    ]

    class SensitiveDataFilter(logging.Filter):
        """日志脱敏过滤器：自动遮蔽密钥、密码等敏感信息"""
        def filter(self, record: logging.LogRecord) -> bool:
            if isinstance(record.msg, str):
                for pattern, replacement in _SENSITIVE_PATTERNS:
                    record.msg = pattern.sub(replacement, record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {
                        k: pattern.sub(replacement, str(v)) if isinstance(v, str) else v
                        for k, v in record.args.items()
                        for pattern, replacement in _SENSITIVE_PATTERNS
                    }
                elif isinstance(record.args, tuple):
                    new_args = []
                    for a in record.args:
                        if isinstance(a, str):
                            for pattern, replacement in _SENSITIVE_PATTERNS:
                                a = pattern.sub(replacement, a)
                        new_args.append(a)
                    record.args = tuple(new_args)
            return True

    class RequestIdFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            try:
                from flask import has_request_context, g

                if has_request_context():
                    record.request_id = getattr(g, 'request_id', '-') or '-'
                else:
                    record.request_id = '-'
            except Exception:
                record.request_id = '-'
            return True

    # 给日志记录补充 request_id 字段（formatter 使用时更利于排障）
    request_id_filter = RequestIdFilter()
    sensitive_filter = SensitiveDataFilter()
    try:
        app.logger.addFilter(request_id_filter)
        app.logger.addFilter(sensitive_filter)
    except Exception:
        pass

    if not app.debug and not app.testing:
        file_handler = RotatingFileHandler(
            os.path.join(app.config['LOG_DIR'], 'app.log'),
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        # 根据环境设置日志级别
        log_level = app.config.get('LOG_LEVEL', logging.INFO)
        if app.config.get('DEBUG'):
            log_level = logging.DEBUG
        
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s [%(request_id)s]: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        try:
            file_handler.addFilter(request_id_filter)
        except Exception:
            pass
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(log_level)
        
        # 生产环境日志提示
        if not app.config.get('DEBUG'):
            app.logger.info(f'生产环境已启动，日志级别: {logging.getLevelName(log_level)}')


def _register_blueprints(app):
    """注册所有蓝图"""
    # 注册所有模块
    from .modules import register_all_modules
    register_all_modules(app)


def _csrf_exempt_api_blueprints(app):
    """豁免所有 API 蓝图的 CSRF 检查（API 使用 JWT 认证，不依赖 cookie）"""
    from .core.extensions import csrf
    for name, bp in app.blueprints.items():
        if 'api' in name:
            csrf.exempt(bp)


def _register_context_processors(app):
    """注册上下文处理器"""
    from flask import session
    
    @app.context_processor
    def inject_user():
        return {
            'logged_in': bool(session.get('user_id')),
            'username': session.get('username'),
            'user_id': session.get('user_id'),
            'is_admin': bool(session.get('is_admin')),
            'is_subject_admin': bool(session.get('is_subject_admin')),
            'is_notification_admin': bool(session.get('is_notification_admin')),
        }


def _register_before_request(app):
    """注册请求前钩子"""
    import uuid
    from flask import request, session, redirect, url_for, jsonify, g
    @app.before_request
    def _assign_request_id():
        rid = request.headers.get('X-Request-ID') or request.headers.get('X-Request-Id')
        if rid:
            rid = str(rid).strip().replace('\n', '').replace('\r', '')
            if len(rid) > 128:
                rid = rid[:128]
        else:
            rid = uuid.uuid4().hex
        g.request_id = rid

    @app.before_request
    def _force_https():
        """生产环境 HTTPS 强制重定向（Flask 层备用）。"""
        if app.debug or app.testing:
            return
        if not app.config.get('FORCE_HTTPS'):
            return
        if request.is_secure or request.headers.get('X-Forwarded-Proto', 'http') == 'https':
            return
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

    @app.after_request
    def _inject_request_id_header(response):
        rid = getattr(g, 'request_id', None)
        if rid:
            response.headers.setdefault('X-Request-ID', rid)

        # 安全 HTTP 头
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        if not app.debug:
            response.headers.setdefault(
                'Strict-Transport-Security', 'max-age=31536000; includeSubDomains'
            )

        # 统一 API 返回信封（尽量不破坏现有前端：保留原字段，同时补齐 data/message/request_id）
        try:
            if getattr(response, 'direct_passthrough', False):
                return response

            if response.mimetype != 'application/json':
                return response

            payload = response.get_json(silent=True)
            if not isinstance(payload, dict):
                return response

            changed = False

            if rid and 'request_id' not in payload:
                payload['request_id'] = rid
                changed = True

            status = payload.get('status')
            if status == 'success':
                if 'message' not in payload:
                    payload['message'] = ''
                    changed = True
                if 'data' not in payload:
                    payload['data'] = {
                        k: v for k, v in payload.items() if k not in ('status', 'message', 'request_id', 'data')
                    }
                    changed = True
            elif status in ('error', 'unauthorized', 'forbidden'):
                if 'message' not in payload:
                    payload['message'] = ''
                    changed = True
                if 'status_code' not in payload and isinstance(getattr(response, 'status_code', None), int):
                    payload['status_code'] = int(response.status_code)
                    changed = True

            if changed:
                response.set_data(json.dumps(payload, ensure_ascii=False))
                response.headers['Content-Type'] = 'application/json; charset=utf-8'
        except Exception:
            return response
        return response

    @app.before_request
    def enforce_login():
        path = request.path or ''
        
        # 检查JWT token（小程序）
        jwt_token = request.headers.get('Authorization') or request.headers.get('authorization')
        has_jwt_token = False
        if jwt_token and jwt_token.startswith('Bearer '):
            # 如果有JWT token，跳过session检查，让@auth_required装饰器处理
            # 但需要先检查路径是否在白名单中（JWT token也需要通过@auth_required验证）
            has_jwt_token = True
        
        # 已登录的会话校验（仅Web端，小程序使用JWT token）
        if session.get('user_id') and not has_jwt_token:
            try:
                if session.get('remember'):
                    session.permanent = True
                uid = session.get('user_id')

                from app.models.user import User as UserModel
                from app.core.extensions import db as _db

                user = UserModel.query.get(uid)

                if not user or user.is_locked:
                    session.clear()
                    if path.startswith('/api'):
                        return jsonify({'status':'unauthorized','message':'会话无效或已被锁定','request_id': getattr(g, 'request_id', None)}), 401
                    return redirect('/login')

                if session.get('session_version') is not None and \
                   session.get('session_version') != (user.session_version or 0):
                    session.clear()
                    if path.startswith('/api'):
                        return jsonify({'status':'unauthorized','message':'会话已失效，请重新登录','request_id': getattr(g, 'request_id', None)}), 401
                    return redirect('/login')

                # 更新session中的权限信息（确保权限同步）
                session['is_admin'] = bool(user.is_admin)
                session['is_subject_admin'] = bool(user.is_subject_admin)
                session['is_notification_admin'] = bool(user.is_notification_admin)

                # 检查用户是否绑定邮箱（排除管理员和绑定邮箱相关的API）
                if not session.get('is_admin'):
                    from app.modules.admin.services.system_config_service import SystemConfigService
                    email_bind_required = SystemConfigService.get_email_bind_required_config()

                    if email_bind_required:
                        email_bound = user.email and user.email.strip()

                        if not email_bound:
                            allowed_paths = {
                                '/',
                                '/terms',
                                '/privacy',
                                '/api/email/send-bind-code',
                                '/api/email/bind',
                                '/api/logout',
                                '/logout',
                                '/static',
                            }

                            is_allowed = False
                            for allowed_path in allowed_paths:
                                if path == allowed_path or path.startswith(allowed_path):
                                    is_allowed = True
                                    break

                            if not is_allowed:
                                if path.startswith('/api'):
                                    return jsonify({
                                        'status': 'error',
                                        'message': '请先绑定邮箱后才能使用此功能',
                                        'code': 'EMAIL_NOT_BOUND'
                                    }), 403
                                return redirect('/')

                # 更新用户最后活动时间（排除静态资源请求）
                if not path.startswith('/static') and not path.endswith('.ico'):
                    try:
                        interval = int(app.config.get('LAST_ACTIVE_UPDATE_INTERVAL_SECONDS', 60) or 60)
                    except Exception:
                        interval = 60
                    if interval < 0:
                        interval = 0

                    if _should_update_last_active(int(uid), interval):
                        from sqlalchemy import func as sa_func
                        user.last_active = sa_func.now()
                        _db.session.commit()
            except Exception as e:
                # 记录错误但不中断请求
                app.logger.warning(f"会话验证异常: {e}", exc_info=True)
                pass
            
            # 管理后台权限校验
            if path.startswith('/admin') or path.startswith('/admin_'):
                is_admin_user = session.get('is_admin')
                is_subject_admin_user = session.get('is_subject_admin')
                is_notification_admin_user = session.get('is_notification_admin')
                
                # 科目管理员允许访问的路由（科目和题集管理）
                # 匹配规则：
                # 1. /admin/subjects 及其子路径
                # 2. /admin/api/subjects 及其子路径
                # 3. /admin/questions 及其子路径（包括 /admin/questions/import, /admin/questions/export 等）
                # 4. /admin/api/questions 相关路径（通过路径包含判断）
                # 5. /admin/download_template（Excel模板下载）
                is_subject_admin_path = (
                    path.startswith('/admin/subjects') or
                    path.startswith('/admin/api/subjects') or
                    path.startswith('/admin/questions') or
                    path == '/admin/types' or  # 题型列表API
                    path == '/admin/download_template' or
                    '/api/subjects' in path or
                    '/api/questions' in path
                )
                
                # 通知管理员允许访问的路由（通知管理）
                # 匹配规则：
                # 1. /admin/notifications 及其子路径
                # 2. /admin/api/notifications 及其子路径
                # 3. /admin/popups 及其子路径（弹窗管理是通知管理的一部分）
                # 4. /admin/api/popups 及其子路径
                # 5. /admin 和 /admin/dashboard（重定向到通知管理）
                is_notification_admin_path = (
                    path.startswith('/admin/notifications') or
                    path.startswith('/admin/api/notifications') or
                    path.startswith('/admin/popups') or
                    path.startswith('/admin/api/popups') or
                    '/api/notifications' in path or
                    '/api/popups' in path
                )
                
                # 通知管理员访问 /admin 或 /admin/dashboard 时，重定向到通知管理页面
                if (path == '/admin' or path == '/admin/') and is_notification_admin_user and not is_admin_user:
                    return redirect('/admin/notifications')
                if path == '/admin/dashboard' and is_notification_admin_user and not is_admin_user:
                    return redirect('/admin/notifications')
                
                # 如果是科目管理员路径，允许科目管理员和管理员访问
                if is_subject_admin_path:
                    if not (is_admin_user or is_subject_admin_user):
                        if path.startswith('/admin/'):
                            return jsonify({'status': 'forbidden', 'message': '需要管理员或科目管理员权限'}), 403
                        return redirect('/')
                # 如果是通知管理员路径，允许通知管理员和管理员访问
                elif is_notification_admin_path:
                    if not (is_admin_user or is_notification_admin_user):
                        if path.startswith('/admin/'):
                            return jsonify({'status': 'forbidden', 'message': '需要管理员或通知管理员权限'}), 403
                        return redirect('/')
                # 其他管理后台路由需要管理员权限
                elif not is_admin_user:
                    if path.startswith('/admin/'):
                        return jsonify({'status': 'forbidden', 'message': '需要管理员权限'}), 403
                    return redirect('/')
            return

        # 未登录白名单（只允许首页和登录）
        allow_paths = {
            '/', '/hub', '/login', '/favicon.ico',
            '/public/banks',  # 公开题库广场（未登录可访问）
            '/terms',  # 服务协议页面
            '/privacy',  # 隐私保护协议页面
            '/api/ping',  # 健康检查（无登录）
            '/api/login',
            '/api/public/banks',  # 公开题库列表（未登录可访问）
            '/api/wechat/login',  # 微信登录（无需登录，支持自动注册）
            '/api/wechat/create',  # 微信创建新账号（临时票据）
            '/api/wechat/bind',  # 微信绑定已有账号（临时票据）
            '/api/wechat/bind/send_code',  # 微信绑定：发送邮箱验证码（临时票据）
            '/api/wechat/bind_confirm',  # Web账号管理：扫码绑定微信（小程序确认）
            '/api/mini/login',  # 小程序：账号密码登录（JWT）
            '/api/mini/email/send-login-code',  # 小程序：发送邮箱登录验证码（JWT）
            '/api/mini/email/login',  # 小程序：邮箱验证码登录（JWT）
            '/api/email/send-login-code',  # 发送登录验证码（无需登录，支持自动注册）
            '/api/email/login',  # 验证码登录（无需登录，支持自动注册）
            '/api/forgot-password/send-code',  # 发送忘记密码验证码（无需登录）
            '/api/forgot-password/reset'  # 重置密码（无需登录）
        }
        if path in allow_paths or path.startswith('/static'):
            return

        # 公开题库相关动态接口（未登录可访问；需要登录的操作由路由装饰器控制）
        if path.startswith('/api/public/banks/'):
            return

        # Web 扫码登录相关 API（未登录可访问，confirm 仍由 jwt_required 控制）
        if path.startswith('/api/web_login/'):
            return

        # 扫码登录二维码图片（仅允许该目录）
        if path.startswith('/uploads/web_login/'):
            return

        # 绑定微信二维码图片（仅允许该目录）
        if path.startswith('/uploads/wechat_bind/'):
            return

        # 小程序 <image> / Web 公共页面无法携带 Authorization Header：
        # 放开头像/题目图片的直链访问（仅常见图片扩展名），避免被登录拦截 302 到 /login 导致图片加载失败。
        if path.startswith(('/uploads/avatars/', '/uploads/question_images/', '/uploads/questions/')):
            lower_path = path.lower()
            if lower_path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
                return

        # 公开API（需要检查参数）
        if path == '/api/questions/count':
            # 检查 mode 参数，如果是 favorites 或 mistakes 模式，需要登录
            mode = request.args.get('mode', '').lower()
            if mode in ('favorites', 'mistakes'):
                # 这些模式需要登录
                if path.startswith('/api'):
                    return jsonify({'status': 'unauthorized', 'message': '请先登录后使用此功能', 'request_id': getattr(g, 'request_id', None)}), 401
                from urllib.parse import quote
                mode_name = '收藏本' if mode == 'favorites' else '错题本'
                login_url = f'/login?from={mode}&redirect={quote(path)}'
                return redirect(login_url)
            # 其他模式允许未登录访问
            return

        if path == '/api/questions/user_counts':
            # 这个 API 允许未登录访问（返回0）
            return

        # 通知 API 允许未登录访问（用于主页显示通知）
        # 但通知历史页面需要登录（属于用户中心功能）
        if path == '/notifications':
            return jsonify({'status': 'unauthorized', 'message': '请先登录', 'request_id': getattr(g, 'request_id', None)}), 401
        
        # /api/notifications 允许未登录访问，但标记已读/关闭等操作仍需要登录
        if path.startswith('/api/notifications'):
            # 对于需要登录的操作（read, dismiss），在路由函数内部检查
            # 列表查询允许未登录访问
            return
        
        # 需要登录的功能路径
        login_required_paths = {
            '/quiz': 'quiz',
            '/exams': 'exams', 
            '/profile': 'profile',
            '/search': 'search',
            '/coding': '编程模式'
        }
        
        for required_path, tip_key in login_required_paths.items():
            if path.startswith(required_path):
                if path.startswith('/api'):
                    return jsonify({'status': 'unauthorized', 'message': '请先登录后使用此功能', 'request_id': getattr(g, 'request_id', None)}), 401
                # 页面请求：重定向到登录页并显示提示
                # 构建登录URL，包含来源和跳转信息
                from urllib.parse import quote
                # 根据路径确定提示信息
                if required_path == '/quiz':
                    mode = request.args.get('mode', 'quiz').lower()
                    if mode == 'memo':
                        tip_key = '背题'
                    elif mode == 'favorites':
                        tip_key = '收藏本'
                    elif mode == 'mistakes':
                        tip_key = '错题本'
                    elif mode == 'exam':
                        tip_key = '考试'
                    else:
                        tip_key = '刷题'
                login_url = f'/login?from={tip_key}&redirect={quote(path)}'
                return redirect(login_url)
        
        # 需要登录的 API 路径
        login_required_apis = [
            '/api/favorite',
            '/api/record_result',
            '/api/progress',
            '/api/exams',
            '/coding/api'
        ]
        
        for api_path in login_required_apis:
            if path.startswith(api_path):
                # 如果有JWT token，让@auth_required装饰器处理
                jwt_token = request.headers.get('Authorization') or request.headers.get('authorization')
                if jwt_token and jwt_token.startswith('Bearer '):
                    return  # 跳过检查，让装饰器处理
                return jsonify({'status': 'unauthorized', 'message': '请先登录后使用此功能', 'request_id': getattr(g, 'request_id', None)}), 401
        
        if path.startswith('/api'):
            # 如果有JWT token，让@auth_required装饰器处理
            jwt_token = request.headers.get('Authorization') or request.headers.get('authorization')
            if jwt_token and jwt_token.startswith('Bearer '):
                return  # 跳过检查，让装饰器处理
            return jsonify({'status': 'unauthorized', 'message': '请先登录', 'request_id': getattr(g, 'request_id', None)}), 401
        return redirect('/login')


def _register_health_endpoints(app: Flask) -> None:
    """注册简单健康检查接口（用于小程序真机连通性测试）。"""
    from flask import jsonify

    @app.get('/api/ping')
    def api_ping():
        return jsonify({'status': 'success', 'data': {'pong': True}})


def _register_error_handlers(app):
    """注册错误处理器"""
    from .core.errors import register_error_handlers
    register_error_handlers(app)


def _start_background_tasks(app):
    """启动后台任务"""
    from .core.tasks import start_background_tasks
    start_background_tasks(app)
