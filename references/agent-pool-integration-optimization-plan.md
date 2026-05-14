# agent_pool集成优化方案（完整版）

**创建时间**: 2026-05-14
**版本**: v2.0
**优先级**: P0
**状态**: 待审计

---

## 一、背景与问题

### 1.1 问题发现

在凭证检测工作流执行验证中发现：

| 问题 | 描述 | 影响 |
|------|------|------|
| **P0** | agent_pool_client参数与技能文档不一致 | 无法使用技能标准调用方式 |
| **P1** | Hook未触发（workflow-step-check） | 约束注入依赖AI手动创建 |
| **P2** | 飞书通知async错误 | 通知失败，不影响核心功能 |

### 1.2 参数不一致详情

**workflow-manager技能文档描述**：
```python
client.execute(
    workflow_name='凭证检测',
    node_id=1,
    node_name='环境准备',
    task_description='...',
    context={...}
)
```

**agent_pool实际API**：
```python
orchestrator.execute(
    task_description='...',
    required_capabilities=['cli_execution'],
    timeout=300,
    max_iterations=50,
    context={...},
    source_workflow='...'
)
```

**参数对比**：

| workflow-manager描述 | agent_pool实际 | 匹配状态 |
|---------------------|---------------|---------|
| workflow_name | ❌ 不存在 | 不匹配 |
| node_id | ❌ 不存在 | 不匹配 |
| node_name | ❌ 不存在 | 不匹配 |
| task_description | ✅ task_description | 匹配 |
| context | ✅ context | 匹配 |
| ❌ 不存在 | required_capabilities | 缺失 |
| ❌ 不存在 | timeout | 缺失 |
| ❌ 不存在 | max_iterations | 缺失 |
| ❌ 不存在 | source_workflow | 缺失 |

---

## 二、优化方案（8个维度）

### 2.1 补充返回结构的完整说明

#### 2.1.1 返回类型分类

| type值 | 含义 | 字段说明 |
|--------|------|---------|
| execution_plan | 执行计划（plan模式） | success, strategy, execution, agent_info |
| direct_result | 直接结果（execute模式） | success, result, agent_id |
| error | 错误信息 | success=false, error, suggestion |
| handoff_detected | 检测到Handoff | success, handoff_info, pending_tasks |
| field_completion_needed | 字段补全请求 | success, missing_fields, suggestions |

#### 2.1.2 完整返回示例

**成功-执行计划**：
```json
{
  "success": true,
  "type": "execution_plan",
  "task_id": "task-xxx",
  "agent_id": "agent-xxx",
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
    "id": "agent-xxx",
    "name": "Specialist: xxx",
    "role": "researcher",
    "capabilities": ["cli_execution", "security"]
  },
  "feedback_required": true,
  "feedback_endpoint": "agent-pool feedback",
  "feedback_payload": {...}
}
```

**错误-能力不匹配**：
```json
{
  "success": false,
  "type": "error",
  "error": "required_capabilities_unavailable",
  "error_message": "所需能力 [web_research, browser_automation] 在现有Agent池中不可用",
  "suggestion": "请使用 --generate 参数生成新Agent，或调整required_capabilities",
  "available_capabilities": ["cli_execution", "data_analysis", "security"],
  "similar_agents": [
    {"id": "agent-xxx", "capabilities": ["cli_execution"], "similarity": 0.75}
  ]
}
```

**错误-参数缺失**：
```json
{
  "success": false,
  "type": "error",
  "error": "missing_required_parameter",
  "error_message": "缺少必需参数: task_description",
  "suggestion": "请提供task_description参数，例如: orchestrator.execute(task_description='你的任务描述')",
  "required_params": ["task_description"],
  "optional_params": ["required_capabilities", "timeout", "context"]
}
```

**错误-超时**：
```json
{
  "success": false,
  "type": "error",
  "error": "timeout_exceeded",
  "error_message": "任务执行超过最大超时时间（300秒）",
  "suggestion": "增加timeout参数，例如: timeout=600",
  "elapsed_time": 300,
  "max_iterations_reached": false
}
```

