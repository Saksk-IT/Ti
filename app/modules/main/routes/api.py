# -*- coding: utf-8 -*-
"""公共科目导出 API"""
from __future__ import annotations

import logging
from urllib.parse import quote

from flask import Blueprint, jsonify, request, send_file, session
from sqlalchemy import text

from app.core.extensions import db, limiter
from app.core.services.export import ExportRequest, ExportResult, fetch_export_questions
from app.core.services.export.word_exporter import generate_word
from app.core.services.export.pdf_exporter import generate_pdf

logger = logging.getLogger(__name__)

main_api_bp = Blueprint("main_api", __name__, url_prefix="/api/subjects")


@main_api_bp.route("/<int:subject_id>/export", methods=["POST"])
@limiter.limit("3/minute")
def export_subject_questions(subject_id: int):
    """导出公共科目题目为 Word 或 PDF。"""
    uid = session.get("user_id")

    # 查询科目
    row = db.session.execute(
        text("SELECT id, name FROM subjects WHERE id = :sid"),
        {"sid": subject_id},
    ).fetchone()
    if not row:
        return jsonify({"status": "error", "message": "科目不存在"}), 404

    subject_name = row._mapping["name"]

    # 解析请求体
    data = request.get_json(silent=True) or {}
    fmt = data.get("format", "word")
    if fmt not in ("word", "pdf"):
        return jsonify({"status": "error", "message": "format 仅支持 word / pdf"}), 400

    scope = data.get("scope", "all")
    if scope not in ("all", "favorites", "mistakes"):
        scope = "all"

    if scope in ("favorites", "mistakes") and not uid:
        return jsonify({"status": "error", "message": "收藏/错题范围需要登录"}), 401

    q_type = data.get("q_type", "all") or "all"
    tag = data.get("tag", "all") or "all"
    include_answer = bool(data.get("include_answer", True))

    req = ExportRequest(
        subject_id=subject_id,
        subject_name=subject_name,
        format=fmt,
        scope=scope,
        q_type=q_type,
        tag=tag,
        include_answer=include_answer,
        user_id=uid,
    )

    # 查询题目
    questions = fetch_export_questions(req)
    if not questions:
        return jsonify({"status": "error", "message": "当前筛选条件下没有题目"}), 400

    # 生成文件
    try:
        if fmt == "word":
            result: ExportResult = generate_word(req, questions)
        else:
            result = generate_pdf(req, questions)
    except RuntimeError as e:
        logger.error("导出失败: %s", e, exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        logger.error("导出失败: %s", e, exc_info=True)
        return jsonify({"status": "error", "message": "导出生成失败，请稍后重试"}), 500

    response = send_file(
        result.buffer,
        as_attachment=True,
        download_name=result.filename,
        mimetype=result.content_type,
    )
    # 手动设置 RFC 5987 编码的 Content-Disposition，确保中文文件名正常显示
    encoded = quote(result.filename, safe="")
    response.headers["Content-Disposition"] = (
        f"attachment; filename=\"{result.filename}\"; filename*=UTF-8''{encoded}"
    )
    return response
