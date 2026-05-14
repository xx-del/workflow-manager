# 文档一致性修复记录

**日期**：2026-05-09
**版本**：v4.5.0 → v4.6.0

---

## 发现的问题

### 1. 字段名不一致

**代码实际行为**：
- `agent_pool_client.py` 返回 `"instructions"` 字段
- `executor.py` 将其重命名为 `"pending_instructions"` 字段
- 主 AI 收到的最终结构使用 `"pending_instructions"`

**文档错误**：
- SKILL.md 中 6 处使用了错误的字段名 `instructions`
- 应该使用 `pending_instructions`

**影响**：
- 主 AI 可能误读字段名
- 尝试读取不存在的 `result['instructions']`
- 应该读取 `result['pending_instructions']`

### 2. 验证清单错误项

**错误内容**：
```markdown
- [x] 已通过 agent-pool 技能匹配 agent
- [x] 已调用 delegate_task 执行每个步骤
```

**错误原因**：
- 主 AI 不需要手动调用 agent-pool
- workflow-manager 的 executor.py 已经内置了 agent_pool_client 调用
- 主 AI 只需执行返回的 pending_instructions

### 3. 重复章节

**重复内容**：
- "严重警告 ⚠️" 章节
- "主 AI 配合清单" 章节
- "严格模式约束 ⚠️" 章节

这些章节与"核心强制约束"章节内容重复。

---

## 修复措施

### 修复 1：统一字段名

修正了 6 处字段名错误：

| 位置 | 修正前 | 修正后 |
|------|--------|--------|
| 第 286 行 | `根据 instructions` | `根据 pending_instructions` |
| 第 291 行 | `包含 instructions` | `包含 pending_instructions` |
| 第 292 行 | `根据 instructions` | `根据 pending_instructions` |
| 第 299 行 | `含 instructions` | `含 pending_instructions` |
| 第 351 行 | `执行 instructions` | `执行 pending_instructions` |
| 第 356 行 | `返回的 instructions` | `返回的 pending_instructions` |

### 修复 2：删除错误验证项示例

删除了第 311-315 行的错误示例：
```markdown
**❌ 错误的验证项**（这些是 workflow-manager 内部操作，不是主 AI 的职责）：
- ~~已通过 agent-pool 技能匹配 agent~~（executor.py 内部完成）
- ~~已调用 delegate_task 执行每个步骤~~（主 AI 根据返回的 instructions 执行，不是自己决定）
- ~~已分析步骤依赖关系~~（executor.py 内部完成）
```

### 修复 3：删除重复章节

删除了以下重复章节：
- "严重警告 ⚠️" 章节（57 行）
- "主 AI 配合清单" 章节（32 行）
- "严格模式约束 ⚠️" 章节（91 行）

---

## 验证结果

### 字段名一致性

```bash
# 检查错误字段名
grep -n '"instructions"' SKILL.md
# 结果：无输出（已清除）

# 检查正确字段名
grep -c 'pending_instructions' SKILL.md
# 结果：21 次
```

### 文档大小

| 指标 | 修复前 | 修复后 | 改善 |
|------|--------|--------|------|
| 文档行数 | 708 行 | 528 行 | -25.5% |
| 文件大小 | 22,293 bytes | 18,243 bytes | -18.2% |

---

## 教训总结

### 文档编写原则

1. **字段名必须与代码一致**
   - 文档示例应使用代码实际返回的字段名
   - 不要使用中间层的字段名

2. **验证清单必须准确**
   - 验证项应该是主 AI 的实际职责
   - 不要包含内部实现细节

3. **避免重复内容**
   - 同一约束不要在多个章节重复
   - 保持文档简洁清晰

### 代码与文档一致性检查方法

```bash
# 1. 检查代码返回的字段名
grep -n "pending_instructions\|\"instructions\"" executor.py

# 2. 检查文档使用的字段名
grep -n "pending_instructions\|\"instructions\"" SKILL.md

# 3. 对比是否一致
```

---

## 后续建议

1. **定期检查一致性**
   - 每次代码更新后，检查文档是否同步
   - 特别是返回值结构变更时

2. **自动化验证**
   - 可以编写脚本自动检查字段名一致性
   - 检查文档示例是否与代码返回结构匹配

3. **文档审查流程**
   - 新增文档示例时，先验证代码实际行为
   - 确保示例准确反映代码实现
