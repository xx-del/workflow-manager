# loader.py WORKFLOW.md 覆盖问题修复

**日期**: 2026-05-12
**修复文件**: `src/tools/loader.py`

---

## 问题根因

loader.py 第 231-236 行用 WORKFLOW.md 解析的 `parsed_steps` 直接覆盖 `_index.yaml` 的 `nodes` 定义。

```python
# 原始代码（有问题）：
if not workflow['nodes'] or all(
    n.get('task') and not n.get('command') 
    for n in workflow['nodes']
):
    workflow['nodes'] = parsed_steps  # ← 直接覆盖
```

**影响**：
- 心跳驱动工作流的节点类型丢失（breakpoint、auto、trigger）
- 验证器检查 WORKFLOW.md 字段名（"执行指令"），但实际使用"命令"
- 导致警告"缺少执行指令"

---

## 修复方案

### 1. 删除覆盖逻辑

```python
# 修复后：
if not workflow['nodes']:
    # 情况1：无节点定义 → 使用 WORKFLOW.md
    workflow['nodes'] = parsed_steps
else:
    # 情况2：有节点定义 → 合并命令，保留结构
    merged_count = self._merge_workflow_md_commands(workflow['nodes'], parsed_steps)
```

### 2. 新增心跳检测方法

```python
def _is_heartbeat_workflow(self, nodes: List[Dict]) -> bool:
    """判断是否为心跳驱动工作流"""
    for node in nodes:
        if node.get('trigger') == 'heartbeat':
            return True
        if node.get('type') in ['breakpoint', 'auto']:
            return True
        if node.get('heartbeat', {}).get('enabled'):
            return True
    return False
```

### 3. 新增命令合并方法

```python
def _merge_workflow_md_commands(self, nodes: List[Dict], parsed_steps: List[Dict]) -> int:
    """将 WORKFLOW.md 解析的命令合并到 _index.yaml 节点"""
    # 构建步骤名称到命令的映射
    step_commands = {}
    for step in parsed_steps:
        step_name = step.get('name', '')
        command = step.get('command', '')
        if step_name and command:
            step_commands[step_name] = command
    
    # 合并到节点（三种匹配方式）
    merged_count = 0
    for node in nodes:
        # 1. 精确匹配
        # 2. 任务名匹配
        # 3. 包含匹配
    return merged_count
```

### 4. 优化验证逻辑

```python
# 心跳驱动工作流跳过验证
elif self._is_heartbeat_workflow(workflow['nodes']):
    self.logger.info(f"心跳驱动工作流 '{workflow['name']}' 跳过步骤定义验证")
```

---

## 验证结果

**home漏扫**：
```
[INFO] 心跳驱动工作流 'home漏扫' 跳过步骤定义验证
```
- ✅ 无警告
- ✅ 节点结构保留（7个节点）

**通用漏洞扫描**：
```
[INFO] 拼接工作流 '通用漏洞扫描' 跳过步骤定义验证
[INFO] 心跳驱动工作流 'home漏扫' 跳过步骤定义验证
[INFO]     从 WORKFLOW.md 补充 12 个节点命令
```

---

## 设计发现

**_index.yaml 与 WORKFLOW.md 的关系**：
- _index.yaml 定义节点结构（breakpoint、auto、trigger）
- WORKFLOW.md 定义详细步骤和命令
- 节点可能是步骤的合并（如"启动扫描"包含步骤 0-4）

**心跳驱动工作流的命令执行**：
- 命令由心跳脚本执行，不在 pending_instructions 中
- 不需要验证"执行指令"字段
