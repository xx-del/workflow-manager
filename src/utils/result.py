#!/usr/bin/env python3
"""
Result - 统一返回格式

职责：
1. 标准化所有模块的返回格式
2. 提供 success/status/data/error/message 统一结构
3. to_dict() 方法保持向后兼容
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from enum import Enum
from datetime import datetime


class Status(str, Enum):
    """状态枚举"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    NOT_FOUND = 'not_found'
    EXECUTION_REQUIRED = 'execution_required'
    CANCELLED = 'cancelled'
    TIMEOUT = 'timeout'


@dataclass
class Result:
    """
    统一返回结果类

    Attributes:
        success: 是否成功
        status: 状态枚举值
        data: 返回数据
        error: 错误信息
        message: 提示信息
        metadata: 元数据（自动添加时间戳）
    """
    success: bool
    status: Status
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """自动添加时间戳"""
        if 'timestamp' not in self.metadata:
            self.metadata['timestamp'] = datetime.now().isoformat()

    @classmethod
    def ok(cls, data: Optional[Dict] = None, message: Optional[str] = None, **metadata) -> 'Result':
        """
        创建成功结果

        Args:
            data: 返回数据
            message: 提示信息
            **metadata: 额外元数据

        Returns:
            Result 实例
        """
        return cls(
            success=True,
            status=Status.COMPLETED,
            data=data,
            message=message,
            metadata=metadata
        )

    @classmethod
    def fail(cls, error: str, status: Status = Status.FAILED, data: Optional[Dict] = None) -> 'Result':
        """
        创建失败结果

        Args:
            error: 错误信息
            status: 状态（默认 FAILED）
            data: 可选的附加数据

        Returns:
            Result 实例
        """
        return cls(
            success=False,
            status=status,
            error=error,
            data=data
        )

    @classmethod
    def not_found(cls, message: str = "资源未找到") -> 'Result':
        """
        创建未找到结果

        Args:
            message: 提示信息

        Returns:
            Result 实例
        """
        return cls(
            success=False,
            status=Status.NOT_FOUND,
            error=message
        )

    @classmethod
    def pending(cls, message: str = "处理中", data: Optional[Dict] = None) -> 'Result':
        """
        创建待处理结果

        Args:
            message: 提示信息
            data: 可选数据

        Returns:
            Result 实例
        """
        return cls(
            success=True,
            status=Status.PENDING,
            message=message,
            data=data
        )

    @classmethod
    def running(cls, message: str = "运行中", data: Optional[Dict] = None) -> 'Result':
        """
        创建运行中结果

        Args:
            message: 提示信息
            data: 可选数据

        Returns:
            Result 实例
        """
        return cls(
            success=True,
            status=Status.RUNNING,
            message=message,
            data=data
        )

    @classmethod
    def execution_required(cls, message: str = "需要执行", data: Optional[Dict] = None) -> 'Result':
        """
        创建需要执行结果

        Args:
            message: 提示信息
            data: 可选数据

        Returns:
            Result 实例
        """
        return cls(
            success=True,
            status=Status.EXECUTION_REQUIRED,
            message=message,
            data=data
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式（向后兼容）

        Returns:
            包含所有非空字段的字典
        """
        result = {
            'success': self.success,
            'status': self.status.value
        }
        if self.data is not None:
            result['data'] = self.data
        if self.error is not None:
            result['error'] = self.error
        if self.message is not None:
            result['message'] = self.message
        if self.metadata:
            result['metadata'] = self.metadata
        return result

    def is_ok(self) -> bool:
        """检查是否成功"""
        return self.success

    def is_fail(self) -> bool:
        """检查是否失败"""
        return not self.success

    def __bool__(self) -> bool:
        """支持 bool(result) 语法"""
        return self.success


# 便捷函数
def ok(data: Optional[Dict] = None, message: Optional[str] = None, **metadata) -> Result:
    """创建成功结果的便捷函数"""
    return Result.ok(data=data, message=message, **metadata)


def fail(error: str, status: Status = Status.FAILED) -> Result:
    """创建失败结果的便捷函数"""
    return Result.fail(error=error, status=status)


def not_found(message: str = "资源未找到") -> Result:
    """创建未找到结果的便捷函数"""
    return Result.not_found(message=message)
