# 工作流状态更新职责

> 本文档定义主AI在执行工作流时的状态更新职责。

## 问题背景

### 现象

执行工作流后，`status.json` 未被更新，仍显示旧的时间戳。

### 根本原因

**子agent（delegate_task）无法更新状态**

| 缺失项 | 说明 |
|--------|------|
| 无路径 | 子agent没收到 workflow_path，不知道 status.json 在哪 |
| 无权限 | update_step_status() 设计给主AI调用，子agent无法访问 executor 实例 |
| 无指令 | WORKFLOW.md 中没有"更新status.json"的步骤要求 |
| 无回调 | delegate_task 返回后没有自动触发状态更新的钩子 |

## 核心原则

**状态更新由主AI负责，不是子agent职责**

子agent是独立执行单元：
- ❌ 不知道 workflow_path
- ❌ 不知道 status.json 位置
- ❌ 没有调用 status_manager 的能力

**主AI是唯一拥有完整上下文的角色，必须负责状态更新。**

## 状态更新时机

| 时机 | 操作 | 状态值 |
|------|------|--------|
| 步骤开始前 | 更新 status.json | `status: "running"`, `current_step: N` |
| 步骤完成后 | 更新 status.json | `status: "completed"/"failed"`, 结果摘要 |

## 状态更新方法

### 方法1：使用 jq 命令

```bash
# 更新状态和心跳
jq '.status = "running" | .progress.current_step = 2 | .workflow.heartbeat = "'$(date -Iseconds)'"' \
   status.json > status.json.tmp && mv status.json.tmp status.json
```

### 方法2：使用 Python

```python
import json
from datetime import datetime

with open('status.json', 'r') as f:
    data = json.load(f)

data['status'] = 'running'
data['progress']['current_step'] = 2
data['workflow']['heartbeat'] = datetime.now().isoformat()

with open('status.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
```

## 执行流程

```
主AI执行每个步骤时：
  1. 步骤开始前 → 更新 status.json（status: running, current_step: N）
  2. 调用 delegate_task → 子agent执行
  3. 步骤完成后 → 更新 status.json（status: completed/failed, 结果摘要）
```

## 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| status.json 未更新 | 主AI调用 delegate_task 后忘记更新状态 | 在执行流程中增加状态更新步骤 |
| 状态时间戳过时 | 子agent无法更新状态 | 主AI在每步前后手动更新 |
| 心跳字段为空 | 主AI未写入心跳 | 每次更新时同时更新 workflow.heartbeat |

## 架构对比

| 维度 | 错误架构 | 正确架构 |
|------|----------|----------|
| 状态更新者 | 子agent | 主AI |
| 更新时机 | 子agent内部 | delegate_task 前后 |
| 上下文持有 | 子agent无 | 主AI有完整上下文 |
| 实现复杂度 | 需要传递路径 | 主AI直接操作 |

## 相关文档

- [references/guardian.md](./guardian.md) - 守护机制详细规范
- [references/troubleshooting.md](./troubleshooting.md) - 故障排查