**Handoff检测**：
```json
{
  "success": true,
  "type": "handoff_detected",
  "handoff_info": {
    "summary": "需要并行处理多个子任务",
    "completed": ["步骤1已完成"],
    "pending_tasks": [
      {"description": "子任务1", "capabilities": ["data_analysis"]},
      {"description": "子任务2", "capabilities": ["data_analysis"]}
    ],
    "final_goal": "汇总所有分析结果"
  },
  "execution": {
    "tool": "delegate_task",
    "params": {
      "tasks": [...]
    }
  }
}
```

---

### 2.2 能力映射表动态推断机制

#### 2.2.1 工作流定义增强

**_index.yaml节点定义**：
```yaml
nodes:
  - id: 1
    name: 环境准备
    type: action
    calls: agent-pool
    required_capabilities: ["cli_execution"]  # 新增字段
    timeout: 300  # 新增字段（可选）
    task_template: "执行凭证检测环境准备"  # 新增字段（可选）
```

#### 2.2.2 动态推断逻辑

```python
def infer_capabilities(node, context):
    """动态推断节点所需能力"""
    
    # 1. 优先使用显式定义
    if node.get('required_capabilities'):
        return node['required_capabilities']
    
    # 2. 根据节点类型推断
    type_to_capabilities = {
        'action': ['cli_execution'],
        'analysis': ['data_analysis'],
        'web_request': ['web_research'],
        'code_gen': ['code_generation'],
        'security': ['cli_execution', 'security']
    }
    
    node_type = node.get('type', 'action')
    capabilities = type_to_capabilities.get(node_type, ['cli_execution'])
    
    # 3. 根据上下文补充
    if context.get('needs_browser'):
        capabilities.append('web_research')
    
    return capabilities
```

#### 2.2.3 默认值与覆盖机制

| 场景 | 默认能力集 | 覆盖方式 |
|------|-----------|---------| 
| 无定义节点 | ["cli_execution"] | required_capabilities字段 |
| 环境准备 | ["cli_execution"] | _index.yaml定义 |
| 执行检测 | ["cli_execution", "security"] | 上下文覆盖 |
| 结果处理 | ["data_analysis"] | _index.yaml定义 |

---

### 2.3 平滑升级与弃用流程

#### 2.3.1 弃用策略

**代码实现**：
```python
import warnings
from typing import Dict, List, Any, Optional

def execute(
    self,
    task_description: str,
    required_capabilities: List[str] = None,
    timeout: int = 300,
    max_iterations: int = 50,
    context: Dict = None,
    source_workflow: str = None,
    # === 废弃参数（v1.x兼容） ===
    workflow_name: str = None,
    node_id: int = None,
    node_name: str = None
) -> Dict[str, Any]:
    """
    执行任务
    
    新参数（推荐）:
        task_description: 任务描述
        required_capabilities: 所需能力列表
        timeout: 超时时间（秒）
        max_iterations: 最大迭代次数
        context: 上下文信息
        source_workflow: 来源工作流
    
    废弃参数（将在v2.0移除）:
        workflow_name: 已废弃，请使用source_workflow
        node_id: 已废弃，任务ID由系统自动生成
        node_name: 已废弃，请使用task_description描述任务
    """
    
    # 检测废弃参数使用
    deprecated_params = []
    if workflow_name is not None:
        deprecated_params.append('workflow_name')
        source_workflow = source_workflow or workflow_name
    
    if node_id is not None:
        deprecated_params.append('node_id')
    
    if node_name is not None:
        deprecated_params.append('node_name')
    
    # 输出弃用警告
    if deprecated_params:
        warnings.warn(
            f"参数 {deprecated_params} 已废弃，将在v2.0版本移除。"
            f"请迁移到新参数：source_workflow, task_description。",
            DeprecationWarning,
            stacklevel=2
        )
        
        # 记录日志（便于排查遗留调用）
        self.logger.warning(
            f"使用了废弃参数: {deprecated_params}",
            extra={
                "deprecated_params": deprecated_params,
                "migration_guide": "https://docs.example.com/migration-v2"
            }
        )
    
    # 执行任务
    return self._orchestrator.execute(
        task_description=task_description,
        required_capabilities=required_capabilities,
        timeout=timeout,
        max_iterations=max_iterations,
        context=context,
        source_workflow=source_workflow
    )
```

