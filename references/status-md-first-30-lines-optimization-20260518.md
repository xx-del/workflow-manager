# status.md 前 30 行优化记录

**日期**: 2026-05-18
**参考**: planning-with-files 设计

---

## 问题

原设计：status.md 前 30 行只包含约束（禁止行为），执行步骤在第 101 行之后。

**影响**：AI 看到约束后不知道要做什么，不会主动读取后面的内容。

---

## 解决方案

参考 planning-with-files 设计：

| 区域 | 内容 | 目的 |
|------|------|------|
| **前 30 行** | Goal、Current Phase、Phases | 告诉 AI 要做什么 |
| **第 31+ 行** | 所有禁止事项和约束 | 约束 AI 行为 |

---

## 新的 status.md 结构

```markdown
# 工作流名称 - 执行计划

**当前步骤**: 步骤 1
**总步骤数**: 12
**执行模式**: serial

---

## Goal

(AI 根据 WORKFLOW.md 填充)

---

## Current Phase

步骤 1: (AI 根据 WORKFLOW.md 填充)

---

## Phases

### 步骤 1: xxx
- **状态**: ⏳ 待执行

---

## 一、执行行为约束

(所有禁止事项，完整保留)
...
```

---

## 修改文件

| 文件 | 修改内容 |
|------|----------|
| execute.py | generate_status_md 函数（前 30 行包含执行指令） |
| execute.py | init_workflow 函数（在返回前生成 status.md） |
| workflow-step-check/handler.sh | 禁用自动创建，保留约束检查 |
| workflow-progress/handler.sh | 提醒更新 status.md |
| SKILL.md | 更新 status.md 定位说明 |

---

## 关键原则

1. **所有禁止事项必须保留**（只是后移，不删除或简化）
2. **AI 生成 status.md**（符合最初设计，不是 Hook 自动生成）
3. **前 30 行包含执行指令**（参考 planning-with-files）
4. **同步更新 SKILL.md**（技能文档一致性）

---

## 验证标准

- ✅ status.md 前 30 行包含 Goal、Current Phase、Phases
- ✅ 所有禁止事项完整保留（21 个"禁止"关键词）
- ✅ 所有约束章节都在（9 个约束章节）
- ✅ AI 能看到执行指令并主动读取完整文件
