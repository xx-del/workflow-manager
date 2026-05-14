#!/usr/bin/env python3
"""
统一日志模块

提供：
1. 统一日志格式
2. 多输出目标（控制台 + 文件）
3. 模块级别控制
4. 支持 get_logger() 便捷函数

Usage:
    from utils.logger import get_logger

    logger = get_logger('executor')
    logger.info("执行工作流")
    logger.error("执行失败", exc_info=True)
"""

import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


# 日志格式
LOG_FORMAT = '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


class WorkflowManagerLogger:
    """工作流管理器日志器"""

    _initialized = False
    _loggers = {}
    _log_dir = None
    _level = logging.INFO

    @classmethod
    def setup(
        cls,
        level: int = logging.INFO,
        log_file: Optional[str] = None,
        log_dir: Optional[str] = None,
        console: bool = True
    ) -> None:
        """
        配置日志系统

        Args:
            level: 日志级别 (logging.DEBUG, INFO, WARNING, ERROR)
            log_file: 日志文件名（不含路径）
            log_dir: 日志目录（默认 ~/.hermes/logs）
            console: 是否输出到控制台
        """
        if cls._initialized:
            return

        # 确定日志目录
        if log_dir:
            log_path = Path(log_dir)
        else:
            # 支持环境变量覆盖
            env_log_dir = os.environ.get('HERMES_LOG_DIR')
            if env_log_dir:
                log_path = Path(env_log_dir)
            else:
                # 从配置获取，避免循环导入
                try:
                    from utils.config import config as get_config
                    log_path = get_config.get_logs_dir()
                except:
                    log_path = Path.home() / '.hermes' / 'logs'

        log_path.mkdir(parents=True, exist_ok=True)
        cls._log_dir = log_path
        cls._level = level

        # 根日志器
        root_logger = logging.getLogger('workflow-manager')
        root_logger.setLevel(level)

        # 清除已有处理器（避免重复）
        root_logger.handlers.clear()

        # 控制台处理器
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
            root_logger.addHandler(console_handler)

        # 文件处理器
        if log_file:
            file_path = log_path / log_file
        else:
            file_path = log_path / f"workflow-{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        root_logger.addHandler(file_handler)

        cls._initialized = True

    @classmethod
    def get_logger(cls, module_name: str) -> logging.Logger:
        """
        获取模块日志器

        Args:
            module_name: 模块名称（如 'executor', 'guardian.monitor'）

        Returns:
            配置好的 Logger 实例
        """
        if not cls._initialized:
            cls.setup()

        full_name = f'workflow-manager.{module_name}'

        if full_name not in cls._loggers:
            cls._loggers[full_name] = logging.getLogger(full_name)

        return cls._loggers[full_name]

    @classmethod
    def set_level(cls, level: int) -> None:
        """
        动态设置日志级别

        Args:
            level: 日志级别
        """
        cls._level = level
        root_logger = logging.getLogger('workflow-manager')
        root_logger.setLevel(level)
        for handler in root_logger.handlers:
            handler.setLevel(level)

    @classmethod
    def get_log_dir(cls) -> Optional[Path]:
        """获取日志目录"""
        return cls._log_dir


def get_logger(name: str) -> logging.Logger:
    """
    便捷函数：获取日志器

    Args:
        name: 模块名称

    Returns:
        Logger 实例

    Example:
        >>> logger = get_logger('executor')
        >>> logger.info("开始执行")
    """
    return WorkflowManagerLogger.get_logger(name)


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    console: bool = True
) -> None:
    """
    配置日志系统（便捷函数）

    Args:
        level: 日志级别
        log_file: 日志文件名
        log_dir: 日志目录
        console: 是否输出到控制台
    """
    WorkflowManagerLogger.setup(
        level=level,
        log_file=log_file,
        log_dir=log_dir,
        console=console
    )


def create_module_logger(module_name: str) -> logging.Logger:
    """
    创建模块级日志器（用于模块顶部）

    Example:
        # 在模块顶部使用
        logger = create_module_logger('executor')
    """
    return get_logger(module_name)


# 模块级便捷函数
def debug(msg: str, *args, **kwargs):
    """快捷调试日志"""
    get_logger('main').debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """快捷信息日志"""
    get_logger('main').info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """快捷警告日志"""
    get_logger('main').warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """快捷错误日志"""
    get_logger('main').error(msg, *args, **kwargs)


def exception(msg: str, *args, **kwargs):
    """快捷异常日志（自动包含堆栈）"""
    get_logger('main').exception(msg, *args, **kwargs)
