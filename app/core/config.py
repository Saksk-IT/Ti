# -*- coding: utf-8 -*-
"""
应用配置模块
"""
import os
import logging
from datetime import timedelta
from app.core.utils.rate_limit_policy import production_rate_limit_multiplier


class Config:
    """基础配置类"""
    # 基础路径（项目根目录）
    # __file__ 是 app/core/config.py，需要向上两级到项目根目录
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    # 运行数据根目录（用于跨平台/Docker 部署解耦 instance/logs/uploads）
    # 默认使用项目根目录下的 var 子目录，避免数据文件散落在根目录
    _DATA_DIR_RAW = os.environ.get('DATA_DIR')
    if _DATA_DIR_RAW:
        DATA_DIR = os.path.abspath(_DATA_DIR_RAW) if os.path.isabs(_DATA_DIR_RAW) else os.path.abspath(os.path.join(BASE_DIR, _DATA_DIR_RAW))
    else:
        DATA_DIR = os.path.join(BASE_DIR, 'var')
    
    # 密钥配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # 数据库配置
    # 统一主数据库：submissions.db
    # 数据库文件位于项目根目录的instance文件夹（app文件夹外）
    DATABASE_PATH = os.path.join(DATA_DIR, 'instance', 'submissions.db')

    # SQLAlchemy 配置（支持 SQLite 和 PostgreSQL）
    # 优先读取 DATABASE_URL 环境变量；未设置时回退到 SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(DATA_DIR, 'instance', 'submissions.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {}  # 子类可覆盖

    SQLITE_TIMEOUT = float(os.environ.get('SQLITE_TIMEOUT', '15') or 15)
    SQLITE_BUSY_TIMEOUT_MS = int(os.environ.get('SQLITE_BUSY_TIMEOUT_MS', '5000') or 5000)
    SQLITE_JOURNAL_MODE = os.environ.get('SQLITE_JOURNAL_MODE', 'WAL')
    SQLITE_SYNCHRONOUS = os.environ.get('SQLITE_SYNCHRONOUS', 'NORMAL')
    DB_SCHEMA_CACHE_TTL_SECONDS = int(os.environ.get('DB_SCHEMA_CACHE_TTL_SECONDS', '60') or 60)
    
    # 上传文件配置
    UPLOAD_FOLDER = os.path.join(DATA_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    
    # 日志配置
    LOG_DIR = os.path.join(DATA_DIR, 'logs')
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 10
    
    # Flask配置
    JSON_AS_ASCII = False
    JSONIFY_MIMETYPE = 'application/json; charset=utf-8'

    # 反向代理（Nginx）转发头支持：用于获取真实 IP / scheme / host
    # 安全建议：仅在 gunicorn 绑定到 127.0.0.1 并由 Nginx 反代时开启。
    PROXY_FIX_ENABLED = os.environ.get('PROXY_FIX_ENABLED', 'false').lower() in ['true', 'on', '1']
    PROXY_FIX_X_FOR = int(os.environ.get('PROXY_FIX_X_FOR', '1') or 1)
    PROXY_FIX_X_PROTO = int(os.environ.get('PROXY_FIX_X_PROTO', '1') or 1)
    PROXY_FIX_X_HOST = int(os.environ.get('PROXY_FIX_X_HOST', '0') or 0)
    PROXY_FIX_X_PREFIX = int(os.environ.get('PROXY_FIX_X_PREFIX', '0') or 0)

    # 响应压缩（可由反向代理/Nginx 接管；直连 Flask 时可显著减少 HTML/CSS/JS/JSON 体积）
    ENABLE_GZIP = os.environ.get('ENABLE_GZIP', 'true').lower() in ['true', 'on', '1']
    GZIP_MINIMUM_SIZE = int(os.environ.get('GZIP_MINIMUM_SIZE', '500') or 500)
    
    # 会话配置：启用永久会话，默认 7 天
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_REFRESH_EACH_REQUEST = True

    # Web 会话活跃时间写入节流（避免每次请求都写 SQLite）
    LAST_ACTIVE_UPDATE_INTERVAL_SECONDS = int(os.environ.get('LAST_ACTIVE_UPDATE_INTERVAL_SECONDS', '60') or 60)

    # SSE 被拒绝后的建议重试间隔（秒）
    SSE_RETRY_AFTER_SECONDS = int(os.environ.get('SSE_RETRY_AFTER_SECONDS', '30') or 30)
    
    # 限流配置
    # 生产环境建议使用 Redis: 'redis://localhost:6379/0'
    RATELIMIT_STORAGE_URI = (
        os.environ.get('RATELIMIT_STORAGE_URI')
        or os.environ.get('RATELIMIT_STORAGE_URL')
        or 'memory://'
    )
    RATELIMIT_STORAGE_URL = RATELIMIT_STORAGE_URI
    RATELIMIT_DEFAULT = "5000 per day;500 per hour;10 per second"
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_LIMIT_MULTIPLIER = 1

    # Redis（缓存/队列/限流共享存储）
    # 优先读 REDIS_URL；若未设置且限流存储为 redis://，则复用其连接
    REDIS_URL = os.environ.get('REDIS_URL') or (
        RATELIMIT_STORAGE_URI if str(RATELIMIT_STORAGE_URI or '').startswith(('redis://', 'rediss://')) else None
    )
    RQ_QUEUE_NAME = os.environ.get('RQ_QUEUE_NAME', 'saksk')

    # AI 解析缓存：默认 30 天
    AI_EXPLAIN_CACHE_TTL_SECONDS = int(os.environ.get('AI_EXPLAIN_CACHE_TTL_SECONDS', str(30 * 24 * 60 * 60)) or (30 * 24 * 60 * 60))

    # Quiz/Subjects/Stats 读接口缓存（Redis 优先；未配置 Redis 时自动无缓存降级）
    QUIZ_API_CACHE_ENABLED = os.environ.get('QUIZ_API_CACHE_ENABLED', 'true').lower() in ['true', 'on', '1']
    QUIZ_CACHE_TTL_QUESTION_DETAIL_SECONDS = int(os.environ.get('QUIZ_CACHE_TTL_QUESTION_DETAIL_SECONDS', '300') or 300)
    QUIZ_CACHE_TTL_COUNTS_SECONDS = int(os.environ.get('QUIZ_CACHE_TTL_COUNTS_SECONDS', '60') or 60)
    QUIZ_CACHE_TTL_USER_COUNTS_SECONDS = int(os.environ.get('QUIZ_CACHE_TTL_USER_COUNTS_SECONDS', '30') or 30)
    QUIZ_CACHE_TTL_HISTORY_SECONDS = int(os.environ.get('QUIZ_CACHE_TTL_HISTORY_SECONDS', '30') or 30)
    QUIZ_CACHE_TTL_SUBJECTS_SECONDS = int(os.environ.get('QUIZ_CACHE_TTL_SUBJECTS_SECONDS', '60') or 60)
    QUIZ_CACHE_TTL_SUBJECTS_META_SECONDS = int(os.environ.get('QUIZ_CACHE_TTL_SUBJECTS_META_SECONDS', '60') or 60)

    # JWT 用户状态缓存（用于减少每次请求都查询 users 表）
    # 注意：对会话强制失效（session_version bump）仍然以 DB 为准；缓存仅作为短 TTL 加速。
    JWT_USER_STATE_CACHE_TTL_SECONDS = int(os.environ.get('JWT_USER_STATE_CACHE_TTL_SECONDS', '20') or 20)

    # 邮件服务配置
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or None
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or None
    MAIL_DEFAULT_SENDER_NAME = os.environ.get('MAIL_DEFAULT_SENDER_NAME') or '系统通知'
    
    # 邮件服务开关（开发环境可以关闭真实邮件发送）
    MAIL_ENABLED = os.environ.get('MAIL_ENABLED', 'true').lower() in ['true', 'on', '1']
    # 开发环境控制台输出验证码（不发送真实邮件）
    MAIL_CONSOLE_OUTPUT = os.environ.get('MAIL_CONSOLE_OUTPUT', 'false').lower() in ['true', 'on', '1']
    
    # 微信小程序配置
    WECHAT_APPID = os.environ.get('WECHAT_APPID') or os.environ.get('WX_APPID')
    WECHAT_SECRET = os.environ.get('WECHAT_SECRET') or os.environ.get('WX_SECRET')
    WECHAT_MINICODE_ENV_VERSION = os.environ.get('WECHAT_MINICODE_ENV_VERSION', '')
    _WECHAT_MINICODE_CHECK_PATH_RAW = os.environ.get('WECHAT_MINICODE_CHECK_PATH')
    if _WECHAT_MINICODE_CHECK_PATH_RAW is None or str(_WECHAT_MINICODE_CHECK_PATH_RAW).strip().lower() == 'auto':
        WECHAT_MINICODE_CHECK_PATH = None
    else:
        WECHAT_MINICODE_CHECK_PATH = str(_WECHAT_MINICODE_CHECK_PATH_RAW).strip().lower() in ['true', 'on', '1', 'yes']

    # 阿里云号码认证服务（DYPNS）
    ALIYUN_ACCESS_KEY_ID = os.environ.get('ALIYUN_ACCESS_KEY_ID')
    ALIYUN_ACCESS_KEY_SECRET = os.environ.get('ALIYUN_ACCESS_KEY_SECRET')
    ALIYUN_SMS_SIGN_NAME = os.environ.get('ALIYUN_SMS_SIGN_NAME', '')
    ALIYUN_SMS_TEMPLATE_CODE = os.environ.get('ALIYUN_SMS_TEMPLATE_CODE', '')
    ALIYUN_SMS_TEMPLATE_CODE_BIND = os.environ.get('ALIYUN_SMS_TEMPLATE_CODE_BIND', '')
    ALIYUN_SMS_TEMPLATE_CODE_RESET = os.environ.get('ALIYUN_SMS_TEMPLATE_CODE_RESET', '')
    ALIYUN_SMS_CODE_LENGTH = int(os.environ.get('ALIYUN_SMS_CODE_LENGTH', '6') or 6)
    ALIYUN_SMS_VALID_TIME = int(os.environ.get('ALIYUN_SMS_VALID_TIME', '300') or 300)
    ALIYUN_SMS_INTERVAL = int(os.environ.get('ALIYUN_SMS_INTERVAL', '60') or 60)
    SMS_ENABLED = os.environ.get('SMS_ENABLED', 'true').lower() in ['true', 'on', '1']
    SMS_CONSOLE_OUTPUT = os.environ.get('SMS_CONSOLE_OUTPUT', 'false').lower() in ['true', 'on', '1']

    # 登录方式开关（DB 配置优先，环境变量用于兜底）
    AUTH_PHONE_LOGIN_ENABLED = os.environ.get('AUTH_PHONE_LOGIN_ENABLED', 'true').lower() in ['true', 'on', '1']
    AUTH_WECHAT_LOGIN_ENABLED = os.environ.get('AUTH_WECHAT_LOGIN_ENABLED', 'true').lower() in ['true', 'on', '1']

    # === 通用 AI 配置（DB 配置优先，环境变量用于兜底）===
    AI_PROVIDER = os.environ.get('AI_PROVIDER', '')
    AI_API_KEY = os.environ.get('AI_API_KEY')
    AI_BASE_URL = os.environ.get('AI_BASE_URL', '')
    AI_API_TYPE = os.environ.get('AI_API_TYPE', '')
    AI_MODEL = os.environ.get('AI_MODEL', '')
    AI_MODEL_SOURCE = os.environ.get('AI_MODEL_SOURCE', '')
    AI_TIMEOUT = int(os.environ.get('AI_TIMEOUT', '25') or 25)
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini')

    # === 阿里云百炼（DashScope OpenAI 兼容接口）===
    # 文档：https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen
    DASHSCOPE_API_KEY = os.environ.get('DASHSCOPE_API_KEY')
    # 北京地域（默认）：https://dashscope.aliyuncs.com/compatible-mode/v1
    # 新加坡地域：    https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    DASHSCOPE_BASE_URL = os.environ.get('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    DASHSCOPE_MODEL = os.environ.get('DASHSCOPE_MODEL', 'qwen-plus')
    DASHSCOPE_TIMEOUT = int(os.environ.get('DASHSCOPE_TIMEOUT', '25') or 25)


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False
    
    # 开发环境默认使用控制台输出
    MAIL_CONSOLE_OUTPUT = os.environ.get('MAIL_CONSOLE_OUTPUT', 'true').lower() in ['true', 'on', '1']

    # 开发环境短信验证码输出到控制台
    SMS_CONSOLE_OUTPUT = os.environ.get('SMS_CONSOLE_OUTPUT', 'true').lower() in ['true', 'on', '1']

    # 开发环境禁用 RQ（Windows 不支持 fork/SIGALRM），强制同步降级
    RQ_DISABLED = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    RATELIMIT_LIMIT_MULTIPLIER = production_rate_limit_multiplier()
    _RATELIMIT_DEFAULT_RAW = os.environ.get('RATELIMIT_DEFAULT')
    _RATELIMIT_DEFAULT_FALLBACK = (
        f"{5000 * RATELIMIT_LIMIT_MULTIPLIER}/day;"
        f"{500 * RATELIMIT_LIMIT_MULTIPLIER}/hour;"
        f"{10 * RATELIMIT_LIMIT_MULTIPLIER}/second"
    )

    # 生产环境 PostgreSQL 连接池配置
    # 2 workers × (3 + 5) = 16 连接，安全在 PostgreSQL 默认 max_connections=100 以内
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', '3') or 3),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', '5') or 5),
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', '300') or 300),
        'pool_pre_ping': True,
    }

    # 生产环境默认启用 ProxyFix（常见部署：Nginx -> gunicorn(127.0.0.1)）
    PROXY_FIX_ENABLED = os.environ.get('PROXY_FIX_ENABLED', 'true').lower() in ['true', 'on', '1']

    # 生产环境 Nginx 接管 Gzip，Flask 层默认关闭
    ENABLE_GZIP = os.environ.get('ENABLE_GZIP', 'false').lower() in ['true', 'on', '1']

    # 生产环境必须设置密钥（不允许使用默认值，启动时由应用工厂校验）
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # 生产环境必须配置 Redis（多 worker 共享缓存/限流/队列，启动时由应用工厂校验）
    REDIS_URL = os.environ.get('REDIS_URL')

    # 强制限流存储使用 Redis（多 worker 共享计数）
    RATELIMIT_STORAGE_URI = REDIS_URL
    RATELIMIT_STORAGE_URL = REDIS_URL

    # 科目/统计缓存 TTL 调优（科目数据极少变化）
    QUIZ_CACHE_TTL_SUBJECTS_SECONDS = int(os.environ.get('QUIZ_CACHE_TTL_SUBJECTS_SECONDS', '300') or 300)
    QUIZ_CACHE_TTL_SUBJECTS_META_SECONDS = int(os.environ.get('QUIZ_CACHE_TTL_SUBJECTS_META_SECONDS', '300') or 300)
    QUIZ_CACHE_TTL_COUNTS_SECONDS = int(os.environ.get('QUIZ_CACHE_TTL_COUNTS_SECONDS', '120') or 120)

    # 生产环境默认大幅放宽全局限流；具体路由上的 @limiter.limit 也会通过 TiLimiter 同步放大。
    RATELIMIT_DEFAULT = (
        _RATELIMIT_DEFAULT_RAW.strip()
        if _RATELIMIT_DEFAULT_RAW and _RATELIMIT_DEFAULT_RAW.strip()
        else _RATELIMIT_DEFAULT_FALLBACK
    )
    
    # 生产环境禁用控制台输出验证码
    MAIL_CONSOLE_OUTPUT = False
    SMS_CONSOLE_OUTPUT = False
    
    # 生产环境安全配置
    # 会话Cookie安全设置（HTTPS环境下启用）
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() in ['true', 'on', '1']
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # 防止XSS攻击
    JSONIFY_PRETTYPRINT_REGULAR = False

    # 生产环境 HTTPS 强制重定向（Flask 层备用；推荐在 Nginx 层处理）
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'false').lower() in ['true', 'on', '1']
    
    # 生产环境日志级别
    LOG_LEVEL = logging.INFO


class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TESTING = True

    # 测试数据库
    DATABASE_PATH = os.path.join(Config.DATA_DIR, 'instance', 'test.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(Config.DATA_DIR, 'instance', 'test.db')}"

    # 测试环境使用内存限流（无需 Redis）
    RATELIMIT_STORAGE_URI = 'memory://'
    RATELIMIT_STORAGE_URL = 'memory://'

    # 测试环境禁用 RQ 任务队列（同步降级）
    RQ_DISABLED = True

    # 测试环境禁用外部服务
    MAIL_ENABLED = False
    SMS_ENABLED = False


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
