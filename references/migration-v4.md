# workflow-manager v3 → v4 迁移指南

版本：v1.0
日期：2026-04-14

## 架构变化

### 核心变化

| 维度 | v3.x | v4.0 |
|------|------|------|
| **执行者** | Node.js 代码 | AI（大模型） |
| **代码职责** | 加载、分析、执行、汇总 | 只提供信息工具 |
| **AI 职责** | 无 | 理解、决策、调用工具 |
| **工具调用** | ❌ 代码无法调用 | ✅ AI 原生支持 |
| **兼容性** | ❌ Node.js 无法使用 Hermes 工具 | ✅ 完全兼容 |

### 文件变化

| 文件 | v3.x | v4.0 |
|------|------|------|
| `workflow-executor.js` | 核心执行器 | 已备份为 .backup |
| `agent-pool-client.js` | agent-pool 客户端 | 已备份为 .backup |
| `step-analyzer.js` | 步骤分析器 | 已备份为 .backup |
| `workflow-tools.js` | 不存在 | ⚠️ 应新增但实际缺失 |
| `SKILL.md` | 代码驱动描述 | ✅ AI 驱动描述 |

**⚠️ 已知问题 (2026-05-11)**:
- `workflow-tools.js` 文件实际不存在
- AI 应直接使用 `read_file` / `write_file` 操作工作流文件
- 无需依赖 workflow-tools.js

### 执行流程变化

#### v3.x（代码驱动）

```
用户 → Node.js 代码 → agent-pool-client.js
  ↓
Python subprocess → 返回执行计划
  ↓
❌ Node.js 无法调用 delegate_task
  ↓
返回计划，未实际执行
```

#### v4.0（AI 驱动）

```
用户 → AI → workflow-tools.js（读取工作流）
  ↓
AI 理解步骤 → 调用 agent-pool 技能
  ↓
agent-pool 返回建议 → AI 调用 delegate_task
  ↓
✅ AI 原生支持 delegate_task
  ↓
实际执行任务
```

## 迁移步骤

### 1. 验证备份

旧代码已自动备份为：
- `src/workflow-executor.js.backup`
- `src/agent-pool-client.js.backup`
- `src/step-analyzer.js.backup`

如需回滚：
```bash
cd ~/.hermes/skills/openclaw-imports/workflow-manager/src
mv workflow-executor.js.backup workflow-executor.js
mv agent-pool-client.js.backup agent-pool-client.js
mv step-analyzer.js.backup step-analyzer.js
```

### 2. 工作流定义无需修改

v4.0 完全兼容 v3.x 的工作流定义格式（`_index.yaml`），无需修改现有工作流。

### 3. 测试工作流执行

执行一个简单的工作流测试：

```
用户："执行凭证检测工作流"
```

AI 应该：
1. 调用 `workflow-tools.js read "凭证检测"`
2. 读取工作流定义
3. 对每个步骤调用 agent-pool 技能
4. 根据返回调用 delegate_task
5. 汇总结果

### 4. 验证并发控制

测试并发工作流，确保 AI 不超过 3 个并行任务。

### 5. 验证守护机制

启动守护 Agent，检查是否正常工作。

## 兼容性说明

### 完全兼容

- ✅ 工作流定义格式（`_index.yaml`）
- ✅ 状态文件格式（`status.json`）
- ✅ 严格模式约束
- ✅ 守护机制
- ✅ 校验功能
- ✅ 优化功能

### 行为变化

| 功能 | v3.x | v4.0 |
|------|------|------|
| 执行方式 | 代码自动执行 | AI 手动调用工具 |
| 错误处理 | 代码捕获异常 | AI 判断并处理 |
| 并发控制 | 代码限制 3 个 | AI 必须遵守约束 |
| 状态更新 | 代码自动更新 | AI 调用工具更新 |

## 常见问题

### Q1: 为什么改为 AI 驱动？

**A**: 解决兼容性问题。v3.x 的核心问题是 Node.js 代码无法调用 Hermes 工具（如 `delegate_task`），导致工作流无法实际执行。v4.0 让 AI 成为执行者，AI 原生支持所有 Hermes 工具。

### Q2: 工作流会变慢吗？

**A**: 可能会略微变慢，因为 AI 需要理解工作流、决策、调用工具。但好处是：
- 彻底解决兼容性问题
- AI 可以根据上下文灵活调整
- 更智能的错误处理

### Q3: 如果 AI 不遵守约束怎么办？

**A**: 通过以下方式约束：
- 技能描述中的明确指令
- SOUL.md 的行为准则
- 严格模式验证清单

### Q4: 可以回滚到 v3.x 吗？

**A**: 可以，恢复备份文件即可。但 v3.x 的兼容性问题未解决。

## 性能对比

| 指标 | v3.x | v4.0 |
|------|------|------|
| 执行成功率 | ❌ 0%（无法执行） | ✅ 预期 90%+ |
| 兼容性 | ❌ 无法使用 Hermes 工具 | ✅ 完全兼容 |
| 灵活性 | ❌ 硬编码 | ✅ AI 自主决策 |
| 维护成本 | ❌ 高（工具更新需改代码） | ✅ 低（无需改代码） |

## 下一步

1. 测试简单工作流（单步骤）
2. 测试复杂工作流（多步骤）
3. 测试并发工作流
4. 测试守护机制
5. 验证所有现有工作流

如有问题，参考 `references/troubleshooting.md` 或联系开发者。
