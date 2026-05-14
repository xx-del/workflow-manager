# 心跳验证清单

> 断点工作流心跳创建后的完整性验证方法

## 背景

断点工作流（如home漏扫）创建心跳cronjob后，必须验证以下内容：
1. cronjob是否真正创建成功
2. 是否有历史遗留心跳干扰
3. 心跳是否正常执行
4. 执行结果是否正确生成

## 验证步骤

### 1. 验证cronjob创建成功

**创建心跳后立即验证**：

```bash
# 列出所有cronjob
cronjob action='list'

# 过滤特定工作流的心跳
cronjob action='list' | grep "工作流名称"
```

**检查要点**：
- ✅ 返回的job_id必须在列表中
- ❌ 如不在列表，说明创建失败，需重新创建

**常见问题**：
| 问题 | 现象 | 解决方案 |
|------|------|----------|
| 创建返回成功但列表无job | job_id返回但不在列表 | 检查Gateway日志，重新创建 |
| 创建时未返回job_id | API调用失败 | 检查参数格式，重试 |

### 2. 检查历史遗留心跳

**问题描述**：
多次执行工作流会创建多个心跳，旧心跳未清理，导致：
- 多个心跳同时运行
- 共享同一个status.json造成状态混乱
- 资源浪费

**检查方法**：

```bash
# 列出所有同名心跳
cronjob action='list' | grep "home漏扫心跳监测"
```

**正常状态**：
- 只有1个同名心跳运行

**异常状态**：
- 有3+个同名心跳同时运行

**处理方法**：

```bash
# 停止旧心跳
cronjob action='delete' job_id='旧job_id'

# 只保留最新的心跳
```

### 3. 验证status.json状态

**检查心跳字段**：

```bash
# 读取status.json
cat ~/.hermes/workflows/<工作流名称>/status.json

# 检查关键字段
cat ~/.hermes/workflows/home漏扫/status.json | jq '{
  status: .status,
  scan_date: .scan_date,
  workflow_started_at: .workflow_started_at,
  heartbeat: .heartbeat
}'
```

**正常状态示例**：

```json
{
  "status": "running",
  "scan_date": "2026-05-09",
  "workflow_started_at": 1778256008,
  "heartbeat": {
    "check_count": 82,        // 递增表示心跳正在执行
    "last_check": "2026-05-09T10:43:45",
    "wih": {
      "complete": false,
      "process_count": 0,
      "latest_file": "/home/tool/wih/xxx.tar.gz"
    },
    "awvs": {
      "completed": 33,
      "total": 35,
      "completion_rate": 94.3
    }
  }
}
```

**检查要点**：
- ✅ `check_count` 递增（每次检测+1）
- ✅ `last_check` 时间接近当前时间（30分钟内）
- ✅ `status` 为 "running"

### 4. 验证执行结果

**4.1 远程结果验证（WIH）**：

```bash
# 获取最新WIH压缩包
ssh -A root@fl "ssh kali@home 'ls -t /home/tool/wih/*.tar.gz | head -1'"

# 获取压缩包时间戳
ssh -A root@fl "ssh kali@home 'stat -c %Y /home/tool/wih/xxx.tar.gz'"
```

**验证逻辑**：
```
1. 获取最新压缩包时间戳
2. 对比 workflow_started_at
3. 如果 压缩包时间戳 > workflow_started_at → 新结果
4. 如果 压缩包时间戳 < workflow_started_at → 历史结果
```

**4.2 远程结果验证（AWVS）**：

```bash
# 获取最新AWVS报告
ssh -A root@fl "ssh kali@home 'ls -t /home/tool/Awvs-Report-Tool/*.html | head -1'"

# 检查报告时间
ssh -A root@fl "ssh kali@home 'ls -l /home/tool/Awvs-Report-Tool/*.html | head -5'"
```

**4.3 本地结果验证**：

```bash
# 检查本地结果目录
ls -la /x/rank/hwxinxisouji/liuliang/results/$(date +%Y%m%d)/

# 检查WIH结果
ls -la /x/rank/hwxinxisouji/liuliang/results/$(date +%Y%m%d)/wih/

# 检查AWVS结果
ls -la /x/rank/hwxinxisouji/liuliang/results/$(date +%Y%m%d)/awvs/
```

**预期结果**：
- ✅ 本地目录存在
- ✅ WIH压缩包已下载
- ✅ AWVS报告已下载

## 验证流程图

