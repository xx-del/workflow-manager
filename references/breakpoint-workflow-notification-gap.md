# 断点工作流完成通知缺失诊断

## 问题描述

**症状**：断点+心跳工作流执行完成后，未收到飞书通知

## 诊断过程

### 1. 验证通知模块可用性

```bash
cd ~/.hermes/skills/openclaw-imports/workflow-feishu-notify
python3 cli.py text --message '测试通知'
# ✅ 发送成功，消息 ID: om_x100b50dac705e4a8b227d28a6696b1e
```

### 2. 检查工作流定义

工作流定义中有 notify 配置：
```yaml
config:
  notify:
    on_complete: true
    on_fail: true
```

### 3. 检查 complete.py 代码

`actions/complete.py` 第 47-62 行、第 150-173 行：
- 有 `send_feishu_message()` 函数
- 有完整的通知逻辑
- 调用 `workflow-feishu-notify` 模块

### 4. 检查调用链

**executor.py 返回**：
```python
'return_info': {
    'finalize_required': True,
    'finalize_command': f'python actions/complete.py {workflow["name"]}'
}
```

**问题**：
- 主 AI 在断点步骤返回后退出
- 心跳 cronjob 执行后续步骤
- 心跳脚本没有调用 complete.py 的逻辑

### 5. 检查历史记录

`history/2026-05-09.json`：
```json
[{
  "timestamp": "2026-05-09T15:46:22.946674",
  "step": "step_10_js_analysis",
  "status": "completed",
  "triggered_by": "wih_monitor_cronjob"
}]
```

无 finalize 记录 → complete.py 未被调用

## 根因

| 组件 | 职责 | 问题 |
|------|------|------|
| executor.py | 返回 finalize_command | ✅ 正常返回 |
| 主 AI | 执行 finalize_command | ⚠️ 断点返回后已退出 |
| 心跳 cronjob | 检测完成 + 通知 | ❌ 无通知逻辑 |
| complete.py | 发送通知 | ✅ 功能完整 |

**结论**：断点工作流的完成通知机制缺失

## 解决方案

### 方案 A：心跳检测完成时调用 complete.py

```python
# heartbeat.py
if all_steps_completed:
    import subprocess
    subprocess.run(['python', 'actions/complete.py', workflow_name])
```

### 方案 B：心跳检测完成时直接发送通知（推荐）

```python
# heartbeat.py
if all_steps_completed and not notification_sent:
    from workflow_feishu_notify import send_workflow_complete
    send_workflow_complete(
        workflow_name="home漏扫",
        status="completed",
        success_rate=f"{completed}/{total}"
    )
```

**推荐方案 B**：
- complete.py 功能完整但依赖复杂（需要历史记录、优化分析等）
- 心跳脚本已掌握完成状态
- 直接调用 workflow-feishu-notify 更简单可靠

## 相关文件

- `~/.hermes/skills/openclaw-imports/workflow-manager/actions/complete.py`
- `~/.hermes/skills/openclaw-imports/workflow-feishu-notify/notify.py`
- `~/.hermes/skills/openclaw-imports/workflow-manager/src/core/executor.py`
