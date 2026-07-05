# -*- coding: utf-8 -*-
"""
管理后台 API Schema 定义（Pydantic）
"""
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional


class SubjectIdsSchema(BaseModel):
    """科目ID列表Schema"""
    subject_ids: List[int] = Field(..., description="科目ID列表", min_length=1)
    
    @field_validator('subject_ids')
    @classmethod
    def validate_subject_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError('科目ID列表不能为空')
        return v


class BatchSubjectActionSchema(BaseModel):
    """批量科目操作Schema"""
    action: str = Field(..., description="操作类型")
    subject_ids: List[int] = Field(..., description="科目ID列表", min_length=1)
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v not in ['restrict', 'unrestrict']:
            raise ValueError('操作类型必须是 restrict 或 unrestrict')
        return v


class BatchUserSubjectActionSchema(BaseModel):
    """批量用户科目操作Schema"""
    action: str = Field(..., description="操作类型")
    user_ids: List[int] = Field(..., description="用户ID列表", min_length=1)
    subject_ids: List[int] = Field(..., description="科目ID列表", min_length=1)
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v not in ['restrict', 'unrestrict']:
            raise ValueError('操作类型必须是 restrict 或 unrestrict')
        return v


class SystemConfigUpdateSchema(BaseModel):
    """系统配置更新Schema"""
    config_value: str = Field(..., description="配置值")
    description: Optional[str] = Field(None, description="配置说明")


class BatchResetQuizCountSchema(BaseModel):
    """批量重置刷题数Schema"""
    user_ids: List[int] = Field(..., description="用户ID列表", min_length=1)


class AIChangeRecordCreateSchema(BaseModel):
    """AI 改动记录写入 Schema。"""

    source: Optional[str] = Field("codex", description="调用来源", max_length=32)
    external_id: Optional[str] = Field(None, description="外部幂等/追踪ID", max_length=128)
    category: Optional[str] = Field(None, description="bug 或 feature")
    title: Optional[str] = Field(None, description="改动标题", max_length=200)
    summary: Optional[str] = Field(None, description="改动摘要", max_length=500)
    changes: List[str] = Field(default_factory=list, description="改动要点")
    files: List[str] = Field(default_factory=list, description="相关文件")
    detail: Dict[str, Any] = Field(default_factory=dict, description="结构化详情")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")




