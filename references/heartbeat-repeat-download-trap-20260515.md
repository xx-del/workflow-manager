# 心跳脚本重复下载陷阱

**日期**: 2026-05-15
**工作流**: home漏扫
**问题**: 心跳每次检测到 AWVS 完成都重新下载报告，导致文件累积

---

## 问题现象

| 指标 | 数值 | 说明 |
|------|------|------|
| 步骤 7 执行次数 | **216 次** | 心跳每次检测都重新执行 |
| 远程服务器报告文件 | **210 个** | 每次执行生成新报告 |
| 本地报告文件 | **9 个** | 今天下载的文件 |

### 本地文件时间分布

```
00:00, 00:14, 00:30, 00:47, 01:00, 01:30, 01:50, 02:00, 02:21, 02:30
```

每 15-30 分钟一个文件，与心跳频率匹配。

---

## 根因分析

### 心跳脚本逻辑缺陷

**heartbeat.py execute_step_7() 函数**：

```python
def execute_step_7():
    """执行步骤7: AWVS下载流程"""
    
    # ❌ 问题：无防重复检测
    # 应该先检查步骤 7 是否已完成
    
    # 7.1 生成合并报告
    report_result = run_ssh_command("python3 awvs14_script.py report")
    # ❌ 问题：每次都生成新报告
    
    # 7.2 获取最新报告文件名
    report_name = run_ssh_command("ls -t *.html | head -1")
    # ❌ 问题：总是获取最新文件，导致每次下载不同文件
    
    # 7.4 下载报告
    # ❌ 问题：未检查本地是否已存在报告
```

### 缺失机制

1. **防重复检测**：未检查步骤状态是否为 completed
2. **本地文件检测**：未检查本地是否已存在报告
3. **远程清理**：未清理历史报告文件

---

## 诊断方法

### 1. 查看心跳日志执行次数

```bash
grep -c "步骤7" ~/.hermes/workflows/home漏扫/heartbeat.log
```

**输出**：`216`

### 2. 查看远程服务器文件数量

```bash
ssh -A root@fl "ssh kali@home 'ls /home/tool/Awvs-Report-Tool/*.html | wc -l'"
```

**输出**：`210`

### 3. 查看本地文件时间分布

```bash
ls -lh /x/rank/hwxinxisouji/liuliang/results/20260515/awvs/
```

**输出**：多个时间戳相近的文件

---

## 修复方案

### 方案 1：代码修复（推荐）

**修改 heartbeat.py execute_step_7() 函数**：

```python
def execute_step_7():
    """执行步骤7: AWVS下载流程"""
    
    # ✅ 新增：防重复检测
    status = read_status()
    step_7_status = status.get("steps", {}).get("7", {}).get("status")
    if step_7_status == "completed":
        log("⏭️ 步骤7已完成，跳过执行")
        return True
    
    log("🚀 开始执行步骤7: AWVS下载")
    update_step_status("step_7", "in_progress")
    
    # 7.3 创建本地目录
    date_str = datetime.now().strftime("%Y%m%d")
    local_dir = f"/x/rank/hwxinxisouji/liuliang/results/{date_str}/awvs"
    os.makedirs(local_dir, exist_ok=True)
    
    # ✅ 新增：检查本地是否已存在报告
    existing_reports = list(Path(local_dir).glob("*.html"))
    if existing_reports:
        latest_report = max(existing_reports, key=os.path.getmtime)
        log(f"⚠️ 本地已存在报告: {latest_report.name}")
        log("   使用现有报告，跳过下载")
        update_step_status("step_7", "completed")
        return True
    
    # 原有下载代码...
    
    # ✅ 新增：清理远程历史报告
    cleanup_result = run_ssh_command(
        "find /home/tool/Awvs-Report-Tool -name '*.html' -mtime +1 -type f -delete"
    )
    log("   🧹 已清理远程历史报告")
    
    return True
```

### 方案 2：数据清理（立即执行）

**清理远程服务器历史报告**：
```bash
ssh -A root@fl "ssh kali@home 'cd /home/tool/Awvs-Report-Tool && find . -name \"*.html\" -mtime +1 -type f -delete'"
```

**清理本地重复文件（保留最新 1 个）**：
```bash
cd /x/rank/hwxinxisouji/liuliang/results/20260515/awvs
ls -t *.html | tail -n +2 | xargs rm -f
```

### 方案 3：配置优化

**心跳完成后自动停止**：
- 在 should_stop() 中检测所有步骤完成
- 完成后停止心跳 cronjob

---

## 验证清单

- [ ] heartbeat.py 已修改
- [ ] 防重复机制已添加（步骤状态检查）
- [ ] 本地文件检测已添加
- [ ] 远程清理逻辑已添加
- [ ] 远程服务器文件数量 ≤ 1
- [ ] 本地文件数量 = 1

---

## 经验总结

1. **防重复设计**：心跳脚本必须检测步骤是否已完成，避免重复执行
2. **本地优先**：下载前检查本地是否已存在文件，避免重复下载
3. **定期清理**：远程服务器应定期清理历史文件，避免累积
4. **日志监控**：定期检查心跳日志，发现异常执行次数

---

## 相关陷阱

- `/tmp/*.log` 权限陷阱（`references/heartbeat-execution-pitfalls-20260514.md`）
- 断点工作流后续步骤未执行（`references/breakpoint-workflow-post-step-diagnosis-20260515.md`）

---

## 代码位置

- `heartbeat.py` 第 654-700 行：execute_step_7() 函数
- `heartbeat.py` 第 660 行：生成合并报告（应添加防重复）
- `heartbeat.py` 第 673 行：创建本地目录（应添加本地文件检测）
- `heartbeat.py` 第 700 行：下载完成（应添加远程清理）
