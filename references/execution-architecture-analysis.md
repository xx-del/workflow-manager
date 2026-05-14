# workflow-manager 执行架构分析

**日期**: 2026-05-09
**版本**: v4.6.0
**分析方法**: 代码深度分析 + 执行流程追踪

---

## 核心发现

### 1. executor.py 内置了 agent-pool 调用

**代码证据**：

```python
# executor.py 第 842 行
plan = agent_pool_client.execute_full(
    task_description=task_description,
    timeout=300,
    max_iterations=50,
    source_workflow=self.current_workflow_name,
)
```

**结论**：workflow-manager 的 Python 主程序（executor.py）内部直接调用 agent_pool_client，主 AI **不需要也不应该**手动调用 agent-pool。

---

### 2. 实际执行流程（代码验证）

```
主 AI 调用 workflow-manager 技能
     ↓
executor.execute() 自动执行：
     ├─ [1/6] 加载工作流（loader.load）
     ├─ [2/6] 展开嵌套节点（workflow_expander.expand）
     ├─ [3/6] 分析步骤依赖（analyzer.analyze）
     ├─ [4/6] 调用 agent-pool（agent_pool_client.execute_full）
     └─ [5/6] 返回 pending_instructions
     ↓
主 AI 执行：
     ├─ 执行 pending_instructions 中的每条指令
     ├─ 更新追踪状态（executor.update_step_status）
     ├─ 汇总结果
     └─ 调用 finalize 停止心跳
```

---

### 3. 返回值结构

```python
{
    'status': 'execution_required',  # ← 表示需要主 AI 执行
    'pending_instructions': [...],   # ← 主 AI 必须执行这些指令
    'execution_status': 'awaiting_delegate_task',
    'execution_mode': {
        'type': 'strict_serial',
        'delegate_task_usage': 'single'
    },
    'ai_action_required': {
        'tool': 'delegate_task',
        'usage': '逐个调用 delegate_task(task=...)'
    }
}
```

---

## 主 AI 职责边界

| 阶段 | 执行者 | 操作 |
|------|--------|------|
| **调用技能** | 主 AI | 调用 workflow-manager 技能 |
| **加载工作流** | executor.py | loader.load(workflow_name) |
| **展开节点** | executor.py | workflow_expander.expand() |
| **分析依赖** | executor.py | analyzer.analyze() |
| **调用 agent-pool** | executor.py | agent_pool_client.execute_full() |
| **生成指令** | executor.py | 构建 instructions 列表 |
| **返回计划** | executor.py | 返回 pending_instructions |
| **执行指令** | 主 AI | 调用 delegate_task 执行每条指令 |
| **更新状态** | 主 AI | 调用 executor.update_step_status() |
| **汇总结果** | 主 AI | 生成执行报告 |
| **停止心跳** | 主 AI | 调用 actions/complete.py |

---

## 常见误解纠正

### ❌ 错误理解

```
执行前验证清单：
- [ ] 已通过 agent-pool 技能匹配 agent
- [ ] 已调用 delegate_task 执行每个步骤
```

### ✅ 正确理解

```
执行前验证清单：
- [x] 已调用 workflow-manager 技能
- [x] 已收到执行计划（包含 pending_instructions）
- [ ] 已执行 pending_instructions 中的每条指令
- [ ] 已汇总执行结果
```

---

## 关键文件

| 文件 | 职责 |
|------|------|
| `src/core/executor.py` | 工作流执行器，内置 agent_pool_client 调用 |
| `src/core/agent_pool_client.py` | agent-pool 客户端，返回执行计划 |
| `src/core/analyzer.py` | 步骤依赖分析器 |
| `src/expander.py` | 嵌套节点展开器 |

---

## 验证方法

在机制测试v2工作流的验证清单中：

```markdown
- [ ] 日志显示 `[AgentPoolClient]` → agent-pool执行成功
```

这是**正确的验证方式**：检查日志输出，而非要求主 AI 手动调用。
