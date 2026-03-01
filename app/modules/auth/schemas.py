# -*- coding: utf-8 -*-
"""
认证模块Schema定义
使用Pydantic进行数据验证和序列化
"""
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, Dict, Any


class SendBindCodeSchema(BaseModel):
    """发送绑定邮箱验证码Schema"""
    email: EmailStr = Field(..., description="邮箱地址")


class BindEmailSchema(BaseModel):
    """绑定邮箱Schema"""
    email: EmailStr = Field(..., description="邮箱地址")
    code: str = Field(..., min_length=4, max_length=8, description="验证码")

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """验证验证码格式"""
        if not v.isdigit():
            raise ValueError('验证码必须是纯数字')
        return v


class SendLoginCodeSchema(BaseModel):
    """发送登录验证码Schema"""
    email: EmailStr = Field(..., description="邮箱地址")


class EmailLoginSchema(BaseModel):
    """邮箱验证码登录Schema"""
    email: EmailStr = Field(..., description="邮箱地址")
    code: str = Field(..., min_length=4, max_length=8, description="验证码")

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """验证验证码格式"""
        if not v.isdigit():
            raise ValueError('验证码必须是纯数字')
        return v


class LoginSchema(BaseModel):
    """登录Schema（仅支持邮箱或手机号）"""
    username: str = Field(..., description="邮箱或手机号")
    password: str = Field(..., min_length=1, description="密码")
    remember: bool = Field(default=False, description="保持登录")
    redirect: Optional[str] = Field(default=None, description="登录后重定向地址")


class BindEmailResponseSchema(BaseModel):
    """绑定邮箱响应Schema"""
    email: str = Field(..., description="绑定的邮箱地址")
    email_verified: bool = Field(..., description="是否已验证")
    
    class Config:
        from_attributes = True


class SendForgotPasswordCodeSchema(BaseModel):
    """发送忘记密码验证码Schema"""
    email: EmailStr = Field(..., description="邮箱地址")


class ResetPasswordSchema(BaseModel):
    """重置密码Schema"""
    email: EmailStr = Field(..., description="邮箱地址")
    code: str = Field(..., min_length=4, max_length=8, description="验证码")
    new_password: str = Field(..., min_length=8, description="新密码")

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """验证验证码格式"""
        if not v.isdigit():
            raise ValueError('验证码必须是纯数字')
        return v
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        return v


class WechatLoginSchema(BaseModel):
    """微信登录Schema"""
    code: str = Field(..., description="微信登录code")
    user_info: Optional[Dict[str, Any]] = Field(None, description="微信用户信息（可选）")
    allow_create: bool = Field(default=True, description="未绑定时是否允许自动创建账号")


# ============================================================================
# 手机号相关 Schema
# ============================================================================

def _validate_phone(v: str) -> str:
    """校验中国大陆手机号（11 位数字，1 开头）"""
    v = v.strip()
    if not v.isdigit() or len(v) != 11 or not v.startswith('1'):
        raise ValueError('请输入正确的手机号')
    return v


class SendPhoneCodeSchema(BaseModel):
    """发送手机验证码Schema"""
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _validate_phone(v)


class PhoneLoginSchema(BaseModel):
    """手机验证码登录Schema"""
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    code: str = Field(..., min_length=4, max_length=8, description="验证码")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _validate_phone(v)

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError('验证码必须是纯数字')
        return v


class BindPhoneSchema(BaseModel):
    """绑定手机号Schema"""
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    code: str = Field(..., min_length=4, max_length=8, description="验证码")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _validate_phone(v)

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError('验证码必须是纯数字')
        return v


class PhoneResetPasswordSchema(BaseModel):
    """手机号重置密码Schema"""
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    code: str = Field(..., min_length=4, max_length=8, description="验证码")
    new_password: str = Field(..., min_length=8, description="新密码")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _validate_phone(v)

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError('验证码必须是纯数字')
        return v

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        return v
