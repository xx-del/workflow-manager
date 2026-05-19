# 拼接工作流执行实例

**日期**: 2026-05-15
**工作流**: 通用漏洞扫描
**类型**: branch（拼接工作流）

---

## 执行流程

### 1. Hook 注入子工作流路径

```
🔄 拼接工作流检测

工作流: 通用漏洞扫描
类型: branch

子工作流路径：
1. 凭证检测: ~/.hermes/workflows/凭证检测/WORKFLOW.md
2. home漏扫: ~/.hermes/workflows/home漏扫/WORKFLOW.md
3. 爆破测试: ~/.hermes/workflows/爆破测试/WORKFLOW.md
4. nuclei扫描: ~/.hermes/workflows/nuclei扫描/WORKFLOW.md

📋 主AI任务：按顺序读取上述WORKFLOW.md，合并生成统一status.md
```

### 2. 主AI 合并 WORKFLOW.md

```python
# 读取所有子工作流 WORKFLOW.md
workflows = [
    "凭证检测/WORKFLOW.md",   # 步骤 1-6
    "home漏扫/WORKFLOW.md",   # 步骤 7-15
    "爆破测试/WORKFLOW.md",   # 步骤 16-25
    "nuclei扫描/WORKFLOW.md"  # 步骤 26-35
]

# 合并步骤，编号连续
total_steps = []
step_id = 1
for wf in workflows:
    for step in wf.steps:
        step.id = step_id
        step.name = f"[{wf.name}] {step.name}"
        total_steps.append(step)
        step_id += 1
```

### 3. 生成统一 status.md

```markdown
# 通用漏洞扫描工作流状态

## 执行信息
- 工作流: 通用漏洞扫描
- 开始时间: 2026-05-15T10:00:00
- 状态: initialized

## 步骤状态

| 步骤 | 名称 | 状态 |
|------|------|------|
| 1 | [凭证检测] 验证输入文件 | pending |
| 2 | [凭证检测] 环境准备 | pending |
| ... | ... | ... |
| 7 | [home漏扫] 准备工作 | pending |
| ... | ... | ... |
| 35 | [nuclei扫描] 提取高危漏洞 | pending |

## 下一步行动
执行步骤 1: [凭证检测] 验证输入文件
```

### 4. 使用 agent-pool 执行

```python
# 执行所有步骤（35个）
for step in total_steps:
    orchestrator.execute(
        task_description=step.name,
        required_capabilities=["cli_execution"],
        source_workflow="通用漏洞扫描"
    )
```

---

## 断点工作流处理

当子工作流包含断点步骤时：

1. 执行到断点步骤 → 启动心跳
2. 标记断点步骤状态为 `heartbeat_running`
3. **继续执行后续步骤**（不等待心跳完成）
4. 心跳自动完成断点后的步骤

**关键**：断点工作流不会阻塞拼接工作流的后续子工作流执行。

---

## 验证清单

- [ ] Hook 检测拼接工作流并注入子工作流路径
- [ ] 主AI 读取所有子工作流 WORKFLOW.md
- [ ] 合并生成统一 status.md（步骤编号连续）
- [ ] 使用 agent-pool 执行所有步骤
- [ ] 断点工作流启动心跳后继续执行后续步骤
