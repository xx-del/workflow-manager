#!/usr/bin/env python3
"""
Helpers - 辅助工具函数
"""

from typing import Any, Optional
from pathlib import Path


def format_duration(seconds: int) -> str:
    """
    格式化时长
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化字符串
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}m {secs}s"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}h {mins}m"


def resolve_path(path: str, base: str = None) -> Path:
    """
    解析路径
    
    Args:
        path: 路径字符串
        base: 基准路径
        
    Returns:
        Path 对象
    """
    p = Path(path)
    
    if p.is_absolute():
        return p
    
    if base:
        return Path(base) / p
    
    return p.expanduser()


def truncate_string(s: str, max_length: int = 100) -> str:
    """
    截断字符串
    
    Args:
        s: 字符串
        max_length: 最大长度
        
    Returns:
        截断后的字符串
    """
    if not s:
        return ''
    
    if len(s) <= max_length:
        return s
    
    return s[:max_length - 3] + '...'


def safe_json_loads(s: str, default: Any = None) -> Any:
    """
    安全的 JSON 解析
    
    Args:
        s: JSON 字符串
        default: 解析失败时的默认值
        
    Returns:
        解析结果
    """
    import json
    
    try:
        return json.loads(s)
    except:
        return default


def merge_dicts(base: dict, override: dict) -> dict:
    """
    合并字典
    
    Args:
        base: 基础字典
        override: 覆盖字典
        
    Returns:
        合并后的字典
    """
    result = base.copy()
    
    for key, value in override.items():
        if (
            key in result and
            isinstance(result[key], dict) and
            isinstance(value, dict)
        ):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result
