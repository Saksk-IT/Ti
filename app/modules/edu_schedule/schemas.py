# -*- coding: utf-8 -*-
"""教务课表 API 输入校验。"""

from __future__ import annotations

import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


_ACCOUNT_RE = re.compile(r"^[A-Za-z0-9_.@-]{3,64}$")
_TERM_VALUES = {"3", "12", "16"}


class EduScheduleCredentialSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        text = (value or "").strip()
        if not _ACCOUNT_RE.fullmatch(text):
            raise ValueError("教务账号格式不正确")
        return text


class EduScheduleTermSchema(BaseModel):
    xnm: str = Field(..., min_length=4, max_length=4)
    xqm: str = Field(..., min_length=1, max_length=8)

    @field_validator("xnm")
    @classmethod
    def validate_xnm(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text.isdigit():
            raise ValueError("学年必须是 4 位年份")
        year = int(text)
        if year < 2000 or year > 2100:
            raise ValueError("学年超出允许范围")
        return text

    @field_validator("xqm")
    @classmethod
    def validate_xqm(cls, value: str) -> str:
        text = str(value or "").strip()
        if text not in _TERM_VALUES:
            raise ValueError("学期参数不正确")
        return text


class EduScheduleQuerySchema(BaseModel):
    terms: List[EduScheduleTermSchema] = Field(..., min_length=1, max_length=12)
    username: Optional[str] = Field(default=None, min_length=3, max_length=64)
    password: Optional[str] = Field(default=None, min_length=1, max_length=128)
    remember: bool = Field(default=False)

    @field_validator("username")
    @classmethod
    def validate_optional_username(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        text = value.strip()
        if not _ACCOUNT_RE.fullmatch(text):
            raise ValueError("教务账号格式不正确")
        return text

    @model_validator(mode="after")
    def validate_credential_pair(self):
        if bool(self.username) != bool(self.password):
            raise ValueError("教务账号和密码需同时填写")
        return self
