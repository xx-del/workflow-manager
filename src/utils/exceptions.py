#!/usr/bin/env python3
"""
Exceptions - 统一异常处理

职责：
1. 定义工作流相关异常类
2. 提供异常上下文信息
3. 支持异常序列化（to_dict）
"""

from typing import Optional, Dict, Any


class WorkflowError(Exception):
    """
    工作流基础异常类

    Attributes:
        message: 错误消息
        workflow_name: 工作流名称
        workflow_path: 工作流路径
        step_name: 步骤名称
    """

    def __init__(
        self,
        message: str,
        workflow_name: Optional[str] = None,
        workflow_path: Optional[str] = None,
        step_name: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.workflow_name = workflow_name
        self.workflow_path = workflow_path
        self.step_name = step_name
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式

        Returns:
            包含错误信息的字典
        """
        result = {
            'error_type': self.__class__.__name__,
            'message': self.message
        }
        if self.workflow_name:
            result['workflow_name'] = self.workflow_name
        if self.workflow_path:
            result['workflow_path'] = self.workflow_path
        if self.step_name:
            result['step_name'] = self.step_name
        if self.cause:
            result['cause'] = str(self.cause)
        return result

    def __str__(self) -> str:
        parts = [self.message]
        if self.workflow_name:
            parts.append(f"工作流: {self.workflow_name}")
        if self.step_name:
            parts.append(f"步骤: {self.step_name}")
        return ' | '.join(parts)


class WorkflowNotFoundError(WorkflowError):
    """工作流未找到异常"""

    def __init__(self, workflow_name: str, workflow_path: Optional[str] = None):
        super().__init__(
            message=f"工作流未找到: {workflow_name}",
            workflow_name=workflow_name,
            workflow_path=workflow_path
        )


class StepExecutionError(WorkflowError):
    """步骤执行失败异常"""

    def __init__(
        self,
        step_name: str,
        reason: str,
        workflow_name: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=f"步骤执行失败: {step_name} - {reason}",
            workflow_name=workflow_name,
            step_name=step_name,
            cause=cause
        )


class WorkflowTimeoutError(WorkflowError):
    """工作流超时异常"""

    def __init__(
        self,
        workflow_name: str,
        timeout_seconds: int,
        elapsed_seconds: Optional[int] = None
    ):
        message = f"工作流执行超时: {workflow_name} (超时: {timeout_seconds}s"
        if elapsed_seconds:
            message += f", 已执行: {elapsed_seconds}s"
        message += ")"
        super().__init__(
            message=message,
            workflow_name=workflow_name
        )
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds


class HeartbeatError(WorkflowError):
    """心跳异常"""

    def __init__(
        self,
        workflow_path: str,
        reason: str,
        last_heartbeat: Optional[str] = None
    ):
        super().__init__(
            message=f"心跳异常: {reason}",
            workflow_path=workflow_path
        )
        self.last_heartbeat = last_heartbeat


class ConfigurationError(WorkflowError):
    """配置错误异常"""

    def __init__(self, config_key: str, reason: str):
        super().__init__(
            message=f"配置错误: {config_key} - {reason}"
        )
        self.config_key = config_key


class RecoveryError(WorkflowError):
    """恢复操作失败异常"""

    def __init__(
        self,
        workflow_path: str,
        action: str,
        reason: str,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=f"恢复操作失败: {action} - {reason}",
            workflow_path=workflow_path,
            cause=cause
        )
        self.action = action


class ValidationError(WorkflowError):
    """验证失败异常"""

    def __init__(
        self,
        target: str,
        errors: list,
        workflow_name: Optional[str] = None
    ):
        super().__init__(
            message=f"验证失败: {target}",
            workflow_name=workflow_name
        )
        self.target = target
        self.errors = errors

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result['target'] = self.target
        result['errors'] = self.errors
        return result


class StatusError(WorkflowError):
    """状态操作异常"""

    def __init__(
        self,
        operation: str,
        workflow_path: str,
        reason: str
    ):
        super().__init__(
            message=f"状态操作失败: {operation} - {reason}",
            workflow_path=workflow_path
        )
        self.operation = operation


class LoaderError(WorkflowError):
    """加载器异常"""

    def __init__(
        self,
        workflow_name: str,
        reason: str,
        file_path: Optional[str] = None
    ):
        super().__init__(
            message=f"加载工作流失败: {reason}",
            workflow_name=workflow_name
        )
        self.file_path = file_path


class AgentPoolError(WorkflowError):
    """Agent Pool 调用异常"""

    def __init__(
        self,
        operation: str,
        reason: str,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=f"Agent Pool 调用失败: {operation} - {reason}",
            cause=cause
        )
        self.operation = operation
