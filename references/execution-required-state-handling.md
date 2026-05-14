# execution_required 状态处理指南

**创建日期**：2026-05-13  
**问题发现**：资产收集流程执行时，execute.py返回`execution_required`而非自动执行

---

## 问题现象

```bash
python actions/execute.py 资产收集流程 --date-start 20260513 --date-end 20260513
```

**返回结果**：
```json
{
  "status": "execution_required",
  "total_steps": 1,
  "pending_instructions": [
    {"tool": "delegate_task", "task": "发送工作流完成通知并生成报告"}
  ]
}
```

**预期行为**：工作流自动执行完成  
**实际行为**：返回`execution_required`，要求主AI手动执行`pending_instructions`

---

## 根因分析

### 设计意图

`execution_required`状态是workflow-manager的设计特性：
1. **安全控制**：某些步骤需要主AI确认后才执行
2. **灵活编排**：允许主AI在执行前调整参数
3. **依赖验证**：等待主AI验证前置条件

### 适用场景

| 场景 | 返回状态 | 说明 |
|------|---------|------|
| 计划生成 | `execution_required` | 只生成计划，不执行 |
| 自动执行 | `completed` | 全自动执行完成 |
| 需要确认 | `execution_required` | 需要主AI确认关键步骤 |

---

## 处理方法

### 方法1：主AI执行pending_instructions（推荐）

```python
# 读取execute.py返回结果
result = execute_workflow(name, date_start, date_end)

if result['status'] == 'execution_required':
    # 逐个执行pending_instructions
    for instruction in result['pending_instructions']:
        if instruction['tool'] == 'delegate_task':
            delegate_task(task=instruction['task'])
        elif instruction['tool'] == 'terminal':
            terminal(command=instruction['command'])
```

### 方法2：修改execute.py为自动执行模式

**修改位置**：`executor.py`的`execute()`方法

**修改逻辑**：
```python
# 原逻辑：返回execution_required
if pending_instructions:
    return {
        'status': 'execution_required',
        'pending_instructions': pending_instructions
    }

# 新逻辑：自动执行
if pending_instructions:
    for instruction in pending_instructions:
        execute_instruction(instruction)
    return {'status': 'completed'}
```

### 方法3：使用--auto-execute参数

**新增参数**：`--auto-execute`

**使用方式**：
```bash
python actions/execute.py 资产收集流程 --date-start 20260513 --auto-execute
```

---

## 注意事项

### ⚠️ 禁止忽略pending_instructions

```python
# ❌ 错误：忽略execution_required
result = execute_workflow(...)
if result['status'] == 'execution_required':
    print("工作流已生成计划")  # 错误！应该执行pending_instructions
    return

# ✅ 正确：执行pending_instructions
result = execute_workflow(...)
if result['status'] == 'execution_required':
    for instruction in result['pending_instructions']:
        delegate_task(task=instruction['task'])
```

### ⚠️ 禁止绕过execute.py直接调用delegate_task

```python
# ❌ 错误：绕过execute.py
delegate_task(task="执行资产收集流程")

# ✅ 正确：通过execute.py获取pending_instructions
result = execute_workflow("资产收集流程", ...)
if result['status'] == 'execution_required':
    for instruction in result['pending_instructions']:
        delegate_task(task=instruction['task'])
```

---

## 调试技巧

### 检查pending_instructions内容

```bash
python actions/execute.py <工作流名称> --date-start YYYYMMDD --json
```

输出：
```json
{
  "status": "execution_required",
  "pending_instructions": [
    {
      "tool": "delegate_task",
      "task": "步骤描述",
      "context": {...}
    }
  ]
}
```

### 检查工作流状态

```bash
python actions/status.py <工作流名称>
```

输出：
```
状态: execution_required
步骤: 5/21
待执行指令数: 16
```

---

## 相关文档

- `references/executor-constraints.md` - 执行器约束机制
- `references/status-update-guide.md` - 状态更新指南
- `SKILL.md` - 主技能文档
