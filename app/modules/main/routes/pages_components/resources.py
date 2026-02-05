# -*- coding: utf-8 -*-
import os

from flask import abort, current_app, render_template, send_from_directory

from .bp import main_pages_bp


_RESOURCES = {
    "xuexitong": {
        "filename": "学习通作业导出助手.user.js",
        "title": "学习通作业导出助手",
        "kind": "油猴/Tampermonkey 脚本",
    },
    "pta": {
        "filename": "PTA题目导出.js",
        "title": "PTA题目导出",
        "kind": "JS 脚本",
    },
}


@main_pages_bp.route("/resources")
def resources_page():
    return render_template("main/resources/resources.html", resources=_RESOURCES)


@main_pages_bp.route("/resources/download/<string:key>")
def resources_download(key: str):
    item = _RESOURCES.get(str(key or "").strip().lower())
    if not item:
        abort(404)

    directory = os.path.join(current_app.root_path, "..")
    filename = item["filename"]
    full_path = os.path.join(directory, filename)
    if not os.path.isfile(full_path):
        abort(404)

    resp = send_from_directory(
        directory,
        filename,
        as_attachment=True,
        download_name=filename,
        conditional=True,
    )
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    return resp
