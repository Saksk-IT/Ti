# -*- coding: utf-8 -*-
import os

from flask import abort, current_app, render_template, send_file

from app.modules.main.services.export_extension_package import (
    PACKAGE_NAME,
    build_export_extension_package,
)
from .bp import main_pages_bp


_RESOURCE_PACKAGE = {
    "filename": PACKAGE_NAME,
    "title": "SAK 题库导出助手扩展",
    "kind": "Chrome / Edge 未打包扩展",
    "download_key": "export-helper",
}
_LEGACY_RESOURCE_KEYS = {"xuexitong", "pta", _RESOURCE_PACKAGE["download_key"]}


@main_pages_bp.route("/resources")
def resources_page():
    return render_template("main/resources/resources.html", resource=_RESOURCE_PACKAGE)


@main_pages_bp.route("/resources/download/<string:key>")
def resources_download(key: str):
    normalized_key = str(key or "").strip().lower()
    if normalized_key not in _LEGACY_RESOURCE_KEYS:
        abort(404)

    directory = os.path.join(current_app.root_path, "..")
    try:
        package = build_export_extension_package(directory)
    except FileNotFoundError:
        current_app.logger.exception("扩展资源包构建失败")
        abort(404)

    resp = send_file(
        package.buffer,
        as_attachment=True,
        download_name=package.filename,
        mimetype="application/zip",
    )
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    return resp