#### 2.3.2 迁移检查清单

```markdown
# agent_pool_client v2.0 迁移检查清单

## 必须修改

- [ ] `workflow_name` → `source_workflow`
- [ ] `node_id` → 删除（系统自动生成）
- [ ] `node_name` → `task_description`

## 推荐修改

- [ ] 添加 `required_capabilities` 参数
- [ ] 添加 `timeout` 参数（默认300秒）
- [ ] 添加 `max_iterations` 参数（默认50次）

## 示例迁移

**旧代码（v1.x）**：
```python
client.execute(
    workflow_name='凭证检测',
    node_id=1,
    node_name='环境准备',
    task_description='验证输入文件',
    context={'work_dir': '/path'}
)
```

**新代码（v2.0）**：
```python
client.execute(
    task_description='验证输入文件',
    required_capabilities=['cli_execution'],
    timeout=300,
    context={'work_dir': '/path'},
    source_workflow='凭证检测'
)
```

## 验证步骤

1. 运行单元测试，确认无DeprecationWarning
2. 检查日志中无"使用了废弃参数"警告
3. 验证返回格式符合新规范
```

---

### 2.4 测试覆盖范围扩展

#### 2.4.1 测试矩阵

| 测试维度 | 测试场景 | 预期结果 |
|---------|---------|---------|
| **模式测试** | mode="plan" | 返回execution_plan |
| | mode="execute" | 返回direct_result |
| | mode="execute" + 无delegate_task注入 | 自动降级为plan模式 |
| **参数测试** | 必填参数缺失 | 返回error + suggestion |
| | 废弃参数使用 | DeprecationWarning |
| | 无效能力值 | 返回error + available_capabilities |
| **超时测试** | timeout=1秒 | 超时错误 |
| | timeout=600秒 | 正常执行 |
| **异常测试** | 任务描述为空字符串 | 返回error |
| | required_capabilities=[] | 使用默认能力集 |
| | context=None | 正常执行 |

#### 2.4.2 回归测试用例

```python
import pytest
from orchestrator import Orchestrator

class TestOrchestrator:
    
    def test_plan_mode_success(self):
        """测试plan模式成功场景"""
        o = Orchestrator(mode="plan")
        result = o.execute("测试任务", required_capabilities=["cli_execution"])
        assert result['success'] == True
        assert result['type'] == 'execution_plan'
        assert 'execution' in result
    
    def test_execute_mode_without_delegate_fn(self):
        """测试execute模式无delegate_task注入（降级）"""
        o = Orchestrator(mode="execute")
        result = o.execute("测试任务")
        assert result['mode_degraded'] == True
        assert result['type'] == 'execution_plan'
        assert 'warning' in result
    
    def test_missing_required_parameter(self):
        """测试缺少必填参数"""
        o = Orchestrator(mode="plan")
        with pytest.raises(TypeError) as exc_info:
            o.execute()  # 缺少task_description
        assert "task_description" in str(exc_info.value)
    
    def test_invalid_capabilities(self):
        """测试无效能力值"""
        o = Orchestrator(mode="plan")
        result = o.execute("测试任务", required_capabilities=["invalid_cap"])
        assert result['success'] == False
        assert result['type'] == 'error'
        assert 'available_capabilities' in result
    
    def test_timeout_exceeded(self):
        """测试超时"""
        o = Orchestrator(mode="plan")
        result = o.execute("长时间任务", timeout=1)
        assert result['success'] == False
        assert result['error'] == 'timeout_exceeded'
    
    def test_deprecated_parameters(self):
        """测试废弃参数"""
        o = Orchestrator(mode="plan")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = o.execute(
                "测试任务",
                workflow_name="old_workflow",
                node_id=1,
                node_name="old_node"
            )
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "workflow_name" in str(w[0].message)
```

