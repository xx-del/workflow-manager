# agent_pool_client v2.0 迁移检查清单

**创建时间**: 2026-05-14
**版本**: v2.0
**优先级**: P0

---

## 一、迁移概览

### 1.1 迁移原因

agent_pool_client参数与agent_pool实际API不一致，需要迁移到新接口。

### 1.2 影响范围

- workflow-manager技能
- 所有使用agent_pool_client的代码
- 工作流定义文件（_index.yaml）

### 1.3 迁移时间表

| 阶段 | 时间 | 任务 |
|------|------|------|
| v1.x兼容期 | 2026-05-14起 | 保留废弃参数 + DeprecationWarning |
| v2.0迁移期 | 2026-05-14 - 2026-06-14 | 逐步迁移到新参数 |
| v2.0正式版 | 2026-06-15起 | 移除废弃参数 |

---

## 二、参数映射表

### 2.1 必须修改

| 旧参数（v1.x） | 新参数（v2.0） | 说明 |
|--------------|---------------|------|
| `workflow_name` | `source_workflow` | 来源工作流名称 |
| `node_id` | 删除 | 任务ID由系统自动生成 |
| `node_name` | `task_description` | 任务描述 |

### 2.2 推荐新增

| 新参数 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `required_capabilities` | List[str] | ["cli_execution"] | 所需能力列表 |
| `timeout` | int | 300 | 超时时间（秒） |
| `max_iterations` | int | 50 | 最大迭代次数 |

---

## 三、代码迁移示例

### 3.1 工作流节点执行

**旧代码（v1.x）**：
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

**新代码（v2.0 - 方式1：直接使用orchestrator）**：
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

**新代码（v2.0 - 方式2：使用适配器）**：
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

---

### 3.2 批量并行执行

**旧代码**：
```python
client = AgentPoolClient()
tasks = [
    {'node_id': 1, 'node_name': '任务1', 'task_description': '...'},
    {'node_id': 2, 'node_name': '任务2', 'task_description': '...'}
]
results = client.batch_execute(tasks)
```

**新代码**：
```python
orchestrator = Orchestrator(mode="plan")
tasks = [
    {
        'description': '任务1描述',
        'required_capabilities': ['cli_execution']
    },
    {
        'description': '任务2描述',
        'required_capabilities': ['cli_execution']
    }
]
result = orchestrator.batch_execute(tasks, parallel=True)
# 返回: {"type": "tool_call_request", "tool": "delegate_task", "params": {"tasks": [...]}}
```

---

### 3.3 工作流定义文件

**旧定义（_index.yaml v1.x）**：
```yaml
nodes:
  - id: 1
    name: 环境准备
    type: action
    calls: agent-pool
```

**新定义（_index.yaml v2.0）**：
```yaml
nodes:
  - id: 1
    name: 环境准备
    type: action
    calls: agent-pool
    required_capabilities: ["cli_execution"]  # 新增
    timeout: 300  # 新增（可选）
    task_template: "执行凭证检测环境准备"  # 新增（可选）
```

---

## 四、迁移检查清单

### 4.1 代码检查

- [ ] **搜索所有使用agent_pool_client的地方**
  ```bash
  grep -r "from agent_pool_client import" ~/.hermes/skills/
  grep -r "AgentPoolClient()" ~/.hermes/skills/
  ```

- [ ] **检查废弃参数使用**
  ```bash
  grep -r "workflow_name=" ~/.hermes/skills/
  grep -r "node_id=" ~/.hermes/skills/
  grep -r "node_name=" ~/.hermes/skills/
  ```

- [ ] **逐个文件迁移**
  - [ ] workflow-manager/SKILL.md
  - [ ] workflow-manager/src/core/agent_pool_client.py
  - [ ] 其他使用agent_pool_client的文件

### 4.2 测试检查

- [ ] **运行单元测试**
  ```bash
  pytest ~/.hermes/skills/openclaw-imports/workflow-manager/tests/
  ```

