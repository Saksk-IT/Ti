# -*- coding: utf-8 -*-
import os

from flask import current_app, redirect, render_template, send_from_directory, session

from app.core.utils.database import get_db

from .bp import main_pages_bp


@main_pages_bp.route('/quiz_settings')
def quiz_settings_page():
    """题库设置页面"""
    return redirect('/settings')


@main_pages_bp.route('/uploads/<path:filename>')
def serve_upload(filename):
    """安全地提供上传的文件（支持音视频 Range 请求）"""
    # 注意：运行时数据目录可能通过 DATA_DIR 映射到容器/宿主机（例如 /data/uploads）。
    # 这里必须使用配置中的 UPLOAD_FOLDER，避免 /app/uploads 与实际上传目录不一致导致 404。
    directory = current_app.config.get('UPLOAD_FOLDER') or os.path.join(current_app.root_path, '..', 'uploads')
    resp = send_from_directory(directory, filename, conditional=True)
    # 让浏览器/音频组件更愿意做断点/Range 拉取（部分移动端对流式更敏感）
    resp.headers.setdefault('Accept-Ranges', 'bytes')
    return resp


@main_pages_bp.route('/about')
def about_page():
    """关于页面（占位）"""
    return redirect('/settings/about')
