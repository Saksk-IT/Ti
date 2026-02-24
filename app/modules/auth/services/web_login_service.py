# -*- coding: utf-8 -*-
"""
Web 扫码登录（小程序确认）服务

存储复用 user_progress 作为 KV，不改数据库结构。
"""
from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any, Optional

from flask import current_app

from app.core.extensions import db
from app.models.user import User
from app.models.quiz import UserProgress
from .wechat_minicode_service import WechatMiniCodeService


WEB_LOGIN_SESSION_EXPIRE_SECONDS = 20 * 60
WEB_LOGIN_TOKEN_EXPIRE_SECONDS = 30
WECHAT_TEMP_TOKEN_EXPIRE_SECONDS = 5 * 60
WEB_WECHAT_BIND_SESSION_EXPIRE_SECONDS = 20 * 60


def _now_ms() -> int:
    return int(time.time() * 1000)


def _ms_from_now(seconds: int) -> int:
    return _now_ms() + int(seconds * 1000)


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _json_loads(raw: str) -> Any:
    return json.loads(raw) if raw else None


def _get_kv_owner_user_id() -> Optional[int]:
    preferred = int(current_app.config.get("KV_OWNER_USER_ID") or 1)
    user = User.query.get(preferred)
    if user:
        return preferred
    first = User.query.order_by(User.id.asc()).first()
    if first:
        return first.id
    return None


@dataclass
class ProgressKV:
    owner_user_id: int

    @staticmethod
    def create() -> "ProgressKV":
        owner = _get_kv_owner_user_id()
        if not owner:
            raise RuntimeError("系统未初始化用户数据（users 为空），无法创建扫码登录会话")
        return ProgressKV(owner_user_id=owner)

    def get(self, key: str) -> Optional[dict]:
        row = UserProgress.query.filter_by(
            user_id=self.owner_user_id, p_key=key
        ).first()
        if not row:
            return None
        try:
            return _json_loads(row.data)
        except Exception:
            return None

    def set(self, key: str, value: dict) -> None:
        data_json = _json_dumps(value)
        row = UserProgress.query.filter_by(
            user_id=self.owner_user_id, p_key=key
        ).first()
        if row:
            row.data = data_json
        else:
            row = UserProgress(
                user_id=self.owner_user_id, p_key=key, data=data_json
            )
            db.session.add(row)
        db.session.commit()

    def delete(self, key: str) -> None:
        UserProgress.query.filter_by(
            user_id=self.owner_user_id, p_key=key
        ).delete()
        db.session.commit()


