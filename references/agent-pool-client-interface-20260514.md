# Agent Pool Client 接口说明

**文档日期**: 2026-05-14
**问题**: 技能文档与实际代码不一致

---

## 问题发现

在凭证检测工作流执行中，发现 `agent_pool_client.execute()` 的实际方法签名与技能文档描述不一致。

---

## 实际方法签名

```python
execute(
    task_description: str,           # 任务描述（必需）
    required_capabilities: List[str] = None,  # 所需能力
    timeout: int = 300,              # 超时秒数
    max_iterations: int = 50,        # 最大迭代次数
    context: Dict = None,            # 上下文信息
    source_workflow: str = None      # 来源工作流
) -> Dict[str, Any]
```

---

## 技能文档中的错误描述

```python
# ❌ 技能文档中描述（错误）
client.execute(
    workflow_name='凭证检测',
    node_id=1,
    node_name='环境准备',
    task_description='...',
    context={...}
)
```

**问题**: 不存在 `workflow_name`, `node_id`, `node_name` 参数

---

## 正确使用方式

### 方式1: 直接调用（推荐）

```python
from agent_pool_client import AgentPoolClient

client = AgentPoolClient()
result = client.execute(
    task_description='执行环境准备工作',
    context={'work_dir': '/path/to/workdir'}
)
```

### 方式2: 降级方案（delegate_task）

如果 `agent_pool_client` 不可用或参数不匹配，使用 `delegate_task`:

```python
delegate_task(
    goal='执行环境准备工作',
    context={'工作目录': '/path/to/workdir'},
    role='leaf',
    toolsets=['terminal']
)
```

---

## 导入问题修复

**问题**: `ModuleNotFoundError: No module named 'utils'`

**原因**: agent_pool_client.py 依赖 workflow-manager 内部模块，独立运行时缺少 sys.path 设置

**修复**: 在 `src/core/agent_pool_client.py` 第15-16行之间添加：

```python
# 添加src目录到sys.path（支持独立运行）
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
```

**验证**:
```bash
cd ~/.hermes/skills/openclaw-imports/workflow-manager/src/core
python3 -c "from agent_pool_client import AgentPoolClient; print('✅ 导入成功')"
```

---

## 建议修复优先级

### P0（阻塞）
- **更新技能文档**: 使 agent_pool_client 调用示例与实际接口一致
- **或修改代码接口**: 使代码支持 workflow_name, node_id 等参数（向后兼容）

### 影响
- 当前状态：无法使用技能文档中的标准调用方式
- 降级方案：使用 delegate_task 替代
- 功能影响：工作流仍可执行，但偏离技能标准

---

## 测试记录

**日期**: 2026-05-14
**工作流**: 凭证检测
**结果**: 使用 delegate_task 降级执行成功

**功能完美度**: 79/100
- agent_pool_client 得分: 0%（接口不一致）
- 其他功能正常

---

## 相关文档

- `references/agent-pool-client-fallback-20260514.md` - 导入失败降级方案
- `src/core/agent_pool_client.py` - 源代码位置
