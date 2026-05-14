# workflow-manager 执行架构

## 核心架构

**workflow-manager 的 Python 主程序（executor.py）内部直接调用 agent_pool_client，主 AI 不需要手动调用 agent-pool。**

---

## 代码证据

### 1. executor.py 内置 agent_pool_client 调用

```python
# executor.py 第 842 行
plan = agent_pool_client.execute_full(
    task_description=task_description,
    timeout=300,
    max_iterations=50,
    source_workflow=self.current_workflow_name,
)
```

### 2. agent_pool_client 返回执行计划

```python
# agent_pool_client.py 第 161-173 行
result = {
    "success": True,
    "type": "execution_plan_with_features",
    "agent_id": plan['agent_id'],
    "task_id": plan['task_id'],
    "strategy": plan['strategy'],
    "execution": plan['execution'],
    "instructions": instructions  # ← 执行指令列表
}
```

### 3. instructions 格式

```python
# agent_pool_client.py 第 381-388 行
instructions.append({
    "step": 1,
    "action": "delegate_task",
    "description": "执行子 Agent 任务（含 handoff 自动处理）",
    "params": params,  # ← delegate_task 参数（已注入心跳、handoff、feedback）
    "output_key": "subagent_result",
    "auto_handoff": self.auto_handoff
})
```

---

## 执行流程

```
主 AI 调用 workflow-manager 技能
     ↓
executor.py 加载工作流（loader.load）
     ↓
executor.py 展开嵌套节点（expander.expand）
     ↓
executor.py 分析依赖关系（analyzer.analyze）
     ↓
executor.py 调用 agent_pool_client.execute_full()
     ↓
agent_pool_client 调用 orchestrator.execute()
     ↓
orchestrator 匹配 agent（matcher.match）
     ↓
orchestrator 生成执行计划（含 instructions）
     ↓
agent_pool_client 注入心跳、handoff、feedback 到 context
     ↓
executor.py 返回执行计划给主 AI
     ↓
主 AI 根据 instructions 调用 delegate_task
```

---

## 主 AI 职责边界

| 阶段 | 主 AI 职责 | workflow-manager 内部职责 |
|------|-----------|-------------------------|
| 调用技能 | ✅ 调用 workflow-manager | - |
| 加载工作流 | - | ✅ loader.load() |
| 展开节点 | - | ✅ expander.expand() |
| 分析依赖 | - | ✅ analyzer.analyze() |
| 匹配 agent | - | ✅ agent_pool_client.execute_full() |
| 生成计划 | - | ✅ 返回 instructions |
| 执行指令 | ✅ 根据 instructions 调用 delegate_task | - |
| 汇总结果 | ✅ 汇总执行结果 | - |

---

## 常见误解

### ❌ 错误理解

"主 AI 需要对每个步骤调用 agent-pool 技能匹配 agent"

### ✅ 正确理解

"主 AI 调用 workflow-manager 技能后，workflow-manager 的 Python 代码内部会自动调用 agent_pool_client，返回执行计划，主 AI 只需执行 instructions"

---

## 验证方法

执行工作流时，检查日志是否显示：

```
[AgentPoolClient] execute-full: <任务描述>
[AgentPoolClient] 能力: [...]
[AgentPoolClient] 注入心跳更新指令: workflow=<工作流名>
```

如果看到这些日志，说明 workflow-manager 正确调用了 agent_pool_client。

---

## 相关文件

| 文件 | 路径 | 说明 |
|------|------|------|
| executor.py | `src/core/executor.py` | 工作流执行器，调用 agent_pool_client |
| agent_pool_client.py | `src/core/agent_pool_client.py` | agent-pool 客户端，封装调用逻辑 |
| orchestrator.py | `agent-pool/src/orchestrator.py` | agent-pool 编排器，匹配和执行 |
| matcher.py | `agent-pool/src/matcher.py` | agent 匹配器 |
