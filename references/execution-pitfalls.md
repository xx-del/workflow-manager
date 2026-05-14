# 工作流执行陷阱

本文档记录工作流执行过程中的常见陷阱和解决方案。

---

## 1. `_index.yaml` 依赖配置错误

### 问题

串行工作流的 `depends_on: []` 未正确设置，导致步骤可并行执行。

### 症状

- WORKFLOW.md 定义了串行流程（步骤 1 → 2 → 3）
- `_index.yaml` 所有步骤的 `depends_on: []`
- 执行时步骤可能乱序，导致输出文件依赖失败

### 检查方法

```bash
# 检查串行工作流的依赖配置
grep -A2 "mode: serial" _index.yaml
# 应该看到每个步骤的 depends_on 有值（除第一步外）
```

### 修复示例

```yaml
# ❌ 错误：串行工作流但无依赖
mode: serial
nodes:
- id: 1
  depends_on: []
- id: 2
  depends_on: []   # 应该是 [1]

# ✅ 正确：串行依赖链
mode: serial
nodes:
- id: 1
  depends_on: []
- id: 2
  depends_on: [1]
- id: 3
  depends_on: [2]
```

---

## 2. 长耗时步骤超时

### 问题

`delegate_task` 默认 30 秒超时，但扫描类步骤可能需要 10-30 分钟。

### 症状

- 步骤执行报 timeout 错误
- 实际后台进程仍在运行

### 解决方案

| 步骤类型 | 推荐方式 |
|---------|---------|
| 短步骤（验证/检查） | `delegate_task`（默认超时） |
| 长步骤（扫描/下载） | `terminal` 工具，超时 600s+ |
| 后台进程 | 轮询等待 |

### 后台进程等待模式

```bash
# 轮询等待后台进程完成
for i in {1..60}; do
  if ! ps aux | grep -q "[p]rocess_name"; then
    echo "进程已结束"
    break
  fi
  size=$(stat -c%s /path/to/output.json 2>/dev/null || echo 0)
  echo "[$i/60] 文件大小: $((size/1024)) KB"
  sleep 5
done
```

---

## 3. NDJSON 格式解析

### 问题

某些工具（如 observer_ward）输出 NDJSON 格式，而非标准 JSON。

### 症状

```python
json.load(f)  # JSONDecodeError: Extra data
```

### 解决方案

```python
# NDJSON 解析
with open('file.json') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        # 处理 item
```

---

## 4. 网络超时处理

### 问题

更新步骤（如下载 POC 库）因网络超时失败。

### 处理流程

```
步骤执行失败
     ↓
[1] 诊断问题
     - 检查网络连接
     - 检查目标服务可用性
     ↓
[2] 尝试修复（最多3次）
     - 使用代理
     - 增加超时
     ↓
[3] 仍失败
     → 询问用户：跳过/停止/其他方案
     → 不要自行决定跳过
```

---

## 版本历史

- v1.0.0 (2026-05-06): 初始版本 - 依赖配置、超时、NDJSON、网络超时