---

### 2.5 适配器层架构设计

#### 2.5.1 架构方案

```
workflow-manager (调用方)
    ↓ 期望接口: execute(workflow_name, node_id, node_name, ...)
    ↓
WorkflowAgentPoolAdapter (适配器层)
    ↓ 转换接口
    ↓ 实际调用: orchestrator.execute(task_description, required_capabilities, ...)
    ↓
Orchestrator (agent_pool核心)
```

#### 2.5.2 适配器实现

```python
# workflow_agent_pool_adapter.py

from typing import Dict, List, Any, Optional
import sys
sys.path.insert(0, '/home/kali/.hermes/skills/openclaw-imports/agent-pool/src')
from orchestrator import Orchestrator

class WorkflowAgentPoolAdapter:
    """
    工作流- agent_pool适配器
    
    职责：
    1. 将workflow-manager期望的接口转换为agent_pool实际接口
    2. 处理参数映射和能力推断
    3. 提供错误处理和日志记录
    """
    
    def __init__(self):
        self.orchestrator = Orchestrator(mode="plan")
        self.logger = get_logger(__name__)
    
    def execute(
        self,
        workflow_name: str,
        node_id: int,
        node_name: str,
        task_description: str,
        context: Dict = None
    ) -> Dict[str, Any]:
        """
        工作流接口 → agent_pool接口
        
        Args:
            workflow_name: 工作流名称
            node_id: 节点ID
            node_name: 节点名称
            task_description: 任务描述
            context: 上下文信息
        
        Returns:
            执行结果（符合workflow-manager期望格式）
        """
        
        # 1. 推断能力
        required_capabilities = self._infer_capabilities(node_name, context)
        
        # 2. 构建上下文
        enriched_context = {
            **(context or {}),
            'workflow_name': workflow_name,
            'node_id': node_id,
            'node_name': node_name
        }
        
        # 3. 调用orchestrator
        try:
            result = self.orchestrator.execute(
                task_description=task_description,
                required_capabilities=required_capabilities,
                timeout=300,
                context=enriched_context,
                source_workflow=workflow_name
            )
            
            # 4. 转换返回格式（保持workflow-manager兼容）
            return self._adapt_result(result, workflow_name, node_id)
            
        except Exception as e:
            self.logger.error(f"工作流节点执行失败: {workflow_name}/{node_name}", exc_info=True)
            return {
                "success": False,
                "type": "error",
                "error": str(e),
                "workflow_name": workflow_name,
                "node_id": node_id
            }
    
    def _infer_capabilities(self, node_name: str, context: Dict) -> List[str]:
        """推断节点所需能力"""
        
        # 节点名称关键词映射
        keywords_map = {
            '环境': ['cli_execution'],
            '检测': ['cli_execution', 'security'],
            '分析': ['data_analysis'],
            '处理': ['data_analysis'],
            '网络': ['web_research'],
            '代码': ['code_generation']
        }
        
        # 匹配关键词
        for keyword, capabilities in keywords_map.items():
            if keyword in node_name:
                return capabilities
        
        # 默认能力
        return ['cli_execution']
    
    def _adapt_result(self, result: Dict, workflow_name: str, node_id: int) -> Dict:
        """转换返回格式"""
        
        # 保持workflow-manager期望的字段
        adapted = {
            **result,
            'workflow_name': workflow_name,
            'node_id': node_id
        }
        
        return adapted

# 全局实例（workflow-manager可直接导入）
workflow_agent_pool_adapter = WorkflowAgentPoolAdapter()
```

#### 2.5.3 使用示例

**workflow-manager调用**：
```python
from workflow_agent_pool_adapter import workflow_agent_pool_adapter

# 使用适配器（符合workflow-manager接口）
result = workflow_agent_pool_adapter.execute(
    workflow_name='凭证检测',
    node_id=1,
    node_name='环境准备',
    task_description='验证输入文件、检查工作目录、安装Node.js依赖',
    context={'work_dir': '/x/rank/...'}
)

print(result['workflow_name'])  # 凭证检测
print(result['node_id'])  # 1
print(result['execution']['tool'])  # delegate_task
```

