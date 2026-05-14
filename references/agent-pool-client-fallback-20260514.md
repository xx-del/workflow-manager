# agent_pool_client 导入失败降级方案

**日期**：2026-05-14
**工作流**：凭证检测
**错误**：ModuleNotFoundError: No module named 'utils'

---

## 错误详情

### 错误信息

```python
>>> from agent_pool_client import AgentPoolClient
Traceback (most recent call last):
  File "<string>", line 2, in <module>
    File "/home/kali/.hermes/skills/openclaw-imports/workflow-manager/src/core/agent_pool_client.py", line 16, in <module>
      from utils.logger import get_logger
ModuleNotFoundError: No module named 'utils'
```

### 错误原因

**agent_pool_client.py 导入了 workflow-manager 内部模块**：

```python
from utils.logger import get_logger
from utils.config import config
```

**问题**：
- 当独立运行 agent_pool_client.py 时，Python 无法找到 utils 模块
- utils 模块位于 workflow-manager/src/ 目录，需要设置 sys.path

---

## 降级方案

### 方案A：使用 delegate_task 替代

**当 agent_pool_client 不可用时，使用 delegate_task 执行工作流节点**：

```python
# 标准方式（如果 agent_pool_client 可用）
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

```python
# 降级方式（使用 delegate_task）
delegate_task(
    goal="执行凭证检测工作流节点1：环境准备（步骤1-7）",
    context={
        "工作目录": "/x/rank/hwxinxisouji/liuliang/autofill-detector/",
        "输入文件": "/x/rank/hwxinxisouji/liuliang/start/dianli.txt"
    },
    role="leaf",
    toolsets=["terminal"]
)
```

**优势**：
- delegate_task 是 Hermes 内置工具，无需导入
- 支持并行执行（通过 tasks 参数）
- 与 agent_pool_client 效果相似（都创建子 agent 执行）

**劣势**：
- 缺少 agent-pool 的智能匹配和向量检索
- 无法利用 agent-pool 的 Handoff 机制
- 无法自动触发 Evolver 优化

### 方案B：修复 sys.path

**在 agent_pool_client.py 开头添加**：

```python
import sys
from pathlib import Path

# 添加 workflow-manager/src 到 sys.path
skill_src = Path(__file__).parent.parent
if str(skill_src) not in sys.path:
    sys.path.insert(0, str(skill_src))

# 然后导入内部模块
from utils.logger import get_logger
from utils.config import config
```

**测试**：
```bash
cd ~/.hermes/skills/openclaw-imports/workflow-manager/src/core
python3 -c "from agent_pool_client import AgentPoolClient; print('OK')"
```

---

## 推荐方案

**短期**：使用方案A（delegate_task 降级）
- 立即可用，无需修改代码
- 功能足够，满足工作流执行需求

**长期**：实施方案B（修复导入）
- 恢复 agent_pool_client 完整功能
- 需要修改代码并测试

---

## 验证标准

**降级成功标准**：
- ✅ 工作流节点能够执行
- ✅ 步骤能够完成
- ✅ 结果文件能够生成

**原方案成功标准**：
- ✅ agent_pool_client 能够导入
- ✅ 能够调用 agent_pool_client.execute()
- ✅ agent-pool 智能匹配生效

---

## 相关文档

- `references/agent-pool-integration-issues.md`：agent-pool 集成问题
- `references/l4-execution-violation-20260514.md`：L4 执行验证标准
