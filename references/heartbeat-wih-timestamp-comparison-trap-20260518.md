# WIH 心跳检测时间戳对比陷阱

## 发现日期: 2026-05-18

## 问题

heartbeat.py 的 `check_wih_progress()` 函数用 `stat -c '%Y'` 获取压缩包 mtime，与 `workflow_started_at` 对比判断压缩包是否为"当天新文件"。结果总是误判为"历史文件"。

## 根因（双重陷阱）

### 陷阱1：workflow_started_at 每次心跳重置

`initialize_scan()` 函数（第 192 行）每次心跳执行都会重新创建 status.json：

```python
initial_status = {
    ...
    "workflow_started_at": int(time.time()),  # ← 每次重置为当前时间！
    ...
}
```

导致 `workflow_started_at` 总是晚于任何已有文件的时间戳。

### 陷阱2：压缩包时间戳 = 扫描开始时间 ≠ 扫描完成时间

wih.sh 的逻辑：
```bash
datetime=$(date +"%Y%m%d%H%M")  # 扫描开始时生成时间戳
# ... 数小时扫描过程 ...
tar -zcvf $datetime.tar.gz $datetime  # 打包时仍用开始时间
```

压缩包文件名 `202605180018.tar.gz` 和 mtime 都反映的是**扫描开始时间**（00:18），不是完成时间。当心跳在 09:00 检测时，`file_timestamp(00:18) < workflow_started_at(09:00)` → 误判为历史文件。

## 实际数据验证

```
压缩包: /home/tool/wih/202605180018.tar.gz
stat mtime: 1779034721 (2026-05-18 00:18:41)

心跳 workflow_started_at: 1779066001 (2026-05-18 09:00:01)

判断: 1779034721 < 1779066001 → "历史文件" ❌
实际: 这是当天的合法产出，WIH 扫描在凌晨完成
```

## 推荐修复方案：日期隔离

```python
if len(processes) == 0:
    latest_file = run_ssh_command("ls -t /home/tool/wih/*.tar.gz | head -1")
    if latest_file.strip():
        filename = os.path.basename(latest_file.strip())
        file_date = filename[:8]  # YYYYMMDD
        today = datetime.now().strftime("%Y%m%d")
        
        if file_date == today:
            is_complete = True
            log(f"✅ WIH完成: {filename} (当天文件)")
        else:
            log(f"⚠️ 压缩包非当天: {filename}")
```

优点：
- 简单可靠，不依赖 stat mtime
- 不受心跳启动时间影响
- 符合业务场景（每天一次扫描）

## 通用教训

**时间戳对比陷阱**：当参考时间点（workflow_started_at）可能晚于被检测事件的实际发生时间时，不能用"参考时间 < 事件时间"判断新事件。应该用更稳定的维度（如日期、序列号）替代时间戳对比。

常见场景：
- 心跳/监控脚本中判断文件是否为"新生成"
- 周期性任务中对比产出时间
- 任何"启动时间 vs 产出时间"的对比逻辑