```
创建心跳
    ↓
验证cronjob是否在列表
    ├─ 在列表 → 继续
    └─ 不在列表 → 重新创建
    ↓
检查是否有历史心跳
    ├─ 只有1个 → 继续
    └─ 有多个 → 清理旧心跳
    ↓
验证status.json
    ├─ check_count递增 → 继续
    └─ 未递增 → 检查心跳进程
    ↓
验证远程结果
    ├─ 有新结果 → 等待心跳下载
    └─ 无新结果 → 继续监控
    ↓
验证本地结果
    ├─ 已下载 → 完成
    └─ 未下载 → 等待心跳触发
```

## 常见问题诊断

### 问题1：cronjob创建成功但不在列表

**诊断步骤**：

```bash
# 1. 检查Gateway日志
tail -100 ~/.hermes/gateway.log | grep cronjob

# 2. 检查jobs.json文件
cat ~/.hermes/cronjobs/jobs.json | jq '.'

# 3. 重启Gateway后重试
hermes gateway restart
```

### 问题2：多个心跳同时运行

**原因**：
- 历史工作流执行未清理cronjob
- 每次执行都创建新cronjob

**解决方案**：

```bash
# 方案A：清理所有旧心跳，只保留最新的
cronjob action='list' | jq -r '.jobs[] | select(.name == "home漏扫心跳监测") | .job_id' | head -n -1 | xargs -I {} cronjob action='delete' job_id='{}'

# 方案B：工作流执行前自动清理
# 在WORKFLOW.md中添加清理步骤
```

### 问题3：心跳执行但未生成结果

**诊断步骤**：

```bash
# 1. 检查心跳触发条件
cat ~/.hermes/workflows/home漏扫/status.json | jq '.heartbeat'

# 2. 检查WIH进程
ssh -A root@fl "ssh kali@home 'ps aux | grep wih'"

# 3. 检查AWVS进度
ssh -A root@fl "ssh kali@home 'cd /home/tool/Awvs-Report-Tool && python awvs14_script.py status'"

# 4. 检查触发阈值
# WIH: process_count=0 + 压缩包时间戳>启动时间
# AWVS: completion_rate>=95%
```

## 验证报告模板

```markdown
## 心跳验证报告

**工作流**: home漏扫
**心跳job_id**: e12736260c86
**验证时间**: 2026-05-09 11:00:00

### 验证结果

| 验证项 | 状态 | 说明 |
|--------|------|------|
| cronjob创建 | ✅/❌ | job_id在列表中 |
| 历史心跳清理 | ✅/❌ | 只有1个同名心跳 |
| status.json更新 | ✅/❌ | check_count递增 |
| 远程结果生成 | ✅/❌ | 新结果文件存在 |
| 本地结果下载 | ✅/❌ | 本地目录存在 |

### 问题汇总

1. 问题1描述
2. 问题2描述

### 建议操作

1. 操作建议1
2. 操作建议2
```

## 自动化验证脚本

```python
#!/usr/bin/env python3
"""心跳完整性验证脚本"""

import json
import subprocess
from datetime import datetime

def verify_heartbeat(workflow_name, job_id):
    """验证心跳完整性"""
    
    results = {
        "cronjob_exists": False,
        "single_heartbeat": False,
        "status_updating": False,
        "remote_results": False,
        "local_results": False
    }
    
    # 1. 验证cronjob存在
    result = subprocess.run(
        ["cronjob", "action='list'"],
        capture_output=True, text=True, shell=True
    )
    jobs = json.loads(result.stdout)
    results["cronjob_exists"] = any(j["job_id"] == job_id for j in jobs["jobs"])
    
    # 2. 验证单一心跳
    same_name_jobs = [j for j in jobs["jobs"] if workflow_name in j["name"]]
    results["single_heartbeat"] = len(same_name_jobs) == 1
    
    # 3. 验证status.json
    status_file = f"~/.hermes/workflows/{workflow_name}/status.json"
    with open(status_file) as f:
        status = json.load(f)
        results["status_updating"] = status["heartbeat"]["check_count"] > 0
    
    # 4. 验证远程结果（需SSH）
    # ...
    
    # 5. 验证本地结果
    # ...
    
    return results

if __name__ == "__main__":
    import sys
    workflow_name = sys.argv[1]
    job_id = sys.argv[2]
    
    results = verify_heartbeat(workflow_name, job_id)
    print(json.dumps(results, indent=2, ensure_ascii=False))
```

## 最佳实践

1. **创建心跳后立即验证**
   - 不要等待用户反馈
   - 主动验证job_id是否在列表

2. **清理历史心跳**
   - 工作流执行前检查是否有旧心跳
   - 自动清理或提示用户清理

3. **独立status文件**
   - 每次执行创建独立status文件
   - 避免多个心跳共享同一文件

4. **验证结果真实性**
   - 对比时间戳而非仅检查文件存在
   - 区分历史文件和新生成文件

5. **报告验证结果**
   - 在工作流报告中包含心跳验证结果
   - 如有异常，明确列出问题
