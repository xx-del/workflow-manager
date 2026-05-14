# 监控脚本触发工作流模式

## 问题场景

监控脚本（如 `wih_monitor.py`）检测到条件满足后，只更新 `status.json`，但没有实际触发后续工作流执行。

## 典型代码

```python
# wih_monitor.py 中的 TODO 注释
# TODO: 这里需要调用workflow-manager执行JS敏感信息分析工作流
# 由于技能无法直接调用，这里先记录信号
log(f"📝 准备执行JS敏感信息分析")
```

## 根本原因

1. **技能无法直接调用**：Python 脚本无法直接调用 workflow-manager 技能
2. **TODO 未实现**：开发者标记了 TODO 但未完成实现
3. **状态更新 ≠ 工作流触发**：只更新状态，不执行后续步骤

## 解决方案：手动触发工作流

### 步骤 1：检测条件

```python
status = read_status()
wih_complete = status.get("heartbeat", {}).get("wih", {}).get("complete", False)
wih_analyzed = status.get("heartbeat", {}).get("wih", {}).get("analyzed", False)

if wih_complete and not wih_analyzed:
    # 触发工作流
    ...
```

### 步骤 2：调用 agent-pool 匹配 Agent

```bash
python ~/.hermes/skills/openclaw-imports/agent-pool/bin/agent-pool match "分析WIH截图中的JS敏感信息"
```

### 步骤 3：调用 delegate_task 执行任务

```python
# 在 AI 会话中调用
delegate_task(
    goal="## 任务：JS敏感信息分析\n\n分析 WIH 截图压缩包...",
    context="工作流：home漏扫\n步骤：10...",
    toolsets=["terminal", "file"]
)
```

### 步骤 4：更新状态

```python
status["heartbeat"]["wih"]["analyzed"] = True
status["heartbeat"]["wih"]["analyzed_at"] = datetime.now().isoformat()
write_status(status)
```

## 完整触发流程

```
监控脚本检测条件
    ↓
条件满足（如 wih.complete = true）
    ↓
监控脚本更新 status.json
    ↓
监控脚本记录 TODO（未实现）
    ↓
【需要外部触发】
    ↓
AI 会话读取 status.json
    ↓
AI 调用 agent-pool 匹配 Agent
    ↓
AI 调用 delegate_task 执行任务
    ↓
AI 更新 status.json（标记 analyzed = true）
```

## 最佳实践

### 方案 A：监控脚本直接触发（推荐）

修改监控脚本，使用 `subprocess` 调用 Hermes CLI：

```python
import subprocess

def trigger_workflow(workflow_name, params):
    """触发工作流执行"""
    cmd = [
        "hermes", "workflow", "execute", workflow_name,
        "--params", json.dumps(params)
    ]
    subprocess.run(cmd, check=True)
```

### 方案 B：使用 Hermes Cronjob

配置 Hermes cronjob 定期检测并触发：

```yaml
# cronjob 配置
name: "WIH 完成检测"
schedule: "every 5m"
prompt: "执行 ~/.hermes/workflows/home漏扫/wih_monitor.py"
skills: ["agent-pool", "workflow-manager"]
```

### 方案 C：AI 手动触发（临时方案）

在 AI 会话中手动执行：

```
用户：执行 wih_monitor.py 并触发 JS 敏感信息分析
AI：[检测条件] → [调用 agent-pool] → [调用 delegate_task] → [更新状态]
```

## 相关文件

- 监控脚本：`wih_monitor.py`
- 状态文件：`status.json`
- 工作流定义：`WORKFLOW.md`
- agent-pool 技能：`~/.hermes/skills/openclaw-imports/agent-pool/`

## 注意事项

1. **防重复触发**：检查 `analyzed` 字段，避免重复执行
2. **状态一致性**：确保状态更新在工作流执行成功后
3. **错误处理**：工作流执行失败时，不要标记为已完成
