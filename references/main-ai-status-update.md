# 主 AI 状态更新指南

## ⚠️ 关键限制

**主 AI 无法调用 executor 方法！**

| 方法 | 可用性 | 原因 |
|------|--------|------|
| `executor.update_step_status()` | ❌ 不可用 | 无 CLI 接口，Python 方法无法导入 |
| `read_file` + `write_file` | ✅ 可用 | 直接操作 status.json |

---

## 正确的状态更新流程

### 步骤1：读取 status.json

```python
status_json = read_file("~/.hermes/workflows/{workflow}/status.json")
status = json.loads(status_json)
```

### 步骤2：更新字段

```python
status['updated'] = datetime.now().isoformat()
status['progress']['current_step'] = step_id
status['progress']['message'] = f"步骤{step_id}完成"
```

### 步骤3：追加步骤记录

```python
status['steps'].append({
    'step_id': step_id,
    'step_name': step_name,
    'status': 'completed',
    'completed_at': datetime.now().isoformat()
})
```

### 步骤4：写回文件

```python
write_file("~/.hermes/workflows/{workflow}/status.json", json.dumps(status, indent=2))
```

---

## 常见错误

### 错误1：尝试调用 executor 方法

```python
# ❌ 错误
executor.update_step_status(step_id, 'completed')

# ✅ 正确
status_json = read_file(...)
status = json.loads(status_json)
status['steps'].append({...})
write_file(...)
```

### 错误2：忘记更新 updated 字段

```python
# ❌ 错误 - 守护机制依赖 updated 字段
status['steps'].append({...})

# ✅ 正确 - 每次更新都要设置 updated
status['updated'] = datetime.now().isoformat()
status['steps'].append({...})
```

---

## SKILL.md 第167行更正

**错误描述**：
```markdown
| **更新状态** | 更新步骤执行状态 | `executor.update_step_status()` |
```

**正确描述**：
```markdown
| **更新状态** | 更新步骤执行状态 | `read_file` + `write_file` 直接操作 status.json |
```
