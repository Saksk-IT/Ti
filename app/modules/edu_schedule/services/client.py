# -*- coding: utf-8 -*-
"""正方教务系统客户端。"""

from __future__ import annotations

import base64
import html
import json
import re
import time
from dataclasses import dataclass
from http.cookiejar import Cookie
from ipaddress import ip_address, ip_network
from typing import Any, Dict
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class ScheduleClientError(RuntimeError):
    """课表客户端错误。"""


class ScheduleAuthError(ScheduleClientError):
    """上游认证失败。"""


_BLOCKED_NETWORKS = tuple(
    ip_network(net)
    for net in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    )
)

_DEFAULT_GRADE_PATH = "/cjcx/cjcx_cxDgXscj.html?doType=query&gnmkdm=N305005"
_LEGACY_GRADE_PATH = "/cjcx/cjcx_cxXsgrcj.html?doType=query&gnmkdm=N305005"


@dataclass(frozen=True)
class ClientConfig:
    enabled: bool
    use_webvpn: bool
    webvpn_base_url: str
    webvpn_login_path: str
    webvpn_username: str
    webvpn_password: str
    webvpn_cookie: str
    jwxt_base_url: str
    jwxt_login_path: str
    schedule_path: str
    grade_path: str
    request_timeout: int
    verify_tls: bool
    allowed_hosts: tuple[str, ...]


def _validate_url(url: str, allowed_hosts: tuple[str, ...]) -> str:
    text = (url or "").strip().rstrip("/")
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ScheduleClientError("上游地址配置不正确")
    host = parsed.hostname or ""
    if allowed_hosts and host not in allowed_hosts:
        raise ScheduleClientError("上游地址不在允许域名内")
    try:
        ip = ip_address(host)
        if any(ip in net for net in _BLOCKED_NETWORKS):
            raise ScheduleClientError("上游地址不允许指向内网或本机")
    except ValueError:
        pass
    return text


