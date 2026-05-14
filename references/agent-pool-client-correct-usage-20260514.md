# agent_pool 正确调用方法

**日期**：2026-05-14
**发现来源**：凭证检测工作流执行验证
**重要性**：P0（技能文档错误）

---

## 核心发现

**workflow-manager 技能文档描述的参数与 agent_pool 实际 API 不一致。**

---

## 错误的文档描述

**workflow-manager 技能文档**：

```python
from agent_pool_client import AgentPoolClient

client = AgentPoolClient()
result = client.execute(
    workflow_name='凭证检测',
    node_id=1,
    node_name='环境准备',
    task_description='...',
    context={...}
)
```

**❌ 上述参数不存在！**

---

## 实际 API

### 方法1：直接使用 Orchestrator

```python
import sys
sys.path.insert(0, '/home/kali/.hermes/skills/openclaw-imports/agent-pool/src')

from orchestrator import Orchestrator

# 创建编排器（plan 模式）
orchestrator = Orchestrator(mode="plan")

# 执行任务
result = orchestrator.execute(
    task_description="执行凭证检测工作流节点1：环境准备",
    required_capabilities=["cli_execution"],  # 关键参数
    timeout=300,
    max_iterations=50,
    context={...},
    source_workflow="凭证检测"  # 可选
)
```

### 方法2：CLI 命令

```bash
python ~/.hermes/skills/openclaw-imports/agent-pool/bin/agent-pool \
  execute "任务描述" \
  --capabilities cli_execution \
  --json
```

---

## 参数对比表

| workflow-manager 描述 | agent_pool 实际 | 匹配 |
|---------------------|----------------|------|
| workflow_name | ❌ 不存在 | 不匹配 |
| node_id | ❌ 不存在 | 不匹配 |
| node_name | ❌ 不存在 | 不匹配 |
| task_description | ✅ task_description | 匹配 |
| context | ✅ context | 匹配 |
| ❌ 缺失 | required_capabilities | **必需** |
| ❌ 缺失 | timeout | 可选 |
| ❌ 缺失 | max_iterations | 可选 |
| ❌ 缺失 | source_workflow | 可选 |

---

## 能力映射表

根据测试结果，agent_pool 使用 `required_capabilities` 参数：

| 工作流节点类型 | required_capabilities | toolsets |
|--------------|----------------------|----------|
| 环境准备 | `["cli_execution"]` | `["terminal", "file"]` |
| 执行检测 | `["cli_execution", "security"]` | `["terminal", "file"]` |
| 结果处理 | `["data_analysis"]` | `["terminal", "file"]` |
| 网络请求 | `["web_research"]` | `["web", "browser"]` |
| 代码生成 | `["code_generation"]` | `["terminal", "file"]` |

---

## 返回格式

```python
{
  "success": True,
  "type": "execution_plan",
  "task_id": "task-1778745313",
  "agent_id": "...",
  "strategy": "reuse_specialist",
  "execution": {
    "type": "tool_call_request",
    "tool": "delegate_task",
    "params": {
      "goal": "...",
      "context": "...",
      "toolsets": ["terminal", "file"],
      "max_iterations": 50
    }
  },
  "agent_info": {
    "id": "...",
    "name": "Specialist: credential_detection",
    "role": "researcher",
    "capabilities": [...]
  }
}
```

---

## 工作流集成示例

### 正确的工作流节点执行函数

```python
import sys
sys.path.insert(0, '/home/kali/.hermes/skills/openclaw-imports/agent-pool/src')
from orchestrator import Orchestrator

def execute_workflow_node(workflow_name, node_id, node_name, task_description, context):
    """工作流节点执行函数（修正版）"""
    
    # 推断能力需求
    capabilities_map = {
        "环境准备": ["cli_execution"],
        "执行检测": ["cli_execution", "security"],
        "结果处理": ["data_analysis"]
    }
    
    # 创建编排器
    orchestrator = Orchestrator(mode="plan")
    
    # 执行任务
    result = orchestrator.execute(
        task_description=task_description,
        required_capabilities=capabilities_map.get(node_name, ["cli_execution"]),
        timeout=300,
        context=context,
        source_workflow=workflow_name
    )
    
    # 返回执行计划
    return result
```

### 降级方案（当 agent_pool 不可用时）

```python
# 直接使用 delegate_task
delegate_task(
    goal=f"执行工作流节点：{node_name}",
    context={"工作目录": "...", "输入文件": "..."},
    role="leaf",
    toolsets=["terminal"]
)
```

---

## 测试验证

**测试代码**：
```python
import sys
sys.path.insert(0, '/home/kali/.hermes/skills/openclaw-imports/agent-pool/src')
from orchestrator import Orchestrator

o = Orchestrator(mode="plan")
result = o.execute(
    "执行凭证检测工作流节点1：环境准备",
    required_capabilities=["cli_execution"],
    timeout=300
)

print(result['execution']['tool'])  # 输出: delegate_task
print(result['execution']['params']['goal'])  # 输出: 完整任务描述
```

**测试结果**：✅ 成功

---

## 修复建议

**优先级 P0**：更新 workflow-manager 技能文档

**方案**：
1. 删除错误的参数描述（workflow_name, node_id, node_name）
2. 添加正确的参数说明（required_capabilities, timeout）
3. 添加能力映射表
4. 提供正确调用示例

**替代方案**：
修复 agent_pool_client.py，添加兼容层：
```python
def execute(self, task_description, required_capabilities=None, timeout=300,
            max_iterations=50, context=None, source_workflow=None,
            # 兼容旧参数（废弃）
            workflow_name=None, node_id=None, node_name=None):
    if source_workflow is None and workflow_name:
        source_workflow = workflow_name
        self.logger.warning("workflow_name 参数已废弃，请使用 source_workflow")
    
    return self._orchestrator.execute(
        task_description=task_description,
        required_capabilities=required_capabilities,
        timeout=timeout,
        max_iterations=max_iterations,
        context=context,
        source_workflow=source_workflow
    )
```

---

## 相关文档

- `references/agent-pool-client-fallback-20260514.md`：导入失败降级方案
- `references/l4-execution-violation-20260514.md`：L4 执行验证标准
- agent-pool 技能 `references/api.md`：agent-pool API 参考