---

### 2.6 开发者迁移指南

#### 2.6.1 代码迁移对比

**场景1：工作流节点执行**

**旧代码（v1.x - agent_pool_client）**：
```python
from agent_pool_client import AgentPoolClient

client = AgentPoolClient()
result = client.execute(
    workflow_name='凭证检测',
    node_id=1,
    node_name='环境准备',
    task_description='验证输入文件',
    context={'work_dir': '/path'}
)
```

**新代码（v2.0 - 直接使用orchestrator）**：
```python
import sys
sys.path.insert(0, '/home/kali/.hermes/skills/openclaw-imports/agent-pool/src')
from orchestrator import Orchestrator

orchestrator = Orchestrator(mode="plan")
result = orchestrator.execute(
    task_description='验证输入文件',
    required_capabilities=['cli_execution'],
    timeout=300,
    context={'work_dir': '/path'},
    source_workflow='凭证检测'
)
```

**新代码（v2.0 - 使用适配器）**：
```python
from workflow_agent_pool_adapter import workflow_agent_pool_adapter

result = workflow_agent_pool_adapter.execute(
    workflow_name='凭证检测',
    node_id=1,
    node_name='环境准备',
    task_description='验证输入文件',
    context={'work_dir': '/path'}
)
```

**场景2：批量并行执行**

**旧代码**：
```python
client = AgentPoolClient()
tasks = [
    {'node_id': 1, 'node_name': '任务1', ...},
    {'node_id': 2, 'node_name': '任务2', ...}
]
results = client.batch_execute(tasks)
```

**新代码**：
```python
orchestrator = Orchestrator(mode="plan")
tasks = [
    {'description': '任务1', 'required_capabilities': ['cli_execution']},
    {'description': '任务2', 'required_capabilities': ['cli_execution']}
]
result = orchestrator.batch_execute(tasks, parallel=True)
# 返回: {"type": "tool_call_request", "tool": "delegate_task", "params": {"tasks": [...]}}
```

#### 2.6.2 context参数最佳实践

**推荐传递的数据结构**：
```python
context = {
    # 工作流上下文（必需）
    'workflow_name': '凭证检测',
    'node_id': 1,
    'node_name': '环境准备',
    
    # 上一步输出（可选，用于步骤间传递）
    'previous_step_output': {
        'input_file': '/path/to/file',
        'result_url': 'http://...'
    },
    
    # 环境信息（可选）
    'work_dir': '/x/rank/hwxinxisouji/liuliang/autofill-detector/',
    'input_file': '/x/rank/hwxinxisouji/liuliang/start/dianli.txt',
    
    # 配置信息（可选）
    'config': {
        'max_retries': 3,
        'timeout': 600
    }
}
```

**特殊键名约定**：
- `previous_step_output`：上一步输出结果
- `work_dir`：工作目录
- `input_file` / `output_file`：输入/输出文件路径
- `config`：配置信息字典

---

### 2.7 异步场景与长任务支持

#### 2.7.1 当前能力分析

**同步模式限制**：
- execute() 是同步阻塞调用
- 长时间任务会阻塞主线程
- 无job_id和轮询机制

**适用场景**：
- 短时间任务（< 5分钟）
- 批量并行任务（delegate_task处理）
- 有明确超时限制的任务

**不适用场景**：
- 超长时间任务（> 30分钟）
- 需要实时进度反馈的任务
- 需要中途取消的任务

#### 2.7.2 异步扩展设计（预留）

```python
# 异步执行接口（未来扩展）
def execute_async(
    task_description: str,
    required_capabilities: List[str] = None,
    timeout: int = 300,
    callback_url: str = None  # 完成回调
) -> Dict[str, Any]:
    """
    异步执行任务
    
    Returns:
        {
            "success": true,
            "job_id": "job-xxx",
            "status": "running",
            "polling_endpoint": "/api/jobs/job-xxx/status"
        }
    """

# 轮询接口（未来扩展）
def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    查询任务状态
    
    Returns:
        {
            "job_id": "job-xxx",
            "status": "running" | "completed" | "failed",
            "progress": 0.75,
            "result": {...}  # 如果completed
        }
    """
```

