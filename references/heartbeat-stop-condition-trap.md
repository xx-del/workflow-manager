# 心跳停止条件陷阱 - 步骤编号不一致导致心跳无法结束

**案例日期**: 2026-05-09  
**严重程度**: 🔴 高危（心跳持续运行 72 小时）  
**影响范围**: 所有使用断点+心跳模式的工作流

---

## 问题表现

用户持续收到旧告警消息，误以为工作流未完成：
- 告警内容显示："⚠️ AWVS 仍有 1 个目标扫描中"
- 实际状态：AWVS 已完成全部扫描（35/35，100%）
- 心跳状态：仍在运行，未自动结束

---

## 根本原因

### 1. 步骤编号不一致

**工作流定义 (_index.yaml)**:
```yaml
nodes:
  - id: step_1  # 启动扫描
  - id: step_2  # 断点返回
  - id: step_3  # 结果处理（心跳自动执行）
```

**心跳代码 (heartbeat.py)**:
```python
def should_stop_and_cleanup(scan_id: str) -> tuple:
    step_status = status.get("step_status", {})
    required_steps = ["step_6", "step_7", "step_8"]  # ← 硬编码的步骤编号
```

**实际 status.json 记录**:
```json
{
  "step_status": {
    "step_10": "JS敏感信息分析",
    "step_11": "AWVS报告分析"
  }
}
```

### 2. 停止条件永远不满足

心跳检查 `step_6/7/8` 是否完成，但实际执行的是 `step_10/11`，导致：
- `all_completed` 永远为 `False`
- 心跳继续运行直到最大运行时间（72小时）

### 3. 告警消息未更新

用户看到的是旧告警消息（19:09 生成），而非最新状态（22:42 最终监测报告）。

---

## 诊断方法

### 1. 检查步骤编号一致性

```bash
# 读取工作流定义
cat ~/.hermes/workflows/<workflow_name>/_index.yaml | grep "id: step_"

# 读取心跳代码中的停止条件
grep -n "required_steps" ~/.hermes/workflows/<workflow_name>/heartbeat.py

# 读取实际执行的步骤
cat ~/.hermes/workflows/<workflow_name>/status.json | jq '.step_status | keys'
```

### 2. 检查心跳停止条件

```python
# 读取 status.json
status = read_status()

# 检查停止条件
step_status = status.get("step_status", {})
required_steps = ["step_6", "step_7", "step_8"]

all_completed = all(
    step_status.get(s, {}).get("status") == "completed"
    for s in required_steps
)

print(f"Required steps: {required_steps}")
print(f"Actual steps: {list(step_status.keys())}")
print(f"All completed: {all_completed}")
```

### 3. 检查最大运行时间

```python
created_str = status.get("created", "")
created = datetime.fromisoformat(created_str)
runtime = (datetime.now() - created).total_seconds()
max_runtime = 259200  # 72小时

print(f"Runtime: {runtime}s ({runtime/3600:.1f}h)")
print(f"Max runtime: {max_runtime}s ({max_runtime/3600:.1f}h)")
print(f"Remaining: {(max_runtime - runtime)/3600:.1f}h")
```

---

## 解决方案

### 方案 1：修复步骤编号不一致（推荐）

**修改心跳代码**：

```python
# 方案 A：动态读取工作流定义
import yaml

def get_required_steps(workflow_path: Path) -> list:
    """从工作流定义中读取所有步骤 ID"""
    index_file = workflow_path / "_index.yaml"
    with open(index_file) as f:
        workflow = yaml.safe_load(f)
    
    return [node["id"] for node in workflow["nodes"]]

# 使用
required_steps = get_required_steps(WORKFLOW_PATH)
```

**或修改工作流定义**：

```yaml
# 统一步骤编号
nodes:
  - id: step_1  # 启动扫描
  - id: step_2  # 断点返回
  - id: step_6  # WIH下载（与心跳代码一致）
  - id: step_7  # AWVS下载
  - id: step_8  # 清理任务
```

