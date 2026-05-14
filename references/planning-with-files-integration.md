# planning-with-files 融合文档

**版本**: v6.2.0  
**更新时间**: 2026-05-12  
**来源**: 融合 planning-with-files v2.27.0 核心机制

---

## 融合概述

workflow-manager v6.2.0 融合了 planning-with-files 技能的核心机制，实现了：

1. **强制 plan 文件生成**：status.md 不存在时阻断执行
2. **持续约束注入**：每次工具调用前注入约束
3. **三文件结构**：status.md + progress.md + findings.md
4. **动态更新支持**：并行任务实时进度追踪

---

## 核心机制对比

### planning-with-files 核心机制

| 机制 | 实现方式 | 强制性 |
|------|---------|--------|
| Create Plan First | init-session.sh 自动创建 | ✅ Non-negotiable |
| Read Before Decide | PreToolUse 注入前 30 行 | ✅ 每次工具调用前 |
| Update After Act | PostToolUse 提醒更新 | ⚠️ 提醒，非强制 |
| 2-Action Rule | 文档规范，无代码强制 | ❌ 依赖 AI 自觉 |

### workflow-manager 融合机制

| 机制 | 实现方式 | 强制性 |
|------|---------|--------|
| 强制生成 | PreToolUse exit 1 阻断 | ✅ **强制阻断** |
| 持续注入 | PreToolUse 注入前 30 行 | ✅ 每次工具调用前 |
| 动态更新 | update_plan.py + PostToolUse 提醒 | ⚠️ 提醒 + 脚本支持 |
| 并行追踪 | update_parallel_progress.py | ✅ 实时更新 |

**关键改进**：
- planning-with-files 是"提醒"，workflow-manager 是"阻断"
- planning-with-files 依赖 AI 自觉，workflow-manager 强制执行

---

## 钩子机制对比

### planning-with-files 钩子

```yaml
hooks:
  UserPromptSubmit:
    - type: command
      command: | 
        # 检测未完成任务，显示 task_plan.md
      
  PreToolUse:
    - matcher: "Write|Edit|Bash|Read|Glob|Grep"
      type: command
      command: |
        # 注入 task_plan.md 前 30 行
      
  PostToolUse:
    - matcher: "Write|Edit"
      type: command
      command: |
        # 提醒更新 progress.md
      
  Stop:
    - type: command
      command: |
        # 检查是否所有阶段完成
```

### workflow-manager 钩子

```yaml
hooks:
  UserPromptSubmit:
    - type: command
      command: bash $SKILL_DIR/hooks/user_prompt_submit.sh
      
  PreToolUse:
    - matcher: "terminal|delegate_task|write_file|patch|browser_navigate|browser_click"
      type: command
      command: bash $SKILL_DIR/hooks/pre_tool_use.sh  # ⭐ exit 1 阻断
      
  PostToolUse:
    - matcher: "terminal|delegate_task|write_file|patch"
      type: command
      command: bash $SKILL_DIR/hooks/post_tool_use.sh
      
  Stop:
    - type: command
      command: bash $SKILL_DIR/hooks/stop.sh
```

**关键差异**：

| 差异点 | planning-with-files | workflow-manager |
|--------|---------------------|------------------|
| PreToolUse 行为 | 注入提醒 | **exit 1 阻断** |
| matcher 覆盖 | 6 个工具 | 6 个工具 |
| PostToolUse 提醒 | 更新 progress.md | 更新 progress.md + status.md |
| Stop 检查 | 所有阶段完成 | 工作流步骤完成 |

---

## 文件结构对比

### planning-with-files 文件结构

```
~/.hermes/plans/{date}-{task}/
├── task_plan.md    # 执行计划（AI 可读）
├── findings.md     # 研究发现
└── progress.md     # 执行日志
```

### workflow-manager 文件结构

```
~/.hermes/workflows/{workflow_name}/
├── WORKFLOW.md     # 工作流定义（模板）
├── status.md       # 执行计划（AI 可读）⭐ 类似 task_plan.md
├── status.json     # 运行状态（机器可读）
├── progress.md     # 执行日志 ⭐ 新增
└── findings.md     # 研究发现 ⭐ 新增
```

**职责对应**：

| planning-with-files | workflow-manager | 职责 |
|---------------------|------------------|------|
| task_plan.md | status.md | 执行计划 |
| progress.md | progress.md | 执行日志 |
| findings.md | findings.md | 研究发现 |

---

## 强制机制详解

### planning-with-files 的"Non-negotiable"

**文档约束**：
```markdown
## Critical Rules

### 1. Create Plan First
Never start a complex task without `task_plan.md`. Non-negotiable.
```

**实际执行**：
- init-session.sh 自动创建
- 但 AI 可以绕过（不运行 init-session.sh）

### workflow-manager 的"exit 1 阻断"

**代码强制**：
```bash
# hooks/pre_tool_use.sh

if [ ! -f "$WORKFLOW_DIR/status.md" ]; then
  echo "❌ 错误：必须先生成执行计划"
  exit 1  # ⭐ 阻断工具调用
fi
```

**效果**：
- AI 无法绕过（钩子在每次工具调用前触发）
- status.md 不存在时，所有工具调用失败
- 必须先运行 execute.py --plan-only

---

## 动态更新机制

### planning-with-files 动态更新

