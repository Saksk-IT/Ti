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
    _validate_required_runtime_config(app)

    # 生产/预发布等非调试环境禁止内存限流存储，避免多实例计数失效
    if not app.config.get('DEBUG') and not app.config.get('TESTING'):
        storage_uri = str(app.config.get('RATELIMIT_STORAGE_URI') or '').strip().lower()
        if storage_uri.startswith('memory://'):
            raise RuntimeError('RATELIMIT_STORAGE_URI 不能为 memory://，请改为 Redis 存储。')

    # Sentry 错误监控（生产环境，需设置 SENTRY_DSN 环境变量）
    _setup_sentry(app)

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

    # 注册 Flask CLI 命令
    _register_cli_commands(app)
    
    # 初始化 ORM 模型（确保 Flask-Migrate 能发现所有表定义）
    with app.app_context():
        from app import models as _models  # noqa: F401
    
    # 启动后台任务
    _start_background_tasks(app)
    
    app.logger.info('应用启动完成')
    
    return app


def _register_cli_commands(app):
    """注册运维命令。"""
    from app.core.cli import register_cli_commands

    register_cli_commands(app)


def _validate_required_runtime_config(app: Flask) -> None:
    """校验生产运行必需配置，避免测试导入阶段误触发生产校验。"""
    if app.config.get('DEBUG') or app.config.get('TESTING'):
        return

    if not app.config.get('SECRET_KEY'):
        raise RuntimeError(
            'SECRET_KEY 未设置！生产环境必须设置 SECRET_KEY 环境变量。'
            '生成方式: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )

    if not app.config.get('REDIS_URL'):
        raise RuntimeError(
            'REDIS_URL 未设置！生产环境必须设置 REDIS_URL 环境变量。'
            '示例: redis://redis:6379/0'
        )


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


def _setup_sentry(app: Flask) -> None:
    """初始化 Sentry 错误监控（需设置 SENTRY_DSN 环境变量）。"""
    if app.debug or app.testing:
        return

    dsn = os.environ.get('SENTRY_DSN', '').strip()
    if not dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
            environment=os.environ.get('FLASK_ENV', 'production'),
            send_default_pii=False,
        )
        app.logger.info('Sentry 已启用')
    except Exception as e:
        app.logger.warning('Sentry 初始化失败：%s', e)


def _ensure_directories(app):
    """确保必要的目录存在"""
    dirs = [
        app.config['LOG_DIR'],
        app.config['UPLOAD_FOLDER'],
        os.path.join(app.config['UPLOAD_FOLDER'], 'avatars'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'bank_covers'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'question_images'),
        os.path.dirname(app.config['DATABASE_PATH'])
    ]
    
    for dir_path in dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)