class WebLoginService:
    @staticmethod
    def create_session(meta: Optional[dict] = None) -> dict:
        kv = ProgressKV.create()
        sid = secrets.token_hex(8)  # 16 chars
        nonce = secrets.token_hex(4)  # 8 chars
        now = _now_ms()
        data = {
            "sid": sid,
            "nonce": nonce,
            "state": "pending",
            "user_id": None,
            "created_at": now,
            "expires_at": _ms_from_now(WEB_LOGIN_SESSION_EXPIRE_SECONDS),
            "confirmed_at": None,
            "exchanged_at": None,
            "token": None,
            "token_expires_at": None,
            "meta": meta or {},
        }
        kv.set(f"web_login_session:{sid}", data)
        return data

    @staticmethod
    def get_session(sid: str) -> Optional[dict]:
        kv = ProgressKV.create()
        data = kv.get(f"web_login_session:{sid}")
        if not data:
            return None
        if int(data.get("expires_at") or 0) <= _now_ms():
            data["state"] = "expired"
            return data
        return data

    @staticmethod
    def confirm_session(sid: str, nonce: str, user_id: int) -> dict:
        kv = ProgressKV.create()
        key = f"web_login_session:{sid}"
        data = kv.get(key)
        if not data:
            raise FileNotFoundError("sid 不存在")
        if int(data.get("expires_at") or 0) <= _now_ms():
            data["state"] = "expired"
            kv.set(key, data)
            raise TimeoutError("会话已过期")
        if str(data.get("nonce") or "") != str(nonce or ""):
            raise PermissionError("nonce 无效")
        if data.get("state") in ("exchanged",):
            raise RuntimeError("会话已完成")
        data["state"] = "confirmed"
        data["user_id"] = int(user_id)
        data["confirmed_at"] = _now_ms()
        kv.set(key, data)
        return data

    @staticmethod
    def ensure_exchange_token(sid: str) -> dict:
        kv = ProgressKV.create()
        key = f"web_login_session:{sid}"
        data = kv.get(key)
        if not data:
            raise FileNotFoundError("sid 不存在")
        if int(data.get("expires_at") or 0) <= _now_ms():
            data["state"] = "expired"
            kv.set(key, data)
            raise TimeoutError("会话已过期")
        if data.get("state") != "confirmed" or not data.get("user_id"):
            return data

        token = data.get("token")
        token_expires = int(data.get("token_expires_at") or 0)
        if token and token_expires > _now_ms():
            return data

        token = secrets.token_hex(16)
        token_expires_at = _ms_from_now(WEB_LOGIN_TOKEN_EXPIRE_SECONDS)
        kv.set(
            f"web_login_token:{token}",
            {
                "token": token,
                "sid": sid,
                "user_id": int(data["user_id"]),
                "expires_at": token_expires_at,
            },
        )
        data["token"] = token
        data["token_expires_at"] = token_expires_at
        kv.set(key, data)
        return data

    @staticmethod
    def consume_exchange_token(token: str) -> dict:
        kv = ProgressKV.create()
        token_key = f"web_login_token:{token}"
        data = kv.get(token_key)
        if not data:
            raise FileNotFoundError("token 不存在")
        if int(data.get("expires_at") or 0) <= _now_ms():
            kv.delete(token_key)
            raise TimeoutError("token 已过期")
        kv.delete(token_key)
        return data

    @staticmethod
    def mark_exchanged(sid: str) -> None:
        kv = ProgressKV.create()
        key = f"web_login_session:{sid}"
        data = kv.get(key)
        if not data:
            return
        data["state"] = "exchanged"
        data["exchanged_at"] = _now_ms()
        kv.set(key, data)

    @staticmethod
    def generate_qrcode_image(session_data: dict) -> dict:
        sid = str(session_data["sid"])
        nonce = str(session_data["nonce"])
        scene = f"sid={sid}&n={nonce}"
        target_page = (current_app.config.get("WEB_LOGIN_MINICODE_PAGE") or "pages/web-login/web-login").strip()
        fallback_page = (current_app.config.get("WEB_LOGIN_MINICODE_FALLBACK_PAGE") or "pages/index/index").strip()
        session_data["page_used"] = target_page

        try:
            img = WechatMiniCodeService.get_unlimited_code(scene=scene, page=target_page)
        except Exception as e:
            msg = str(e)
            if "errcode=41030" in msg:
                current_app.logger.warning(
                    "生成小程序码 page 无效，回退到 %s（原 page=%s）: %s",
                    fallback_page,
                    target_page,
                    msg,
                )
                try:
                    img = WechatMiniCodeService.get_unlimited_code(scene=scene, page=fallback_page)
                    session_data["page_fallback"] = True
                    session_data["page_used"] = fallback_page
                except Exception as e2:
                    msg2 = str(e2)
                    if "errcode=41030" in msg2:
                        current_app.logger.warning(
                            "生成小程序码 fallback page 仍无效，改为不传 page（让微信使用默认落地页）: %s",
                            msg2,
                        )
                        img = WechatMiniCodeService.get_unlimited_code(scene=scene, page=None)
                        session_data["page_fallback"] = True
                        session_data["page_used"] = None
                    else:
                        raise
            else:
                raise

        upload_dir = current_app.config.get("UPLOAD_FOLDER") or os.path.join(current_app.root_path, "..", "..", "uploads")
        target_dir = os.path.join(str(upload_dir), "web_login")
        os.makedirs(target_dir, exist_ok=True)
        filename = f"web_login_{sid}.png"
        abs_path = os.path.join(target_dir, filename)
        with open(abs_path, "wb") as f:
            f.write(img)

        rel_url = f"/uploads/web_login/{filename}"
        session_data["qrcode_url"] = rel_url
        return session_data


