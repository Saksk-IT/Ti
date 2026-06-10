# -*- coding: utf-8 -*-
"""
微信小程序码生成服务（getwxacodeunlimit）
用于 Web 扫码登录生成小程序码图片。
"""
from __future__ import annotations

import time
from typing import Optional

import requests
from flask import current_app


_ACCESS_TOKEN_CACHE = {
    "appid": None,  # type: Optional[str]
    "token": None,  # type: Optional[str]
    "expires_at": 0.0,  # unix seconds
}


class WechatMiniCodeService:
    @staticmethod
    def _get_appid_secret() -> tuple[str, str]:
        from app.modules.admin.services.system_config_service import SystemConfigService

        cfg = SystemConfigService.get_wechat_miniprogram_config()
        appid = cfg.get("appid")
        secret = cfg.get("secret")
        if not appid or not secret:
            raise ValueError("微信小程序配置缺失：WECHAT_APPID / WECHAT_SECRET")
        return str(appid), str(secret)

    @staticmethod
    def get_access_token() -> str:
        now = time.time()
        appid, secret = WechatMiniCodeService._get_appid_secret()
        cached = _ACCESS_TOKEN_CACHE.get("token")
        expires_at = float(_ACCESS_TOKEN_CACHE.get("expires_at") or 0)
        cached_appid = _ACCESS_TOKEN_CACHE.get("appid")
        if cached and cached_appid == appid and now < (expires_at - 60):
            return str(cached)

        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {"grant_type": "client_credential", "appid": appid, "secret": secret}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if "errcode" in data:
            raise RuntimeError(f"获取微信 access_token 失败: {data.get('errmsg')} (errcode={data.get('errcode')})")

        token = data.get("access_token")
        expires_in = int(data.get("expires_in") or 0)
        if not token or expires_in <= 0:
            raise RuntimeError("获取微信 access_token 失败: 返回数据异常")

        _ACCESS_TOKEN_CACHE.update({
            "appid": appid,
            "token": token,
            "expires_at": now + max(0, expires_in),
        })
        return str(token)

    @staticmethod
    def get_unlimited_code(scene: str, page: Optional[str] = None) -> bytes:
        """
        获取小程序码（不限量）
        - scene 最长 32 字符
        - page 不带 / 开头，示例: pages/web-login/web-login
        """
        if not scene or len(scene) > 32:
            raise ValueError("scene 无效或超过 32 字符")
        if page:
            page = str(page).strip()
        if page and page.startswith("/"):
            page = page.lstrip("/")

        token = WechatMiniCodeService.get_access_token()
        url = f"https://api.weixin.qq.com/wxa/getwxacodeunlimit?access_token={token}"
        from app.modules.admin.services.system_config_service import SystemConfigService

        cfg = SystemConfigService.get_wechat_miniprogram_config()
        env_version = (cfg.get("minicode_env_version") or "").strip()
        if not env_version:
            env_version = "develop" if bool(current_app.config.get("DEBUG") or current_app.debug) else "release"
        if env_version not in ("release", "trial", "develop"):
            env_version = "release"
        check_path = cfg.get("minicode_check_path")
        if check_path is None:
            # 开发/体验版常见"代码未提审导致 page 不存在"，默认不校验避免 41030
            check_path = False if env_version in ("develop", "trial") else True
        payload = {
            "scene": scene,
            "check_path": bool(check_path),
            "env_version": env_version,
            "is_hyaline": True,
        }
        if page:
            payload["page"] = page
        resp = requests.post(url, json=payload, timeout=15)
        ct = (resp.headers.get("Content-Type") or "").lower()
        if "application/json" in ct:
            data = resp.json()
            raise RuntimeError(f"生成小程序码失败: {data.get('errmsg')} (errcode={data.get('errcode')})")
        if resp.status_code != 200:
            raise RuntimeError(f"生成小程序码失败: HTTP {resp.status_code}")
        return resp.content