**PostToolUse 提醒**：
```bash
echo "[planning-with-files] Update progress.md with what you just did."
```

**依赖**：AI 自觉更新

### workflow-manager 动态更新

**PostToolUse 提醒**：
```bash
echo "[workflow-manager] 请更新 progress.md"
echo "更新命令："
echo "  python actions/update_plan.py <workflow> --step <step> --status completed"
```

**脚本支持**：
```bash
# 自动更新步骤状态
python actions/update_plan.py asset-collection --step port-scan --status completed

# 标记工作流完成
python actions/update_plan.py asset-collection --completed

# 添加研究发现
python actions/update_plan.py asset-collection --add-finding "发现开放端口 8080"
```

---

## 并行任务支持

### planning-with-files

无专门的并行任务支持机制。

### workflow-manager

**并行任务追踪模板**：
```markdown
## 并行任务追踪

**总任务数**: 100
**批次大小**: 10
**总批次数**: 10

### 批次 1 (任务 1-10)
- **状态**: ⏳ 执行中
- **Agent**: agent-pool-worker-1
- **进度**: 5/10 完成

...

## 实时进度统计

- ✅ 已完成：XX 个
- ⏳ 执行中：XX 个
- ⏸️ 等待中：XX 个
- ❌ 失败：XX 个
```

**动态更新脚本**：
```bash
# 初始化并行任务追踪
python update_parallel_progress.py asset-collection --init --total-tasks 100 --batch-size 10

# 更新批次进度
python update_parallel_progress.py asset-collection --batch 1 --completed 5 --total 10

# 查看进度摘要
python update_parallel_progress.py asset-collection --summary
```

---

## 使用流程对比

### planning-with-files 使用流程

```
1. AI 创建 task_plan.md
   ├─ 手动创建，或
   └─ 运行 init-session.sh
   
2. 执行任务
   ├─ PreToolUse 注入 task_plan.md 前 30 行
   └─ PostToolUse 提醒更新 progress.md
   
3. AI 自觉更新 progress.md 和 findings.md

4. Stop 钩子检查是否所有阶段完成
```

### workflow-manager 使用流程

```
1. AI 执行工作流
   └─ 调用 execute.py --plan-only（强制生成 status.md）
   
2. PreToolUse 钩子
   ├─ 检查 status.md 是否存在
   ├─ 不存在 → exit 1 阻断执行
   └─ 存在 → 注入前 30 行
   
3. 执行步骤
   ├─ PreToolUse 注入约束
   └─ PostToolUse 提醒更新 progress.md
   
4. AI 或脚本更新进度
   ├─ 手动更新：python update_plan.py ...
   └─ 并行任务：python update_parallel_progress.py ...
   
5. Stop 钩子检查工作流完成状态
```

---

## 核心改进总结

| 改进项 | planning-with-files | workflow-manager v6.2 |
|--------|---------------------|----------------------|
| plan 文件强制 | ⚠️ 文档约束（AI 可绕过） | ✅ exit 1 阻断（不可绕过） |
| 钩子覆盖范围 | 6 个工具 | 6 个工具 |
| 文件结构 | 3 个文件 | 3 个文件（新增 2 个） |
| 动态更新 | ⚠️ 提醒，无脚本支持 | ✅ 提醒 + 完整脚本支持 |
| 并行任务 | ❌ 无支持 | ✅ 实时进度追踪 |

---

## 最佳实践

### 创建工作流时

1. **必须先生成 status.md**
   ```bash
   python actions/execute.py <workflow_name> --plan-only
   ```

2. **初始化三文件结构**
   ```bash
   # execute.py --plan-only 会自动生成
   # - status.md（执行计划）
   # - progress.md（执行日志）
   # - findings.md（研究发现）
   ```

### 执行工作流时

1. **钩子自动注入约束**
   - PreToolUse 自动检查 status.md 存在性
   - PreToolUse 自动注入前 30 行约束

2. **PostToolUse 提醒更新**
   - 每次工具调用后提醒更新 progress.md

### 并行任务时

1. **初始化并行追踪**
   ```bash
   python actions/update_parallel_progress.py <workflow> --init --total-tasks 100 --batch-size 10
   ```

2. **实时更新进度**
   ```bash
   python actions/update_parallel_progress.py <workflow> --batch 1 --completed 5 --total 10
   ```

3. **查看进度摘要**
   ```bash
   python actions/update_parallel_progress.py <workflow> --summary
   ```

---

## 故障排查

### 钩子不触发

**检查清单**：
- [ ] hooks/*.sh 是否有执行权限（chmod +x）
- [ ] SKILL.md frontmatter 中 hooks 配置是否正确
- [ ] $SKILL_DIR 环境变量是否注入

### status.md 不存在被阻断

**解决方法**：
```bash
# 强制生成 status.md
python actions/execute.py <workflow_name> --plan-only
```

### 并行任务进度不更新

**检查清单**：
- [ ] 是否已初始化并行追踪（--init）
- [ ] status.md 中是否有"并行任务追踪"章节
- [ ] update_parallel_progress.py 脚本路径是否正确

---

## 参考资料

- planning-with-files SKILL.md v2.27.0
- workflow-manager SKILL.md v6.2.0
- ByteRover 工作流执行案例
- workflow-manager/references/hooks-architecture.md
