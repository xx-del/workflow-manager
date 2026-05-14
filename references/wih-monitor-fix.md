# WIH 监控修复模式

> 当 WIH 监控脚本检测到 WIH 未启动时的修复流程

## 问题现象

WIH 监控脚本（wih_monitor.py）检测到：
- WIH 进程不存在
- 无新压缩包生成
- 最新压缩包时间戳 < 工作流启动时间

## 诊断流程

### 1. 检查 WIH 进程

```bash
ssh -A root@fl "ssh -o StrictHostKeyChecking=no kali@home 'ps aux | grep -E \"wih.sh|gowitness\" | grep -v grep'"
```

**结果解读**：
- 有进程 → WIH 正在执行
- 无进程 → WIH 已完成或未启动

### 2. 检查最新压缩包

```bash
ssh -A root@fl "ssh -o StrictHostKeyChecking=no kali@home 'ls -lt /home/tool/wih/*.tar.gz | head -1'"
```

### 3. 对比时间戳

```python
# 时间戳对比逻辑
if latest_file_timestamp < workflow_started_at:
    # 历史压缩包，本次扫描未执行 WIH
    return "WIH 未启动"
else:
    # 新压缩包，WIH 已完成
    return "WIH 已完成"
```

### 4. 检查 URL 文件

```bash
ssh -A root@fl "ssh -o StrictHostKeyChecking=no kali@home 'cat /home/tool/wih/url.txt | wc -l'"
```

## 修复方法

### 关键：使用 background=True 启动远程进程

⚠️ **错误方式**（会报错）：

```python
terminal('ssh -A root@fl "ssh kali@home \'cd /home/tool/wih && nohup bash wih.sh url.txt > /tmp/wih.log 2>&1 &\'"')
```

**报错信息**：
```
Foreground command uses shell-level background wrappers (nohup/disown/setsid). 
Use terminal(background=true) so Hermes can track the process
```

✅ **正确方式**：

```python
terminal(
    background=True,
    command='ssh -A root@fl "ssh -o StrictHostKeyChecking=no kali@home \'cd /home/tool/wih && bash wih.sh url.txt > /tmp/wih_manual.log 2>&1\'"',
    timeout=600
)
```

### 原因说明

Hermes terminal 工具不支持在 foreground 模式下使用 `nohup`、`disown`、`setsid` 等后台包装器。必须使用 `background=True` 参数让 Hermes 跟踪进程。

## 状态更新

修复后更新 status.json：

```python
import json
from datetime import datetime

with open('/home/kali/.hermes/workflows/home漏扫/status.json') as f:
    status = json.load(f)

status['heartbeat']['wih']['process_count'] = 1
status['heartbeat']['wih']['manual_triggered_at'] = datetime.now().isoformat()
status['heartbeat']['wih']['triggered_by'] = 'wih_monitor.py (cronjob)'
status['heartbeat']['wih']['screenshot_count'] = 4  # 当前已生成的 CSV 数量

with open('/home/kali/.hermes/workflows/home漏扫/status.json', 'w') as f:
    json.dump(status, f, indent=2, ensure_ascii=False)
```

## 验证

### 1. 等待 10 秒后检查进程

```bash
sleep 10 && ssh -A root@fl "ssh -o StrictHostKeyChecking=no kali@home 'ps aux | grep wih_linux | grep -v grep'"
```

**预期输出**：
```
kali  1418663  747  0.2 721824 38244 ?  Rl  15:30  0:14 ./wih_linux_amd64 -t http://...
```

### 2. 检查 CSV 输出

```bash
ssh -A root@fl "ssh -o StrictHostKeyChecking=no kali@home 'ls -la /home/tool/wih/*.csv | wc -l'"
```

**预期输出**：数量逐渐增加（每个目标生成一个 CSV）

## 完整修复流程

```python
# 1. 诊断
process_result = terminal('ssh ... ps aux | grep wih_linux')
if process_result['exit_code'] == 0:
    print("WIH 正在运行")
else:
    print("WIH 未运行，检查压缩包...")
    
    # 2. 检查压缩包时间戳
    latest_file = get_latest_wih_tarball()
    if latest_file.timestamp < workflow_started_at:
        print("历史压缩包，需要手动触发 WIH")
        
        # 3. 手动触发
        terminal(
            background=True,
            command='ssh ... bash wih.sh url.txt',
            timeout=600
        )
        
        # 4. 更新状态
        update_status_json()
        
        # 5. 验证
        sleep(10)
        verify_wih_running()
```

## 相关文件

- 监控脚本：`~/.hermes/workflows/home漏扫/wih_monitor.py`
- 状态文件：`~/.hermes/workflows/home漏扫/status.json`
- WIH 脚本：`/home/tool/wih/wih.sh`（远程服务器）
- WIH 工具：`/home/tool/wih/wih_linux_amd64`（远程服务器）

## 修复日期

2026-05-09
