# 钩子机制实现文档

**版本**: v5.3.0
**更新时间**: 2026-05-11
**来源**: 融合 planning-with-files 技能机制

---

## 概述

为 workflow-manager 添加钩子机制，实现注意力操控，防止 AI 执行工作流时偏离目标。

**核心变化**：
- `status.md`：执行计划（AI可读），执行前生成一次
- `status.json`：运行时状态（机器可读），持续更新
- 钩子注入：每次工具调用前注入约束清单

---

## 文件职责

| 文件 | 作用 | 生成时机 | 更新频率 |
|------|------|----------|----------|
| `WORKFLOW.md` | 步骤模板 | 创建工作流时 | 不变 |
| `status.md` | 执行计划（AI可读） | 每次执行前 | 静态 |
| `status.json` | 运行状态（机器可读） | 执行开始时 | 每步骤更新 |

---

## 钩子配置

### UserPromptSubmit 钩子

**触发时机**：会话开始时

**作用**：检测未完成工作流，提示继续执行

**实现**：
```bash
STATUS_FILE=$(find ~/.hermes/workflows -name "status.json" -exec grep -l '"status": "running"' {} \; 2>/dev/null | grep -v ".backup" | head -1)
if [ -n "$STATUS_FILE" ]; then
  WORKFLOW_DIR=$(dirname "$STATUS_FILE")
  WORKFLOW_NAME=$(basename "$WORKFLOW_DIR")
  echo "🔔 检测到未完成工作流: $WORKFLOW_NAME"
  if [ -f "$WORKFLOW_DIR/status.md" ]; then
    head -60 "$WORKFLOW_DIR/status.md"
  fi
fi
```

### PreToolUse 钩子

**触发时机**：每次 terminal/delegate_task 调用前

**作用**：注入当前步骤和约束清单

**实现**：
```bash
STATUS_FILE=$(find ~/.hermes/workflows -name "status.json" -exec grep -l '"status": "running"' {} \; 2>/dev/null | grep -v ".backup" | head -1)
if [ -n "$STATUS_FILE" ]; then
  WORKFLOW_DIR=$(dirname "$STATUS_FILE")
  CURRENT_STEP=$(python3 -c "
import json
with open('$STATUS_FILE') as f:
    d = json.load(f)
print(d['workflow']['current_step'])
" 2>/dev/null)
  echo "⚠️  当前步骤: $CURRENT_STEP"
  sed -n '/## 约束清单/,/^## /p' "$WORKFLOW_DIR/status.md" | head -15
fi
```

### PostToolUse 钩子

**触发时机**：每次 terminal/delegate_task 调用后

**作用**：提示状态已更新

---

## status.md 格式

```markdown
# 工作流执行计划：{workflow_name}

**生成时间**: {timestamp}
**执行模式**: 串行严格模式
**总步骤**: {total_steps}

---

## 目标
{从 WORKFLOW.md 读取的目标}

---

## 执行步骤

### 步骤 1: {step_name}
- **做什么**: {description}
- **执行指令**: 
  ```bash
  {command}
  ```
- **输入**: {input}
- **输出**: {output}
- **状态**: ⏳ 待执行

...

---

## 约束清单 ⚠️（必须严格遵守）

- [ ] 严格按步骤顺序执行
- [ ] 禁止修改上述命令
- [ ] 禁止添加 WORKFLOW.md 没有的步骤
- [ ] 禁止添加 timeout 参数
- [ ] 每步执行后验证输出
- [ ] 遇到问题立即停止，不推断原因

---

## 错误日志（执行时填写）

| 错误 | 步骤 | 尝试 | 解决方案 |
|------|------|------|----------|
| (执行时填写) | | | |

---

## 执行记录

- {timestamp}: 工作流启动，执行计划已生成
```

---

## executor.py 新增方法

### generate_execution_plan_md()

**位置**：WorkflowExecutor 类

**调用时机**：execute() 方法开头，加载工作流后

**作用**：生成 status.md（执行计划）

**返回**：status.md 文件路径

### get_execution_plans()

**位置**：WorkflowExecutor 类

**调用时机**：execute.py --plan-only 模式

**作用**：返回执行计划（不执行）

**返回**：
```python
{
    'workflow': workflow_name,
    'total_steps': len(expanded_nodes),
    'mode': workflow.get('mode', 'serial'),
    'pending_instructions': pending_instructions,
    'status_md_path': status_md_path
}
```

---

## 测试验证

**测试工作流**：电力数据
**日期范围**：20260508 - 20260511

**验证结果**：
- ✅ status.md 自动生成
- ✅ PreToolUse 钩子注入约束
- ✅ UserPromptSubmit 钩子检测未完成任务
- ✅ --plan-only 模式正常工作

---

## 注意事项

1. **AI 驱动工作流**：节点没有 command 字段时，status.md 显示"（无命令）"，这是设计如此，AI 会读取 WORKFLOW.md 执行步骤

2. **多工作流检测**：钩子使用 `head -1` 只处理第一个运行中的工作流

3. **备份文件**：修改前自动创建备份（SKILL.md.bak_*, executor.py.bak_*）

---

## 自动生成机制

**问题**：钩子依赖 status.md 存在，但 AI 可能直接执行工作流而不生成

**解决**：钩子检测到 status.md 不存在时，自动调用 `execute.py --plan-only` 生成

**实现位置**：
- UserPromptSubmit 钩子
- PreToolUse 钩子

**触发条件**：
```bash
if [ ! -f "$WORKFLOW_DIR/status.md" ]; then
  python3 .../execute.py "$WORKFLOW_NAME" --plan-only
fi
```

**效果**：
- AI 直接执行工作流 → 钩子自动生成 status.md → 注入约束
- 双重保障：规范层（SKILL.md 规则）+ 代码层（钩子自动生成）

**验证结果**（2026-05-11）：
- ✅ UserPromptSubmit 钩子自动生成 status.md
- ✅ PreToolUse 钩子自动生成 status.md
- ✅ SKILL.md 新增"执行前必须生成 status.md"章节
- ✅ 双重保障机制完整

---

## 相关技能

- planning-with-files：借鉴了其钩子机制和 task_plan.md 格式
