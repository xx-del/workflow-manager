# terminal 执行约束（主 AI 必须遵守）

## ⚠️ 最高优先级

**工作流执行场景下，禁止使用 timeout 参数**

这是强制约束，违反即失败。违反后本次执行无效。

---

## 核心原则

**工作流执行 ≠ 普通 CLI 任务**

| 场景 | terminal 调用 | 说明 |
|------|---------------|------|
| 普通 CLI | `timeout=60` 可用 | 快速返回任务 |
| 工作流执行 | **禁止 timeout** | 必须等待完成或心跳接管 |

---

## 绝对禁止

### ❌ 禁止在 workflow 步骤中使用 timeout 参数

```python
# ❌ 错误
terminal(command="bash scan.sh", timeout=60)

# ✅ 正确（断点工作流）
terminal(command="bash scan.sh", background=True)
# 启动心跳后返回

# ✅ 正确（同步工作流）
terminal(command="python main.py")
# 不设 timeout，等待完成
```

### ❌ 禁止将"命令返回"等同于"工作流完成"

```
命令返回 (exit_code=0 或 124)
    ↓
≠ 工作流完成
    ↓
必须检查 status.json 或输出文件
```

---

## 执行模式规范

### 同步工作流

```python
# 执行（不设 timeout）
result = terminal(command="python main.py")

# 验证输出
assert os.path.exists(output_file)

# 标记完成
set_status(step_id, "completed")
```

### 断点工作流

```python
# 启动（不设 timeout，使用 background）
terminal(command="bash scan.sh", background=True)

# 启动心跳监测
cronjob(action="create", schedule="every 30m", ...)

# 返回（不执行后续步骤）
return "断点返回，心跳已启动"
```

### 串行依赖

```python
# 检查依赖状态
for dep in depends_on:
    if get_status(dep) != "completed":
        return f"等待 {dep} 完成"

# 依赖满足后执行
execute_step(step_id)
```

---

## 验证清单

执行任何 workflow 步骤前必须确认：

- [ ] 是否是断点工作流？→ 使用 background + 心跳
- [ ] 是否是同步工作流？→ 不设 timeout，等待完成
- [ ] 依赖步骤是否完成？→ 检查 status.json
- [ ] 输出文件是否存在？→ 验证结果

---

## 违规后果

| 违规行为 | 后果 |
|----------|------|
| 使用 timeout 参数 | 命令被强制中断，工作流状态异常 |
| 未等待依赖完成 | 越权执行，结果无效 |
| 断点未启动心跳 | 后续步骤无法触发 |
