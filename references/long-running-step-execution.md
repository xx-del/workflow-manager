# 长时间运行步骤的执行模式

## 问题场景

工作流步骤中包含耗时操作（如批量URL检测、端口扫描），使用 `terminal` 工具执行时：
- 默认 60 秒超时限制
- 进程在超时后被终止
- 结果文件未更新，工作流失败

**案例（2026-05-12）**：
```
步骤 8：执行凭证检测
命令：cd /x/rank/hwxinxisouji/liuliang/autofill-detector/ && node batch-login-detect.js
结果：执行 60 秒后超时，进程被终止（检测了 71/112 URL）
```

## 解决方案

### 方案 1：后台模式执行（推荐）

使用 `terminal(background=true)` 启动后台进程：

```python
# 正确：后台执行长时间任务
result = terminal(
    command="cd /path/to/project && node long-running-task.js",
    background=True,
    notify_on_complete=True
)

# 返回：
# - session_id: "proc_xxx"
# - pid: 12345
# - 完成后自动通知
```

**优点**：
- 不受 60 秒超时限制
- Hermes 跟踪进程状态
- 完成后自动通知
- 可通过 `process(action='poll')` 检查状态

### 方案 2：轮询等待

使用后台进程 + 轮询检查：

```python
# 1. 启动后台进程
proc = terminal(command="long-task.sh", background=True, notify_on_complete=True)

# 2. 定期检查状态
import time
while True:
    status = process(action='poll', session_id=proc['session_id'])
    if status['status'] != 'running':
        break
    time.sleep(30)  # 每 30 秒检查一次
```

### 方案 3：nohup 后台（不推荐）

```bash
# 错误：使用 nohup 不会被 Hermes 跟踪
nohup node long-task.js > /tmp/log.txt 2>&1 &
```

**问题**：Hermes 无法跟踪进程状态，无法知道何时完成。

## 执行约束

### 禁止行为

❌ **禁止使用同步模式执行长时间任务**
```python
# 错误：同步执行会超时
terminal(command="node batch-detect.js")  # 60秒超时
```

❌ **禁止使用 nohup 后台模式**
```python
# 错误：Hermes 无法跟踪
terminal(command="nohup node task.js &")  # 触发错误
```

### 必须行为

✅ **必须使用 background=True 执行长时间任务**
```python
terminal(command="node task.js", background=True, notify_on_complete=True)
```

✅ **必须使用 session_id 管理进程**
```python
# 启动
result = terminal(command="task.sh", background=True)
session_id = result['session_id']

# 检查状态
process(action='poll', session_id=session_id)

# 停止
process(action='kill', session_id=session_id)
```

## 判断标准

**何时使用后台模式**：

| 任务类型 | 执行模式 | 原因 |
|---------|---------|------|
| 批量URL检测 | background | 需要 5-15 分钟 |
| 端口扫描 | background | 需要数分钟到数小时 |
| 数据处理脚本 | background | 取决于数据量 |
| 简单验证命令 | 同步 | 几秒内完成 |
| 文件操作 | 同步 | 几秒内完成 |

**判断依据**：
- 包含网络请求、循环处理 → 后台模式
- 单次操作、本地文件 → 同步模式
- 不确定时 → 默认后台模式

## 相关文档

- [terminal-execution-constraints.md](./terminal-execution-constraints.md) - 执行约束
- [workflow-design-patterns.md](./workflow-design-patterns.md) - 设计模式
