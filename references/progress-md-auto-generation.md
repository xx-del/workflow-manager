# progress.md 自动生成机制

**版本**: v6.2.0
**更新时间**: 2026-05-12
**实施状态**: ✅ 已完成

---

## 概述

workflow-manager v6.2.0 实现了 progress.md 自动生成机制，解决了以下问题：

1. **progress.md 未自动生成**：execute.py --plan-only 只生成 status.md，不生成 progress.md
2. **执行过程无记录**：步骤执行后没有自动记录执行过程
3. **会话恢复困难**：中断后无法了解执行进度

---

## 实施方案

**方案 B：步骤执行时自动追加**

### 核心函数

#### 1. init_progress_md(workflow_name: str)

**功能**：初始化 progress.md 文件

**参数**：
- workflow_name: 工作流名称

**输出**：生成 progress.md 文件（从模板或默认内容）

**实现**：
```python
def init_progress_md(workflow_name: str):
    """初始化 progress.md 文件"""
    progress_path = WORKFLOWS_DIR / workflow_name / "progress.md"
    
    if progress_path.exists():
        return
    
    # 从模板读取
    template_path = Path.home() / ".hermes/skills/openclaw-imports/workflow-manager/templates/progress.md"
    if template_path.exists():
        content = template_path.read_text()
    else:
        # 默认模板
        content = f"""# 工作流执行日志：{workflow_name}
...
"""
    
    progress_path.write_text(content)
```

---

#### 2. log_step_execution(workflow_name, step_name, command, output, duration, status)

**功能**：记录步骤执行到 progress.md

**参数**：
- workflow_name: 工作流名称
- step_name: 步骤名称
- command: 执行的命令
- output: 执行输出
- duration: 执行耗时（秒）
- status: 执行状态（completed/failed/skipped）

**输出**：追加执行记录到 progress.md

**实现**：
```python
def log_step_execution(workflow_name: str, step_name: str, command: str, output: str, duration: float, status: str = "completed"):
    """记录步骤执行到 progress.md"""
    progress_path = WORKFLOWS_DIR / workflow_name / "progress.md"
    
    # 如果文件不存在，先初始化
    if not progress_path.exists():
        init_progress_md(workflow_name)
    
    # 生成执行记录
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    status_icon = {
        "completed": "✅ 已完成",
        "failed": "❌ 失败",
        "skipped": "⏭️ 已跳过",
        "in_progress": "⏳ 执行中"
    }
    
    entry = f"""
### {timestamp} - {step_name}

**执行时间**: {timestamp}
**状态**: {status_icon.get(status, status)}
**耗时**: {duration:.1f} 秒

**执行命令**:
```bash
{command}
```

**执行结果**:
```
{output[:500]}...
```

---
"""
    
    # 插入到"步骤执行记录"章节之后
    ...
```

---

### 命令行接口

#### --init-progress

**用法**：
```bash
python update_plan.py <workflow_name> --init-progress
```

**功能**：初始化 progress.md 文件

**示例**：
```bash
python update_plan.py asset-collection --init-progress
```

---

#### --log-step

**用法**：
```bash
python update_plan.py <workflow_name> --log-step <step_name> \
  --command <cmd> \
  --output <out> \
  --duration <sec> \
  [--status <status>]
```

**功能**：记录步骤执行到 progress.md

**参数**：
- step_name: 步骤名称
- --command: 执行的命令
- --output: 执行输出
- --duration: 执行耗时（秒）
- --status: 执行状态（可选，默认 completed）

**示例**：
```bash
# 记录成功的步骤
python update_plan.py asset-collection --log-step "步骤 1: 端口扫描" \
  --command "nmap -sV 192.168.1.1" \
  --output "发现 259 个开放端口" \
  --duration 120.5

# 记录失败的步骤
python update_plan.py asset-collection --log-step "步骤 3: 漏洞扫描" \
  --command "nmap --script vuln 192.168.1.1" \
  --output "错误：目标不可达" \
  --duration 5.2 \
  --status failed
```

---

## 使用场景

### 场景 1：工作流开始时初始化

```bash
# 初始化 progress.md
python update_plan.py asset-collection --init-progress

# 然后执行工作流
python execute.py asset-collection --plan-only
```

