# planning-with-files + agent-pool 接管架构

## 设计理念

**借鉴 L4 任务流程**：
- L4 = 用户确认执行（批准计划）→ AI 实际执行
- 角色：甲（AI planner）→ 乙（user approver）→ 甲（AI executor）

**映射到工作流**：
```
execute.py --plan-only → 甲制定计划
用户同意 → 乙批准计划
planning-with-files + agent-pool → 甲执行计划
```

## 职责分工

| 组件 | 职责 |
|------|------|
| workflow-manager | 生成执行计划（pending_instructions） |
| planning-with-files | 动态追踪、钩子注入、错误积累 |
| agent-pool | 能力匹配、执行、Handoff 注入 |
| 主AI | 协调、监控、异常处理 |

## 接管方式

**SKILL.md 描述 + 技能调用**：

```markdown
## 执行工作流（planning-with-files + agent-pool 接管）

**阶段 1**：planning-with-files 初始化
- 创建 task_plan.md（从 pending_instructions 生成）
- 创建 progress.md（空）
- 创建 findings.md（空）

**阶段 2**：agent-pool 执行
- 能力匹配
- Handoff 注入
- 执行任务

**阶段 3**：planning-with-files 更新
- 更新 progress.md
- 更新 task_plan.md 状态
- 追加 findings.md

**阶段 4**：完成
- 标记所有阶段 complete
- 生成最终报告
```

## 核心收益

| 功能 | 现有架构 | planning-with-files 接管 |
|------|----------|-------------------------|
| 计划文件 | status.md（静态） | task_plan.md（动态） |
| 进度追踪 | 主AI 自己管理 | progress.md 自动记录 |
| 结果收集 | 分散在各处 | findings.md 统一收集 |
| 错误追踪 | 无 | 有（3次失败机制） |
| 会话恢复 | 依赖 status.json | 支持 /clear 恢复 |
| 注意力操控 | 钩子显示当前步骤 | PreToolUse 每次读取计划 |

## 前置条件

- [ ] status.md 是否存在？
- [ ] pending_instructions 是否获得？
- [ ] planning-with-files 是否可用？
- [ ] agent-pool 是否可用？

## 实施状态

- ✅ planning-with-files 初始化可用
- ✅ 从 pending_instructions 生成 task_plan.md 可用
- ⚠️ agent-pool 能力匹配需修复导入
- ✅ planning-with-files 钩子机制可用
- ✅ 动态更新 task_plan.md 可用
