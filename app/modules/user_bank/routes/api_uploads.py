# -*- coding: utf-8 -*-
"""用户题库上传 API。"""

from __future__ import annotations

import os
import uuid

from flask import current_app, request
from sqlalchemy import text

from app.core.extensions import db, limiter
from app.core.utils.api_response import error_response, success_response
from app.core.utils.decorators import auth_required, current_user_id

from .api_base import user_bank_api_bp


ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _file_extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def _stream_size(file_storage) -> int:
    stream = file_storage.stream
    current_pos = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(current_pos)
    return int(size)


def _detect_image_extension(head: bytes) -> str:
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(head) >= 12 and head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "webp"
    return ""


def _validate_image_file(file_storage, *, label: str):
    if not file_storage or not file_storage.filename:
        return None, "没有选择文件"

    ext = _file_extension(file_storage.filename)
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return None, "不支持的文件格式，请上传 png、jpg、jpeg、gif 或 webp 图片"

    mimetype = (file_storage.mimetype or "").lower()
    if mimetype and mimetype != "application/octet-stream" and mimetype not in ALLOWED_IMAGE_MIME_TYPES:
        return None, "文件类型不是图片"

    try:
        size = _stream_size(file_storage)
    except Exception:
        return None, "无法读取上传文件"

    if size <= 0:
        return None, "不能上传空文件"
    if size > MAX_IMAGE_BYTES:
        return None, f"{label}不能超过 5MB"

    head = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    detected_ext = _detect_image_extension(head)
    if not detected_ext:
        return None, "文件内容不是有效图片"

    return detected_ext, ""


def _save_image_file(file_storage, extension: str, *, folder: str, filename_prefix: str) -> dict:
    upload_root = current_app.config["UPLOAD_FOLDER"]
    save_dir = os.path.realpath(os.path.join(upload_root, folder))
    os.makedirs(save_dir, exist_ok=True)

    filename = f"{filename_prefix}_{uuid.uuid4().hex[:16]}.{extension}"
    filepath = os.path.realpath(os.path.join(save_dir, filename))
    if os.path.commonpath([save_dir, filepath]) != save_dir:
        raise ValueError("invalid upload path")

    file_storage.save(filepath)
    return {
        "filename": filename,
        "path": f"{folder}/{filename}",
        "url": f"/uploads/{folder}/{filename}",
    }


def _ensure_bank_owner(bank_id: int, user_id: int) -> bool:
    row = db.session.execute(
        text(
            """
            SELECT id
            FROM user_question_banks
            WHERE id = :bank_id AND user_id = :user_id AND status = 1
            """
        ),
        {"bank_id": int(bank_id), "user_id": int(user_id)},
    ).fetchone()
    return row is not None


def _handle_bank_cover_upload(user_id: int):
    file_storage = request.files.get("file") or request.files.get("cover")
    extension, message = _validate_image_file(file_storage, label="封面图片")
    if not extension:
        return error_response(message)

    try:
        saved = _save_image_file(
            file_storage,
            extension,
            folder="bank_covers",
            filename_prefix=f"bank_cover_{int(user_id)}",
        )
    except Exception as exc:
        current_app.logger.error("题库封面上传失败: %s", exc, exc_info=True)
        return error_response("上传失败，请稍后重试", 500)

    return success_response(data=saved, message="封面上传成功")


def _handle_question_image_upload(user_id: int):
    file_storage = request.files.get("file") or request.files.get("image")
    extension, message = _validate_image_file(file_storage, label="题目图片")
    if not extension:
        return error_response(message)

    try:
        saved = _save_image_file(
            file_storage,
            extension,
            folder="user_bank_question_images",
            filename_prefix=f"user_bank_question_{int(user_id)}",
        )
    except Exception as exc:
        current_app.logger.error("个人题库题目图片上传失败: %s", exc, exc_info=True)
        return error_response("上传失败，请稍后重试", 500)

    return success_response(data=saved, message="题目图片上传成功")


@user_bank_api_bp.route("/cover/upload", methods=["POST"])
@auth_required
@limiter.limit("10 per minute;200 per day")
def upload_bank_cover():
    """上传题库封面图片（创建页与编辑页共用）。"""
    user_id = int(current_user_id() or 0)
    return _handle_bank_cover_upload(user_id)


@user_bank_api_bp.route("/<int:bank_id>/cover/upload", methods=["POST"])
@auth_required
@limiter.limit("10 per minute;200 per day")
def upload_existing_bank_cover(bank_id: int):
    """上传已有题库封面图片，仅题库创建者可操作。"""
    user_id = int(current_user_id() or 0)
    if not _ensure_bank_owner(bank_id, user_id):
        return error_response("题库不存在或无权操作", 404)
    return _handle_bank_cover_upload(user_id)


@user_bank_api_bp.route("/<int:bank_id>/question-images/upload", methods=["POST"])
@auth_required
@limiter.limit("20 per minute;400 per day")
def upload_question_image(bank_id: int):
    """上传个人题库题目图片，仅题库创建者可操作。"""
    user_id = int(current_user_id() or 0)
    if not _ensure_bank_owner(bank_id, user_id):
        return error_response("题库不存在或无权操作", 404)
    return _handle_question_image_upload(user_id)