class JWXTClient:
    """查询教务课表的最小客户端。"""

    def __init__(self, config: Dict[str, Any]):
        allowed_hosts = tuple(config.get("allowed_hosts") or ())
        self.config = ClientConfig(
            enabled=bool(config.get("enabled")),
            use_webvpn=bool(config.get("use_webvpn")),
            webvpn_base_url=_validate_url(str(config.get("webvpn_base_url") or ""), allowed_hosts)
            if config.get("use_webvpn") and config.get("webvpn_base_url") else "",
            webvpn_login_path=str(config.get("webvpn_login_path") or "/users/sign_in"),
            webvpn_username=str(config.get("webvpn_username") or ""),
            webvpn_password=str(config.get("webvpn_password") or ""),
            webvpn_cookie=str(config.get("webvpn_cookie") or ""),
            jwxt_base_url=_validate_url(str(config.get("jwxt_base_url") or ""), allowed_hosts),
            jwxt_login_path=str(config.get("jwxt_login_path") or "/xtgl/login_slogin.html"),
            schedule_path=str(config.get("schedule_path") or "/kbcx/xskbcx_cxXsgrkb.html?gnmkdm=N253508"),
            grade_path=str(config.get("grade_path") or _DEFAULT_GRADE_PATH),
            request_timeout=int(config.get("request_timeout") or 20),
            verify_tls=bool(config.get("verify_tls", True)),
            allowed_hosts=allowed_hosts,
        )

    def fetch_schedule(self, username: str, password: str, xnm: str, xqm: str) -> Dict[str, Any]:
        if not self.config.enabled:
            raise ScheduleClientError("课表查询功能未开启")
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; TiEduSchedule/1.0)",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        if self.config.use_webvpn:
            self._prepare_webvpn(session)
        self._login_jwxt(session, username, password)
        return self._query_schedule(session, xnm, xqm)

    def fetch_grades(self, username: str, password: str, xnm: str, xqm: str) -> Dict[str, Any]:
        if not self.config.enabled:
            raise ScheduleClientError("成绩查询功能未开启")
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; TiEduSchedule/1.0)",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        if self.config.use_webvpn:
            self._prepare_webvpn(session)
        self._login_jwxt(session, username, password)
        return self._query_grades(session, xnm, xqm)

    def _request(self, session: requests.Session, method: str, url: str, **kwargs):
        follow_redirects = bool(kwargs.pop("allow_redirects", False))
        kwargs.setdefault("timeout", self.config.request_timeout)
        kwargs.setdefault("verify", self.config.verify_tls)

        current_url = url
        current_method = method
        current_kwargs = dict(kwargs)
        for _ in range(6):
            _validate_url(current_url, self.config.allowed_hosts)
            response = session.request(
                current_method,
                current_url,
                allow_redirects=False,
                **current_kwargs,
            )
            if not response.is_redirect:
                return response

            location = response.headers.get("Location", "")
            if not location:
                return response
            next_url = urljoin(current_url, location)
            _validate_url(next_url, self.config.allowed_hosts)
            if not follow_redirects:
                return response

            if response.status_code in {301, 302, 303} and current_method.upper() != "HEAD":
                current_method = "GET"
                current_kwargs = {
                    key: value
                    for key, value in current_kwargs.items()
                    if key not in {"data", "json", "files"}
                }
            current_url = next_url
        raise ScheduleClientError("上游跳转次数过多")

    def _prepare_webvpn(self, session: requests.Session) -> None:
        if self.config.webvpn_cookie:
            _load_cookie_header(session, self.config.webvpn_cookie, self.config.webvpn_base_url)
            _load_cookie_header(session, self.config.webvpn_cookie, self.config.jwxt_base_url)
            return
        if not self.config.webvpn_username or not self.config.webvpn_password:
            raise ScheduleAuthError("WebVPN 未配置可用登录态")

        login_url = urljoin(self.config.webvpn_base_url + "/", self.config.webvpn_login_path.lstrip("/"))
        page = self._request(session, "GET", login_url, allow_redirects=True)
        token = _extract_input_value(page.text, "authenticity_token")
        if not token:
            raise ScheduleAuthError("WebVPN 登录页解析失败")

        data = {
            "utf8": "✓",
            "authenticity_token": token,
            "user[login]": self.config.webvpn_username,
            "user[password]": self.config.webvpn_password,
            "user[dymatice_code]": "unknown",
            "user[otp_with_capcha]": "false",
            "commit": "登录 Login",
        }
        result = self._request(session, "POST", login_url, data=data, allow_redirects=True)
        if "用户登录" in result.text or "请输入验证码" in result.text:
            raise ScheduleAuthError("WebVPN 登录需要验证码或账号密码校验失败")

    def _login_jwxt(self, session: requests.Session, username: str, password: str) -> None:
        login_url = urljoin(self.config.jwxt_base_url.rstrip("/") + "/", self.config.jwxt_login_path.lstrip("/"))
        page = self._request(session, "GET", login_url, allow_redirects=True)
        if _looks_logged_in(page.text):
            return
        if "沈阳师范大学 WebVPN" in page.text or "WebVPN" in page.text and "用户登录" in page.text:
            raise ScheduleAuthError("WebVPN 登录态不可用")

        csrf_token = _extract_input_value(page.text, "csrftoken")
        encrypted_password = self._encrypt_jwxt_password(session, password)
        data = {"yhm": username, "mm": encrypted_password}
        if csrf_token:
            data["csrftoken"] = csrf_token

        result = self._request(session, "POST", login_url, data=data, allow_redirects=True)
        if "用户名或密码" in result.text or "登录" in result.url and "login_slogin" in result.url:
            raise ScheduleAuthError("教务系统账号或密码错误")

    def _encrypt_jwxt_password(self, session: requests.Session, password: str) -> str:
        key_url = urljoin(self.config.jwxt_base_url.rstrip("/") + "/", "xtgl/login_getPublicKey.html")
        response = self._request(session, "GET", f"{key_url}?time={int(time.time() * 1000)}", allow_redirects=True)
        try:
            data = response.json()
            modulus = int.from_bytes(base64.b64decode(data["modulus"]), "big")
            exponent = int.from_bytes(base64.b64decode(data["exponent"]), "big")
        except Exception as exc:
            raise ScheduleAuthError("教务系统登录密钥获取失败") from exc

        public_numbers = rsa.RSAPublicNumbers(exponent, modulus)
        public_key = public_numbers.public_key()
        cipher = public_key.encrypt(password.encode("utf-8"), padding.PKCS1v15())
        return base64.b64encode(cipher).decode("ascii")

    def _query_schedule(self, session: requests.Session, xnm: str, xqm: str) -> Dict[str, Any]:
        url = urljoin(self.config.jwxt_base_url.rstrip("/") + "/", self.config.schedule_path.lstrip("/"))
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }
        data = {"xnm": xnm, "xqm": xqm, "kzlx": "ck", "xsdm": "", "kclbdm": "", "kclxdm": ""}
        response = self._request(session, "POST", url, headers=headers, data=data, allow_redirects=True)
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise ScheduleClientError("教务课表返回格式不正确") from exc
        if not isinstance(payload, dict) or "kbList" not in payload:
            raise ScheduleClientError("教务课表数据不完整")
        return payload

    def _query_grades(self, session: requests.Session, xnm: str, xqm: str) -> Dict[str, Any]:
        data = {
            "xnm": xnm,
            "xqm": xqm,
            "sfzgcj": "",
            "kcbj": "",
            "pkey": "",
            "_search": "false",
            "nd": str(int(time.time() * 1000)),
            "queryModel.showCount": "100",
            "queryModel.currentPage": "1",
            "queryModel.sortName": " ",
            "queryModel.sortOrder": "asc",
            "time": "0",
        }
        last_error: Exception | None = None
        for grade_path in _grade_path_candidates(self.config.grade_path):
            url = urljoin(self.config.jwxt_base_url.rstrip("/") + "/", grade_path.lstrip("/"))
            headers = {
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Origin": _origin_from_url(url),
                "Referer": urljoin(
                    self.config.jwxt_base_url.rstrip("/") + "/",
                    _grade_page_path(grade_path).lstrip("/"),
                ),
            }
            response = self._request(session, "POST", url, headers=headers, data=data, allow_redirects=True)
            try:
                payload = response.json()
            except json.JSONDecodeError as exc:
                last_error = exc
                continue
            if isinstance(payload, dict) and isinstance(payload.get("items"), list):
                return payload
            last_error = ScheduleClientError("教务成绩数据不完整")

        raise ScheduleClientError("教务成绩返回格式不正确") from last_error