#### 2.7.3 推荐值与调整说明

| 参数 | 默认值 | 推荐范围 | 说明 |
|------|--------|---------|------|
| timeout | 300秒 | 60-600秒 | 根据任务复杂度调整 |
| max_iterations | 50次 | 10-100次 | 防止无限循环 |
| required_capabilities | - | - | 建议显式指定，避免推断错误 |

**调整示例**：
```python
# 短任务（文件验证）
result = orchestrator.execute(
    "验证输入文件",
    required_capabilities=['cli_execution'],
    timeout=60  # 1分钟足够
)

# 中等任务（依赖安装）
result = orchestrator.execute(
    "安装Node.js依赖",
    required_capabilities=['cli_execution'],
    timeout=300  # 5分钟
)

# 长任务（批量检测）
result = orchestrator.execute(
    "检测100个URL的凭证",
    required_capabilities=['cli_execution', 'security'],
    timeout=600,  # 10分钟
    max_iterations=100  # 允许更多迭代
)
```

---

### 2.8 安全性与鉴权说明

#### 2.8.1 敏感信息保护

**禁止在任务描述中传递**：
- ❌ 密码、密钥、Token
- ❌ 完整URL（含认证信息）
- ❌ 数据库连接字符串

**推荐方式**：
```python
# ❌ 错误：在任务描述中泄露密码
task_description = "使用密码password123连接数据库"

# ✅ 正确：通过context传递，并标记为敏感
context = {
    'db_config': {
        'host': 'localhost',
        'port': 5432,
        'username': 'admin',
        'password_ref': 'env://DB_PASSWORD'  # 引用环境变量
    }
}
```

#### 2.8.2 认证信息传递

**环境变量注入**（推荐）：
```python
# 在调用前设置环境变量
os.environ['API_TOKEN'] = 'xxx'

# context中引用环境变量
context = {
    'api_config': {
        'endpoint': 'https://api.example.com',
        'token_ref': 'env://API_TOKEN'
    }
}
```

**Orchestrator自动读取**：
- orchestrator会从系统环境变量读取常见认证信息
- 如：`HTTP_PROXY`, `HTTPS_PROXY`, `API_KEY`等
- 无需在context中显式传递

#### 2.8.3 权限隔离

**能力级别的权限控制**：
```python
# 低风险能力
['cli_execution', 'data_analysis']

# 中风险能力
['web_research', 'code_generation']

# 高风险能力（需要额外权限）
['security', 'automation', 'cronjob']
```

**权限检查机制**：
```python
# orchestrator内部会检查权限
if 'security' in required_capabilities:
    if not context.get('security_clearance'):
        return {
            "success": False,
            "type": "error",
            "error": "insufficient_permissions",
            "error_message": "需要安全审计权限才能执行此任务",
            "suggestion": "请在context中提供security_clearance凭证"
        }
```

---

## 三、实施计划

### 3.1 P0（立即执行）

| 任务 | 文件位置 | 审计要点 | 预计耗时 |
|------|---------|---------|---------|
| 创建适配器 | workflow_agent_pool_adapter.py | 参数映射、能力推断、错误处理 | 2小时 |
| 补充返回结构说明 | agent-pool-integration-optimization-plan.md | 类型完整性、错误场景覆盖 | 1小时 |
| 编写迁移检查清单 | agent-pool-client-migration-v2.md | 步骤完整性、示例准确性 | 1小时 |

### 3.2 P1（本周完成）

| 任务 | 文件位置 | 审计要点 | 预计耗时 |
|------|---------|---------|---------|
| 实现能力推断机制 | capability_inference.yaml | 规则合理性、默认值合理性 | 2小时 |
| 扩展测试覆盖 | test_agent_pool_adapter.py | 场景覆盖、断言准确性 | 3小时 |
| 增强CLI帮助 | agent-pool CLI | 参数说明、示例准确性 | 1小时 |

