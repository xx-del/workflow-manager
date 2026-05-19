# 心跳脚本 WIH 路径修复 - 20260517

## 问题描述

心跳脚本检测 WIH 进度时使用了错误的路径，导致：
- `screenshot_count` 始终为 0
- 无法正确检测 WIH 产出变化
- 心跳持续运行但无法完成

## 错误路径

```python
# ❌ 错误 - 目录不存在
count_result = run_ssh_command("sudo ls /home/tool/wih/screenshots/ 2>/dev/null | wc -l")
```

## 正确路径

WIH 实际产出目录：`/home/tool/wih/*.tar.gz`

```python
# ✅ 正确 - WIH 产出是压缩包
count_result = run_ssh_command("ls /home/tool/wih/*.tar.gz 2>/dev/null | wc -l")
```

## 验证命令

```bash
# 检查 WIH 压缩包数量
ssh -A root@fl "ssh kali@home 'ls /home/tool/wih/*.tar.gz | wc -l'"

# 查看最新压缩包
ssh -A root@fl "ssh kali@home 'ls -lt /home/tool/wih/*.tar.gz | head -5'"
```

## 修复位置

文件：`~/.hermes/workflows/home漏扫/heartbeat.py`

行号：467-472

## 经验教训

1. WIH 产出是 `*.tar.gz` 压缩包，不是 `screenshots/` 目录
2. 心跳脚本检测路径必须与实际产出路径一致
3. 路径错误会导致状态检测失败，心跳无法停止
