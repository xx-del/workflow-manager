# WIH 完成检测心跳 - 工作流联动触发机制

> 本文档记录 WIH（Web Info Hunter）扫描完成后自动触发子工作流的联动机制。

## 背景

在 `home漏扫` 工作流中，WIH 扫描是一个独立阶段。扫描完成后，需要自动触发 `JS敏感信息分析` 工作流进行深度分析。

## 架构设计

### 监控流程

```
┌─────────────────────────────────────────────────────────────┐
│                 WIH 完成检测心跳                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐                                           │
│  │ Hermes Cron  │──每15分钟──▶ 执行检测脚本                  │
│  │ (定时触发)    │                                           │
│  └──────────────┘            │                             │
│                              ▼                             │
│                      ┌──────────────┐                      │
│                      │ 读取 status  │                      │
│                      │ .json        │                      │
│                      └──────┬───────┘                      │
│                             │                              │
│                    ┌────────┴────────┐                     │
│                    │ wih.complete?   │                     │
│                    └────────┬────────┘                     │
│                        否   │   是                         │
│                        ▼   │   ▼                           │
│                    [静默退出]│ [检查 analyzed]              │
│                            │   │                           │
│                            │   ▼                           │
│                            │ ┌────────────┐                │
│                            │ │ analyzed?  │                │
│                            │ └──────┬─────┘                │
│                            │   否   │   是                 │
│                            │   ▼    │   ▼                  │
│                            │ [触发]  │ [静默]               │
│                            │   │    │                      │
│                            │   ▼    │                      │
│                            │ [更新]  │                      │
│                            │ status  │                      │
│                            └──┘     │                      │
│                                    │                      │
└─────────────────────────────────────────────────────────────┘
```

### 状态流转

```
[WIH 扫描中] → wih.complete = true → [检测心跳触发] → analyzed = true → [JS分析完成]
```

## status.json 数据结构

```json
{
  "scan_date": "2026-05-08",
  "status": "running",
  "heartbeat": {
    "wih": {
      "complete": false,        // WIH 扫描是否完成
      "stagnant": false,        // 是否停滞
      "latest_file": "/home/tool/wih/202605072216.tar.gz",
      "screenshot_count": 0,
      "stagnant_checks": 0,
      "process_count": 0,
      "analyzed": false,        // 是否已分析（防重复）
      "analyzed_at": null       // 分析完成时间
    }
  }
}
```

## 检测逻辑

### 触发条件

必须同时满足：
1. `heartbeat.wih.complete == true` （WIH 扫描完成）
2. `heartbeat.wih.analyzed != true` （未分析过）

### 执行步骤

1. **读取 status.json**
   ```python
   with open("~/.hermes/workflows/home漏扫/status.json") as f:
       status = json.load(f)
   ```

2. **检查触发条件**
   ```python
   wih_complete = status["heartbeat"]["wih"]["complete"]
   already_analyzed = status["heartbeat"]["wih"].get("analyzed", False)
   
   if wih_complete and not already_analyzed:
       # 触发 JS 敏感信息分析
   ```

3. **触发子工作流**
   - 使用 `delegate_task` 调用 `JS敏感信息分析` 工作流
   - 传入参数：`wih_result`（WIH 扫描结果文件路径）

4. **更新 status.json**
   ```python
   status["heartbeat"]["wih"]["analyzed"] = True
   status["heartbeat"]["wih"]["analyzed_at"] = datetime.now().isoformat()
   
   with open("~/.hermes/workflows/home漏扫/status.json", "w") as f:
       json.dump(status, f, indent=4, ensure_ascii=False)
   ```

## 参数传递

### 输入参数提取

```python
# 从 scan_date 获取日期字符串
scan_date = status["scan_date"]  # "2026-05-08"
date_str = scan_date.replace("-", "")  # "20260508"

# 构建 WIH 结果文件路径
wih_result = f"/x/rank/hwxinxisouji/liuliang/results/{date_str}/wih/{latest_file_name}"
```

### 工作流调用示例

```python
delegate_task(
    goal="执行 JS敏感信息分析 工作流...",
    context=f"""
    工作流：JS敏感信息分析
    输入：{wih_result}
    工作目录：/x/rank/hwxinxisouji/liuliang/jietu
    输出目录：/x/rank/hwxinxisouji/liuliang/results/{date_str}/wih/
    触发来源：home漏扫工作流WIH完成检测心跳
    """,
    toolsets=["terminal", "file"],
    role="leaf"
)
```

## Cronjob 配置

### Hermes Cronjob 示例

