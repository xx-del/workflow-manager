#!/usr/bin/env python3
"""
测试 recovery.py 正确调用飞书通知的方式
"""

import asyncio
import sys
from pathlib import Path

# 添加模块路径
notify_path = Path.home() / ".hermes/skills/openclaw-imports/workflow-feishu-notify"
if str(notify_path) not in sys.path:
    sys.path.insert(0, str(notify_path))

from notify import send_workflow_alert, WorkflowFeishuNotify


def test_sync_in_async_context():
    """测试在 async 上下文中调用同步方法"""
    print("=" * 60)
    print("测试：在 async 上下文中调用同步飞书方法")
    print("=" * 60)
    
    # 方式 1: 直接调用便捷函数（同步）
    print("\n[方式 1] 直接调用便捷函数 send_workflow_alert()...")
    result = send_workflow_alert(
        workflow_name="guardian-test",
        current_step="test_step",
        progress="1/1",
        causes=[{"description": "测试原因", "confidence": 0.9}],
        actions=[{"description": "测试操作", "risk": "low"}]
    )
    if result.success:
        print(f"  ✅ 发送成功: {result.message_id}")
    else:
        print(f"  ❌ 发送失败: {result.error}")
    
    # 方式 2: 通过实例调用同步方法
    print("\n[方式 2] 通过实例调用 send_workflow_alert_sync()...")
    notify = WorkflowFeishuNotify()
    result = notify.send_workflow_alert_sync(
        workflow_name="guardian-test-2",
        current_step="test_step_2",
        progress="2/2",
        causes=[{"description": "测试原因 2", "confidence": 0.8}]
    )
    if result.success:
        print(f"  ✅ 发送成功: {result.message_id}")
    else:
        print(f"  ❌ 发送失败: {result.error}")
    
    return result.success


async def test_async_method():
    """测试 async 方法"""
    print("\n" + "=" * 60)
    print("测试：在 async 上下文中调用 async 飞书方法")
    print("=" * 60)
    
    notify = WorkflowFeishuNotify()
    
    result = await notify.send_workflow_alert(
        workflow_name="guardian-test-async",
        current_step="test_step_async",
        progress="1/1",
        causes=[{"description": "异步测试", "confidence": 0.95}]
    )
    
    if result.success:
        print(f"  ✅ 发送成功: {result.message_id}")
    else:
        print(f"  ❌ 发送失败: {result.error}")
    
    return result.success


if __name__ == "__main__":
    # 测试同步方法
    sync_result = test_sync_in_async_context()
    
    # 测试异步方法
    async_result = asyncio.run(test_async_method())
    
    print("\n" + "=" * 60)
    print(f"同步方法测试: {'✅ 通过' if sync_result else '❌ 失败'}")
    print(f"异步方法测试: {'✅ 通过' if async_result else '❌ 失败'}")
    print("=" * 60)
