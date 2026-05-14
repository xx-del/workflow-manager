# Hook 约束注入机制 v6.6

**版本**: v6.6
**创建时间**: 2026-05-14
**设计目标**: 两层约束注入 + 防止主 AI 误删文件

---

## 核心设计

### 两层注入机制

**第一层：创建 status.md（持久化）**
- Hook 检测 status.md 不存在时自动创建
- 注入完整约束（6 大类）
- 包括 agent-pool 使用指南

**第二层：注入前 30 行（临时提醒）**
- 借鉴 planning-with-files 机制
- 每次工具调用前提醒当前进度

---

## 约束内容（6 大类）

### 一、执行行为约束

```markdown
**绝对禁止**:
- ❌ 禁止修改 WORKFLOW.md 定义的命令
- ❌ 禁止添加 timeout 参数
- ❌ 禁止跳过步骤
- ❌ 禁止使用替代方案
- ❌ 禁止自行决定

**必须遵守**:
- ✅ 严格按指令执行
- ✅ 验证每个输出
- ✅ 每步执行后更新状态
```

### 二、主 AI 职责边界约束

```markdown
**禁止行为**:
- ❌ 禁止自己读取 _index.yaml（代码已实现）
- ❌ 禁止自己判断步骤顺序（代码已实现）
- ❌ 禁止自己检测依赖关系（代码已实现）

**允许行为**:
- ✅ 读取 WORKFLOW.md 理解定义
- ✅ 读取 status.md 获取约束
- ✅ 使用 agent-pool 执行步骤
- ✅ 更新 status.md 状态
```

### 三、Agent-Pool 使用约束

```markdown
**必须使用 agent-pool**:
- ⚠️ 工作流步骤执行必须通过 agent-pool
- ⚠️ 禁止直接使用 terminal 执行工作流步骤

**如何使用 agent-pool**:

步骤 1：调用 agent_pool_client.execute()
步骤 2：获取 pending_instructions
步骤 3：使用 delegate_task 执行指令
步骤 4：更新 status.json
```

### 四、异常处理约束

```markdown
**处理流程**:
- 立即停止工作流（不诊断、不修复、不跳过）
- 记录异常到 status.md 错误日志
- 上报用户，等待指示
```

### 五、进度记录约束

```markdown
**必须记录**:
- 每步执行前：更新 status.json（status: running）
- 每步执行后：更新 status.json（status: completed）
```

### 六、完成判定约束

```markdown
**完成标准**:
- 所有步骤 status = completed
- 所有预期输出文件存在
- 无未处理的错误
```

---

## 文件操作约束（新增）

### 绝对禁止删除

- ❌ 禁止删除工作流目录
- ❌ 禁止删除 WORKFLOW.md
- ❌ 禁止删除 _index.yaml
- ❌ 禁止删除任何已存在的文件

### 只允许清理状态文件

- ✅ 清理由 execute.py --init 自动完成
- ✅ 主 AI 不要手动删除任何文件

### 清理状态的正确方法

```bash
# 不要手动删除，使用命令：
python actions/execute.py <工作流名称> --init  # 清理并初始化
python actions/complete.py <工作流名称>        # 完成并清理标记
```

---

## 硬约束 Block 机制

### Hook 拦截删除命令

```bash
if echo "$TOOL_INPUT" | grep -qE "(rm -rf|rm -r|rmdir).*workflows"; then
    # 返回 block
fi
```

### Block 返回格式

```json
{
    "action": "block",
    "message": "⛔ 禁止删除工作流目录。\n\n清理状态请使用：\npython actions/execute.py <工作流名称> --init"
}
```

---

## 完整流程

```
1. execute.py --init
   → 生成 status.json（status: initialized）
   → 创建会话标记

2. Hook（pre_llm_call）
   → 提醒 AI 读取 WORKFLOW.md

3. 主 AI 读取 WORKFLOW.md

4. Hook（pre_tool_call）
   → status.md 不存在 → 创建并注入完整约束
   → status.md 存在 → 注入前 30 行

5. 主 AI 根据 status.md 执行
   → 使用 agent-pool
   → 更新 status.md

6. Hook（post_tool_call）
   → 提醒更新 status.md
```

---

## 设计原则

1. **约束整合在 status.md 中**：AI 唯一约束来源
2. **Hook 只注入，不生成约束**：约束由模板定义
3. **防止误删**：block 机制 + 明确约束
4. **两层注入**：持久化 + 临时提醒

---

## 相关文件

- `hooks/workflow-step-check/handler.sh`：约束注入实现
- `references/status-md-constraint-injection-enhancement.md`：约束分类详细说明
