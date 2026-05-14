# 主 AI 状态更新指南

**创建时间**: 2026-05-11
**原因**: 修复 SKILL.md 中误导性的 `executor.update_step_status()` 描述

---

## 核心原则

**⚠️ 主 AI 无法导入 Python 模块，只能通过工具操作文件。**

---

## 状态更新完整流程

### 1. 读取 status.json

```python
status_json = read_file("~/.hermes/workflows/{workflow}/status.json")
status = json.loads(status_json)
```

### 2. 更新字段

```python
status['updated'] = datetime.now().isoformat()
status['progress']['current_step'] = step_id
status['progress']['message'] = f"步骤{step_id}完成"
```

### 3. 追加步骤记录

**⚠️ 必须追加，不能覆盖**

```python
status['steps'].append({
    'step_id': step_id,
    'step_name': step_name,
    'status': 'completed',
    'completed_at': datetime.now().isoformat(),
    'duration': execution_time
})
```

### 4. 写回文件

```python
write_file("~/.hermes/workflows/{workflow}/status.json", 
           json.dumps(status, indent=2, ensure_ascii=False))
```

---

## 完整示例

```python
import json
from datetime import datetime

# 读取
status_json = read_file("~/.hermes/workflows/资产收集流程/status.json")
status = json.loads(status_json)

# 更新
status['updated'] = '2026-05-11T16:00:00+08:00'
status['progress']['current_step'] = 2
status['progress']['message'] = '步骤2完成：域名处理'
status['steps'].append({
    'step_id': 2,
    'step_name': '域名处理',
    'status': 'completed',
    'completed_at': '2026-05-11T16:00:00+08:00',
    'duration': 120
})

# 写回
write_file("~/.hermes/workflows/资产收集流程/status.json", 
           json.dumps(status, indent=2, ensure_ascii=False))
```

---

## status.json 必需字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| workflow_id | string | ✅ | 工作流唯一标识 |
| workflow_name | string | ✅ | 工作流名称 |
| status | string | ✅ | 状态：initialized/running/completed/failed |
| started | string/null | ✅ | 开始时间（ISO格式），未开始时为 null |
| updated | string | ✅ | 最后更新时间（ISO格式），**必须每次更新** |
| progress | object | ✅ | 进度信息 |
| steps | array | ✅ | 步骤记录数组 |

---

## steps 数组元素必需字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| step_id | integer | ✅ | 步骤编号（从1开始） |
| step_name | string | ✅ | 步骤名称 |
| status | string | ✅ | 步骤状态：pending/running/completed/failed/skipped |

---

## 常见错误

### 错误1：尝试导入 executor 模块

```python
# ❌ 错误：主 AI 无法导入 Python 模块
from core.executor import WorkflowExecutor
executor = WorkflowExecutor()
executor.update_step_status(...)
```

**正确方式**：使用 read_file + write_file

### 错误2：覆盖 steps 数组

```python
# ❌ 错误：覆盖会丢失历史记录
status['steps'] = [new_step]
```

**正确方式**：追加

```python
# ✅ 正确：追加保留历史
status['steps'].append(new_step)
```

### 错误3：忘记更新 updated 字段

```python
# ❌ 错误：守护机制依赖 updated 字段
status['steps'].append(new_step)
# 缺少：status['updated'] = ...
```

**正确方式**：每次更新都必须设置 updated

```python
# ✅ 正确
status['updated'] = datetime.now().isoformat()
status['steps'].append(new_step)
```

---

## 修复历史

| 日期 | 问题 | 修复 |
|------|------|------|
| 2026-05-11 | SKILL.md 第167行说主AI调用 `executor.update_step_status()` | 改为 `read_file + write_file` |
| 2026-05-11 | 缺少状态更新详细流程 | 新增本文件 |
| 2026-05-11 | 验证清单不完整 | 补充初始化/执行/完成三阶段验证 |