### 方案 2：立即停止心跳（临时）

```bash
# 查看当前心跳
hermes cron list

# 删除心跳
hermes cron remove <job_id>

# 更新 status.json
# 将 status 改为 "completed"
```

### 方案 3：更新告警消息

```python
# 重新生成告警消息
# 使用最新的实时状态
# 删除旧的 alert_message.md
```

---

## 预防措施

### 1. 工作流设计规范

**规则**：工作流步骤编号必须在定义和代码中保持一致

**验证方法**：

```bash
# 创建工作流后立即验证
python3 << 'EOF'
import yaml
import json
from pathlib import Path

workflow_path = Path("~/.hermes/workflows/<workflow_name>").expanduser()

# 读取工作流定义
with open(workflow_path / "_index.yaml") as f:
    workflow = yaml.safe_load(f)
defined_steps = [node["id"] for node in workflow["nodes"]]

# 读取心跳代码中的停止条件
with open(workflow_path / "heartbeat.py") as f:
    code = f.read()
import re
match = re.search(r'required_steps\s*=\s*\[(.*?)\]', code)
if match:
    hardcoded_steps = [s.strip().strip('"\'') for s in match.group(1).split(',')]
    
    if set(defined_steps) != set(hardcoded_steps):
        print("⚠️ 步骤编号不一致！")
        print(f"  定义: {defined_steps}")
        print(f"  代码: {hardcoded_steps}")
    else:
        print("✅ 步骤编号一致")
EOF
```

### 2. 心跳监控增强

**在心跳日志中记录停止条件检查结果**：

```python
def should_stop_and_cleanup(scan_id: str) -> tuple:
    step_status = status.get("step_status", {})
    required_steps = get_required_steps(WORKFLOW_PATH)
    
    # 记录检查详情
    log(f"📊 停止条件检查:")
    log(f"  定义步骤: {required_steps}")
    log(f"  实际步骤: {list(step_status.keys())}")
    
    for step in required_steps:
        step_state = step_status.get(step, {}).get("status", "未执行")
        log(f"  {step}: {step_state}")
    
    all_completed = all(
        step_status.get(s, {}).get("status") == "completed"
        for s in required_steps
    )
    
    log(f"  结论: {'✅ 可停止' if all_completed else '❌ 继续运行'}")
    
    return all_completed, "所有步骤已完成" if all_completed else ""
```

### 3. 告警消息版本管理

**规则**：每次重新分析后，必须删除旧告警消息，生成新告警

```python
# 生成新告警
alert_file = output_dir / "alert_message.md"
alert_file.write_text(new_alert_message)

# 记录版本信息
status["heartbeat"]["awvs"]["alert_version"] = datetime.now().isoformat()
status["heartbeat"]["awvs"]["alert_file"] = str(alert_file)
write_status(status)
```

---

## 检查清单

创建或修改工作流时，必须检查：

- [ ] 工作流定义中的步骤编号与心跳代码一致
- [ ] 心跳停止条件检查所有必要步骤
- [ ] 心跳日志记录停止条件检查详情
- [ ] 告警消息在重新分析后更新
- [ ] status.json 记录告警版本和时间

---

## 相关案例

- [workflow-design-patterns 模式 9: 断点工作流心跳触发模式](../../workflow-design-patterns/SKILL.md)
- [workflow-completion-monitoring-architecture](../workflow-completion-monitoring-architecture.md)
- [cronjob-execution-practice-20260509-5](../../awvs-report-extractor/references/cronjob-execution-practice-20260509-5.md)

---

## 关键教训

1. **步骤编号是契约** - 工作流定义和代码必须保持一致
2. **停止条件需要验证** - 不能假设步骤编号正确
3. **告警消息会过期** - 必须在重新分析后更新
4. **心跳日志要详细** - 记录停止条件检查过程，便于诊断
