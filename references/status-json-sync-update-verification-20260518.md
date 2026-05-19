# status.json 同步更新实测验证

日期：2026-05-18

## 测试工作流

**工作流名**：status-json-test

**步骤**：
1. 读取初始状态
2. 执行简单任务
3. 验证状态更新
4. 最终确认

## 测试流程

### 1. 初始化工作流

```bash
python3 actions/execute.py status-json-test --init
```

**结果**：status.md 生成，包含"执行后操作"章节

### 2. 验证 status.md 结构

```python
# 前30行：执行指令
# 第31+行：执行后操作章节
```

**验证结果**：
```
=== 执行后操作章节 ===
## 执行后操作（必须）

**步骤执行完成后，必须更新 status.json**：

```bash
python3 -c "
import json
from datetime import datetime
path = '/home/kali/.hermes/workflows/status-json-test/status.json'
...
"
```
```

### 3. 执行步骤并更新状态

**步骤1执行**：
```bash
echo '步骤1: 读取初始状态'
```

**更新 status.json**：
```python
d['steps']['1']['status'] = 'completed'
d['steps']['1']['completed_at'] = datetime.now().isoformat()
d['current_step'] = 2
```

**步骤2-4执行**：同样流程

### 4. 最终验证

**status.json 最终状态**：
```json
{
  "workflow": "status-json-test",
  "status": "completed",
  "current_step": 5,
  "steps": {
    "1": {"status": "completed", "completed_at": "..."},
    "2": {"status": "completed", "completed_at": "..."},
    "3": {"status": "completed", "completed_at": "..."},
    "4": {"status": "completed", "completed_at": "..."}
  }
}
```

## 验证结论

✅ **修改生效**：
- status.md 第31+行包含"执行后操作"章节
- 主 AI 按指令更新 status.json
- 步骤状态正确追踪

✅ **最小改动**：
- 仅修改 execute.py（+23行）
- Hook、SKILL.md 零改动

✅ **符合 planning-with-files 哲学**：
- 前30行：告诉 AI 做什么
- 第31+行：告诉 AI 怎么做

## 测试文件

**位置**：`~/.hermes/workflows/status-json-test/`

**文件**：
- status.json：状态文件
- status.md：执行计划
- WORKFLOW.md：工作流定义（可选）
