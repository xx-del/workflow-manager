# status.json 不自动更新机制

## 发现日期
2026-05-18

## 问题
工作流步骤执行后，status.json 不会自动更新步骤状态。

## 根因分析

### Hook 职责链

| Hook | 事件 | 实际行为 |
|------|------|----------|
| workflow-step-check | PreToolUse | 检测活跃工作流 + 串行模式检查 + 注入约束 |
| workflow-progress | PostToolUse | **仅提醒**更新状态，不执行更新 |
| workflow-context | UserPromptSubmit | 注入工作流上下文 |
| workflow-cleanup | Stop | 清理会话标记 |

### workflow-progress Hook 源码分析

文件：`hooks/workflow-progress/handler.sh`

核心逻辑：
```bash
# 只输出提醒文本
echo "📝 请更新 status.md："
echo "1. 更新当前步骤状态"
echo "2. 更新 Current Phase"
```

**关键**：Hook 是 Shell 脚本，只能输出文本提醒。无法直接修改 status.json。

### 测试验证

创建 `status-json-test` 工作流（4步骤），执行后观察：

| 步骤 | 执行状态 | status.json 更新 |
|------|----------|------------------|
| 步骤1 | ✅ 完成 | ❌ 仍为 pending |
| 步骤2 | ✅ 完成 | ❌ 仍为 pending |
| 步骤3 | ✅ 完成 | ❌ 仍为 pending |
| 步骤4 | ✅ 完成 | ❌ 仍为 pending |

手动执行更新命令后才变为 completed。

## 正确做法

主 AI 在每步执行后必须手动更新 status.json：
1. 步骤执行完成
2. 执行 `python3 -c "..."` 更新 status.json
3. 验证更新结果
4. 继续执行下一步骤

## 对比 home 漏扫心跳

| 项目 | workflow-manager | home 漏扫心跳 |
|------|------------------|---------------|
| 完成判断 | ✅ 依赖 status.json | ❌ 直接检测远程 |
| 状态写入 | 主 AI 手动 | 心跳脚本自动 |
| 自动更新 | ❌ 无 | ✅ 有 |

## 改进方向

1. 方案A：PostToolUse Hook 直接更新 status.json（需修改 handler.sh）
2. 方案B：使用 Python Hook 替代 Shell（更灵活，可执行更新逻辑）
3. 方案C：execute.py 添加 --step-complete 参数，Hook 调用

## 清理

测试工作流 `status-json-test` 创建在 `~/.hermes/workflows/status-json-test/`，可删除。
