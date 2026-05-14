# Workflow-manager 空指令问题

**发现日期**: 2026-05-13  
**问题状态**: 待修复

---

## 问题现象

执行 `python actions/execute.py 资产收集流程` 返回：
- 状态: `execution_required`
- 所有步骤的 `instructions` 都是空数组 `[]`
- 消息: "无需执行额外指令"
- 只有 finalize 指令

```json
{
  "id": "root_电力数据_1",
  "name": "解析日期范围",
  "success": true,
  "status": "plan_ready",
  "instructions": [],
  "message": "无需执行额外指令"
}
```

---

## 根本原因

**代码路径**: `executor.py` 第 713-723 行

```python
# 调用 agent_pool_client.execute_full()
result = await self._call_agent_pool(...)

# 返回的 pending_instructions 为空
all_instructions = result.get('pending_instructions', result.get('instructions', []))
pending_instructions = all_instructions  # 空数组
```

**agent_pool_client.execute_full()** 返回空的 `instructions`。

---

## 影响范围

1. **工作流无法执行**: 主 AI 收到空指令，无法调用 delegate_task
2. **Hook 未触发**: 没有实际执行步骤，Hook 不会被调用
3. **状态未更新**: complete.py 读取旧的 completed 状态
4. **文档未生成**: 今天（20260513）的三个文档未生成

---

## 预期行为

`execute.py` 应返回：

```json
{
  "status": "execution_required",
  "pending_instructions": [
    {
      "step_id": "root_电力数据_1",
      "step_name": "解析日期范围",
      "action": "delegate_task",
      "goal": "解析日期参数...",
      "context": "..."
    },
    {
      "step_id": "root_电力数据_2",
      "step_name": "备份并清理",
      "action": "delegate_task",
      "goal": "..."
    }
  ]
}
```

---

## 修复方向

### 方案 A: 修复 agent_pool_client

让 `execute_full()` 返回实际的执行指令：

```python
# agent_pool_client.py
def execute_full(self, task_description, capabilities, context):
    # 生成 delegate_task 指令
    return {
        "success": True,
        "pending_instructions": [{
            "action": "delegate_task",
            "goal": task_description,
            "context": context
        }]
    }
```

### 方案 B: 修改 executor._execute_step()

直接在 executor 中生成指令：

```python
# executor.py _execute_step()
return {
    'instructions': [{
        'step_id': step['id'],
        'step_name': step['name'],
        'action': 'delegate_task',
        'goal': task_description,
        'context': step.get('_context')
    }]
}
```

---

## 临时解决方案

主 AI 收到 `execution_required` 后：
1. 检查 `pending_instructions` 是否为空
2. 如果为空，读取 status.md 获取步骤列表
3. 手动构建 delegate_task 指令
4. 逐个执行

---

## 验证方法

```bash
# 执行工作流
python3 actions/execute.py 资产收集流程 --date-start 20260513 --date-end 20260513 --json | jq '.pending_instructions | length'

# 预期输出: 22（21个步骤 + 1个finalize）
# 实际输出: 1（只有finalize）
```

---

## 相关文件

- `/home/kali/.hermes/skills/openclaw-imports/workflow-manager/src/core/executor.py`
- `/home/kali/.hermes/skills/openclaw-imports/workflow-manager/src/core/agent_pool_client.py`
- `/home/kali/.hermes/skills/openclaw-imports/workflow-manager/actions/execute.py`
