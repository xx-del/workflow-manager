# 心跳执行陷阱与修复经验

## 1. WIH url.txt 未复制到工作目录陷阱 ⚠️（2026-05-15 新增）

**现象**: 
- scan.sh 执行成功（退出码 0）
- WIH 目录存在且有 wih.sh
- 但 `/home/tool/wih/url.txt` 不存在
- WIH 无法执行截图扫描

**根因**: scan.sh 的 `prepare_targets()` 函数中 `cp "$target_file" /home/tool/wih/url.txt` 执行失败，但未终止脚本

**诊断方法**:
```bash
# 1. 检查 url.txt 是否存在于各位置
ssh -A root@fl "ssh kali@home 'ls -la /home/tool/new/url.txt /home/tool/wih/url.txt /home/tool/Awvs-Report-Tool/url.txt 2>&1'"

# 2. 检查 WIH 扫描目录内容（文件是否全为 0 字节）
ssh -A root@fl "ssh kali@home 'ls -la /home/tool/wih/$(date +%Y%m%d)*/'"

# 3. 如果 url1.txt 和 url200ok.txt 都是 0 字节 → WIH 无目标执行
```

**判断逻辑**:
```
WIH 目标文件检查：
- /home/tool/new/url.txt 存在 ✓ → scan.sh 目标文件正常
- /home/tool/wih/url.txt 不存在 ✗ → 复制失败
- /home/tool/wih/YYYYMMDDHHMM/url1.txt 大小为 0 → WIH 无目标

结论：url.txt 复制静默失败
```

**修复**:
```bash
# 手动复制 url.txt 到 wih 目录
ssh -A root@fl "ssh kali@home 'cp /home/tool/new/url.txt /home/tool/wih/url.txt'"

# 重新执行 WIH
ssh -A root@fl "ssh kali@home 'cd /home/tool/wih && bash wih.sh url.txt > /home/tool/wih/wih_run.log 2>&1 &'"
```

**预防**: 
- scan.sh 应在 `cp` 后验证文件存在
- 心跳脚本应增加 `/home/tool/wih/url.txt` 存在性检查

---

## 2. WIH 脚本路径不一致陷阱

**现象**: WORKFLOW.md 中写的是 `/home/tool/new/wih.sh`，但实际路径是 `/home/tool/wih/wih.sh`

**检测方法**:
```bash
# 检查两个路径
ssh -A root@fl "ssh kali@home 'ls -la /home/tool/new/wih.sh /home/tool/wih/wih.sh 2>&1'"
```

**修复**: 更新 WORKFLOW.md 中的路径为 `/home/tool/wih/wih.sh`

**预防**: 工作流文档中的脚本路径必须与实际位置一致，否则步骤执行时会找不到脚本

---

## 2. WIH 未启动陷阱

**现象**: scan.sh 执行完成（退出码 0），但 WIH 进程不存在，无新压缩包生成。

**根因**: scan.sh 通过 `cd /home/tool/wih && bash wih.sh url.txt > /tmp/wih_start.log 2>&1 &` 启动 WIH，但：
- 日志文件 `/tmp/wih_start.log` 可能被 root 用户占有（上次以 root 运行遗留），kali 用户无法写入
- WIH 启动失败时 scan.sh 只输出 warn，不影响退出码
- 心跳脚本只检测"进程是否存在+压缩包时间戳"，无法发现"从未启动"的情况

**检测方法**:
```bash
# 检查 WIH 进程
ps aux | grep -E "wih.sh|gowitness|wih_linux" | grep -v grep

# 检查日志文件权限
ls -la /tmp/wih_start.log

# 检查日志最后修改时间（如果很旧说明本次未启动）
stat /tmp/wih_start.log | grep Modify
```

**修复**:
```bash
# 方法1：用其他日志路径
ssh -A root@fl "ssh kali@home 'cd /home/tool/wih && bash wih.sh url.txt > /home/tool/wih/wih_$(date +%Y%m%d).log 2>&1 &'"

# 方法2：先修复日志文件权限
ssh -A root@fl "ssh kali@home 'sudo chown kali:kali /tmp/wih_start.log'"
```

