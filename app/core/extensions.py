# -*- coding: utf-8 -*-
"""
Flask扩展初始化
"""
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# 初始化限流器（不绑定app）
limiter = Limiter(
    key_func=get_remote_address
)

# CSRF 保护（不绑定app）
csrf = CSRFProtect()

# SQLAlchemy ORM（不绑定app）
db = SQLAlchemy()

# Alembic 数据库迁移（不绑定app）
migrate = Migrate()


def init_extensions(app):
    """初始化所有扩展"""
    limiter.init_app(app)

    # CSRF 保护：保护 Web 表单，API 端点在蓝图注册后统一豁免
    csrf.init_app(app)

    # SQLAlchemy ORM
    db.init_app(app)

    # Alembic 迁移（绑定 db 实例）
    migrate.init_app(app, db)

    # CORS 配置：生产环境仅允许指定域名，开发环境允许所有来源
    cors_origins = ["https://servicewechat.com"]
    extra_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '')
    if extra_origins:
        cors_origins.extend([o.strip() for o in extra_origins.split(',') if o.strip()])
    if app.debug:
        cors_origins.extend(["http://localhost:5000", "http://127.0.0.1:5000",
                             "http://localhost:3000", "http://127.0.0.1:3000"])

    CORS(app, resources={
        r"/api/*": {
            "origins": cors_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": False
        }
    })
