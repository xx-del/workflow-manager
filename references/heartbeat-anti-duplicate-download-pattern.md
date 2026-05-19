# 心跳脚本防重复下载设计模式

## 问题场景

心跳脚本每30分钟执行一次，检测到AWVS完成率≥95%就下载报告，导致重复下载累积大量文件。

## 根本原因

1. **信号不同步**：主循环的signals变量在循环开始时读取，execute_step_7()更新status后，signals未更新
2. **时间基准不统一**：使用当前日期生成目录，而非scan_date
3. **防重复机制缺失**：只检查步骤状态，未检查下载信号

## 解决方案

### 1. 双重检查机制

```python
def execute_step_7():
    status = read_status()
    
    # 双重检查：步骤状态 + 下载信号
    step_7_status = status.get("step_status", {}).get("step_7", {}).get("status")
    awvs_downloaded = status.get("parallel_signal", {}).get("awvs_downloaded", False)
    
    if step_7_status == "completed" or awvs_downloaded:
        log(f"⏭️ 步骤7已完成或已下载，跳过执行")
        return True
    
    # ... 下载逻辑 ...
    
    # 下载完成后标记
    status["parallel_signal"]["awvs_downloaded"] = True
    write_status(status)
```

### 2. 主循环信号同步

```python
# 直接从status读取，避免引用不一致
status = read_status()
awvs_downloaded = status.get("parallel_signal", {}).get("awvs_downloaded", False)
if awvs_status["completion_rate"] >= 95 and not awvs_downloaded:
    execute_step_7()
```

### 3. 时间基准统一

```python
# 使用scan_date而非当前日期
scan_date = status.get("scan_date", datetime.now().strftime("%Y-%m-%d"))
date_str = scan_date.replace("-", "")
local_dir = f"/x/rank/hwxinxisouji/liuliang/results/{date_str}/awvs"
```

## 设计原则

1. **双重保险**：step_status + parallel_signal
2. **直接读取**：主循环从status读取，不依赖局部变量
3. **时间基准统一**：所有目录生成使用scan_date
4. **立即标记**：下载完成后立即设置信号

## WIH检测修复

**路径错误**：
- ❌ `/home/tool/wih/screenshots/`
- ✅ `/home/tool/wih/*.tar.gz`

**验证增强**：
```python
# 双重验证：时间戳 + 文件名日期
timestamp_valid = started_at > 0 and file_timestamp > started_at
date_valid = file_date and scan_date and file_date == scan_date.replace("-", "")

if timestamp_valid and date_valid:
    is_complete = True
```

## 相关文件

- 心跳脚本：`~/.hermes/workflows/home漏扫/heartbeat.py`
- WIH检测：`check_wih_progress()`
- AWVS下载：`execute_step_7()`
- 主循环：`main()`

## 修复日期

2026-05-17
