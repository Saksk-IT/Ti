# -*- coding: utf-8 -*-
"""敏感凭据加密工具。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


_PREFIX = "enc:v1:"


class CredentialCryptoError(RuntimeError):
    """凭据加解密失败。"""


def _secret_material() -> str:
    secret = os.environ.get("SCHEDULE_CREDENTIAL_SECRET", "").strip()
    if not secret:
        try:
            secret = str(current_app.config.get("SCHEDULE_CREDENTIAL_SECRET") or "").strip()
        except RuntimeError:
            secret = ""
    if not secret:
        try:
            secret = str(current_app.config.get("SECRET_KEY") or "").strip()
        except RuntimeError:
            secret = os.environ.get("SECRET_KEY", "").strip()
    if not secret:
        raise CredentialCryptoError("凭据加密密钥未配置")
    return secret


def _fernet() -> Fernet:
    digest = hashlib.sha256(_secret_material().encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    text = value or ""
    token = _fernet().encrypt(text.encode("utf-8")).decode("ascii")
    return f"{_PREFIX}{token}"


def decrypt_secret(value: str) -> str:
    text = value or ""
    if not text:
        return ""
    if not text.startswith(_PREFIX):
        raise CredentialCryptoError("凭据不是受支持的密文格式")
    token = text[len(_PREFIX):].encode("ascii")
    try:
        return _fernet().decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialCryptoError("凭据解密失败") from exc


def is_encrypted_secret(value: str) -> bool:
    return bool(value) and str(value).startswith(_PREFIX)


def credential_fingerprint(value: str, *, purpose: str = "credential") -> str:
    """生成不可逆、可稳定比对的凭据标识，不保存凭据明文。"""
    normalized = str(value or "").strip()
    signing_key = hashlib.sha256(
        f"ti:{purpose}:{_secret_material()}".encode("utf-8")
    ).digest()
    return hmac.new(signing_key, normalized.encode("utf-8"), hashlib.sha256).hexdigest()
