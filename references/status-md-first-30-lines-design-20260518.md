# status.md 前 30 行设计问题分析

**发现日期**: 2026-05-18
**状态**: 待修复

---

## 问题

workflow-manager 的 status.md 前 30 行只包含约束（禁止行为），不包含执行指令。

**对比 planning-with-files**：

| 项目 | planning-with-files | workflow-manager（现状） |
|------|---------------------|--------------------------|
| 前 30 行内容 | Goal、Current Phase、Phases（执行指令） | 约束（禁止行为） |
| AI 看到后行为 | 知道要做什么、当前在哪里、下一步是什么 | 只知道不能做什么 |
| 执行指令位置 | 前 30 行 | 第 101 行之后 |

---

## planning-with-files 设计分析

### 生成机制

| 步骤 | 执行者 | 内容 |
|------|--------|------|
| 1. 创建模板 | init-session.sh | Goal、Current Phase、Phases 结构（前 30 行） |
| 2. 填充内容 | AI | 根据用户任务填充具体内容 |
| 3. 更新状态 | AI | 更新 Phase status（in_progress → completed） |

### 前 30 行模板

```markdown
# Task Plan: [Brief Description]

## Goal
[One sentence describing the end state]

## Current Phase
Phase 1

## Phases

### Phase 1: Requirements & Discovery
- [ ] Understand user intent
- [ ] Identify constraints
- **Status:** in_progress

### Phase 2: Planning & Structure
- [ ] Define approach
- **Status:** pending
```

**关键特征**：
- 模板设计**故意**让前 30 行包含执行指令
- AI 每次都能看到 Goal、Current Phase、Phases
- AI 知道要做什么、当前在哪里、下一步是什么

---

## workflow-manager 现状分析

### 生成机制（现状）

| 步骤 | 执行者 | 内容 | 位置 |
|------|--------|------|------|
| 1. 创建 status.md | PreToolUse Hook | 约束（禁止行为） | 前 30 行 |
| 2. 执行步骤 | execute.py | 读取 WORKFLOW.md 生成 | 第 101 行之后 |

**问题**：
- 前 30 行只包含约束，不包含执行指令
- 执行步骤在第 101 行之后，AI 看不到
- AI 只知道不能做什么，不知道要做什么

---

## 根本原因

1. execute.py 的 generate_status_md() 在 return 之后，不执行
2. PreToolUse Hook 添加了自动生成逻辑（第 123 行）
3. Hook 生成的 status.md 前 30 行是约束，不是执行指令
4. 违背了最初的设计原则（AI 动态生成）

---

## 解决方案

参考 planning-with-files，重新设计 status.md 结构：

| 区域 | 行数 | 内容 | 目的 |
|------|------|------|------|
| **头部** | 1-10 行 | 工作流名称、当前步骤、总步骤数 | 快速定位 |
| **当前执行指令** | 11-30 行 | 当前步骤的详细执行指令 | 告诉 AI 要做什么 |
| **执行步骤概览** | 31-50 行 | 所有步骤的概览和状态 | 了解全局进度 |
| **执行行为约束** | 51-100 行 | 禁止行为、必须遵守 | 约束 AI 行为 |
| **详细执行步骤** | 101+ 行 | 每个步骤的完整定义 | 完整参考 |

**关键点**：
- 前 30 行包含执行指令（Goal、Current Phase、Phases）
- 所有禁止事项保留（只是后移，不删除或简化）
- AI 生成并更新 status.md

---

## 完整禁止事项清单（25项）

### 一、执行行为约束（5项）

- ❌ 禁止修改 WORKFLOW.md 定义的命令
- ❌ 禁止添加 timeout 参数
- ❌ 禁止跳过步骤
- ❌ 禁止使用替代方案
- ❌ 禁止自行决定

### 二、主AI职责边界约束（3项）

- ❌ 禁止自己读取 _index.yaml
- ❌ 禁止自己判断步骤顺序
- ❌ 禁止自己检测依赖关系

### 二之一、文件操作约束（4项）

- ❌ 禁止删除工作流目录
- ❌ 禁止删除 WORKFLOW.md
- ❌ 禁止删除 _index.yaml
- ❌ 禁止删除任何已存在的文件

### 三、Agent-Pool 使用约束（2项）

- ⚠️ 工作流步骤执行必须通过 agent-pool
- ⚠️ 禁止直接使用 terminal 执行工作流步骤

### 四、异常处理约束（4项）

- ❌ 禁止自行诊断原因
- ❌ 禁止自行尝试修复
- ❌ 禁止跳过失败步骤
- ❌ 禁止静默降级

### 七、拼接工作流约束（4项）

- ⚠️ 必须展开所有子工作流
- ⚠️ 子工作流串行执行（禁止并行）
- ⚠️ 所有子工作流完成才算完成
- ⚠️ 禁止询问"是否继续执行下一个子工作流"

### 七、断点工作流约束（3项）

- ⚠️ 执行断点步骤后返回，等待心跳触发
- ⚠️ 禁止跳过断点检查
- ⚠️ 禁止手动继续后续步骤

---

## 参考

- `architecture-refactor-v6.4-hook-injection-20260513.md` - 最初设计（AI动态生成）
- `status-json-init-gap-20260518.md` - status.json 空模板问题
