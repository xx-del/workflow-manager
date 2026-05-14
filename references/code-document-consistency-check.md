# 代码与文档一致性检查方法

## 检查目的

确保 workflow-manager 技能文档（SKILL.md）准确描述代码实际行为。

---

## 检查流程

### 步骤 1：分析代码返回值

检查 `src/core/executor.py` 和 `src/core/agent_pool_client.py` 的返回结构。

**关键位置**：
- `executor.py` 第 213-257 行：`execute()` 方法的最终返回值
- `agent_pool_client.py` 第 161-173 行：`execute_full()` 方法的返回值

### 步骤 2：对比文档示例

检查 SKILL.md 中的返回值示例是否与代码一致。

**常见问题**：
- 字段名不一致（如 `instructions` vs `pending_instructions`）
- 字段类型不一致
- 字段缺失或多余

### 步骤 3：验证字段名转换

**代码实际流程**：

```python
# agent_pool_client.py 返回
{
    "instructions": [...]  # 原始字段名
}

# executor.py 读取并重命名（第 397 行）
all_instructions = result.get('pending_instructions', result.get('instructions', []))

# executor.py 最终返回（第 218 行）
{
    'pending_instructions': all_instructions  # 重命名后的字段
}
```

**主 AI 应该读取**：`pending_instructions` 字段

---

## 一致性检查清单

- [ ] executor.py 返回值示例与文档一致
- [ ] 字段名使用 `pending_instructions`（不是 `instructions`）
- [ ] 主 AI 职责描述与代码行为一致
- [ ] 验证清单项与代码流程一致

---

## 历史修复记录

### 2026-05-09

**问题**：SKILL.md 中 4 处使用了错误的字段名 `instructions`

**修复**：统一改为 `pending_instructions`

**位置**：
- 第 305 行：`包含 instructions` → `包含 pending_instructions`
- 第 306 行：`instructions 中的 delegate_task` → `pending_instructions 中的 delegate_task`
- 第 333 行：`根据 instructions 调用` → `根据 pending_instructions 调用`
- 第 335 行：`"instructions": [` → `"pending_instructions": [`

**根因**：文档编写时参考了 agent_pool_client.py 的返回结构，未考虑 executor.py 的字段重命名。
