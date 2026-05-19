# 心跳脚本 Status 文件同步机制修复

**日期**：2026-05-17
**问题**：心跳脚本与分析脚本使用不同status文件，导致状态不同步

---

## 问题表现

1. **Status文件不一致**
   - 心跳使用：`status_{scan_id}.json`（临时文件）
   - 分析脚本使用：`status.json`（主文件）
   - 结果：心跳误判step仍在运行

2. **时间戳不统一**
   - WIH下载：使用`datetime.now()`（当前日期）
   - AWVS下载：使用`scan_date`（已修复）
   - 结果：目录分散在不同日期

3. **环境变量未传递**
   - 分析脚本无法获取正确的status文件路径
   - 导致状态更新写入错误文件

---

## 根本原因

**心跳脚本设计缺陷**：
- `initialize_scan()`生成临时文件：`status_{scan_id}.json`
- 主循环动态修改：`STATUS_FILE = WORKFLOW_PATH / f"status_{scan_id}.json"`
- 分析脚本固定更新：`status.json`
- 两者完全不同步

---

## 修复方案

### 修改1：initialize_scan() 使用主status文件

**位置**：heartbeat.py 第174行

**修改**：
```python
# 原代码
status_file = WORKFLOW_PATH / f"status_{scan_id}.json"

# 修改为
status_file = STATUS_FILE  # 使用主status文件
```

---

### 修改2：删除动态STATUS_FILE修改

**位置**：heartbeat.py 第1105-1107行

**修改**：
```python
# 原代码
global STATUS_FILE
STATUS_FILE = WORKFLOW_PATH / f"status_{scan_id}.json"

# 修改为
# 删除动态修改，使用主status文件
```

---

### 修改3：execute_step_6() 使用scan_date

**位置**：heartbeat.py 第594-596行

**修改**：
```python
# 原代码
date_str = datetime.now().strftime("%Y%m%d")

# 修改为
status = read_status()
scan_date = status.get("scan_date", datetime.now().strftime("%Y-%m-%d"))
date_str = scan_date.replace("-", "")
```

---

### 修改4：分析脚本读取环境变量

**位置**：awvs_analyzer.py 第17行，js_analyzer.py 第17行

**修改**：
```python
# 原代码
STATUS_FILE = WORKFLOW_PATH / "status.json"

# 修改为
STATUS_FILE = Path(os.environ.get("STATUS_FILE", str(WORKFLOW_PATH / "status.json")))
```

---

### 修改5：心跳传递环境变量

**位置**：heartbeat.py execute_step_10() 和 execute_step_11()

**修改**：
```python
env = os.environ.copy()
env["STATUS_FILE"] = str(STATUS_FILE)
proc = subprocess.Popen(..., env=env)
```

---

## 验证方法

执行心跳后检查：
- 所有目录在同一个日期下
- step状态正确更新
- 分析结果生成
- 无重复启动

---

## 关键教训

1. **统一状态文件路径**
   - 心跳和分析脚本必须使用同一个status文件
   - 避免临时文件导致状态不同步

2. **统一时间基准**
   - 所有目录生成使用scan_date
   - 避免使用datetime.now()

3. **环境变量传递**
   - 子进程需要通过环境变量获取配置
   - 避免硬编码路径

4. **审计的重要性**
   - 用户3次审计发现遗漏
   - 方案需要逐步完善

---

## 相关文件

- `heartbeat.py` - 心跳脚本
- `awvs_analyzer.py` - AWVS分析脚本
- `js_analyzer.py` - JS分析脚本
- `status.json` - 主状态文件
