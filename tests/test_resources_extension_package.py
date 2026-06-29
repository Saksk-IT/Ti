# -*- coding: utf-8 -*-
import io
import json
import zipfile
from pathlib import Path


def test_resources_page_promotes_single_extension_package(auth_client):
    response = auth_client.get("/resources")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "SAK 题库导出助手扩展" in body
    assert "雨课堂题目导出" in body
    assert "下载扩展包" in body
    assert "/resources/download/export-helper" in body
    assert "/resources/download/xuexitong" not in body
    assert "/resources/download/pta" not in body


def test_export_helper_download_contains_loadable_extension_files(auth_client):
    response = auth_client.get("/resources/download/export-helper")

    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert "SAK" in response.headers.get("Content-Disposition", "")

    with zipfile.ZipFile(io.BytesIO(response.data), "r") as zf:
        names = set(zf.namelist())
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))

    assert manifest["manifest_version"] == 3
    assert manifest["name"] == "SAK 题库导出助手"
    assert "content/userscript-compat.js" in names
    assert "content/xuexitong-export.js" in names
    assert "content/pta-export.js" in names
    assert "vendor/docx.min.js" in names
    assert "vendor/FileSaver.min.js" in names
    assert "vendor/xlsx.full.min.js" in names
    assert "vendor/jspdf.umd.min.js" in names
    assert "vendor/html2canvas.min.js" in names


def test_export_helper_manifest_supports_yuketang_exam_pages(auth_client):
    response = auth_client.get("/resources/download/export-helper")

    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.data), "r") as zf:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))

    assert "*://*.yuketang.cn/*" in manifest["host_permissions"]

    pta_scripts = [
        script
        for script in manifest["content_scripts"]
        if "content/pta-export.js" in script.get("js", [])
    ]
    pta_matches = {
        match
        for script in pta_scripts
        for match in script.get("matches", [])
    }
    assert "*://*.yuketang.cn/result/*" in pta_matches
    assert "*://*.yuketang.cn/exam_room/show_paper*" in pta_matches


def test_pta_export_script_contains_yuketang_adapter_without_bundled_token():
    source = (
        Path("app/modules/main/resources/export_extension/content/pta-export.js")
        .read_text(encoding="utf-8")
    )

    assert "fetchYuketangShowPaperPayload" in source
    assert "buildYuketangPortableJson" in source
    assert "credentials: 'include'" in source
    assert "x_access_token" not in source


def test_legacy_script_download_keys_return_combined_extension_package(auth_client):
    for key in ("xuexitong", "pta"):
        response = auth_client.get(f"/resources/download/{key}")

        assert response.status_code == 200
        assert response.mimetype == "application/zip"
        with zipfile.ZipFile(io.BytesIO(response.data), "r") as zf:
            assert "manifest.json" in zf.namelist()
