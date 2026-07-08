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
    assert "background/import-to-bank.js" in names
    assert manifest["background"]["service_worker"] == "background/import-to-bank.js"


def test_export_helper_supports_one_click_user_bank_import(auth_client):
    response = auth_client.get("/resources/download/export-helper")

    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.data), "r") as zf:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        background = zf.read("background/import-to-bank.js").decode("utf-8")
        pta_source = zf.read("content/pta-export.js").decode("utf-8")
        xuexitong_source = zf.read("content/xuexitong-export.js").decode("utf-8")

    assert "http://localhost/*" in manifest["host_permissions"]
    assert "http://127.0.0.1/*" in manifest["host_permissions"]
    assert "/user/banks/api/" in background
    assert "/questions/import/json" in background
    assert "credentials: 'include'" in background
    assert "'X-Requested-With': 'XMLHttpRequest'" in background
    assert "SAK_IMPORT_TO_BANK_REQUEST" in background

    for source in (pta_source, xuexitong_source):
        assert "一键导入题库" in source
        assert "SAK_BANK_ID_KEY" in source
        assert "SAK_IMPORT_TO_BANK_REQUEST" in source
        assert "chrome.runtime.sendMessage" in source


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
    assert "*://pintia.cn/*" in pta_matches
    assert "*://pta.pintia.cn/*" in pta_matches
    assert "*://*.yuketang.cn/*" in pta_matches
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


def test_pta_export_script_has_page_state_prompts_and_fetch_fallbacks():
    packaged_source = Path(
        "app/modules/main/resources/export_extension/content/pta-export.js"
    ).read_text(encoding="utf-8")
    root_source = Path("PTA题目导出.js").read_text(encoding="utf-8")

    assert root_source == packaged_source

    for text in (
        "当前页面暂不支持导出",
        "请打开已支持的 PTA 题目页面、雨课堂考试结果页或 show_paper 页面后再试",
        "雨课堂登录态缺失或无权限",
        "请先在当前浏览器登录雨课堂",
        "show_paper 拉取失败",
        "可以直接打开 show_paper 页面确认接口能返回 JSON",
        "getPageSupportState",
        "buildYuketangShowPaperFetchErrorMessage",
    ):
        assert text in packaged_source


def test_legacy_script_download_keys_return_combined_extension_package(auth_client):
    for key in ("xuexitong", "pta"):
        response = auth_client.get(f"/resources/download/{key}")

        assert response.status_code == 200
        assert response.mimetype == "application/zip"
        with zipfile.ZipFile(io.BytesIO(response.data), "r") as zf:
            assert "manifest.json" in zf.namelist()
