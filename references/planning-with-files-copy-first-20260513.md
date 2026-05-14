# planning-with-files 完整抄作业指南

**日期**：2026-05-13  
**来源**：用户明确纠正

---

## 核心纠正

用户原话：
> "抄作业先完整抄 抄完再优化 而不是自作主张"

这适用于所有技能融合场景，不仅是 workflow-manager。

---

## 错误示范（本次会话）

### 错误1：自作主张写代码脚本

```python
# update_plan.py - 自作主张写的动态更新脚本
def update_step_status(workflow_name, step_name, status):
    """更新步骤状态"""  # ← 这是代码解决方案，不是机制融合

# update_parallel_progress.py - 自作主张写的并行追踪脚本  
def init_parallel_tracking(workflow_name, total_tasks, batch_size):
    """初始化并行追踪"""  # ← 同上
```

**问题**：planning-with-files 根本没有这些脚本，它是靠 AI 直接编辑文件。

### 错误2：预定义动态模板

```yaml
# 自作主张设计的 dynamic_batch 类型
### 步骤 3: URL分析
- type: dynamic_batch  # ← planning-with-files 没有这个
- config:
    input_file: "{{步骤2.output_file}}"
    batch_size: 100
```

**问题**：planning-with-files 的动态更新是 AI 自由编辑，不需要预定义模板。

### 错误3：优化后才抄

设计了"混合方案 C"（代码 + 钩子），而不是完整抄 planning-with-files 的纯钩子方案。

---

## 正确做法

### 步骤1：完整抄机制

planning-with-files 的核心机制：

```
1. UserPromptSubmit 钩子：显示 task_plan.md 前 50 行 + progress.md 后 20 行
2. PreToolUse 钩子：注入 task_plan.md 前 30 行
3. PostToolUse 钩子：提醒更新 progress.md 和 task_plan.md
4. Stop 钩子：检查所有阶段完成
5. AI 直接编辑 task_plan.md（动态更新）
6. 钩子确保 AI 始终看到最新计划
```

映射到 workflow-manager：

```
1. UserPromptSubmit 钩子：显示 status.md 前 50 行 + progress.md 后 20 行
2. PreToolUse 钩子：注入 status.md 前 30 行
3. PostToolUse 钩子：提醒更新 progress.md 和 status.md
4. Stop 钩子：检查所有步骤完成
5. AI 直接编辑 status.md（动态更新）
6. 钩子确保 AI 始终看到最新状态
```

### 步骤2：抄完再优化

完整抄完机制后，观察运行效果，再针对性优化。

优化必须在"完整抄"基础上做，不是在"没抄就改"的基础上做。

---

## planning-with-files 钩子详细配置（抄作业源码）

### UserPromptSubmit

```yaml
hooks:
  - type: command
    command: |
      PLAN_DIR=$(ls -td ~/.hermes/plans/20* 2>/dev/null | head -1)
      if [ -n "$PLAN_DIR" ] && [ -f "$PLAN_DIR/task_plan.md" ]; then
        echo "[planning-with-files] ACTIVE PLAN — $PLAN_DIR"
        head -50 "$PLAN_DIR/task_plan.md"
        echo ''
        echo '=== recent progress ==='
        tail -20 "$PLAN_DIR/progress.md" 2>/dev/null
        echo ''
        echo "[planning-with-files] Read findings.md for research context. Continue from the current phase."
      fi
```

### PreToolUse

```yaml
hooks:
  - matcher: "Write|Edit|Bash|Read|Glob|Grep"
    hooks:
      - type: command
        command: |
          PLAN_DIR=$(ls -td ~/.hermes/plans/20* 2>/dev/null | head -1)
          if [ -n "$PLAN_DIR" ] && [ -f "$PLAN_DIR/task_plan.md" ]; then
            cat "$PLAN_DIR/task_plan.md" | head -30
          fi
```

### PostToolUse

```yaml
hooks:
  - matcher: "Write|Edit"
    hooks:
      - type: command
        command: |
          PLAN_DIR=$(ls -td ~/.hermes/plans/20* 2>/dev/null | head -1)
          if [ -n "$PLAN_DIR" ] && [ -f "$PLAN_DIR/task_plan.md" ]; then
            echo "[planning-with-files] Update $PLAN_DIR/progress.md with what you just did. If a phase is now complete, update task_plan.md status."
          fi
```

### Stop

```yaml
hooks:
  - type: command
    command: |
      sh "$SKILL_DIR/scripts/check-complete.sh"
```

---

## workflow-manager 钩子适配（完整抄 + 路径替换）

### 路径映射

| planning-with-files | workflow-manager |
|---------------------|------------------|
| `~/.hermes/plans/20*` | `~/.hermes/workflows/*/` |
| `task_plan.md` | `status.md` |
| `findings.md` | `findings.md` |
| `progress.md` | `progress.md` |
| `[planning-with-files]` | `[workflow-manager]` |
| `phase` | `step` |

### UserPromptSubmit（适配后）

```bash
WORKFLOW_DIR="$HOME/.hermes/workflows"
STATUS_FILE=$(find "$WORKFLOW_DIR" -name "status.md" 2>/dev/null | head -1)

if [ -n "$STATUS_FILE" ]; then
    WF_DIR=$(dirname "$STATUS_FILE")
    echo "[workflow-manager] ACTIVE WORKFLOW — $WF_DIR"
    head -50 "$STATUS_FILE"
    echo ''
    echo '=== recent progress ==='
    tail -20 "$WF_DIR/progress.md" 2>/dev/null
    echo ''
    echo "[workflow-manager] Read findings.md for research context. Continue from the current step."
fi
```

### PreToolUse（适配后）

```bash
WORKFLOW_DIR="$HOME/.hermes/workflows"
STATUS_FILE=$(find "$WORKFLOW_DIR" -name "status.md" 2>/dev/null | head -1)

if [ -n "$STATUS_FILE" ]; then
    cat "$STATUS_FILE" | head -30
fi
```

### PostToolUse（适配后）

```bash
WORKFLOW_DIR="$HOME/.hermes/workflows"
STATUS_FILE=$(find "$WORKFLOW_DIR" -name "status.md" 2>/dev/null | head -1)

if [ -n "$STATUS_FILE" ]; then
    WF_DIR=$(dirname "$STATUS_FILE")
    echo "[workflow-manager] Update $WF_DIR/progress.md with what you just did."
    echo "If you discovered new sub-steps or batches, update status.md to add them."
fi
```

---

## 待删除的代码脚本

| 文件 | 原因 |
|------|------|
| `actions/update_plan.py` | 多余，AI 直接编辑 status.md |
| `actions/update_parallel_progress.py` | 多余，AI 直接编辑 status.md |
| `references/progress-md-auto-generation.md` | 代码脚本文档，已废弃 |

## 待实施的钩子修改

| 钩子 | 当前 | 应改为 |
|------|------|--------|
| workflow-status-check | 显示简要状态 | 显示 status.md 前 50 行 + progress.md 后 20 行 |
| workflow-step-check | 注入约束清单 | 注入 status.md 前 30 行 |
| workflow-progress-update | 泛泛提醒 | 提醒更新 progress.md 和 status.md |
| workflow-session-cleanup | 检查状态 | 检查步骤完成 |

## 验证清单

- [ ] update_plan.py 已删除
- [ ] update_parallel_progress.py 已删除
- [ ] progress-md-auto-generation.md 已删除
- [ ] 4 个钩子逻辑已替换
- [ ] matcher 已扩展
- [ ] check-complete.sh 已创建
- [ ] SKILL.md 已更新
