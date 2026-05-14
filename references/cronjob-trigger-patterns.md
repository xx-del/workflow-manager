# Cronjob 触发工作流模式

## 背景

工作流监控脚本（如 `wih_monitor.py`）检测到条件满足后，需要触发后续工作流。本文档记录正确的触发方式。

## 问题案例

### wih_monitor.py 的缺陷

**文件位置**: `~/.hermes/workflows/home漏扫/wih_monitor.py`

**问题代码** (第76-77行):
```python
# TODO: 这里需要调用workflow-manager执行JS敏感信息分析工作流
# 由于技能无法直接调用，这里先记录信号
```

**当前行为**:
- 仅更新 `status.json` 标记 `analyzed = True`
- **未实际触发 JS 敏感信息分析工作流**

**影响**:
- WIH 完成后不会自动执行 JS 分析
- 需要人工介入或外部触发

## 正确触发方式

### 方式 1: Hermes Cronjob（推荐）

使用 Hermes cronjob 系统触发工作流：

```python
import subprocess
import json

def trigger_workflow(workflow_name, params):
    """通过 Hermes cronjob 触发工作流"""
    prompt = f"执行工作流: {workflow_name}\n参数: {json.dumps(params)}"
    
    result = subprocess.run(
        ["hermes", "cronjob", "create", 
         "--name", f"触发-{workflow_name}",
         "--schedule", "now",  # 立即执行
         "--prompt", prompt,
         "--skills", "workflow-manager,agent-pool",
         "--deliver", "local"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        log(f"✅ 工作流触发成功: {workflow_name}")
    else:
        log(f"❌ 工作流触发失败: {result.stderr}")
```

### 方式 2: 直接调用 AI Agent

通过 `delegate_task` 启动子 agent 执行工作流：

```python
def trigger_workflow_via_agent(workflow_name, params):
    """通过 delegate_task 触发工作流"""
    goal = f"""
## 任务
执行工作流: {workflow_name}

## 参数
{json.dumps(params, indent=2)}

## 要求
1. 使用 workflow-manager 技能读取工作流定义
2. 按步骤执行
3. 汇总结果并更新状态
"""
    
    # 这里需要通过 Hermes API 或其他方式调用 delegate_task
    # Python 脚本无法直接调用，需要通过 Hermes CLI 或 HTTP API
    log(f"📝 需要触发工作流: {workflow_name}")
    log(f"   参数: {json.dumps(params)}")
```

### 方式 3: 信号文件 + 独立 Cronjob

写入信号文件，由独立 cronjob 检测并触发：

```python
def write_trigger_signal(workflow_name, params):
    """写入触发信号文件"""
    signal = {
        "workflow": workflow_name,
        "params": params,
        "triggered_at": datetime.now().isoformat(),
        "status": "pending"
    }
    
    signal_file = f"~/.hermes/workflows/{workflow_name}/trigger_signal.json"
    with open(signal_file, "w") as f:
        json.dump(signal, f, indent=2)
    
    log(f"✅ 触发信号已写入: {signal_file}")
```

然后配置独立 cronjob 每 N 分钟检测信号文件并触发。

## 修复 wih_monitor.py 的方案

### 方案 A: 使用 Hermes Cronjob（推荐）

```python
# 在 check_and_trigger() 函数中添加
def check_and_trigger():
    # ... 现有检测逻辑 ...
    
    if wih_complete and not wih_analyzed:
        log("🚀 WIH完成，触发JS敏感信息分析")
        
        # 获取参数
        scan_date = status.get("scan_date", datetime.now().strftime("%Y-%m-%d"))
        scan_date_no_hyphen = scan_date.replace("-", "")
        
        # 触发工作流
        trigger_workflow("JS敏感信息分析", {
            "wih_result_dir": f"/x/rank/hwxinxisouji/liuliang/results/{scan_date_no_hyphen}/wih",
            "output_dir": f"/x/rank/hwxinxisouji/liuliang/results/{scan_date_no_hyphen}/js_analysis"
        })
```

### 方案 B: 写入信号文件

```python
# 在 check_and_trigger() 函数中添加
def check_and_trigger():
    # ... 现有检测逻辑 ...
    
    if wih_complete and not wih_analyzed:
        log("🚀 WIH完成，写入触发信号")
        
        # 写入信号文件
        write_trigger_signal("JS敏感信息分析", {
            "wih_result_dir": wih_result_dir,
            "output_dir": output_dir
        })
        
        # 更新状态
        status["heartbeat"]["wih"]["analyzed"] = True
        status["heartbeat"]["wih"]["analyzed_at"] = datetime.now().isoformat()
        write_status(status)
```

## 当前工作流设计

根据 `WORKFLOW.md` 步骤 10 的设计：

```yaml
步骤 10: WIH 完成后自动触发 JS 分析
- 类型: 自动触发（心跳 cronjob）
- 配置文件: post_workflows/wih_complete_monitor.json
- 调度: 每 5 分钟检测一次
- 触发条件: heartbeat.wih.complete == true
- 执行工作流: JS敏感信息分析
```

**问题**: `wih_monitor.py` 就是这个 cronjob 的执行脚本，但它没有实现触发逻辑。

## 建议

1. **短期修复**: 在 `wih_monitor.py` 中实现触发逻辑（方案 A 或 B）
2. **长期方案**: 统一使用 Hermes cronjob 系统管理所有工作流触发

## 相关文档

- [hermes-cronjob-heartbeat](../hermes-cronjob-heartbeat/SKILL.md) - Hermes cronjob 心跳模式
- [workflow-design-patterns](../workflow-design-patterns/SKILL.md) - 工作流设计模式
