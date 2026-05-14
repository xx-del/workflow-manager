---
name: workflow-manager
description: AI-Native 工作流管理
hooks:
  UserPromptSubmit:
    - hooks: [{type: command, command: bash hooks/workflow-context/handler.sh}]
  PreToolUse:
    - matcher: "terminal|delegate_task|write_file|patch"
      hooks: [{type: command, command: bash hooks/workflow-step-check/handler.sh}]
  PostToolUse:
    - hooks: [{type: command, command: bash hooks/workflow-progress/handler.sh}]
  Stop:
    - hooks: [{type: command, command: bash hooks/workflow-cleanup/handler.sh}]
---

# workflow-manager 使用说明

## 一、快速开始
```bash
python actions/execute.py <工作流名称> --init  # 初始化
python actions/complete.py <工作流名称>        # 完成
```

## 二、agent_pool_client 调用（v2.0）

### 推荐方式
```python
import sys
sys.path.insert(0, '/home/kali/.hermes/skills/openclaw-imports/agent-pool/src')
from orchestrator import Orchestrator

orchestrator = Orchestrator(mode="plan")
result = orchestrator.execute(
    task_description="执行凭证检测节点1：环境准备",
    required_capabilities=["cli_execution"],  # 所需能力
    timeout=300,                              # 超时（秒）
    max_iterations=50,                        # 最大迭代次数
    context={"work_dir": "/path"},
    source_workflow="凭证检测"
)
```

### 适配器方式（向后兼容）
```python
from workflow_agent_pool_adapter import workflow_agent_pool_adapter
result = workflow_agent_pool_adapter.execute(
    workflow_name='凭证检测', node_id=1, node_name='环境准备',
    task_description='验证输入文件', context={'work_dir': '/path'})
```

## 三、参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `task_description` | 必填 | 任务描述 |
| `required_capabilities` | ["cli_execution"] | 所需能力 |
| `timeout` | 300 | 超时（秒） |
| `max_iterations` | 50 | 最大迭代次数 |
| `source_workflow` | None | 来源工作流 |

## 四、⚠️ 废弃参数警告

- `workflow_name` → 使用 `source_workflow`
- `node_id` → 删除（系统自动生成）
- `node_name` → 使用 `task_description`

**迁移指南**: `references/agent-pool-client-migration-v2.md`
**完整优化方案**: `references/agent-pool-integration-optimization-plan.md` (27.9KB, 8个维度)

## 五、降级方案
```python
delegate_task(goal="执行节点", context={"工作目录": "..."}, role="leaf", toolsets=["terminal"])
```

## 六、AI 职责
**必须**：读取 status.md、调用 agent-pool/delegate_task、更新 status.json
**自动**：工作流加载、类型识别、约束注入

## 七、执行约束
**禁止**：修改 WORKFLOW.md 命令、跳过步骤、删除工作流目录
**必须**：使用 agent-pool/delegate_task、验证输出、更新状态

## 八、常用命令
| 命令 | 用途 |
|------|------|
| `actions/execute.py <名称> --init` | 初始化 |
| `actions/complete.py <名称>` | 完成 |
| `actions/validate.py <名称>` | 验证 |
| `actions/execute.py <名称> --init --reset-findings` | 重置问题记录 |

**迁移指南**: `references/agent-pool-client-migration-v2.md`

## 九、问题记录机制 (findings.md)

### 用途
记录工作流执行中遇到的问题，持久化保存，不受 `execute.py --init` 影响。

### 文件位置
`~/.hermes/workflows/{workflow-name}/findings.md`

### 自动记录
- 当步骤执行失败（退出码非0），Hook 脚本自动追加问题记录
- 统计信息（总问题数、已解决、待解决）自动维护

### 手动更新
- 问题解决后，手动更新表格中的"解决方案"和"状态"列
- 工作流完成后，在"经验总结"章节添加 1-3 条关键经验

### 重置问题记录
`execute.py --init --reset-findings` 会删除并重建 `findings.md`，**所有历史记录将被清除**。

### 问题类型说明
| 类型 | 说明 | 示例 |
|------|------|------|
| API 错误 | 外部 API 调用失败 | HTTP 503, 超时 |
| 网络错误 | 连接问题 | SSH 超时, DNS 失败 |
| 权限错误 | 认证失败 | 401, 密钥过期 |
| 数据错误 | 数据格式问题 | JSON 错误, 字段缺失 |
| 逻辑错误 | 工作流逻辑 | 依赖错误, 条件判断 |

**实现细节**: `references/findings-md-mechanism-20260514.md`
