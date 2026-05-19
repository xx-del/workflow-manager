# delegate_task 后台进程陷阱

**发现日期**: 2026-05-18
**影响技能**: workflow-manager, agent-pool
**严重程度**: 高（导致任务失败）

---

## 问题描述

使用 delegate_task 执行涉及后台进程等待的任务时，子 agent 会陷入轮询循环，最终达到 max_iterations（50次API调用）限制而失败。

## 触发场景

| 场景 | 是否触发 | 原因 |
|------|----------|------|
| 启动后台进程并等待完成 | ✅ 触发 | 子 agent 轮询进程状态 |
| 执行短命令（<60秒） | ❌ 不触发 | 直接返回结果 |
| 执行长时间命令（>60秒但同步） | ⚠️ 可能 | 取决于 agent 行为 |

## 实际案例

**任务**: 月报生成 Step 1 - 数据库更新检查

**delegate_task 调用**:
```python
delegate_task(
    goal="执行月报生成工作流步骤1：准备阶段...",
    context={...},
    toolsets=["terminal", "file"]
)
```

**结果**:
- API 调用: 50 次
- 执行时间: 1689.62 秒
- 退出原因: max_iterations
- 实际进展: 启动了后台进程，但卡在轮询等待

**日志片段**:
```
tool_trace: [
    {"tool": "terminal", "args_bytes": 528, "result_bytes": 177},
    {"tool": "terminal", "args_bytes": 119, "result_bytes": 2451, "status": "error"},
    {"tool": "process", "args_bytes": 69, "result_bytes": 116},  # 轮询开始
    {"tool": "process", "args_bytes": 53, "result_bytes": 181},  # 继续轮询
    ... # 重复 40+ 次
]
```

## 正确做法

### 方案 A：直接 terminal 执行

```python
# 启动后台进程
terminal(
    command="cd /path && ./update.sh > /tmp/update.log 2>&1 &",
    background=True
)

# 直接检查状态
terminal(command="ps aux | grep update")
terminal(command="tail -20 /tmp/update.log")
```

### 方案 B：分离启动和检查

```python
# Step 1: 启动（不等待）
terminal(command="nohup ./update.sh &", background=True)

# Step 2: 检查（单独调用，不轮询）
terminal(command="cat /tmp/status.json")
```

## 根本原因

delegate_task 创建的子 agent 会尝试"完成任务"，对于后台进程，它会：
1. 启动进程
2. 检查进程状态
3. 发现进程还在运行
4. 再次检查（循环）
5. 达到 max_iterations 限制

子 agent 无法理解"启动后台进程后应该立即返回"的语义。

## 预防措施

1. **识别后台任务**: 涉及 `&`、`nohup`、`background: true` 的命令
2. **避免 delegate_task**: 后台任务用 terminal 直接执行
3. **状态检查分离**: 启动后用独立的 terminal 命令检查

## 相关

- workflow-manager SKILL.md 已添加此陷阱
- agent-pool 的 execute 命令同样受影响