---

### 场景 2：步骤执行后记录

**主 AI 在执行步骤后调用**：

```python
# 步骤执行前
start_time = time.time()

# 执行步骤
result = terminal(command=step_command)

# 步骤执行后
duration = time.time() - start_time

# 记录到 progress.md
terminal(command=f"""python update_plan.py {workflow_name} \
  --log-step "{step_name}" \
  --command "{step_command}" \
  --output "{result}" \
  --duration {duration}""")
```

---

### 场景 3：失败步骤记录

```bash
# 记录失败步骤
python update_plan.py asset-collection --log-step "步骤 3: 漏洞扫描" \
  --command "nmap --script vuln 192.168.1.1" \
  --output "错误：目标不可达" \
  --duration 5.2 \
  --status failed
```

---

## 生成的 progress.md 结构

```markdown
# 工作流执行日志：asset-collection

**创建时间**: 2026-05-12 17:00:00
**工作流版本**: 1.0.0

---

## 会话记录

---

## 步骤执行记录

### 2026-05-12 17:05:00 - 步骤 1: 端口扫描

**执行时间**: 2026-05-12 17:05:00
**状态**: ✅ 已完成
**耗时**: 120.5 秒

**执行命令**:
```bash
nmap -sV 192.168.1.1
```

**执行结果**:
```
发现 259 个开放端口
```

---

### 2026-05-12 17:07:00 - 步骤 2: 服务识别

**执行时间**: 2026-05-12 17:07:00
**状态**: ✅ 已完成
**耗时**: 85.3 秒

**执行命令**:
```bash
nmap -sV --version-intensity 5 192.168.1.1
```

**执行结果**:
```
识别到 HTTP, SSH, MySQL 服务
```

---

### 2026-05-12 17:08:30 - 步骤 3: 漏洞扫描

**执行时间**: 2026-05-12 17:08:30
**状态**: ❌ 失败
**耗时**: 5.2 秒

**执行命令**:
```bash
nmap --script vuln 192.168.1.1
```

**执行结果**:
```
错误：目标不可达
```

---

## 错误记录

| 错误 | 步骤 | 尝试 | 解决方案 |
|------|------|------|----------|

---

## 统计信息

- ✅ 成功步骤：2
- ❌ 失败步骤：1
- ⏭️ 跳过步骤：0
- ⏱️ 总耗时：211.0 秒
```

---

## 与 planning-with-files 对比

| 维度 | planning-with-files | workflow-manager v6.2 |
|------|---------------------|----------------------|
| progress.md 生成 | PostToolUse 提醒 + AI 更新 | --init-progress + --log-step |
| 更新时机 | 每次工具调用后 | 步骤执行后 |
| 强制性 | ⚠️ 提醒，非强制 | ✅ 可编程调用 |
| 自动化程度 | 低（依赖 AI） | 中（需主 AI 调用） |
| 记录完整性 | 依赖 AI 记忆 | ✅ 完整记录命令/输出/耗时 |

**优势**：
- 可编程调用，不依赖 AI 记忆
- 完整记录命令、输出、耗时
- 支持失败状态标记
- 支持会话恢复

---

## 功能测试结果

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 初始化 progress.md | ✅ 通过 | 文件正确生成（958 bytes） |
| 记录步骤执行 | ✅ 通过 | 内容正确追加 |
| 记录多个步骤 | ✅ 通过 | 多步骤记录正常 |
| 记录失败步骤 | ✅ 通过 | 失败状态正确标记（❌ 失败） |

**通过率**：4/4 (100%)

---

## 后续优化（可选）

1. **统计信息自动更新**
   - 当前：模板中的统计信息是占位符
   - 优化：每次记录步骤后自动更新统计信息

2. **错误记录自动追加**
   - 当前：错误记录章节需要手动填写
   - 优化：失败步骤自动追加到错误记录表

3. **PostToolUse 钩子集成**
   - 当前：需要主 AI 手动调用
   - 优化：钩子自动检测并记录（需要 Hermes 支持）

---

## 参考资料

- workflow-manager SKILL.md v6.2.0
- update_plan.py 源代码
- templates/progress.md 模板