def _extract_input_value(html_text: str, name: str) -> str:
    pattern = re.compile(rf'name=["\']{re.escape(name)}["\'][^>]*value=["\']([^"\']*)["\']', re.I)
    match = pattern.search(html_text or "")
    if match:
        return html.unescape(match.group(1))
    pattern = re.compile(rf'value=["\']([^"\']*)["\'][^>]*name=["\']{re.escape(name)}["\']', re.I)
    match = pattern.search(html_text or "")
    return html.unescape(match.group(1)) if match else ""


def _looks_logged_in(html_text: str) -> bool:
    text = html_text or ""
    return "login_slogin" not in text and ("退出" in text or "个人信息" in text or "jwglxt" in text)


def _grade_path_candidates(configured_path: str) -> tuple[str, ...]:
    primary = (configured_path or "").strip() or _DEFAULT_GRADE_PATH
    candidates = [primary, _DEFAULT_GRADE_PATH, _LEGACY_GRADE_PATH]
    result = []
    seen = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        result.append(path)
    return tuple(result)


def _grade_page_path(query_path: str) -> str:
    parsed = urlparse((query_path or "").strip() or _DEFAULT_GRADE_PATH)
    params = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key != "doType"]
    if not any(key == "layout" for key, _ in params):
        params.append(("layout", "default"))
    return urlunparse(("", "", parsed.path, "", urlencode(params), ""))


def _origin_from_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _load_cookie_header(session: requests.Session, cookie_header: str, base_url: str) -> None:
    domain = urlparse(base_url).hostname or ""
    for item in _normalize_cookie_header(cookie_header).split(";"):
        if "=" not in item:
            continue
        name, value = item.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        cookie = Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain=domain,
            domain_specified=True,
            domain_initial_dot=False,
            path="/",
            path_specified=True,
            secure=base_url.startswith("https://"),
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False,
        )
        session.cookies.set_cookie(cookie)


def _normalize_cookie_header(cookie_text: str) -> str:
    """兼容标准 Cookie 头和浏览器导出的 Cookie 表格。"""
    text = (cookie_text or "").strip()
    if not text:
        return ""
    if "\n" not in text and "=" in text:
        return text

    pairs = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "=" in line and "\t" not in line:
            pairs.append(line)
            continue
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) < 2:
            continue
        name = parts[0].strip()
        value = parts[1].strip()
        if not name or not re.fullmatch(r"[A-Za-z0-9_.$-]+", name):
            continue
        pairs.append(f"{name}={value}")
    return "; ".join(pairs)
