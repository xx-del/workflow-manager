#!/usr/bin/env python3
"""
工具函数模块
"""

from utils.logger import get_logger
import re
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional


def sanitize_name(name: str) -> str:
    """
    清理名称，生成有效的文件名
    """
    # 移除特殊字符
    sanitized = re.sub(r'[^\w\u4e00-\u9fff-]', '-', name)
    # 合并连续横线
    sanitized = re.sub(r'-+', '-', sanitized)
    # 移除首尾横线
    sanitized = sanitized.strip('-')
    # 转小写
    return sanitized.lower()


def generate_workflow_id(name: str) -> str:
    """
    生成唯一的工作流 ID
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M')
    hash_suffix = hashlib.md5(name.encode()).hexdigest()[:6]
    return f"{sanitize_name(name)}-{timestamp}-{hash_suffix}"


def format_date_range(start_date: str, end_date: str) -> str:
    """
    格式化日期范围
    """
    return f"{start_date}-{end_date}"


def parse_date_range(date_range: str) -> tuple[str, str]:
    """
    解析日期范围
    """
    if '-' in date_range:
        parts = date_range.split('-')
        if len(parts) == 2:
            return parts[0], parts[1]
    return date_range, date_range


def get_date_placeholder(placeholder: str) -> str:
    """
    解析日期占位符

    支持：
    - {{today}}: 今天
    - {{yesterday}}: 昨天
    - {{last_n_days:N}}: 过去N天
    - {{this_week}}: 本周
    - {{this_month}}: 本月
    """
    today = datetime.now()

    if placeholder == '{{today}}':
        return today.strftime('%Y%m%d')

    elif placeholder == '{{yesterday}}':
        yesterday = today - timedelta(days=1)
        return yesterday.strftime('%Y%m%d')

    elif placeholder.startswith('{{last_n_days:'):
        match = re.search(r'{{last_n_days:(\d+)}}', placeholder)
        if match:
            n = int(match.group(1))
            start = today - timedelta(days=n)
            return f"{start.strftime('%Y%m%d')}-{today.strftime('%Y%m%d')}"

    elif placeholder == '{{this_week}}':
        start = today - timedelta(days=today.weekday())
        return f"{start.strftime('%Y%m%d')}-{today.strftime('%Y%m%d')}"

    elif placeholder == '{{this_month}}':
        start = today.replace(day=1)
        return f"{start.strftime('%Y%m%d')}-{today.strftime('%Y%m%d')}"

    return placeholder


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    截断文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def extract_urls(text: str) -> list[str]:
    """
    从文本中提取 URL
    """
    pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(pattern, text)


def extract_file_paths(text: str) -> list[str]:
    """
    从文本中提取文件路径
    """
    pattern = r'(?:^|\s)(/[a-zA-Z0-9_\-./]+)'
    matches = re.findall(pattern, text)
    return [m.strip() for m in matches if m.strip()]


def is_safe_command(command: str) -> bool:
    """
    检查命令是否安全（简单规则）
    """
    dangerous_patterns = [
        r'rm\s+-rf\s+/',
        r'mkfs',
        r'dd\s+if=',
        r':(){:|:&};:',
        r'chmod\s+777\s+/',
        r'wget.*\|\s*bash',
        r'curl.*\|\s*bash',
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return False

    return True


def merge_dicts(base: dict, override: dict) -> dict:
    """
    深度合并字典
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def main():
    """测试函数"""
    # 测试日期占位符
    self.logger.info(f"today: {get_date_placeholder('{{today}}')}")
    self.logger.info(f"yesterday: {get_date_placeholder('{{yesterday}}')}")
    self.logger.info(f"last_7_days: {get_date_placeholder('{{last_n_days:7}}')}")

    # 测试名称清理
    self.logger.info(f"sanitized: {sanitize_name('数据 采集/处理 @#$% 工作流')}")


if __name__ == "__main__":
    main()