### 3.3 P2（迭代优化）

| 任务 | 文件位置 | 审计要点 | 预计耗时 |
|------|---------|---------|---------|
| 预留异步接口 | orchestrator.py | 接口设计、扩展性 | 4小时 |
| 完善安全审计 | orchestrator.py | 权限检查、敏感信息保护 | 2小时 |

---

## 四、方案对比

### 4.1 方案A：适配器层

**优点**：
- ✅ 零侵入（不修改agent_pool_client）
- ✅ 隔离接口变更
- ✅ 易于测试
- ✅ 符合设计模式

**缺点**：
- ⚠️ 增加一层抽象
- ⚠️ 需要维护额外文件

**适用场景**：
- 多个项目依赖agent_pool_client
- 需要长期维护
- 需要灵活切换实现

---

### 4.2 方案B：直接修复

**优点**：
- ✅ 直接解决问题
- ✅ 无额外抽象
- ✅ 代码简洁

**缺点**：
- ⚠️ 可能影响其他依赖方
- ⚠️ 需要修改现有代码
- ⚠️ 需要全面回归测试

**适用场景**：
- 单一项目依赖
- 可以接受破坏性变更
- 有完整的测试覆盖

---

### 4.3 推荐方案

**推荐：方案A（适配器层）**

**理由**：
1. workflow-manager是独立技能，但agent_pool_client可能被其他地方使用
2. 适配器层提供了更好的隔离性
3. 易于测试和维护
4. 符合开闭原则（对扩展开放，对修改关闭）

---

## 五、风险与缓解

### 5.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 适配器性能开销 | 低 | 低 | 性能测试，优化关键路径 |
| 能力推断不准确 | 中 | 中 | 提供显式覆盖机制 |
| 废弃参数误用 | 低 | 中 | DeprecationWarning + 日志 |

### 5.2 兼容性风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 旧代码无法运行 | 高 | 低 | 保留废弃参数兼容 |
| 返回格式变更 | 中 | 低 | 保持向后兼容字段 |
| 文档不一致 | 中 | 中 | 同步更新所有文档 |

---

## 六、验收标准

### 6.1 功能验收

- [ ] 适配器正确转换接口
- [ ] 能力推断准确率 ≥ 95%
- [ ] 废弃参数正常工作 + 警告
- [ ] 所有测试用例通过

### 6.2 性能验收

- [ ] 适配器性能开销 < 50ms
- [ ] 执行时间与直接调用相差 < 5%

### 6.3 文档验收

- [ ] 迁移指南完整
- [ ] API文档更新
- [ ] 示例代码可运行

---

## 七、附录

### 7.1 相关文件位置

**agent_pool核心文件**：
- `~/.hermes/skills/openclaw-imports/agent-pool/src/orchestrator.py`
- `~/.hermes/skills/openclaw-imports/agent-pool/src/matcher.py`
- `~/.hermes/skills/openclaw-imports/agent-pool/src/generator.py`
- `~/.hermes/skills/openclaw-imports/agent-pool/src/registry.py`

**workflow-manager文件**：
- `~/.hermes/skills/openclaw-imports/workflow-manager/src/core/agent_pool_client.py`
- `~/.hermes/skills/openclaw-imports/workflow-manager/SKILL.md`

**工作流定义示例**：
- `~/.hermes/workflows/凭证检测/_index.yaml`
- `~/.hermes/workflows/凭证检测/WORKFLOW.md`

### 7.2 参考资料

- agent_pool API文档：`~/.hermes/skills/openclaw-imports/agent-pool/references/api.md`
- workflow-manager技能文档：`~/.hermes/skills/openclaw-imports/workflow-manager/SKILL.md`
- Hermes双重Hook机制：`~/.hermes/skills/openclaw-imports/workflow-manager/references/hermes-dual-hook-mechanism-20260514.md`

---

**文档版本**: v2.0
**最后更新**: 2026-05-14
**作者**: AI Agent
**审核状态**: 待用户审计
