# -*- coding: utf-8 -*-
"""论坛图片上传 API"""
import os
import uuid

from flask import jsonify, request, current_app

from ..api import forum_api_bp
from app.core.extensions import limiter
from app.core.utils.decorators import auth_required

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def _allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@forum_api_bp.route('/upload/image', methods=['POST'])
@auth_required
@limiter.limit("10 per minute;200 per day")
def api_upload_image():
    """上传论坛图片"""
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': '未选择文件'}), 400

        file = request.files['file']
        if not file or not file.filename:
            return jsonify({'status': 'error', 'message': '未选择文件'}), 400

        if not _allowed_file(file.filename):
            return jsonify({'status': 'error', 'message': '不支持的文件格式'}), 400

        # 检查文件大小
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_FILE_SIZE:
            return jsonify({'status': 'error', 'message': '文件大小不能超过5MB'}), 400

        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"forum_{uuid.uuid4().hex[:12]}.{ext}"
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'forum')
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        url = f'/uploads/forum/{filename}'
        return jsonify({'status': 'success', 'data': {'url': url, 'filename': filename}})
    except Exception as e:
        current_app.logger.error(f"上传图片失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '上传失败'}), 500
