#!/usr/bin/env python3
"""
清理残留的会话标记文件

用途：
1. Gateway 启动时调用
2. 会话异常中断后手动调用
3. 定期清理任务

调用方式：
    python scripts/cleanup_marker.py
    python scripts/cleanup_marker.py --force  # 强制清理
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime


def cleanup_stale_marker(force: bool = False) -> dict:
    """
    清理残留的会话标记文件
    
    Args:
        force: 强制清理（不检查 PID）
    
    Returns:
        清理结果
    """
    marker_file = Path.home() / ".hermes" / "workflows" / ".active_session"
    
    if not marker_file.exists():
        return {
            "success": True,
            "action": "none",
            "message": "无会话标记文件"
        }
    
    try:
        data = json.loads(marker_file.read_text(encoding='utf-8'))
        marker_pid = data.get("pid")
        workflow_name = data.get("workflow_name", "unknown")
        started_at = data.get("started_at", "unknown")
        
        if force:
            # 强制清理
            marker_file.unlink()
            return {
                "success": True,
                "action": "force_removed",
                "message": f"已强制清理会话标记",
                "workflow": workflow_name,
                "pid": marker_pid
            }
        
        # 检查进程是否存活
        if marker_pid:
            try:
                os.kill(marker_pid, 0)  # 检查进程存在（不发送信号）
                # 进程存活，不清理
                return {
                    "success": True,
                    "action": "skipped",
                    "message": f"工作流进程仍在运行 (PID: {marker_pid})",
                    "workflow": workflow_name,
                    "pid": marker_pid
                }
            except ProcessLookupError:
                # 进程不存在，清理残留标记
                marker_file.unlink()
                return {
                    "success": True,
                    "action": "cleaned",
                    "message": f"已清理残留标记: 进程 {marker_pid} 已不存在",
                    "workflow": workflow_name,
                    "pid": marker_pid,
                    "started_at": started_at
                }
            except PermissionError:
                # 进程存在但无权限发送信号（通常意味着进程存活）
                return {
                    "success": True,
                    "action": "skipped",
                    "message": f"工作流进程可能仍在运行 (PID: {marker_pid})",
                    "workflow": workflow_name,
                    "pid": marker_pid
                }
        else:
            # 无 PID 信息，清理
            marker_file.unlink()
            return {
                "success": True,
                "action": "cleaned",
                "message": "已清理无 PID 的会话标记",
                "workflow": workflow_name
            }
            
    except json.JSONDecodeError as e:
        # JSON 损坏，清理
        marker_file.unlink()
        return {
            "success": True,
            "action": "cleaned",
            "message": f"已清理损坏的会话标记: {e}"
        }
    except Exception as e:
        return {
            "success": False,
            "action": "error",
            "message": f"清理失败: {e}"
        }


def main():
    parser = argparse.ArgumentParser(description='清理残留的会话标记文件')
    parser.add_argument('--force', action='store_true', help='强制清理（不检查 PID）')
    parser.add_argument('--json', action='store_true', help='JSON 格式输出')
    
    args = parser.parse_args()
    
    result = cleanup_stale_marker(force=args.force)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result['success']:
            if result['action'] == 'none':
                pass  # 无标记，静默
            elif result['action'] == 'skipped':
                print(f"⏭️  {result['message']}")
            else:
                print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
    
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    main()
