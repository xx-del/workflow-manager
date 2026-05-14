# 工作流一致性检查方法论

## 适用场景

当需要验证工作流技能代码与SKILL.md文档是否一致时使用此方法论。

## 检查流程

### 步骤1：加载技能SKILL.md

```python
skill_view(name="workflow-manager")
```

关键章节：
- 执行流程说明
- 核心强制要求
- 返回值说明
- 状态更新规则

### 步骤2：读取工作流定义

```bash
# 读取工作流配置
cat ~/.hermes/workflows/{工作流名称}/_index.yaml

# 读取工作流步骤
cat ~/.hermes/workflows/{工作流名称}/WORKFLOW.md
```

### 步骤3：执行验证清单

| 验证项 | SKILL.md要求 | 实际执行 | 一致性 |
|--------|-------------|----------|--------|
| 调用workflow-manager技能 | 必须调用 | ✅/❌ | ✅/❌ |
| 读取工作流定义 | 必须读取 | ✅/❌ | ✅/❌ |
| 分析步骤依赖 | 必须分析 | ✅/❌ | ✅/❌ |
| 通过agent-pool匹配agent | 必须匹配 | ✅/❌ | ✅/❌ |
| 调用delegate_task执行 | 必须调用 | ✅/❌ | ✅/❌ |
| 更新状态 | 必须更新 | ✅/❌ | ✅/❌ |

### 步骤4：对比返回值格式

**SKILL.md描述**：
```python
{
    'status': 'execution_required',
    'pending_instructions': [...],
    'execution_status': 'awaiting_delegate_task',
    'execution_mode': {...}
}
```

**实际返回**：
```python
# 对比字段是否匹配
```

### 步骤5：输出一致性报告

```markdown
## 一致性验证报告

### 执行验证清单
| 项目 | 状态 |
|------|------|
| ... | ... |

### 发现的问题
| 问题ID | 描述 | 严重性 |
|--------|------|--------|

### 一致性评分
XX%
```

## 常见问题模式

### P1：未生成status.md执行计划

**症状**：工作流执行前未生成status.md
**根因**：未调用execute.py --plan-only
**修复**：在执行工作流前调用生成命令

### P2：agent-pool未返回pending_instructions

**症状**：agent-pool execute只返回匹配结果
**根因**：命令默认输出友好格式
**修复**：修改agent-pool/bin/agent-pool，默认包含pending_instructions字段

### P3：匹配策略判断不一致

**症状**：相似度低于阈值却返回REUSE策略
**根因**：matcher.py有复杂度相关的阈值调整逻辑
**修复**：删除复杂度调整逻辑，统一使用固定阈值

### P4：返回格式不符合标准

**症状**：返回格式缺少execution字段
**根因**：cmd_execute函数未构建标准格式
**修复**：修改cmd_execute函数，默认包含所有必需字段

## 案例参考

**凭证检测工作流一致性检查（2026-05-11）**：

发现4个问题：
- P1：未生成status.md（已修复）
- P2：agent-pool未返回pending_instructions（已修复）
- P3：匹配策略不一致（已修复）
- P4：返回格式不标准（已修复）

一致性评分：85% → 100%

详见：`~/.hermes/plans/2026-05-11-workflow-consistency-fix/`
