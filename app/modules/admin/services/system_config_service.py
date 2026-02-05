# -*- coding: utf-8 -*-
"""
系统配置管理服务
"""
import os
import threading
import time
from typing import Dict, Any, List, Optional
from app.core.utils.database import get_db


_CACHE_TTL_SECONDS = int(os.environ.get('SYSTEM_CONFIG_CACHE_TTL_SECONDS', '15') or 15)
_CACHE_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {}
_MISSING = object()


def _now() -> float:
    return time.monotonic()


def _cache_get(key: str):
    ttl = _CACHE_TTL_SECONDS
    if ttl <= 0:
        return _MISSING

    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if not item:
            return _MISSING
        exp_at, value = item
        if exp_at < _now():
            _CACHE.pop(key, None)
            return _MISSING
        return value


def _cache_set(key: str, value: Any):
    ttl = _CACHE_TTL_SECONDS
    if ttl <= 0:
        return
    with _CACHE_LOCK:
        _CACHE[key] = (_now() + float(ttl), value)


def _cache_clear():
    with _CACHE_LOCK:
        _CACHE.clear()


class SystemConfigService:
    """系统配置管理服务类"""
    
    @staticmethod
    def get_all_configs() -> List[Dict[str, Any]]:
        """
        获取所有系统配置
        
        Returns:
            配置列表
        """
        cached = _cache_get('__all__')
        if cached is not _MISSING and isinstance(cached, list):
            return [dict(x) for x in cached]

        conn = get_db()
        rows = conn.execute(
            'SELECT * FROM system_config ORDER BY config_key'
        ).fetchall()
        
        result = [dict(row) for row in rows]
        _cache_set('__all__', result)
        return result
    
    @staticmethod
    def get_config(config_key: str) -> Optional[Dict[str, Any]]:
        """
        获取指定配置
        
        Args:
            config_key: 配置键
            
        Returns:
            配置字典，如果不存在返回None
        """
        ck = f'key:{config_key}'
        cached = _cache_get(ck)
        if cached is not _MISSING:
            return dict(cached) if isinstance(cached, dict) else None

        conn = get_db()
        row = conn.execute(
            'SELECT * FROM system_config WHERE config_key = ?',
            (config_key,)
        ).fetchone()
        
        result = dict(row) if row else None
        _cache_set(ck, result)
        return result
    
    @staticmethod
    def update_config(
        config_key: str,
        config_value: str,
        description: Optional[str] = None,
        admin_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        更新系统配置
        
        Args:
            config_key: 配置键
            config_value: 配置值
            description: 配置说明（可选）
            admin_id: 操作的管理员ID（可选）
            
        Returns:
            更新后的配置字典
        """
        conn = get_db()
        
        # 检查配置是否存在
        existing = conn.execute(
            'SELECT id FROM system_config WHERE config_key = ?',
            (config_key,)
        ).fetchone()
        
        if existing:
            # 更新现有配置
            if description:
                conn.execute(
                    '''UPDATE system_config 
                       SET config_value = ?, description = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ?
                       WHERE config_key = ?''',
                    (config_value, description, admin_id, config_key)
                )
            else:
                conn.execute(
                    '''UPDATE system_config 
                       SET config_value = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ?
                       WHERE config_key = ?''',
                    (config_value, admin_id, config_key)
                )
        else:
            # 创建新配置
            conn.execute(
                '''INSERT INTO system_config 
                   (config_key, config_value, description, updated_by)
                   VALUES (?, ?, ?, ?)''',
                (config_key, config_value, description or '', admin_id)
            )
        
        conn.commit()
        _cache_clear()
        
        return SystemConfigService.get_config(config_key)
    
    @staticmethod
    def get_quiz_limit_config() -> Dict[str, Any]:
        """
        获取刷题限制相关配置
        
        Returns:
            包含功能开关和限制数量的字典
        """
        enabled_config = SystemConfigService.get_config('quiz_limit_enabled')
        count_config = SystemConfigService.get_config('quiz_limit_count')
        
        return {
            'quiz_limit_enabled': enabled_config['config_value'] == '1' if enabled_config else False,
            'quiz_limit_count': int(count_config['config_value']) if count_config else 100
        }
    
    @staticmethod
    def get_email_bind_required_config() -> bool:
        """
        获取邮箱绑定是否必需的配置
        
        Returns:
            如果邮箱绑定必需返回True，否则返回False（默认True，保持向后兼容）
        """
        config = SystemConfigService.get_config('email_bind_required')
        if config:
            return config['config_value'] == '1'
        # 默认返回True，保持向后兼容（原有行为）
        return True




