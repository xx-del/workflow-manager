#!/usr/bin/env python3
"""
测试 workflow-feishu-notify 模块
验证同步方法是否可以在独立进程中正常工作
"""

import sys
from pathlib import Path

# 添加模块路径
notify_path = Path.home() / ".hermes/skills/openclaw-imports/workflow-feishu-notify"
if str(notify_path) not in sys.path:
    sys.path.insert(0, str(notify_path))

from notify import send_workflow_alert, send_text, WorkflowFeishuNotify


def test_sync_methods():
    """测试同步方法"""
    print("=" * 60)
    print("测试 workflow-feishu-notify 同步方法")
    print("=" * 60)
    
    # 测试 1: 检查 SDK 是否可用
    print("\n[测试 1] 检查 lark-oapi SDK...")
    try:
        import lark_oapi as lark
        print("  ✅ lark-oapi 已安装")
    except ImportError:
        print("  ❌ lark-oapi 未安装")
        return False
    
    # 测试 2: 检查配置文件
    print("\n[测试 2] 检查配置文件...")
    config_file = Path.home() / ".hermes/workflow-notify.yaml"
    if config_file.exists():
        print(f"  ✅ 配置文件存在: {config_file}")
        import yaml
        config = yaml.safe_load(config_file.read_text()) or {}
        app_id = config.get('app_id', '未配置')
        print(f"     app_id: {app_id[:10] if app_id else '未配置'}...")
        print(f"     default_chat_id: {config.get('default_chat_id', '未配置')}")
    else:
        print(f"  ⚠️ 配置文件不存在: {config_file}")
        print("     尝试从环境变量读取...")
        
    # 测试 3: 创建通知实例
    print("\n[测试 3] 创建 WorkflowFeishuNotify 实例...")
    notify = WorkflowFeishuNotify()
    if notify.client:
        print("  ✅ Client 创建成功")
    else:
        print("  ❌ Client 创建失败（检查 app_id/app_secret）")
        return False
    
    # 测试 4: 发送测试消息
    print("\n[测试 4] 发送测试消息...")
    result = send_text("🧪 Guardian 测试：同步方法可用")
    if result.success:
        print(f"  ✅ 消息发送成功: message_id={result.message_id}")
    else:
        print(f"  ❌ 消息发送失败: {result.error}")
        return False
    
    # 测试 5: 发送工作流告警
    print("\n[测试 5] 发送工作流告警...")
    result = send_workflow_alert(
        workflow_name="guardian-test",
        current_step="test_step",
        progress="1/1",
        causes=[
            {"description": "测试原因", "confidence": 0.9}
        ],
        actions=[
            {"description": "测试操作", "risk": "low"}
        ]
    )
    if result.success:
        print(f"  ✅ 告警发送成功: message_id={result.message_id}")
    else:
        print(f"  ❌ 告警发送失败: {result.error}")
        return False
    
    return True


if __name__ == "__main__":
    result = test_sync_methods()
    print("\n" + "=" * 60)
    if result:
        print("✅ 所有测试通过")
    else:
        print("❌ 测试失败")
    print("=" * 60)
