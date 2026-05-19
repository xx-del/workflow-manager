# 断点工作流类型注入修复

## 问题描述

拼接工作流展开时，`expander.py` 只解析 WORKFLOW.md，忽略 _index.yaml 的节点类型信息，导致断点步骤丢失 `type` 和 `trigger` 字段。

## 根本原因

`parse_workflow_steps_full()` 只读取 WORKFLOW.md 的纯文本步骤，不读取 _index.yaml 的节点定义：
- 节点类型（breakpoint/auto）丢失
- 触发器（trigger: heartbeat）丢失
- 主AI无法识别断点，导致工作流串行执行失败

## 解决方案

### 核心修改

`expander.py` 增加节点类型注入逻辑：

```python
def load_node_definitions(workflow_path):
    """从 _index.yaml 加载节点定义"""
    index_yaml = workflow_path / '_index.yaml'
    if not index_yaml.exists():
        return []
    with open(index_yaml, encoding='utf-8') as f:
        index = yaml.safe_load(f)
    return index.get('nodes', [])

def match_step_to_node(step, node):
    """判断步骤归属节点（一对多映射）"""
    step_name = step.get('name', '')
    node_task = node.get('task', '')
    
    # 规则1：步骤名称包含节点任务（最高优先级）
    if node_task and node_task in step_name:
        if node.get('type') != 'breakpoint':
            return True
    
    # 规则4：断点节点必须明确匹配
    if node.get('type') == 'breakpoint':
        if ('启动心跳' in step_name or '核心断点' in step_name):
            return True
    
    return False

def inject_node_type(step, node):
    """注入节点类型信息"""
    step['type'] = node.get('type', 'action')
    step['trigger'] = node.get('trigger')
    step['node_id'] = node.get('id')
    step['node_name'] = node.get('name')
    return step
```

### 映射规则

_index.yaml 节点与 WORKFLOW.md 步骤是**一对多**映射：

```
_index.yaml节点        WORKFLOW.md步骤         步骤数
────────────────────────────────────────────────────
step_1 (启动扫描)   →  步骤0-5              →  6步骤
step_2 (断点返回)   →  步骤5.5             →  1步骤
step_3 (WIH下载)    →  步骤6               →  1步骤
```

### 匹配陷阱

**错误模式**：规则过于宽泛导致一个步骤匹配多个节点
```python
# ❌ 错误：所有包含"心跳"的步骤都匹配断点节点
if '心跳' in step_name:
    return True
```

**正确模式**：精确匹配断点步骤
```python
# ✅ 正确：只匹配明确的断点步骤
if ('启动心跳' in step_name or '核心断点' in step_name):
    return True
```

## 验证方法

```bash
# 重新初始化工作流
python actions/execute.py 通用漏洞扫描 --init

# 检查断点步骤
python3 -c "
import json
with open('~/.hermes/workflows/通用漏洞扫描/status.json') as f:
    d = json.load(f)
for k, v in d['steps'].items():
    if v.get('type') == 'breakpoint':
        print(f'步骤{k}: {v[\"name\"]} type={v.get(\"type\")}')
"
```

## 预期结果

status.json 中断点步骤应包含：
```json
{
  "name": "启动心跳监测 ⚠️（核心断点）",
  "type": "breakpoint",
  "trigger": null,
  "command": "# 断点步骤：启动心跳后返回"
}
```

心跳步骤应包含：
```json
{
  "name": "WIH下载流程（心跳直接执行）",
  "type": "auto",
  "trigger": "heartbeat"
}
```

## 修复文件

- `expander.py`：核心修复（注入节点类型）
- `SKILL.md`：新增断点识别章节
- `execute.py`：无需修改（已自动保留字段）

## 相关问题

- 断点工作流执行到断点后不返回控制权
- 父工作流串行执行中断
- 心跳步骤未正确标记

## 日期

2026-05-18
