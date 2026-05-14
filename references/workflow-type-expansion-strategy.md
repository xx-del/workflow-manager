# 工作流类型识别与展开策略

**修复日期**: 2026-05-12
**修复文件**: `src/tools/loader.py`
**问题等级**: 架构级

---

## 问题背景

### 核心矛盾

loader.py 使用 WORKFLOW.md 解析的 `parsed_steps` 覆盖 _index.yaml 的 `nodes`，导致不同类型工作流的处理逻辑混乱。

### 症状表现

- 心跳驱动工作流（home漏扫）的节点定义被破坏（breakpoint、trigger 丢失）
- 依赖验证警告"缺少执行指令"（字段名不匹配）
- 步骤数量不匹配（预期 48，实际 25）
- pending_instructions 包含大量"（无命令）"

---

## 解决方案：三阶段处理流程

```
阶段1：识别工作流类型
    ↓
阶段2：选择展开策略
    ↓
阶段3：生成执行计划
```

---

## 阶段1：工作流类型识别

### 识别方法

```python
def _identify_workflow_type(self, index: Dict, nodes: List[Dict]) -> str:
    """
    识别工作流类型
    
    Returns:
        'branch' - 拼接工作流
        'heartbeat' - 心跳驱动工作流
        'normal' - 普通工作流
    """
    # 1. branch 类型
    if index.get('type') == 'branch':
        return 'branch'
    if all(n.get('calls') == 'workflow-manager' for n in nodes):
        return 'branch'
    
    # 2. heartbeat 类型
    config = index.get('config', {})
    if config.get('heartbeat', {}).get('enabled'):
        return 'heartbeat'
    if any(n.get('type') in ['breakpoint', 'auto'] for n in nodes):
        return 'heartbeat'
    if any(n.get('trigger') == 'heartbeat' for n in nodes):
        return 'heartbeat'
    
    # 3. normal 类型
    return 'normal'
```

### 类型特征

| 类型 | 判定条件 | 示例工作流 |
|------|----------|-----------|
| branch | `type: branch` 或所有节点 `calls: workflow-manager` | 通用漏洞扫描 |
| heartbeat | 有 `heartbeat.enabled` 或 `breakpoint/auto` 节点 | home漏扫 |
| normal | 其他 | 凭证检测、爆破测试、nuclei扫描 |

---

## 阶段2：展开策略选择

### 策略矩阵

| 工作流类型 | nodes 来源 | parsed_steps 用途 | 合并策略 |
|-----------|-----------|------------------|---------|
| branch | _index.yaml | 不解析 | 不合并，递归展开 |
| heartbeat | _index.yaml | 记录但不合并 | 保留双层结构 |
| normal（1对1） | _index.yaml | 补充命令 | 名称匹配合并 |
| normal（1对多） | WORKFLOW.md | 作为 nodes | 完全替换 |

### 实现代码

```python
# === 根据类型选择展开策略 ===
wf_type = workflow['type']

if wf_type == 'branch':
    # 拼接工作流：不处理 WORKFLOW.md，保持 nodes 引用
    pass

elif wf_type == 'heartbeat':
    # 心跳驱动：保留双层结构
    # nodes = 逻辑层（_index.yaml 节点）
    # execution_steps = 执行层（WORKFLOW.md 步骤）
    workflow['execution_steps'] = parsed_steps

elif wf_type == 'normal':
    # 普通工作流：判断节点-步骤对应关系
    nodes_count = len(workflow['nodes'])
    steps_count = len(parsed_steps)
    
    if nodes_count == steps_count:
        # 1对1：补充命令到节点
        self._merge_workflow_md_commands(workflow['nodes'], parsed_steps)
    elif nodes_count < steps_count:
        # 1对多：使用 WORKFLOW.md 步骤作为 nodes
        workflow['logic_nodes'] = workflow['nodes']  # 保留原始逻辑节点
        self._rebuild_depends_on(parsed_steps, workflow['nodes'])
        workflow['nodes'] = parsed_steps
```

---

## 阶段3：依赖重建

### 问题：WORKFLOW.md 步骤的 depends_on 引用原始步骤编号

**症状**：
```
节点 '检查工作目录' 的 depends_on 引用了不存在的步骤: 'step_1'
```

**原因**：
- parsed_steps 的 ID 为 `step_1`, `step_2`, ...
- 但 depends_on 引用的也是 `step_1`（原始编号）
- 需要重建为串行依赖链

### 解决方案：_rebuild_depends_on 方法

```python
def _rebuild_depends_on(self, steps: List[Dict], logic_nodes: List[Dict]) -> None:
    """
    重建执行步骤的依赖关系（1对多模式）
    """
    if not logic_nodes or not steps:
        return
    
    # 清除原始 depends_on，重新建立串行依赖链
    for i, step in enumerate(steps):
        # 确保 ID 正确
        if not step.get('id'):
            step['id'] = f'step_{i+1}'
        
        if i == 0:
            step['depends_on'] = []
        else:
            prev_id = steps[i-1].get('id', f'step_{i}')
            step['depends_on'] = [prev_id]
```

---

## 验证修复

### 修复前

- total_steps: 25
- 大部分命令为"（无命令）"
- 跨工作流依赖警告

### 修复后

- total_steps: 43
- 所有步骤都有正确的命令
- 无依赖验证错误

### 测试结果

| 工作流 | 类型 | nodes | execution_steps | 状态 |
|--------|------|-------|-----------------|------|
| 通用漏洞扫描 | branch | 4 | - | ✅ |
| home漏扫 | heartbeat | 7 | 12 | ✅ |
| 凭证检测 | normal | 12 | - | ✅ |
| 爆破测试 | normal | 12 | - | ✅ |
| nuclei扫描 | normal | 12 | - | ✅ |

---

## 关键教训

### 设计原则

1. **类型识别先行**：不同类型工作流有不同的展开需求
2. **策略分离**：一种策略不适用所有场景
3. **双层结构**：心跳驱动工作流需要保留逻辑层和执行层
4. **智能合并**：普通工作流根据节点-步骤关系智能选择合并策略

### 避免的错误

- ❌ 用单一逻辑处理所有工作流类型
- ❌ 用 WORKFLOW.md 覆盖 _index.yaml 节点定义
- ❌ 忽略节点-步骤对应关系的差异

---

## 相关文档

- `references/loader-workflow-md-override-fix-20260512.md` - loader.py 修复实施记录
- `references/heartbeat-workflow-detection.md` - 心跳驱动工作流识别机制
- `references/cross-workflow-dependency-issue.md` - 跨工作流依赖问题（待修复）