class WebWechatBindService:
    """
    Web 账号管理页：绑定微信（扫码 -> 小程序确认）
    - Web 端必须已登录（session）才能创建绑定会话
    - 小程序端通过 wx.login 获取 code -> openid，确认后绑定到 web_user_id
    """

    @staticmethod
    def create_session(web_user_id: int, meta: Optional[dict] = None) -> dict:
        kv = ProgressKV.create()
        sid = secrets.token_hex(8)  # 16 chars
        nonce = secrets.token_hex(4)  # 8 chars
        now = _now_ms()
        conn_user = User.query.get(int(web_user_id))
        data = {
            "sid": sid,
            "nonce": nonce,
            "state": "pending",
            "web_user_id": int(web_user_id),
            "web_username": conn_user.username if conn_user else None,
            "created_at": now,
            "expires_at": _ms_from_now(WEB_WECHAT_BIND_SESSION_EXPIRE_SECONDS),
            "confirmed_at": None,
            "bound_at": None,
            "openid": None,
            "meta": meta or {},
        }
        kv.set(f"web_wechat_bind_session:{sid}", data)
        return data

    @staticmethod
    def get_session(sid: str) -> Optional[dict]:
        kv = ProgressKV.create()
        data = kv.get(f"web_wechat_bind_session:{sid}")
        if not data:
            return None
        if int(data.get("expires_at") or 0) <= _now_ms():
            data["state"] = "expired"
            return data
        return data

    @staticmethod
    def confirm_bind(sid: str, nonce: str, openid: str) -> dict:
        kv = ProgressKV.create()
        key = f"web_wechat_bind_session:{sid}"
        data = kv.get(key)
        if not data:
            raise FileNotFoundError("sid 不存在")
        if int(data.get("expires_at") or 0) <= _now_ms():
            data["state"] = "expired"
            kv.set(key, data)
            raise TimeoutError("会话已过期")
        if str(data.get("nonce") or "") != str(nonce or ""):
            raise PermissionError("nonce 无效")
        if data.get("state") in ("bound",):
            return data

        web_user_id = int(data.get("web_user_id") or 0)
        if not web_user_id:
            raise RuntimeError("会话数据异常")

        existing = User.query.filter(User.openid == openid).first()
        if existing and existing.id != web_user_id:
            raise RuntimeError("该微信已绑定其他账号")

        # 绑定 openid 到当前 web 用户
        try:
            target_user = User.query.get(web_user_id)
            if target_user:
                target_user.openid = openid
                db.session.commit()
            else:
                raise RuntimeError("用户不存在")
        except Exception:
            db.session.rollback()
            raise

        data["state"] = "bound"
        data["openid"] = openid
        data["confirmed_at"] = _now_ms()
        data["bound_at"] = _now_ms()
        kv.set(key, data)
        return data

    @staticmethod
    def generate_qrcode_image(session_data: dict) -> dict:
        sid = str(session_data["sid"])
        nonce = str(session_data["nonce"])

        # scene 最长 32：使用紧凑格式（B + sid + nonce）
        scene = f"B{sid}{nonce}"

        target_page = (current_app.config.get("WEB_WECHAT_BIND_MINICODE_PAGE") or "pages/web-bind/web-bind").strip()
        fallback_page = (current_app.config.get("WEB_WECHAT_BIND_MINICODE_FALLBACK_PAGE") or "pages/index/index").strip()
        session_data["page_used"] = target_page

        try:
            img = WechatMiniCodeService.get_unlimited_code(scene=scene, page=target_page)
        except Exception as e:
            msg = str(e)
            if "errcode=41030" in msg:
                current_app.logger.warning(
                    "生成微信绑定小程序码 page 无效，回退到 %s（原 page=%s）: %s",
                    fallback_page,
                    target_page,
                    msg,
                )
                try:
                    img = WechatMiniCodeService.get_unlimited_code(scene=scene, page=fallback_page)
                    session_data["page_fallback"] = True
                    session_data["page_used"] = fallback_page
                except Exception as e2:
                    msg2 = str(e2)
                    if "errcode=41030" in msg2:
                        current_app.logger.warning(
                            "生成微信绑定小程序码 fallback page 仍无效，改为不传 page: %s",
                            msg2,
                        )
                        img = WechatMiniCodeService.get_unlimited_code(scene=scene, page=None)
                        session_data["page_fallback"] = True
                        session_data["page_used"] = None
                    else:
                        raise
            else:
                raise

        upload_dir = current_app.config.get("UPLOAD_FOLDER") or os.path.join(current_app.root_path, "..", "..", "uploads")
        target_dir = os.path.join(str(upload_dir), "wechat_bind")
        os.makedirs(target_dir, exist_ok=True)
        filename = f"wechat_bind_{sid}.png"
        abs_path = os.path.join(target_dir, filename)
        with open(abs_path, "wb") as f:
            f.write(img)
        session_data["qrcode_url"] = f"/uploads/wechat_bind/{filename}"
        return session_data


class WechatTempTokenService:
    @staticmethod
    def issue(openid: str, user_info: Optional[dict] = None) -> dict:
        kv = ProgressKV.create()
        token = secrets.token_hex(16)
        data = {
            "token": token,
            "openid": openid,
            "user_info": user_info or None,
            "expires_at": _ms_from_now(WECHAT_TEMP_TOKEN_EXPIRE_SECONDS),
            "created_at": _now_ms(),
        }
        kv.set(f"wechat_temp_token:{token}", data)
        return data

    @staticmethod
    def consume(token: str) -> dict:
        kv = ProgressKV.create()
        key = f"wechat_temp_token:{token}"
        data = kv.get(key)
        if not data:
            raise FileNotFoundError("wechat_temp_token 不存在")
        if int(data.get("expires_at") or 0) <= _now_ms():
            kv.delete(key)
            raise TimeoutError("wechat_temp_token 已过期")
        kv.delete(key)
        return data

    @staticmethod
    def peek(token: str) -> Optional[dict]:
        kv = ProgressKV.create()
        data = kv.get(f"wechat_temp_token:{token}")
        if not data:
            return None
        if int(data.get("expires_at") or 0) <= _now_ms():
            return None
        return data

    @staticmethod
    def delete(token: str) -> None:
        kv = ProgressKV.create()
        kv.delete(f"wechat_temp_token:{token}")


def set_web_session(user_id: int) -> dict:
    """扫码 exchange 时写入 Web session（保持与 /api/login 一致的字段）"""
    from flask import session
    user = User.query.get(user_id)
    if not user:
        raise FileNotFoundError("用户不存在")

    session.permanent = True
    session["user_id"] = user.id
    session["username"] = user.username
    session["is_admin"] = bool(user.is_admin)
    session["is_subject_admin"] = bool(user.is_subject_admin)
    session["is_notification_admin"] = bool(user.is_notification_admin)
    session["session_version"] = user.session_version or 0
    session["remember"] = True
    return {
        'id': user.id, 'username': user.username, 'is_admin': user.is_admin,
        'session_version': user.session_version,
    }
