# status.json 依赖模式分析

日期：2026-05-18

## 一、workflow-manager 依赖 status.json 的组件

### 1. 代码模块（Python）

| 模块 | 读取 | 写入 | 用途 |
|------|------|------|------|
| execute.py | ✅ | ❌ | 初始化时读取状态 |
| complete.py | ✅ | ❌ | 完成时汇总结果 |
| status.py | ✅ | ✅ | 状态管理器（核心） |
| executor.py | ✅ | ✅ | 执行器（读写状态） |

### 2. Hook 脚本（Shell）

| Hook | 读取 | 用途 |
|------|------|------|
| workflow-step-check | ✅ | 检测活跃工作流、串行模式检查 |
| workflow-context | ✅ | 注入工作流上下文 |

---

## 二、具体依赖场景

### 1. Hook：检测活跃工作流

```bash
# handler.sh L16
ACTIVE_WORKFLOW=$(find "$WORKFLOW_DIR" -maxdepth 2 -name "status.json" \
  -exec grep -l -E '"status": "(running|initialized)"' {} \;)
```

用途：发现未完成的工作流时阻止执行，要求先初始化

### 2. Hook：串行模式检查

```bash
# handler.sh L103-120
WORKFLOW_MODE=$(python3 -c "import json; d=json.load(open('$STATUS_JSON')); \
  print(d.get('mode', 'serial'))")

CURRENT_STEP=$(python3 -c "import json; d=json.load(open('$STATUS_JSON')); \
  print(d.get('current_step', 1))")

PREV_STATUS=$(python3 -c "import json; d=json.load(open('$STATUS_JSON')); \
  print(d.get('steps', {}).get(str($PREV_STEP), {}).get('status', 'pending'))")
```

用途：串行模式下检查前一步骤是否完成

### 3. Status Manager：状态管理

```python
# status.py
def get_status(workflow_path):
    status_path = Path(workflow_path) / "status.json"
    return json.load(open(status_path))

def update_status(workflow_path, data):
    existing = json.load(open(status_path))
    new_status = {**existing, **data}
    json.dump(new_status, open(status_path, 'w'))
```

用途：所有状态读写的核心接口

---

## 三、与心跳脚本的对比

### home 漏扫心跳脚本机制

**完成判断（不依赖 status.json）**：
- WIH：`ps aux | grep wih.sh` + `ls *.tar.gz` 时间戳
- AWVS：`awvs14_script.py status` 完成率

**触发控制（依赖 status.json）**：
- `parallel_signal` 信号量 → 防止重复触发
- 只触发一次：`if complete and not signals.get("wih_complete")`

### 对比总结

| 项目 | workflow-manager | home 漏扫心跳 |
|------|------------------|---------------|
| 完成判断 | ✅ 依赖 status.json | ❌ 直接检测远程 |
| 触发控制 | ✅ 依赖 status.json | ✅ 依赖 status.json |
| 状态写入 | Hook + Executor 写入 | 心跳脚本写入 |

---

## 四、设计原则

**workflow-manager**：完全依赖 status.json
- 所有判断都基于状态文件
- Hook 拦截依赖状态检查
- 适合需要严格状态追踪的场景

**心跳脚本**：状态文件只做信号量
- 完成判断独立于状态文件
- 状态文件用于防重复触发
- 适合需要实时检测的长时间运行任务

---

## 五、选择建议

| 场景 | 推荐方案 |
|------|----------|
| 短时工作流（<1小时） | workflow-manager（完全依赖 status.json） |
| 长时工作流（>1小时） | 心跳脚本（远程检测 + 信号量） |
| 需要实时状态 | 心跳脚本 |
| 需要严格顺序 | workflow-manager |
