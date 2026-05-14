#!/usr/bin/env python3
"""
Config - 配置读取工具

从 ~/.hermes/config.yaml 读取配置
支持环境变量覆盖路径配置

Usage:
    from utils.config import config

    # 获取路径
    agent_pool_path = config.get_agent_pool_src_path()
    workflows_dir = config.get_workflows_dir()

    # 环境变量覆盖
    # HERMES_CONFIG_PATH=/custom/config.yaml
    # HERMES_LOG_DIR=/custom/logs
"""

import os
from pathlib import Path
from typing import Any, Optional
import yaml

# 简单日志实现（避免循环导入）
import logging
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class Config:
    """配置管理器"""

    def __init__(self, config_path: str = None):
        """
        初始化

        Args:
            config_path: 配置文件路径（默认 ~/.hermes/config.yaml）
        """

        self.logger = get_logger(__name__)
        # 支持环境变量覆盖
        env_path = os.environ.get('HERMES_CONFIG_PATH')
        self.config_path = Path(config_path or env_path or Path.home() / '.hermes' / 'config.yaml')
        self._config = None

    def _load(self) -> dict:
        """加载配置"""
        if self._config is not None:
            return self._config

        try:
            if not self.config_path.exists():
                self._config = {}
                return self._config

            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
                return self._config

        except Exception as e:
            # 使用 logger 如果可用，否则 print
            try:
                from utils.logger import get_logger
                get_logger('config').warning(f"加载配置失败: {e}")
            except ImportError:
                self.logger.error(f"[Config] 加载配置失败: {e}")
            self._config = {}
            return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键（支持点号分隔，如 'delegation.terminal_timeout'）
            default: 默认值

        Returns:
            配置值
        """
        config = self._load()

        keys = key.split('.')
        value = config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

            if value is None:
                return default

        return value

    # ============ 路径配置方法 ============

    def get_hermes_root(self) -> Path:
        """获取 Hermes 根目录"""
        env_root = os.environ.get('HERMES_ROOT')
        if env_root:
            return Path(env_root)
        return Path(self.get('paths.hermes_root', Path.home() / '.hermes'))

    def get_agent_pool_path(self) -> Path:
        """获取 agent-pool 路径"""
        env_path = os.environ.get('HERMES_AGENT_POOL_PATH')
        if env_path:
            return Path(env_path)
        default = self.get_hermes_root() / 'skills' / 'openclaw-imports' / 'agent-pool'
        return Path(self.get('paths.agent_pool', default))

    def get_agent_pool_src_path(self) -> Path:
        """获取 agent-pool src 路径"""
        return self.get_agent_pool_path() / 'src'

    def get_agent_pool_cli_path(self) -> Path:
        """获取 agent-pool CLI 路径"""
        return self.get_agent_pool_path() / 'bin' / 'agent-pool'

    def get_feishu_notify_path(self) -> Path:
        """获取飞书通知模块路径"""
        default = self.get_hermes_root() / 'skills' / 'openclaw-imports' / 'workflow-feishu-notify'
        return Path(self.get('paths.feishu_notify', default))

    def get_workflows_dir(self) -> Path:
        """获取工作流目录"""
        env_dir = os.environ.get('HERMES_WORKFLOWS_DIR')
        if env_dir:
            return Path(env_dir)
        default = self.get_hermes_root() / 'workflows'
        return Path(self.get('paths.workflows', default))

    def get_workspace_dir(self) -> Path:
        """获取工作空间目录"""
        default = self.get_hermes_root() / 'workspace' / 'workflows'
        return Path(self.get('paths.workspace', default))

    def get_logs_dir(self) -> Path:
        """获取日志目录"""
        env_dir = os.environ.get('HERMES_LOG_DIR')
        if env_dir:
            return Path(env_dir)
        default = self.get_hermes_root() / 'logs'
        return Path(self.get('paths.logs', default))

    # ============ 业务配置方法 ============

    def get_terminal_timeout(self) -> int:
        """获取终端超时配置（秒）"""
        return self.get('delegation.terminal_timeout', 1296000)  # 默认 15 天

    def get_heartbeat_interval(self) -> int:
        """获取心跳间隔（秒）"""
        return self.get('heartbeat.interval', 300)  # 默认 5 分钟

    def get_guardian_check_interval(self) -> int:
        """获取 Guardian 检查间隔（秒）"""
        return self.get('guardian.check_interval', 1800)  # 默认 30 分钟

    def get_guardian_stuck_threshold(self) -> int:
        """获取卡住判定阈值（秒）"""
        return self.get('guardian.stuck_threshold', 1800)  # 默认 30 分钟

    def get_max_recovery_attempts(self) -> int:
        """获取最大恢复尝试次数"""
        return self.get('guardian.max_recovery_attempts', 3)

    def get_max_concurrent_agents(self) -> int:
        """获取最大并发 Agent 数"""
        return self.get('execution.max_concurrent_agents', 3)

    def get_default_timeout(self) -> int:
        """获取默认超时时间（秒）"""
        return self.get('execution.default_timeout', 300)

    def get_retry_enabled(self) -> bool:
        """是否启用重试"""
        return self.get('retry.enabled', True)

    def get_retry_max_attempts(self) -> int:
        """获取最大重试次数"""
        return self.get('retry.max_attempts', 3)

    def get_retry_interval(self) -> int:
        """获取重试间隔（秒）"""
        return self.get('retry.interval', 60)

    # ============ 兼容旧方法 ============

    def get_workflows_dir_str(self) -> str:
        """获取工作流目录（字符串，兼容旧代码）"""
        return str(self.get_workflows_dir())


# 单例实例
config = Config()