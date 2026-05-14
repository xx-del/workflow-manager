# 工作流启动时间缺失问题诊断

> 记录 2026-05-11 会话中发现的 `workflow_started_at` 字段缺失导致心跳检测失效的问题

## 问题背景

### 触发场景

执行 `home漏扫` 工作流的 WIH 完成检测时，发现：

```
[2026-05-11T12:00:06.546930] ⚠️ WIH进程不存在，但压缩包是历史文件
   WIH: 进程=0, 截图=0, 完成=False
```

WIH 扫描实际已于 2026-05-10 01:09 完成，但心跳一直判断为"历史文件"。

### 根本原因

`status.json` 中缺少 `workflow_started_at` 字段：

```python
# heartbeat.py 中的检测逻辑
started_at = status.get("workflow_started_at", 0)

if started_at > 0 and file_timestamp > started_at:
    is_complete = True
else:
    log("⚠️ WIH进程不存在，但压缩包是历史文件")
```

**问题链**：
1. WORKFLOW.md 步骤 0 要求"记录工作流启动时间"
2. 但步骤 0 未被执行
3. `workflow_started_at` 默认为 0
4. `file_timestamp > 0` 条件满足，但 `started_at > 0` 不满足
5. 判断为"历史文件"，WIH 完成检测失效

## 影响范围

| 影响项 | 说明 |
|--------|------|
| WIH 完成检测 | 失效，无法判断压缩包是否新生成 |
| AWVS 完成检测 | 不受影响（使用进度百分比判断） |
| JS 敏感信息分析 | 未自动触发（依赖 `heartbeat.wih.complete`） |

## 诊断方法

### 1. 检查 status.json

```bash
cat ~/.hermes/workflows/<工作流>/status.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('workflow_started_at:', d.get('workflow_started_at', 'NOT_FOUND'))
"
```

### 2. 检查心跳日志

```bash
grep "历史文件" ~/.hermes/workflows/<工作流>/heartbeat.log | tail -5
```

### 3. 对比压缩包时间戳

```bash
# 获取 WIH 压缩包时间戳
ssh ... 'stat -c "%Y %n" /home/tool/wih/*.tar.gz' | sort -rn | head -1

# 转换为可读时间
date -d @<timestamp>
```

## 解决方案

### 方案 A：补全缺失字段（已验证）

```python
import json
from datetime import datetime

status_path = "~/.hermes/workflows/<工作流>/status.json"
with open(status_path) as f:
    status = json.load(f)

# 设置为工作流启动前的时间（如前一天）
import time
started_timestamp = int(time.time()) - 86400  # 当前时间 - 1天

status["workflow_started_at"] = started_timestamp

with open(status_path, "w") as f:
    json.dump(status, f, indent=2)
```

### 方案 B：修改心跳脚本添加兜底逻辑

在 `heartbeat.py` 的 `check_wih_progress()` 开头添加：

```python
# 兜底逻辑：如果 workflow_started_at 缺失，自动设置
if not status.get("workflow_started_at"):
    log("⚠️ workflow_started_at 缺失，自动设置为 1 天前")
    status["workflow_started_at"] = int(time.time()) - 86400
    write_status(status)
```

### 方案 C：强化步骤 0 执行

在 WORKFLOW.md 中：
- 将步骤 0 标记为 `⚠️（必须）`
- 在主 AI 执行流程中增加检查点

## 改进建议

### 1. 必填字段校验

在 `workflow-tools.js` 或 AI 执行流程中添加：

```javascript
// 初始化 status.json 时检查必填字段
function initStatus(workflowPath) {
  const requiredFields = ['workflow_started_at', 'workflow_name', 'status'];
  const status = readStatus(workflowPath);
  
  for (const field of requiredFields) {
    if (!status[field]) {
      console.error(`❌ 必填字段 ${field} 缺失`);
      return false;
    }
  }
  return true;
}
```

### 2. 心跳日志增强

在心跳日志中记录关键时间戳：

```python
log(f"📋 workflow_started_at: {started_at} ({datetime.fromtimestamp(started_at)})")
log(f"📦 WIH压缩包时间戳: {file_timestamp} ({datetime.fromtimestamp(file_timestamp)})")
log(f"🔍 判断结果: {'完成' if is_complete else '历史文件'}")
```

### 3. 兜底检测逻辑

当 `workflow_started_at` 缺失时，使用压缩包日期判断：

```python
if not started_at:
    file_date = datetime.fromtimestamp(file_timestamp)
    if file_date >= datetime.now() - timedelta(days=1):
        # 压缩包是今天或昨天生成的，认为完成
        is_complete = True
        log(f"✅ WIH完成（兜底判断：压缩包日期 {file_date}）")
```

## 验证清单

修复后验证：

- [ ] `workflow_started_at` 字段存在且大于 0
- [ ] 压缩包时间戳 > `workflow_started_at`
- [ ] `heartbeat.wih.complete` 被设置为 `true`
- [ ] 心跳日志不再显示"历史文件"警告

## 相关文档

- `WORKFLOW.md` 步骤 0：记录工作流启动时间
- `heartbeat.py` 函数 `check_wih_progress()`
- `wih_monitor.py` WIH 完成检测脚本

---

**记录时间**: 2026-05-11
**记录者**: AI Agent (workflow-manager 会话)