```yaml
name: wih-complete-check
schedule: "*/15 * * * *"  # 每15分钟
command: |
  你是 home漏扫 工作流的 WIH 完成检测心跳。
  
  ## 任务
  1. 读取 ~/.hermes/workflows/home漏扫/status.json
  2. 检查 heartbeat.wih.complete 是否为 true
  3. 检查 heartbeat.wih.analyzed 是否已为 true（防重复）
  4. 如果 wih.complete == true 且 analyzed 不为 true：
     - 获取 scan_date，去掉横杠得到日期字符串（如 2026-05-08 → 20260508）
     - 调用 workflow-manager 技能执行 JS敏感信息分析 工作流
     - 输入参数：wih_result = /x/rank/hwxinxisouji/liuliang/results/{日期字符串}/wih
     - 输出目录：/x/rank/hwxinxisouji/liuliang/results/{日期字符串}/js_analysis/
     - 执行完成后，更新 status.json：heartbeat.wih.analyzed = true, heartbeat.wih.analyzed_at = 当前时间
  5. 如果 wih.complete 不为 true 或 analyzed 已为 true，静默退出（不输出任何内容）
  
  ## 约束
  - 如果 WIH 未完成，不要输出任何内容
  - 如果已经分析过，不要输出任何内容
  - 只在触发执行时输出结果
destination: feishu  # 可选：发送结果到飞书
```

### 配置文件位置

```
~/.hermes/cronjobs/jobs.json
```

## 执行结果示例

### 成功执行

```markdown
## ✅ WIH 完成检测心跳执行成功

### 执行摘要
- **触发条件**：home漏扫 工作流 WIH 扫描完成
- **执行结果**：成功触发并执行 JS敏感信息分析 工作流

### 工作流执行详情
| 项目 | 结果 |
|------|------|
| 输入文件 | /x/rank/.../202605072216.tar.gz |
| 输出报告 | /x/rank/.../ok.md |
| 执行耗时 | 528.11 秒 |
| 状态 | ✅ 成功完成 |

### 状态更新
```json
{
  "heartbeat": {
    "wih": {
      "complete": true,
      "analyzed": true,
      "analyzed_at": "2026-05-08T17:07:08.812833"
    }
  }
}
```
```

### 静默退出

如果 WIH 未完成或已分析，不输出任何内容（cronjob 系统自动处理）。

## 防重复机制

### 双重检查

1. **状态检查**：读取 `analyzed` 字段
2. **原子更新**：更新 status.json 时立即设置 `analyzed = true`

### 竞态条件处理

如果多个 cronjob 同时检测到条件满足：

```python
# 读取时加锁（可选）
import fcntl

with open("status.json", "r+") as f:
    fcntl.flock(f, fcntl.LOCK_EX)  # 排他锁
    
    status = json.load(f)
    
    if not status["heartbeat"]["wih"].get("analyzed"):
        # 执行工作流
        ...
        
        # 更新状态
        status["heartbeat"]["wih"]["analyzed"] = True
        f.seek(0)
        json.dump(status, f, indent=4)
        f.truncate()
    
    fcntl.flock(f, fcntl.LOCK_UN)  # 释放锁
```

## 故障排查

### 心跳未触发

检查项：
1. Cronjob 是否正常执行：`hermes cron list`
2. status.json 是否存在：`cat ~/.hermes/workflows/home漏扫/status.json`
3. `wih.complete` 是否为 true
4. `analyzed` 是否已为 true

### 工作流执行失败

检查项：
1. WIH 结果文件是否存在
2. delegate_task 是否有错误日志
3. 工作流定义是否正确（`_index.yaml`）

### status.json 更新失败

检查项：
1. 文件权限
2. JSON 格式是否正确
3. 磁盘空间

## 扩展应用

### 通用模式

WIH 完成检测心跳模式可应用于其他工作流联动场景：

```python
# 通用模板
def trigger_downstream_workflow(status_path, trigger_field, downstream_workflow):
    """
    检测工作流完成状态并触发下游工作流
    
    Args:
        status_path: status.json 路径
        trigger_field: 触发字段（如 "heartbeat.wih.complete"）
        downstream_workflow: 下游工作流名称
    """
    with open(status_path) as f:
        status = json.load(f)
    
    # 解析触发字段路径
    keys = trigger_field.split(".")
    value = status
    for key in keys:
        value = value.get(key, False)
    
    # 检查是否已处理
    processed_field = trigger_field.replace(".complete", ".processed")
    processed = get_nested_value(status, processed_field, False)
    
    if value and not processed:
        # 触发下游工作流
        execute_workflow(downstream_workflow)
        
        # 更新状态
        set_nested_value(status, processed_field, True)
        save_status(status_path, status)
```

### 应用场景

1. **AWVS 扫描完成 → 漏洞报告生成**
   - 触发字段：`heartbeat.awvs.is_complete`
   - 下游工作流：`漏洞报告生成`

2. **端口扫描完成 → 服务识别**
   - 触发字段：`heartbeat.port_scan.complete`
   - 下游工作流：`服务识别`

3. **数据收集完成 → 数据分析**
   - 触发字段：`data_collection.complete`
   - 下游工作流：`数据分析流程`

## 相关文档

- [guardian.md](./guardian.md) - 工作流智能守护机制
- [workflow-linkage-improvement](../../workflow-linkage-improvement/SKILL.md) - 工作流机制联动改进
- [hermes-cronjob-heartbeat](../../hermes-cronjob-heartbeat/SKILL.md) - Hermes cronjob 心跳模式
