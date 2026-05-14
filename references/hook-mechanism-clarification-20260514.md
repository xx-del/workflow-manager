# Hook 约束注入机制澄清

**日期**：2026-05-14
**用户纠正**：status.md 由 AI 创建，Hook 负责注入约束

---

## 用户纠正

**我之前的理解**：
- ❌ "Hook未触发，status.md需AI手动创建"
- ❌ 认为Hook应该自动创建status.md

**用户纠正**：
- ✅ "status.md就是需要ai手动创建的"
- ✅ "只需要注入禁止事项到status.md"

---

## 正确的机制

### status.md 创建流程

```
execute.py --init
    ↓ 清理旧 status.md
    ↓ 生成 status.json
    ↓ 创建会话标记

AI 执行
    ↓ 读取 WORKFLOW.md
    ↓ **AI 手动创建 status.md**
    ↓ AI 注入约束内容
    ↓ AI 分解任务
```

### Hook 的作用

**Hook 不负责创建 status.md**，而是：

1. **注入约束提醒**（pre_tool_call）
   - 检测到工作流会话标记
   - 注入 status.md 前 30 行作为提醒
   - 提醒 AI 遵守约束

2. **阻止违规操作**（pre_tool_call）
   - 检测删除工作流目录的命令
   - 返回 `{"action": "block"}` 阻止执行
   - 提示正确做法

3. **清理会话标记**（on_session_end）
   - 工作流完成时清理 .active_session
   - 防止 Hook 在非工作流会话触发

---

## 验证结果

**凭证检测工作流执行**：

1. ✅ execute.py --init 清理了旧 status.md
2. ✅ AI 手动创建了 status.md
3. ✅ AI 注入了约束内容（禁止修改命令、禁止 timeout）
4. ✅ status.md 包含完整的约束内容
5. ✅ Hook 未触发，但不影响执行

**结论**：
- Hook 未触发不是问题
- AI 手动创建 status.md 是正确流程
- 约束已成功注入到 status.md

---

## Hook 触发条件

**workflow-step-check Hook**：

```bash
# 触发条件
1. 存在 ~/.hermes/workflows/.active_session
2. 存在 status.json 且状态为 initialized
3. 不存在 status.md
4. AI 执行工具调用（terminal/delegate_task/write_file/patch）
```

**如果 Hook 触发**：
- 自动创建 status.md
- 注入完整约束（6 大类）
- 包括 agent-pool 使用指南

**如果 Hook 未触发**：
- AI 手动创建 status.md
- AI 注入约束内容
- 执行效果相同

---

## 约束注入内容

**status.md 应包含的约束**：

### 一、执行行为约束
- ❌ 禁止修改 WORKFLOW.md 定义的命令
- ❌ 禁止添加 timeout 参数
- ❌ 禁止跳过步骤
- ❌ 禁止使用替代方案

### 二、主 AI 职责边界约束
- ✅ 读取 WORKFLOW.md 理解定义
- ✅ 读取 status.md 获取约束
- ✅ 使用 agent-pool 执行步骤
- ✅ 更新 status.md 状态

### 三、Agent-Pool 使用约束
- ⚠️ 工作流步骤执行必须通过 agent-pool
- ⚠️ 禁止直接使用 terminal 执行工作流步骤

### 四、文件操作约束
- ❌ 禁止删除工作流目录
- ❌ 禁止删除 WORKFLOW.md
- ✅ 清理由 execute.py --init 自动完成

---

## 相关文档

- `references/hook-constraint-injection-mechanism-v6.6-20260514.md`：Hook 约束注入机制架构
- `references/hook-session-marker-mechanism-20260514.md`：会话标记机制
