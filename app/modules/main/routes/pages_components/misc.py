# -*- coding: utf-8 -*-
import os

from flask import abort, current_app, redirect, render_template, send_from_directory, session

from .bp import main_pages_bp


@main_pages_bp.route('/quiz_settings')
def quiz_settings_page():
    """题库设置页面"""
    return redirect('/settings')


@main_pages_bp.route('/uploads/<path:filename>')
def serve_upload(filename):
    """安全地提供上传的文件（支持音视频 Range 请求）"""
    # 路径遍历防护：拒绝包含 .. 的路径
    if '..' in filename or filename.startswith('/'):
        abort(400)
    directory = current_app.config.get('UPLOAD_FOLDER') or os.path.join(current_app.root_path, '..', 'uploads')
    resp = send_from_directory(directory, filename, conditional=True)
    resp.headers.setdefault('Accept-Ranges', 'bytes')
    return resp


@main_pages_bp.route('/about')
def about_page():
    """关于页面（占位）"""
    return redirect('/settings/about')
