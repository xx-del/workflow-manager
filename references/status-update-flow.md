# 工作流状态更新流程

## 问题背景

在 v4.3.0 及之前版本中，工作流执行时 status.json 不会被更新，导致：
- 守护机制无法监测工作流进度
- 用户无法查看中间状态
- 工作流失败时无法定位问题步骤

## 根因分析

### 为什么子agent不能更新状态

| 原因 | 说明 |
|------|------|
| 无路径 | 子agent通过 delegate_task 执行，没有收到 workflow_path 参数 |
| 无权限 | executor.update_step_status() 设计给主AI调用，需要 executor 实例 |
| 无上下文 | 子agent不知道当前是哪个工作流的哪个步骤 |
| 无义务 | 子agent只负责任务执行，不应承担编排职责 |

### 架构分析

```
错误的期望:
主AI → delegate_task → 子agent执行 → 子agent更新status.json ❌
                                              ↓
                                        子agent无路径、无权限、无上下文

正确的架构:
主AI → 初始化status → delegate_task → 读取结果 → 更新status.json ✅
                                                      ↓
                                                主AI有完整上下文
```

## 解决方案

### 状态更新时机

| 时机 | 操作 | 工具 | 执行者 |
|------|------|------|--------|
| 工作流开始 | 初始化 status.json | write_file | 主AI |
| 步骤开始 | progress.current_step | read + write_file | 主AI |
| 步骤完成 | steps[] 追加记录 | read + write_file | 主AI |
| 工作流完成 | status=completed | read + write_file | 主AI |
| 工作流失败 | status=failed + error | read + write_file | 主AI |

### 执行流程

```
用户: "执行资产收集流程"
         ↓
[步骤0] 主AI 初始化 status.json
         {
           "workflow_id": "资产收集流程",
           "status": "running",
           "progress": { "current_step": 0, "total_steps": 5 },
           "steps": []
         }
         ↓
[步骤1] 主AI 调用 delegate_task(步骤1: 电力数据)
         ↓
         子agent执行，返回结果
         ↓
[步骤1后] 主AI 更新 status.json
         - progress.current_step = 1
         - steps.push({ step_id: 1, status: "completed", ... })
         ↓
[步骤2] 主AI 调用 delegate_task(步骤2: 域名处理)
         ↓
         ... 循环 ...
         ↓
[完成] 主AI 更新 status.json
         - status = "completed"
         - completed_at = "当前时间"
```

## 代码模板

### 初始化 status.json

```json
{
  "tool": "write_file",
  "params": {
    "path": "{workflow_path}/status.json",
    "content": "{\n  \"workflow_id\": \"{workflow_name}\",\n  \"workflow_name\": \"{workflow_name}\",\n  \"status\": \"running\",\n  \"started\": \"{当前时间ISO格式}\",\n  \"updated\": \"{当前时间ISO格式}\",\n  \"progress\": {\n    \"current_step\": 0,\n    \"total_steps\": {总步骤数},\n    \"message\": \"工作流开始执行\"\n  },\n  \"steps\": []\n}"
  }
}
```

### 步骤完成后更新

```python
# 1. 读取现有状态
status = read_file(f"{workflow_path}/status.json")
status_json = json.loads(status)

# 2. 更新内容
status_json["updated"] = datetime.now().isoformat()
status_json["progress"]["current_step"] = step_id
status_json["progress"]["message"] = f"步骤{step_id}完成"

# 3. 追加完成的步骤（注意：追加，不覆盖）
status_json["steps"].append({
    "step_id": step_id,
    "step_name": step_name,
    "status": "completed",
    "duration": duration_seconds,
    "completed_at": datetime.now().isoformat()
})

# 4. 写回文件
write_file(f"{workflow_path}/status.json", json.dumps(status_json, indent=2))
```

## 常见错误

### 错误1：依赖子agent更新状态

```
❌ 错误做法:
delegate_task(context="完成后请更新 status.json")

✅ 正确做法:
主AI 在 delegate_task 返回后，自己更新 status.json
```

### 错误2：覆盖 steps 数组

```
❌ 错误做法:
status_json["steps"] = [{ step_id: 1, ... }]  # 覆盖了之前的步骤

✅ 正确做法:
status_json["steps"].append({ step_id: 1, ... })  # 追加新步骤
```

### 错误3：只在工作流结束时更新

```
❌ 错误做法:
所有步骤完成后才更新 status.json

✅ 正确做法:
每个步骤完成后立即更新，保证中间状态可追溯
```

## 版本记录

- v4.5.0 (2026-05-11): 新增状态更新机制
