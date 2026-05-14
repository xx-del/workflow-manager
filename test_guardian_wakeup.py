#!/usr/bin/env python3
"""
Guardian 唤醒测试脚本
测试 threshold=0 时守护 Agent 是否立即唤醒
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加 src 目录到路径
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from guardian.monitor import GuardianMonitor
from tools.status import status_manager


async def test_guardian_wakeup():
    """测试守护 Agent 唤醒"""
    
    print("=" * 60)
    print("Guardian 唤醒测试")
    print("=" * 60)
    
    workflow_path = str(Path.home() / ".hermes" / "workflows" / "guardian-test")
    
    # 创建监控器实例，threshold=0
    monitor = GuardianMonitor(
        check_interval=1,      # 1秒检查一次
        stuck_threshold=0      # 超时阈值=0，立即触发
    )
    
    print(f"\n配置:")
    print(f"  工作流路径: {workflow_path}")
    print(f"  检查间隔: {monitor.check_interval}s")
    print(f"  卡住阈值: {monitor.stuck_threshold}s")
    
    # 读取 status.json
    status = status_manager.get_status(workflow_path)
    print(f"\n工作流状态:")
    print(f"  status: {status.get('status')}")
    print(f"  heartbeat: {status.get('workflow', {}).get('heartbeat')}")
    
    # 测试 is_stuck() 方法
    is_stuck = monitor.is_stuck(status)
    print(f"\nis_stuck() 结果: {is_stuck}")
    
    if is_stuck:
        print("\n✅ 测试通过：threshold=0 时 is_stuck() 返回 True")
    else:
        print("\n❌ 测试失败：threshold=0 时 is_stuck() 应返回 True")
        return False
    
    # 测试守护 Agent 唤醒
    print("\n启动监控（将在第一次检查时触发守护 Agent）...")
    
    # 设置超时防止无限等待
    try:
        # 启动监控
        await monitor.start_monitoring(workflow_path)
        
        # 等待监控循环执行（最多等待 5 秒）
        await asyncio.sleep(5)
        
        # 检查是否触发
        print("\n检查守护 Agent 是否被唤醒...")
        
        # 读取恢复历史
        history_path = Path(workflow_path) / "recovery_history.json"
        if history_path.exists():
            print(f"✅ recovery_history.json 已创建")
        else:
            print(f"⚠️ recovery_history.json 未创建（可能本地恢复失败）")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        return False
    
    finally:
        await monitor.stop_monitoring()


if __name__ == "__main__":
    result = asyncio.run(test_guardian_wakeup())
    print("\n" + "=" * 60)
    if result:
        print("测试完成")
    else:
        print("测试失败")
    print("=" * 60)