def _setup_logging(app):
    """配置日志系统

    优化点：
    - Filter 挂载到 root logger，所有 getLogger(__name__) 的模块日志均生效
    - RotatingFileHandler 指定 encoding='utf-8'，解决 Windows 中文乱码
    - SensitiveDataFilter dict args 处理 bug 修复
    - 日志格式添加 %(name)s 区分模块来源
    - 开发环境也配置统一格式的 StreamHandler
    """
    import re

    _SENSITIVE_PATTERNS = [
        (re.compile(r'(SECRET_KEY|WECHAT_SECRET|AI_API_KEY|OPENAI_API_KEY|DASHSCOPE_API_KEY|MAIL_PASSWORD|password|token|secret)[=:]\s*["\']?([^\s"\']{4})[^\s"\']*', re.IGNORECASE), r'\1=\2****'),
        (re.compile(r'(sk-)[a-zA-Z0-9]{4}[a-zA-Z0-9]+', re.IGNORECASE), r'\1****'),
    ]

    def _sanitize_str(s: str) -> str:
        for pattern, replacement in _SENSITIVE_PATTERNS:
            s = pattern.sub(replacement, s)
        return s

    class SensitiveDataFilter(logging.Filter):
        """日志脱敏过滤器：自动遮蔽密钥、密码等敏感信息"""
        def filter(self, record: logging.LogRecord) -> bool:
            if isinstance(record.msg, str):
                record.msg = _sanitize_str(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {
                        k: _sanitize_str(str(v)) if isinstance(v, str) else v
                        for k, v in record.args.items()
                    }
                elif isinstance(record.args, tuple):
                    record.args = tuple(
                        _sanitize_str(a) if isinstance(a, str) else a
                        for a in record.args
                    )
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

    # P0-1: Filter 挂载到每个 Handler 上（而非 logger 上）
    # Python logging 机制：logger 上的 Filter 只对直接调用该 logger 的日志生效，
    # 不对通过传播链到达的日志生效。挂到 Handler 上才能拦截所有模块的日志。
    root_logger = logging.getLogger()
    request_id_filter = RequestIdFilter()
    sensitive_filter = SensitiveDataFilter()

    # 统一日志格式（P2-6: 添加 %(name)s 区分模块）
    _LOG_FMT = '%(asctime)s %(levelname)s %(name)s [%(request_id)s]: %(message)s [in %(pathname)s:%(lineno)d]'
    formatter = logging.Formatter(_LOG_FMT)

    log_level = app.config.get('LOG_LEVEL', logging.INFO)
    if app.config.get('DEBUG') or app.debug:
        log_level = logging.DEBUG

    def _attach_filters(handler: logging.Handler) -> None:
        handler.addFilter(request_id_filter)
        handler.addFilter(sensitive_filter)

    if not app.debug and not app.testing:
        # P0-2: encoding='utf-8' 解决 Windows 中文乱码
        file_handler = RotatingFileHandler(
            os.path.join(app.config['LOG_DIR'], 'app.log'),
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT'],
            encoding='utf-8',
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        _attach_filters(file_handler)
        root_logger.addHandler(file_handler)
    else:
        # P2-7: 开发环境也使用统一格式的 StreamHandler
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(log_level)
        _attach_filters(stream_handler)
        # 精确匹配 StreamHandler（排除 FileHandler 等子类），避免误判
        if not any(type(h) is logging.StreamHandler for h in root_logger.handlers):
            root_logger.addHandler(stream_handler)
        # 给已有的 handler 也挂上 Filter 和统一格式
        for h in root_logger.handlers:
            if not any(isinstance(f, RequestIdFilter) for f in h.filters):
                _attach_filters(h)
            if not h.formatter or 'request_id' not in (h.formatter._fmt or ''):
                h.setFormatter(formatter)

    root_logger.setLevel(log_level)
    app.logger.setLevel(log_level)

    # 移除 Flask 自带的 handler，避免开发环境日志重复输出
    # app.logger 的日志会传播到 root logger，由 root 的 handler 统一输出
    app.logger.handlers.clear()

    if not app.debug and not app.testing:
        app.logger.info('生产环境已启动，日志级别: %s', logging.getLevelName(log_level))


def _register_blueprints(app):
    """注册所有蓝图"""
    # 注册所有模块
    from .modules import register_all_modules
    register_all_modules(app)


def _csrf_exempt_api_blueprints(app):
    """豁免所有 API 蓝图的 CSRF 检查（API 使用 JWT 认证，不依赖 cookie）"""
    from .core.extensions import csrf
    for name, bp in app.blueprints.items():
        if 'api' in name or name in {'sse', 'public_bank'}:
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

    @app.context_processor
    def inject_asset_url():
        """提供 asset_url() 函数，基于文件 mtime 生成 ?v= 参数实现缓存破坏"""
        _asset_versions: dict[str, str] = {}

        def asset_url(filename: str) -> str:
            if filename in _asset_versions:
                return f"/static/{filename}?v={_asset_versions[filename]}"
            filepath = os.path.join(app.static_folder or '', filename)
            try:
                mtime = int(os.path.getmtime(filepath))
                version = hex(mtime)[2:]
            except OSError:
                version = '0'
            _asset_versions[filename] = version
            return f"/static/{filename}?v={version}"

        return {'asset_url': asset_url}


def _register_before_request(app):
    """注册请求前钩子"""
    import uuid
    from flask import request, session, redirect, url_for, jsonify, g

    def _valid_jwt_payload_from_header():
        token = request.headers.get('Authorization') or request.headers.get('authorization') or ''
        raw = str(token).strip()
        if not raw:
            return None
        if raw.startswith('Bearer '):
            raw = raw[7:].strip()
        if not raw:
            return None
        try:
            from app.core.utils.jwt_utils import decode_jwt_token
            payload = decode_jwt_token(raw)
            if payload and payload.get('user_id'):
                return payload
        except Exception:
            return None
        return None

    def _has_valid_jwt_header() -> bool:
        cache_key = '_valid_jwt_header_cache'
        cached = getattr(g, cache_key, None)
        if cached is not None:
            return bool(cached)
        payload = _valid_jwt_payload_from_header()
        ok = bool(payload)
        setattr(g, cache_key, ok)
        return ok
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
        g.request_start = time.monotonic()

    # S4: API 写操作 CSRF 防护
    _CSRF_EXEMPT_ENDPOINTS = frozenset({
        '/api/login',
        '/api/wechat/login',
        '/api/wechat/create',
        '/api/wechat/bind',
        '/api/wechat/bind/send_code',
        '/api/wechat/bind_confirm',
        '/api/mini/login',
        '/api/mini/email/send-login-code',
        '/api/mini/email/login',
        '/api/email/send-login-code',
        '/api/email/login',
        '/api/forgot-password/send-code',
        '/api/forgot-password/reset',
        '/api/sms/send-login-code',
        '/api/sms/login',
        '/api/sms/send-bind-code',
        '/api/sms/bind',
        '/api/sms/forgot-password/send-code',
        '/api/sms/forgot-password/reset',
    })

    @app.before_request
    def _check_api_write_csrf():
        """拦截无 XHR 标记的 API 写请求（防 CSRF）"""
        if request.method not in ('POST', 'PUT', 'DELETE', 'PATCH'):
            return
        path = request.path or ''
        if not path.startswith('/api'):
            return
        # 放行：小程序有效 JWT 请求
        if _has_valid_jwt_header():
            return
        # 放行：XHR 请求（前端 fetch monkey-patch 自动注入）
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return
        # 放行：豁免端点（登录/注册等）
        if path in _CSRF_EXEMPT_ENDPOINTS:
            return
        return jsonify({'status': 'error', 'message': '请求被拒绝（缺少安全标头）'}), 403

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

    # P1-3: 访问日志专用 logger（非静态资源）
    _access_logger = logging.getLogger('access')
    _STATIC_PREFIXES = ('/static/', '/favicon.ico', '/robots.txt')

    @app.after_request
    def _inject_request_id_header(response):
        req_start = getattr(g, 'request_start', None)
        duration = 0.0
        if req_start is not None:
            duration = time.monotonic() - req_start
            if duration > 1.0:
                app.logger.warning(
                    'SLOW REQUEST: %s %s %.2fs [%s]',
                    request.method, request.path, duration,
                    getattr(g, 'request_id', '-'),
                )

        # 访问日志：排除静态资源
        path = request.path or ''
        if not path.startswith(_STATIC_PREFIXES):
            user = session.get('username', '-')
            dur_str = f'{duration:.3f}s' if req_start is not None else '-'
            _access_logger.info(
                '%s %s %s %s user=%s ip=%s',
                request.method, path, response.status_code,
                dur_str, user, request.remote_addr,
            )

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

        # 快速跳过：静态资源 / favicon / 健康检查无需任何 DB 查询
        if path.startswith('/static') or path.endswith('.ico') or path == '/api/ping':
            return

        # 检查JWT token（小程序）
        has_jwt_token = _has_valid_jwt_header()

        # 已登录的会话校验（仅Web端，小程序使用JWT token）
        if session.get('user_id') and not has_jwt_token:
            try:
                if session.get('remember'):
                    session.permanent = True
                uid = session.get('user_id')

                from app.models.user import User as UserModel
                from app.core.extensions import db as _db
                from app.core.utils.user_state_cache import get_user_state, set_user_state

                # 优先从缓存读取用户状态（减少每次请求的 DB 查询）
                cached_state = get_user_state(int(uid))
                if cached_state is not None:
                    is_locked = cached_state.get('is_locked', False)
                    cached_sv = cached_state.get('session_version', 0)

                    if is_locked:
                        session.clear()
                        if path.startswith('/api'):
                            return jsonify({'status':'unauthorized','message':'会话无效或已被锁定','request_id': getattr(g, 'request_id', None)}), 401
                        return redirect('/login')

                    if session.get('session_version') is not None and \
                       session.get('session_version') != cached_sv:
                        session.clear()
                        if path.startswith('/api'):
                            return jsonify({'status':'unauthorized','message':'会话已失效，请重新登录','request_id': getattr(g, 'request_id', None)}), 401
                        return redirect('/login')

                    # 从缓存同步权限
                    session['is_admin'] = bool(cached_state.get('is_admin', False))
                    session['is_subject_admin'] = bool(cached_state.get('is_subject_admin', False))
                    session['is_notification_admin'] = bool(cached_state.get('is_notification_admin', False))
                    user = None  # 标记：已从缓存获取，按需再查 DB
                else:
                    # 缓存未命中，查 DB
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

                    session['is_admin'] = bool(user.is_admin)
                    session['is_subject_admin'] = bool(user.is_subject_admin)
                    session['is_notification_admin'] = bool(user.is_notification_admin)

                    # 写入缓存供后续请求复用
                    set_user_state(int(uid), {
                        'is_locked': bool(user.is_locked),
                        'session_version': user.session_version or 0,
                        'is_admin': bool(user.is_admin),
                        'is_subject_admin': bool(user.is_subject_admin),
                        'is_notification_admin': bool(user.is_notification_admin),
                        'email': user.email or '',
                    })

                # 检查用户是否绑定邮箱（排除管理员和绑定邮箱相关的API）
                if not session.get('is_admin'):
                    from app.modules.admin.services.system_config_service import SystemConfigService
                    email_bind_required = SystemConfigService.get_email_bind_required_config()

                    if email_bind_required:
                        # 从缓存或 DB 对象获取 email
                        if cached_state is not None:
                            email_val = cached_state.get('email', '')
                        elif user is not None:
                            email_val = user.email or ''
                        else:
                            email_val = ''
                        email_bound = email_val and email_val.strip()

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

                # 更新用户最后活动时间（静态资源已在开头 return）
                try:
                    interval = int(app.config.get('LAST_ACTIVE_UPDATE_INTERVAL_SECONDS', 60) or 60)
                except Exception:
                    interval = 60
                if interval < 0:
                    interval = 0

                if _should_update_last_active(int(uid), interval):
                    from sqlalchemy import func as sa_func
                    if user is None:
                        user = UserModel.query.get(uid)
                    if user:
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
            '/api/auth/login-methods',  # 登录方式公开配置（登录页/小程序登录页使用）
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
            '/api/forgot-password/reset',  # 重置密码（无需登录）
            '/api/sms/send-login-code',  # 手机验证码登录：发送验证码（无需登录）
            '/api/sms/login',  # 手机验证码登录（无需登录，支持自动注册）
            '/api/sms/forgot-password/send-code',  # 手机忘记密码：发送验证码（无需登录）
            '/api/sms/forgot-password/reset',  # 手机忘记密码：重置密码（无需登录）
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
        if path.startswith(('/uploads/avatars/', '/uploads/bank_covers/', '/uploads/question_images/', '/uploads/questions/')):
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
                if has_jwt_token:
                    return  # 跳过检查，让装饰器处理
                return jsonify({'status': 'unauthorized', 'message': '请先登录后使用此功能', 'request_id': getattr(g, 'request_id', None)}), 401
        
        if path.startswith('/api'):
            # 如果有JWT token，让@auth_required装饰器处理
            if has_jwt_token:
                return  # 跳过检查，让装饰器处理
            return jsonify({'status': 'unauthorized', 'message': '请先登录', 'request_id': getattr(g, 'request_id', None)}), 401
        return redirect('/login')


def _register_health_endpoints(app: Flask) -> None:
    """注册简单健康检查接口（用于小程序真机连通性测试）。"""
    from flask import jsonify, request as _req

    @app.get('/api/ping')
    def api_ping():
        if _req.args.get('deep') != '1':
            return jsonify({'status': 'success', 'data': {'pong': True}})

        # 深度检查：DB + Redis 连通性
        checks: dict = {'pong': True, 'db': False, 'redis': False}

        # DB
        try:
            from app.core.extensions import db as _db
            _db.session.execute(_db.text('SELECT 1'))
            checks['db'] = True
        except Exception as e:
            checks['db_error'] = str(e)

        # Redis
        try:
            from app.core.utils.redis_utils import get_redis_connection
            r = get_redis_connection()
            if r is not None:
                r.ping()
                checks['redis'] = True
            else:
                checks['redis_error'] = 'not configured'
        except Exception as e:
            checks['redis_error'] = str(e)

        all_ok = checks['db'] and checks['redis']
        status_code = 200 if all_ok else 503
        return jsonify({'status': 'success' if all_ok else 'degraded', 'data': checks}), status_code


def _register_error_handlers(app):
    """注册错误处理器"""
    from .core.errors import register_error_handlers
    register_error_handlers(app)


def _start_background_tasks(app):
    """启动后台任务"""
    from .core.tasks import start_background_tasks
    start_background_tasks(app)
