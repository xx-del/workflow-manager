#!/usr/bin/env python3
"""
Container - 依赖注入容器

职责：
1. 管理组件生命周期（单例模式）
2. 解耦模块依赖
3. 支持测试时 mock
"""

from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar('T')


class Container:
    """
    简单依赖注入容器

    使用方法：
        # 注册工厂
        Container.register('config', lambda: Config())

        # 获取实例（单例）
        config = Container.get('config')

        # 测试时替换
        Container.set('config', mock_config)

        # 重置（清理测试）
        Container.reset()
    """
    _instances: Dict[str, Any] = {}
    _factories: Dict[str, Callable[[], Any]] = {}

    @classmethod
    def register(cls, name: str, factory: Callable[[], T]) -> None:
        """
        注册组件工厂

        Args:
            name: 组件名称
            factory: 创建组件的工厂函数（无参，返回实例）
        """
        cls._factories[name] = factory

    @classmethod
    def get(cls, name: str) -> Any:
        """
        获取组件实例（懒加载单例）

        Args:
            name: 组件名称

        Returns:
            组件实例

        Raises:
            KeyError: 组件未注册
        """
        if name not in cls._instances:
            if name not in cls._factories:
                raise KeyError(f"组件未注册: {name}")
            cls._instances[name] = cls._factories[name]()
        return cls._instances[name]

    @classmethod
    def get_optional(cls, name: str) -> Optional[Any]:
        """
        获取组件实例（可选，不存在返回 None）

        Args:
            name: 组件名称

        Returns:
            组件实例或 None
        """
        try:
            return cls.get(name)
        except KeyError:
            return None

    @classmethod
    def set(cls, name: str, instance: Any) -> None:
        """
        直接设置组件实例（用于测试）

        Args:
            name: 组件名称
            instance: 组件实例
        """
        cls._instances[name] = instance

    @classmethod
    def has(cls, name: str) -> bool:
        """
        检查组件是否已注册

        Args:
            name: 组件名称

        Returns:
            是否已注册
        """
        return name in cls._factories

    @classmethod
    def has_instance(cls, name: str) -> bool:
        """
        检查组件实例是否已创建

        Args:
            name: 组件名称

        Returns:
            是否已创建实例
        """
        return name in cls._instances

    @classmethod
    def reset(cls) -> None:
        """
        重置所有实例（保留工厂注册）
        用于测试清理
        """
        cls._instances.clear()

    @classmethod
    def clear(cls) -> None:
        """
        清空所有注册和实例
        """
        cls._instances.clear()
        cls._factories.clear()

    @classmethod
    def list_registered(cls) -> list:
        """
        列出所有已注册的组件名称

        Returns:
            组件名称列表
        """
        return list(cls._factories.keys())


def init_container() -> None:
    """
    初始化容器，注册核心组件

    应在应用启动时调用
    """
    # 配置
    Container.register('config', lambda: __import__('utils.config', fromlist=['config']).config)

    # 工作流加载器
    Container.register('loader', lambda: __import__('tools.loader', fromlist=['WorkflowLoader']).WorkflowLoader())

    # 状态管理器
    Container.register('status_manager', lambda: __import__('tools.status', fromlist=['status_manager']).status_manager)

    # 心跳管理器
    Container.register('heartbeat', lambda: __import__('utils.heartbeat', fromlist=['HeartbeatManager']).HeartbeatManager())


# 自动初始化（延迟到首次使用）
_container_initialized = False


def ensure_initialized() -> None:
    """确保容器已初始化"""
    global _container_initialized
    if not _container_initialized:
        init_container()
        _container_initialized = True


def get_component(name: str) -> Any:
    """
    获取组件的便捷函数

    Args:
        name: 组件名称

    Returns:
        组件实例
    """
    ensure_initialized()
    return Container.get(name)
