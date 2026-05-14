# 长时间运行任务处理模式

## 问题背景

`delegate_task` 工具有 30 秒超时限制。当工作流步骤执行时间超过 30 秒时（如批量扫描、爆破测试、大文件处理），会导致超时失败。

## 解决方案

使用 `terminal` 工具的 `background` 模式替代 `delegate_task`。

## 处理流程

```
步骤执行 → 预计时间 > 30秒？
     ↓ 是
delegate_task 超时（30秒限制）
     ↓
改用 terminal background 模式
     ↓
terminal(background=true, notify_on_complete=true, timeout=7200)
     ↓
更新 status.json 记录进程信息
     ↓
向用户报告：任务已后台运行，完成后通知
     ↓
继续执行后续步骤或等待完成
```

## 参数说明

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `background` | 后台运行模式 | `true` |
| `notify_on_complete` | 完成后通知 | `true` |
| `timeout` | 超时时间（秒） | `7200`（2小时） |
| `workdir` | 工作目录 | 根据任务设置 |

## 示例代码

```json
{
  "tool": "terminal",
  "params": {
    "command": "cd /x/rank/hwxinxisouji/liuliang/baopo/ && uv run main.py",
    "background": true,
    "notify_on_complete": true,
    "timeout": 7200,
    "workdir": "/x/rank/hwxinxisouji/liuliang/baopo/"
  }
}
```

## 返回值

```json
{
  "output": "Background process started",
  "session_id": "proc_c43c14e8b900",
  "pid": 264926,
  "exit_code": 0,
  "error": null,
  "notify_on_complete": true
}
```

## 进程管理

### 检查进程状态

```json
{
  "tool": "process",
  "params": {
    "action": "poll",
    "session_id": "proc_c43c14e8b900"
  }
}
```

### 终止进程

```json
{
  "tool": "process",
  "params": {
    "action": "kill",
    "session_id": "proc_c43c14e8b900"
  }
}
```

## 状态更新

在启动后台进程后，必须更新工作流状态文件：

```json
{
  "status": "running",
  "progress": {
    "current_step": 7,
    "total_steps": 12,
    "message": "正在执行爆破测试（后台运行）"
  },
  "background_process": {
    "session_id": "proc_c43c14e8b900",
    "pid": 264926,
    "command": "uv run main.py"
  }
}
```

## 适用场景

| 场景 | 预计时间 | 处理方式 |
|------|----------|----------|
| 批量扫描（>100目标） | 分钟级 | terminal background |
| 爆破测试 | 小时级 | terminal background |
| 大文件处理（>1GB） | 分钟级 | terminal background |
| 数据同步/备份 | 分钟级 | terminal background |
| 简单命令（<30秒） | 秒级 | delegate_task |

## 注意事项

1. **必须设置 notify_on_complete**：否则无法知道任务何时完成
2. **记录 session_id 和 pid**：用于后续进程管理
3. **更新工作流状态**：让用户知道任务在后台运行
4. **合理设置 timeout**：根据任务预估时间设置，避免过早超时