**预防**: 心跳脚本应增加"从未启动"检测 — 对比 url.txt 修改时间与 WIH 压缩包时间戳。

---

## 2.5. AWVS 扫描任务添加失败陷阱 ⚠️（2026-05-15 新增）

**现象**: 
- scan.sh 执行成功（退出码 0）
- awvs14_script.py 输出"已启动 N 个扫描任务"
- 但 AWVS API 返回扫描任务数为 0
- 心跳脚本无法检测到 AWVS 进度

**根因**: 
- scan.sh 通过重定向到 `/tmp/awvs_add.log` 读取 awvs14_script.py 输出
- 日志文件 `/tmp/awvs_add.log` 可能被 root 用户占有
- kali 用户无法写入，导致无法读取任务状态
- awvs14_script.py 实际已添加任务，但 scan.sh 无法确认

**诊断方法**:
```bash
# 1. 检查 AWVS 扫描任务数
ssh -A root@fl "ssh kali@home 'cd /home/tool/Awvs-Report-Tool && python3 awvs14_script.py status'"
# 如果输出"总任务数: 0"但 scan.sh 报告成功 → 任务添加失败

# 2. 直接通过 API 检查
ssh -A root@fl "ssh kali@home 'curl -s -k https://10.8.0.3:13443/api/v1/scans -H \"X-Auth: <API_KEY>\" | jq \".scans | length\"'"

# 3. 检查日志文件权限
ls -la /tmp/awvs_add.log /tmp/awvs_delete.log
```

**修复**:
```bash
# 方法1：删除权限问题日志文件
ssh -A root@fl "ssh kali@home 'sudo rm -f /tmp/awvs_add.log /tmp/awvs_delete.log /tmp/wih_start.log'"

# 方法2：重新执行 scan.sh
ssh -A root@fl "ssh kali@home 'cd /home/tool/new && bash scan.sh url.txt'"

# 方法3：直接使用 awvs14_script.py 添加任务
ssh -A root@fl "ssh kali@home 'cd /home/tool/Awvs-Report-Tool && python3 awvs14_script.py add url.txt && python3 awvs14_script.py start'"
```

**预防**: 
- scan.sh 应使用可写目录（如 `/home/tool/new/logs/`）而非 `/tmp/`
- 心跳脚本应直接查询 AWVS API 验证任务数，而非仅依赖 scan.sh 输出

---

## 2. heartbeat.py 行为问题

**问题**: heartbeat.py 每次运行会：
1. 删除现有心跳 cronjob（`发现 N 个旧心跳 → 已删除`）
2. 创建新的 `status_YYYYMMDD-HHMMSS.json` 文件
3. 不更新主 `status.json`

**影响**:
- 多次运行产生多个 status 文件，造成状态碎片化
- 主 status.json 与实际状态不同步
- 原有 cronjob 被删除后如果新 cronjob 创建失败，监测中断

**建议修复方向**:
- heartbeat.py 应更新主 status.json 而非创建新文件
- 不应自动删除现有 cronjob，除非确认新 cronjob 创建成功
- 添加 `--no-cleanup` 参数控制是否清理旧 cronjob

---

## 3. Hermes Cron 命令语法

**错误**: `hermes cronjob create` → 报错 `invalid choice: 'cronjob'`

**正确**:
```bash
# 列出
hermes cron list

# 创建
hermes cron create "every 30m" "任务提示词" \
  --name "任务名称" \
  --skill agent-pool \
  --repeat 96 \
  --deliver local

# 删除
hermes cron remove <job_id>

# 暂停/恢复
hermes cron pause <job_id>
hermes cron resume <job_id>
```

**注意**: 子命令是 `cron`，不是 `cronjob`。

---

## 4. SSH 链路权限陷阱

**场景**: 通过 `ssh -A root@fl "ssh kali@home 'command'"` 执行命令时

