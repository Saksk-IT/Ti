# -*- coding: utf-8 -*-
"""Gunicorn 生产环境配置

默认 2 workers × 4 threads = 8 并发槽位（gthread 模式）
适配 2核2G 服务器，环境变量可覆盖：GUNICORN_WORKERS, GUNICORN_THREADS
"""
import os

# Worker 配置
workers = int(os.environ.get("GUNICORN_WORKERS", 2))
threads = int(os.environ.get("GUNICORN_THREADS", 4))
worker_class = "gthread"

# 超时（AI 慢请求可能需要 25s+）
timeout = 60

# 不预加载应用：当前应用启动阶段会初始化扩展、Redis 与后台任务。
# 预加载后再 fork worker 容易继承连接/线程状态，导致生产健康检查偶发超时。
preload_app = False

# Worker 自动重启（防内存泄漏）
max_requests = 1000
max_requests_jitter = 50

# 绑定地址
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

# 日志
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