- [ ] **检查DeprecationWarning**
  - 确认无废弃参数警告
  - 确认日志中无"使用了废弃参数"警告

- [ ] **验证返回格式**
  - 确认返回格式符合新规范
  - 确认所有字段都存在

### 4.3 文档检查

- [ ] **更新API文档**
  - [ ] 更新workflow-manager/SKILL.md
  - [ ] 更新agent_pool/references/api.md

- [ ] **更新示例代码**
  - [ ] 更新所有代码示例
  - [ ] 验证示例可运行

- [ ] **更新工作流定义**
  - [ ] 更新所有_index.yaml文件
  - [ ] 添加required_capabilities字段

---

## 五、验证步骤

### 5.1 功能验证

1. **执行测试工作流**
   ```bash
   cd ~/.hermes/skills/openclaw-imports/workflow-manager
   python actions/execute.py 凭证检测 --init
   ```

2. **检查执行结果**
   - 确认工作流正常执行
   - 确认返回结果正确
   - 确认无错误或警告

3. **检查日志**
   ```bash
   tail -f ~/.hermes/logs/workflow-manager.log
   ```

### 5.2 性能验证

1. **执行基准测试**
   ```python
   import time
   start = time.time()
   result = orchestrator.execute("测试任务", required_capabilities=['cli_execution'])
   elapsed = time.time() - start
   print(f"执行时间: {elapsed}秒")
   ```

2. **对比性能**
   - 对比新旧接口执行时间
   - 确认性能差异 < 5%

---

## 六、回滚计划

### 6.1 回滚条件

如果迁移后发现以下问题，应回滚：

- 工作流无法执行
- 性能下降 > 10%
- 数据丢失或损坏

### 6.2 回滚步骤

1. **恢复旧代码**
   ```bash
   cd ~/.hermes/skills/openclaw-imports/workflow-manager
   git checkout HEAD~1 src/core/agent_pool_client.py
   ```

2. **恢复工作流定义**
   ```bash
   git checkout HEAD~1 workflows/*/index.yaml
   ```

3. **验证回滚**
   - 执行测试工作流
   - 确认功能正常

---

## 七、常见问题

### Q1: 为什么要移除node_id参数？

**A**: node_id是内部实现细节，任务ID由系统自动生成，不需要用户指定。移除后可以：
- 避免ID冲突
- 简化接口
- 提高灵活性

### Q2: required_capabilities如何推断？

**A**: 有三种方式：
1. **显式指定**：在_index.yaml中定义required_capabilities字段
2. **关键词推断**：根据节点名称中的关键词自动推断
3. **默认值**：使用["cli_execution"]作为默认值

### Q3: 旧代码还能运行吗？

**A**: v1.x兼容期内（2026-05-14 - 2026-06-14），旧代码仍可运行，但会输出DeprecationWarning。v2.0正式版后，废弃参数将被移除。

### Q4: 如何选择直接使用orchestrator还是使用适配器？

**A**: 
- **直接使用orchestrator**：适合新项目，无历史包袱
- **使用适配器**：适合现有项目，保持向后兼容

---

## 八、联系与支持

### 8.1 问题反馈

如果在迁移过程中遇到问题，请：

1. 查看日志：`~/.hermes/logs/workflow-manager.log`
2. 查看文档：`~/.hermes/skills/openclaw-imports/workflow-manager/references/agent-pool-integration-optimization-plan.md`
3. 提交Issue：https://github.com/your-repo/issues

### 8.2 迁移支持

- 文档位置：`~/.hermes/skills/openclaw-imports/workflow-manager/references/`
- 示例代码：`~/.hermes/skills/openclaw-imports/workflow-manager/examples/`
- 测试用例：`~/.hermes/skills/openclaw-imports/workflow-manager/tests/`

---

**文档版本**: v2.0
**最后更新**: 2026-05-14
