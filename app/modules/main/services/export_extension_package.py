# -*- coding: utf-8 -*-
"""Build the downloadable browser extension package for question export scripts."""
from __future__ import annotations

import io
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path


PACKAGE_NAME = "SAK题库导出助手扩展.zip"
EXTENSION_DIR = Path("app/modules/main/resources/export_extension")
SCRIPT_SOURCES = (
    "content/xuexitong-export.js",
    "content/pta-export.js",
)
REQUIRED_EXTENSION_FILES = (
    "manifest.json",
    "README.md",
    "content/userscript-compat.js",
)
VENDOR_FILES = (
    "vendor/docx.min.js",
    "vendor/docx.LICENSE.txt",
    "vendor/FileSaver.min.js",
    "vendor/FileSaver.LICENSE.md",
    "vendor/xlsx.full.min.js",
    "vendor/xlsx.LICENSE",
    "vendor/jspdf.umd.min.js",
    "vendor/jspdf.LICENSE",
    "vendor/html2canvas.min.js",
    "vendor/html2canvas.LICENSE",
)


@dataclass(frozen=True)
class ExtensionPackage:
    filename: str
    buffer: io.BytesIO


def build_export_extension_package(repo_root: str | os.PathLike[str]) -> ExtensionPackage:
    """Create a zip package that can be extracted and loaded as an unpacked extension."""
    root = Path(repo_root).resolve()
    extension_dir = root / EXTENSION_DIR
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for relative in REQUIRED_EXTENSION_FILES:
            _write_file(zf, extension_dir / relative, relative)
        for relative in VENDOR_FILES:
            _write_file(zf, extension_dir / relative, relative)
        for relative in SCRIPT_SOURCES:
            _write_file(zf, extension_dir / relative, relative)

    zip_buffer.seek(0)
    return ExtensionPackage(filename=PACKAGE_NAME, buffer=zip_buffer)


def _write_file(zf: zipfile.ZipFile, file_path: Path, archive_name: str) -> None:
    if not file_path.is_file():
        raise FileNotFoundError(f"扩展资源文件不存在：{file_path}")
    zf.write(file_path, archive_name)
