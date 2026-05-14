# loader.py WORKFLOW.md 覆盖 _index.yaml 问题

**发现时间**: 2026-05-12
**影响版本**: v6.3.0

---

## 问题描述

loader.py 第 231-236 行会使用 WORKFLOW.md 解析的 `parsed_steps` 覆盖 _index.yaml 定义的 `nodes`：

```python
# 如果 _index.yaml 节点为空或为占位符，使用 WORKFLOW.md 步骤
if not workflow['nodes'] or all(
    n.get('task') and not n.get('command') 
    for n in workflow['nodes']
):
    workflow['nodes'] = parsed_steps  # ← 覆盖了 _index.yaml 的节点定义
```

---

## 问题影响

### 心跳驱动工作流被破坏

**设计意图**：
- _index.yaml 定义心跳驱动结构（breakpoint、auto、trigger: heartbeat）
- WORKFLOW.md 提供详细执行说明

**实际行为**：
- WORKFLOW.md 解析的步骤覆盖了 _index.yaml 的节点定义
- 导致心跳驱动特性（breakpoint、trigger）丢失

### 验证器报假阳性警告

**验证逻辑**（第 97-101 行）：
```python
required_fields = ['做什么', '执行指令']
for field in required_fields:
    if field not in content:
        warnings.append(f"步骤 '{step_name}' 缺少 '{field}' 定义")
```

**问题**：
- WORKFLOW.md 使用"命令"字段名
- 验证器期望"执行指令"字段名
- 导致大量"缺少执行指令"警告

**但命令实际已提取**：
- 解析逻辑（第 299 行）直接提取 ```bash 代码块
- 不检查字段名
- 所以 pending_instructions 中包含正确命令

---

## 根本原因

**两种工作流定义方式的冲突**：

| 方式 | 适用场景 | 特点 |
|------|---------|------|
| _index.yaml 驱动 | 心跳工作流、复杂编排 | 支持 breakpoint、trigger、capabilities |
| WORKFLOW.md 驱动 | 简单线性工作流 | 步骤详情、命令定义 |

loader.py 假设所有工作流都是"简单线性工作流"，用 WORKFLOW.md 覆盖 _index.yaml。

---

## 影响案例

**home漏扫工作流**：

- _index.yaml：定义 7 个节点（breakpoint、auto、trigger: heartbeat）
- WORKFLOW.md：定义 12 个步骤（详细命令）
- 结果：心跳驱动结构被破坏，验证器报 12 个警告

---

## 解决方案

### 方案 A：修复 WORKFLOW.md 格式（临时）

将"命令"字段改为"执行指令"，补充缺失字段。

### 方案 B：修复 loader.py 逻辑（推荐）

不使用 WORKFLOW.md parsed_steps 覆盖 _index.yaml nodes：

```python
# 修改第 231-236 行
if not workflow['nodes']:  # 仅当 _index.yaml 节点为空时才使用 WORKFLOW.md
    workflow['nodes'] = parsed_steps
```

### 方案 C：统一工作流定义规范（长期）

明确区分：
- **结构定义**：_index.yaml（节点、依赖、触发器）
- **执行详情**：WORKFLOW.md（命令、说明）

---

## 验证清单

检查工作流是否有此问题：

```bash
# 检查 _index.yaml 是否定义了心跳驱动节点
grep -E "type: (breakpoint|auto)|trigger:" _index.yaml

# 如果有，检查 loader 是否覆盖
python -c "
from tools.loader import loader
wf = loader.load('工作流名称')
print('nodes from _index.yaml:', len([n for n in wf['nodes'] if n.get('trigger')]))
"
```

---

## 相关代码位置

- **覆盖逻辑**：`src/tools/loader.py` 第 231-236 行
- **验证逻辑**：`src/tools/loader.py` 第 97-101 行
- **解析逻辑**：`src/tools/loader.py` 第 273-321 行
