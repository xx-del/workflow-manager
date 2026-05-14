# 后台进程监控技术

## 场景

工作流执行过程中，某些步骤需要长时间运行（如凭证检测、漏洞扫描），需要后台监控进程完成。

## 技术方案

### 1. 启动后台监控进程

使用 terminal 工具的 `background` 参数：

```python
from hermes_tools import terminal

result = terminal(
    command="#!/bin/bash\nwhile pgrep -f 'target-process' > /dev/null; do\n    echo '[$(date +%H:%M:%S)] 进程仍在运行...'\n    sleep 30\ndone\necho '✅ 进程已完成！'",
    background=True,
    notify_on_complete=True
)

# 返回值
print(f"Session ID: {result['session_id']}")
print(f"PID: {result['pid']}")
```

**参数说明**：
- `background=True`：以后台进程方式运行
- `notify_on_complete=True`：进程完成后自动通知

### 2. 检查进程状态

```bash
# 检查进程是否还在运行
if pgrep -f "batch-login-detect" > /dev/null; then
    echo "⏳ 进程仍在运行"
    ps aux | grep batch-login-detect | grep -v grep
else
    echo "✅ 进程已结束"
fi
```

### 3. 等待进程完成（同步方式）

```bash
# 方案1：简单等待
while pgrep -f "target-process" > /dev/null; do
    echo "等待中..."
    sleep 30
done

# 方案2：超时等待
max_wait=600
waited=0
interval=30

while [ $waited -lt $max_wait ]; do
    if ! pgrep -f "target-process" > /dev/null; then
        echo "✅ 进程已完成"
        break
    fi
    sleep $interval
    waited=$((waited + interval))
done

if [ $waited -ge $max_wait ]; then
    echo "⏰ 等待超时"
fi
```

## 注意事项

### execute_code 超时问题

使用 `execute_code` 执行等待脚本时，默认超时时间为 300 秒。如果进程运行时间超过 5 分钟，脚本会被强制终止。

**解决方案**：
- 使用 `terminal(background=True)` 启动后台监控
- 或者在主 AI 循环中定期检查进程状态

### terminal 超时问题

`terminal` 工具默认超时时间为 60 秒。包含 `sleep` 命令的脚本会在 60 秒后超时。

**解决方案**：
- 使用 `background=True` 参数
- 避免在单个命令中包含长时间 sleep

## 最佳实践

### 推荐：后台监控 + 主循环检查

```python
# 1. 启动后台进程
terminal(command="long-running-task &")

# 2. 启动后台监控
monitor = terminal(
    command="#!/bin/bash\nwhile pgrep -f 'task' > /dev/null; do sleep 30; done\necho '完成'",
    background=True,
    notify_on_complete=True
)

# 3. 主 AI 继续其他工作，收到通知后处理结果
```

### 不推荐：同步等待

```python
# ❌ 会阻塞主 AI，无法处理其他任务
while True:
    if not check_process():
        break
    time.sleep(30)
```

## 应用场景

- 凭证检测工作流：检测 100+ URL，需要 10-15 分钟
- 漏洞扫描工作流：扫描大量目标，需要数小时
- 数据收集工作流：爬取大量数据，时间不确定
- 断点工作流：心跳监控进程完成情况

## 相关文档

- [terminal-execution-constraints.md](terminal-execution-constraints.md) - 执行约束
- [breakpoint-workflow-handling.md](breakpoint-workflow-handling.md) - 断点工作流处理
