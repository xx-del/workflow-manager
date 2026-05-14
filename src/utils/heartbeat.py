#!/usr/bin/env python3
"""
Heartbeat - 心跳管理工具

职责：
1. 提供心跳启动、停止、写入功能
2. 支持依赖注入
3. 支持失败重试和状态回调
"""

import asyncio
import os
from datetime import datetime
from typing import Optional, Callable, Any
from pathlib import Path

from utils.logger import get_logger


class HeartbeatManager:
    """
    心跳管理器

    使用方法：
        heartbeat = HeartbeatManager()
        heartbeat.on_fail(callback)  # 设置失败回调
        await heartbeat.start(workflow_path, step_name)
        heartbeat.update(step_name="new_step")
        await heartbeat.stop()
    """

    def __init__(
        self,
        interval: int = 300,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        status_manager=None
    ):
        """
        初始化

        Args:
            interval: 心跳间隔（秒），默认 5 分钟
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            status_manager: 状态管理器（可选，支持依赖注入）
        """
        self.logger = get_logger(__name__)
        self.interval = interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # 依赖注入支持
        self._status_manager = status_manager
        self._task: Optional[asyncio.Task] = None
        self._running = False

        # 心跳状态
        self._workflow_path: Optional[str] = None
        self._current_step: Optional[str] = None
        self._step_progress: Optional[str] = None

        # 回调函数
        self._on_fail_callbacks: list[Callable[[str], Any]] = []
        self._on_success_callbacks: list[Callable[[], Any]] = []

        # 统计信息
        self._total_writes = 0
        self._failed_writes = 0
        self._last_heartbeat_time: Optional[datetime] = None

    @property
    def status_manager(self):
        """获取状态管理器（延迟加载）"""
        if self._status_manager is None:
            from tools.status import status_manager
            self._status_manager = status_manager
        return self._status_manager

    def on_fail(self, callback: Callable[[str], Any]) -> None:
        """
        注册失败回调

        Args:
            callback: 回调函数，接收错误消息
        """
        self._on_fail_callbacks.append(callback)

    def on_success(self, callback: Callable[[], Any]) -> None:
        """
        注册成功回调

        Args:
            callback: 回调函数
        """
        self._on_success_callbacks.append(callback)

    async def start(
        self,
        workflow_path: str,
        current_step: Optional[str] = None,
        step_progress: Optional[str] = None
    ) -> bool:
        """
        启动心跳

        Args:
            workflow_path: 工作流目录路径
            current_step: 当前步骤名称
            step_progress: 步骤进度

        Returns:
            是否成功启动
        """
        if self._running:
            self.logger.warning("[Heartbeat] 已在运行中，跳过启动")
            return False

        self._workflow_path = workflow_path
        self._current_step = current_step
        self._step_progress = step_progress
        self._running = True

        # 立即写入一次
        if not self.write():
            self.logger.error("[Heartbeat] 初始心跳写入失败")
            # 不阻止启动，继续尝试

        # 启动定时任务
        self._task = asyncio.create_task(self._heartbeat_loop())

        self.logger.info(f"[Heartbeat] 已启动 (间隔: {self.interval}s, 路径: {workflow_path})")
        return True

    async def stop(self) -> None:
        """停止心跳"""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        # 写入最后一次心跳
        self.write()

        self.logger.info(f"[Heartbeat] 已停止 (总计: {self._total_writes}, 失败: {self._failed_writes})")

    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self._running:
            try:
                await asyncio.sleep(self.interval)
                if not self.write():
                    # 写入失败，触发回调
                    await self._handle_fail("心跳写入失败")
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"[Heartbeat] 循环异常: {e}")
                await self._handle_fail(str(e))

    def write(self) -> bool:
        """
        写入心跳（带重试）

        Returns:
            是否成功
        """
        if not self._workflow_path:
            return False

        for attempt in range(self.max_retries):
            try:
                result = self.status_manager.write_heartbeat(
                    self._workflow_path,
                    current_step=self._current_step,
                    step_progress=self._step_progress,
                    pid=os.getpid(),
                )

                if result:
                    self._total_writes += 1
                    self._last_heartbeat_time = datetime.now()

                    # 触发成功回调
                    for callback in self._on_success_callbacks:
                        try:
                            callback()
                        except Exception as e:
                            self.logger.warning(f"[Heartbeat] 成功回调异常: {e}")

                    return True
                else:
                    self.logger.warning(f"[Heartbeat] 写入返回 False (尝试 {attempt + 1}/{self.max_retries})")

            except Exception as e:
                self.logger.error(f"[Heartbeat] 写入异常 (尝试 {attempt + 1}/{self.max_retries}): {e}")

            # 重试延迟
            if attempt < self.max_retries - 1:
                import time
                time.sleep(self.retry_delay)

        # 所有重试失败
        self._failed_writes += 1
        return False

    async def _handle_fail(self, error: str) -> None:
        """处理心跳失败"""
        self.logger.error(f"[Heartbeat] 失败: {error}")

        for callback in self._on_fail_callbacks:
            try:
                result = callback(error)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self.logger.warning(f"[Heartbeat] 失败回调异常: {e}")

    def update(
        self,
        current_step: Optional[str] = None,
        step_progress: Optional[str] = None
    ) -> bool:
        """
        更新心跳信息并立即写入

        Args:
            current_step: 当前步骤名称
            step_progress: 步骤进度

        Returns:
            是否成功写入
        """
        if current_step:
            self._current_step = current_step
        if step_progress:
            self._step_progress = step_progress

        return self.write()

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running

    @property
    def last_heartbeat(self) -> Optional[datetime]:
        """最后心跳时间"""
        return self._last_heartbeat_time

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'total_writes': self._total_writes,
            'failed_writes': self._failed_writes,
            'last_heartbeat': self._last_heartbeat_time.isoformat() if self._last_heartbeat_time else None,
            'is_running': self._running,
            'workflow_path': self._workflow_path,
            'current_step': self._current_step,
        }


def create_heartbeat(
    interval: int = 300,
    status_manager=None
) -> HeartbeatManager:
    """
    创建心跳管理器的便捷函数

    Args:
        interval: 心跳间隔
        status_manager: 状态管理器（可选）

    Returns:
        HeartbeatManager 实例
    """
    return HeartbeatManager(interval=interval, status_manager=status_manager)


# 单例实例（向后兼容）
heartbeat = HeartbeatManager()