**问题**:
- root@fl → kali@home 的 SSH 会话中，某些文件可能被 root 创建
- 后续以 kali 用户执行时遇到权限问题（如 `/tmp/wih_start.log`）
- `rm -f` 也可能因权限不足而失败（`不允许的操作`）

**解决**:
```bash
# 通过 root@fl 以 root 身份修复权限
ssh -A root@fl "ssh root@home 'chown kali:kali /tmp/wih_start.log'"

# 或使用 sudo
ssh -A root@fl "ssh kali@home 'sudo chown kali:kali /tmp/wih_start.log'"
```

---

## 7. 心跳脚本版本隔离机制（v3.2）

**现象**: heartbeat.py v3.2 每次运行会创建独立的 `status_{scan_id}.json` 文件

**机制**:
- 生成 `scan_id = YYYYMMDD-HHMMSS`
- 创建 `status_{scan_id}.json` 存储本次检测状态
- 写入 `.current_scan_id` 标记当前活跃扫描
- 主 `status.json` 与独立状态文件分离

**优点**:
- 日期隔离：新的一天自动重置状态
- 历史归档：历史状态自动归档到 `history/` 目录
- 状态追踪：每次心跳有独立记录

**注意**:
- 读取状态时应优先检查 `.current_scan_id` 指向的文件
- 心跳停止时应清理 `.current_scan_id` 标记

---

## 8. WIH 手动启动方法

当 scan.sh 执行但 WIH 未启动时，手动启动：

```bash
# 检查 url.txt 是否已复制到 wih 目录
ssh -A root@fl "ssh kali@home 'ls -la /home/tool/wih/url.txt'"

# 启动 WIH（使用其他日志路径避免权限问题）
ssh -A root@fl "ssh kali@home 'cd /home/tool/wih && bash wih.sh url.txt > /home/tool/wih/wih_run.log 2>&1 &'"

# 验证启动
ssh -A root@fl "ssh kali@home 'ps aux | grep -E \"wih.sh|wih_linux\" | grep -v grep'"
```

**注意**: 终端工具不允许使用 `nohup`，使用 `&` 即可后台运行。

---

## 6. WIH 进程结束但无新压缩包陷阱

**现象**: 
- WIH 进程已结束（`ps aux | grep wih` 无结果）
- 最新压缩包时间早于工作流启动时间
- 新目录已创建但内部文件全为空（0 字节）

**根因**:
- WIH 执行中途失败或被中断
- `gowitness.sqlite3` 数据库无截图记录
- `tar -zcvf` 打包步骤未执行

**检测方法**:
```bash
# 1. 检查进程状态
ps aux | grep -E "wih.sh|gowitness|wih_linux" | grep -v grep

# 2. 获取最新压缩包信息和时间戳
ls -lt /home/tool/wih/*.tar.gz 2>/dev/null | head -1

# 3. 对比压缩包时间戳与 workflow_started_at
# workflow_started_at 在 status.json 中记录
# 如果 压缩包时间戳 < workflow_started_at → 历史压缩包，WIH 未完成

# 4. 检查新目录是否为空
ls -lh /home/tool/wih/$(date +%Y%m%d)*
# 如果文件大小全为 0 → WIH 执行失败

# 5. 检查 gowitness 数据库
sqlite3 /home/tool/wih/gowitness.sqlite3 "SELECT COUNT(*) FROM urls;"
# 返回 0 → 无截图记录，WIH 未正常完成
```

**判断逻辑**:
```
WIH 完成条件（必须全部满足）：
1. WIH 进程不存在（已结束）
2. 最新压缩包时间戳 > workflow_started_at
3. 压缩包大小 > 0

如果条件 1 满足但条件 2/3 不满足 → WIH 异常终止
```

**修复**:
```bash
# 检查 WIH 执行日志
tail -100 /home/tool/wih/wih_run.log

# 重新执行 WIH
cd /home/tool/new && bash wih.sh url.txt > /home/tool/wih/wih_run.log 2>&1 &

# 验证启动
ps aux | grep wih | grep -v grep
```

**预防**: 心跳脚本应增加"压缩包有效性检测" — 不仅检查时间戳，还要检查文件大小和数据库记录数。
