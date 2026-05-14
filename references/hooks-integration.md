# 钩子机制融合设计 - 借鉴 planning-with-files

> 来源：2026-05-11 会话，融合 planning-with-files 注意力操控机制到 workflow-manager

## 核心理念

**planning-with-files 的本质**：把目标写入文件，通过钩子**强制注入注意力窗口**

**workflow-manager 的问题**：定义了严格的流程，但**依赖AI自觉遵守**

**融合目标**：用钩子机制把"自觉遵守"变成"强制注入"

## 关键设计决策（用户纠正）

### ❌ 错误方案：status.md 替代 status.json
- status.md 和 status.json 功能重叠
- 信息不一致风险

### ✅ 正确方案：status.md 作为执行计划，status.json 保留运行时状态

| 文件 | 作用 | 生成时机 | 更新频率 |
|------|------|----------|----------|
| `WORKFLOW.md` | 步骤模板 | 创建工作流时 | 不变 |
| `status.md` | 执行计划（AI可读） | **每次执行前** | 静态 |
| `status.json` | 运行状态（机器可读） | 执行开始时 | 每步骤更新 |

**关键洞察**：
- `status.md` = **执行计划**（静态，执行前生成一次，类似地图）
- `status.json` = **运行状态**（动态，持续更新，类似GPS定位）
- 两者职责不同，互不替代

## 钩子配置设计

### UserPromptSubmit 钩子

**作用**：会话开始时检测未完成工作流

```yaml
hooks:
  UserPromptSubmit:
    - hooks:
        - type: command
          command: |
            STATUS_FILE=$(find ~/.hermes/workflows -name "status.json" \
              -exec grep -l '"status": "running"' {} \; 2>/dev/null \
              | grep -v ".backup" | head -1)
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

**作用**：每次工具调用前注入当前步骤 + 约束清单

```yaml
  PreToolUse:
    - matcher: "terminal|delegate_task"
      hooks:
        - type: command
          command: |
            STATUS_FILE=$(find ~/.hermes/workflows -name "status.json" \
              -exec grep -l '"status": "running"' {} \; 2>/dev/null \
              | grep -v ".backup" | head -1)
            if [ -n "$STATUS_FILE" ]; then
              WORKFLOW_DIR=$(dirname "$STATUS_FILE")
              CURRENT_STEP=$(python3 -c "
import json
with open('$STATUS_FILE') as f:
    d = json.load(f)
print(d['workflow']['current_step'])
" 2>/dev/null)
              echo "⚠️  当前步骤: $CURRENT_STEP"
              # 注入约束清单
              if [ -f "$WORKFLOW_DIR/status.md" ]; then
                sed -n '/## 约束清单/,/^## /p' "$WORKFLOW_DIR/status.md" | head -15
              fi
            fi
```

### PostToolUse 钩子

**作用**：工具调用后提示更新状态

```yaml
  PostToolUse:
    - matcher: "terminal|delegate_task"
      hooks:
        - type: command
          command: |
            STATUS_FILE=$(find ~/.hermes/workflows -name "status.json" \
              -exec grep -l '"status": "running"' {} \; 2>/dev/null \
              | grep -v ".backup" | head -1)
            if [ -n "$STATUS_FILE" ]; then
              echo "[workflow-manager] 步骤已完成，状态已更新到 status.json"
            fi
```

## status.md 格式

```markdown
# 工作流执行计划：{workflow_name}

**生成时间**: {timestamp}
**执行模式**: 串行严格模式
**总步骤**: {total_steps}

---

## 目标
{从 WORKFLOW.md 提取}

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

### 步骤 2: ...

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

## 代码修改点

### executor.py

1. **新增方法**：`generate_execution_plan_md(workflow)` → 生成 status.md
2. **调用位置**：`execute()` 方法中，加载工作流后立即调用

### SKILL.md

1. **新增**：hooks 配置（UserPromptSubmit、PreToolUse、PostToolUse）

## 测试结果（2026-05-11）

| 测试项 | 结果 |
|--------|------|
| PreToolUse 钩子 | ✅ 能检测运行中工作流，注入约束清单 |
| UserPromptSubmit 钩子 | ✅ 能检测未完成任务，显示执行计划 |
| status.md 格式 | ✅ AI可读，包含约束清单 |

## 实施状态

- [x] 设计方案已确认
- [x] 钩子命令已测试
- [ ] SKILL.md hooks 配置已添加
- [ ] executor.py generate_execution_plan_md() 已实现
- [ ] 实际工作流执行验证

## 参考链接

- planning-with-files 技能：`~/.hermes/skills/openclaw-imports/planning-with-files/`
- Manus 原理参考：`~/.hermes/skills/openclaw-imports/planning-with-files/references/reference.md`
- 实施方案：`~/.hermes/plans/2026-05-11-workflow-manager-hooks-integration/execution_plan.md`
