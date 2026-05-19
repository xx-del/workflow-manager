# 计划任务动态更新机制

**日期**: 2026-05-15
**触发场景**: 分析工作流并行执行时计划任务是否动态更新

---

## 一、核心结论

**计划任务会动态更新，但由主 AI 手动执行，不是自动机制。**

---

## 二、更新机制

### 更新时机

| 时机 | 执行者 | 文件 |
|------|--------|------|
| 初始化 | planning-with-files | task_plan.md |
| 阶段完成 | 主 AI | status.md, task_plan.md |
| 批次完成 | 主 AI | status.md |
| 最终完成 | 主 AI | status.md |

### 不更新的情况

| 情况 | 原因 |
|------|------|
| 子 agent 执行 | 无权限、无路径、无指令 |
| 并行执行中 | 子 agent 只执行任务，不更新状态 |
| 自动更新 | 不存在此机制 |

---

## 三、执行流程

```
分割文件（主 AI）
    ↓
生成批次文件（batch_1.json ~ batch_N.json）
    ↓
主 AI 更新 task_plan.md（记录分割完成）
    ↓
并行执行批次（delegate_task × 3）
    ↓
每个批次完成后 → 主 AI 更新 status.md
    ↓
合并结果 → 主 AI 更新最终状态
```

---

## 四、验证方法

### 检查 status.md

```bash
cat ~/.hermes/workflows/<工作流>/status.md | grep -A5 "步骤状态"
```

### 检查 task_plan.md

```bash
cat ~/.hermes/workflows/<工作流>/task_plan.md | grep -E "complete|pending"
```

### 检查执行记录

```bash
lcm_grep(query="更新 status.md", session_scope="all")
```

---

## 五、案例

**URL分析工作流（2026-05-12）**：

| 阶段 | 操作 | 状态更新 |
|------|------|----------|
| Phase 1-3 | 串行执行 | ✅ 每阶段完成后更新 |
| Phase 4 | 分割 383 URL → 13 批次 | ✅ 主 AI 更新 task_plan.md |
| 批次 1-3 | delegate_task 并行 | ✅ 完成后主 AI 更新 |
| 批次 4-13 | delegate_task 并行 | ✅ 完成后主 AI 更新 |
| 合并结果 | 主 AI 执行 | ✅ 更新最终状态 |

---

## 六、关键发现

1. **子 agent 不更新状态** - 只有主 AI 有权限和指令
2. **planning-with-files 生成初始计划** - 不是自动更新
3. **主 AI 负责所有状态更新** - 执行过程中手动更新
4. **execute.py --init 会重置状态** - 历史执行记录可能被清理

---

## 七、架构说明

| 组件 | 职责 |
|------|------|
| planning-with-files | 生成初始计划（task_plan.md） |
| 主 AI | 执行计划 + 更新状态 |
| 子 agent | 只执行任务，不更新状态 |
| Hook | 注入约束，不更新状态 |
