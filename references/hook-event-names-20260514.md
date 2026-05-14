# Hook 事件名称规范

**日期**: 2026-05-14
**问题**: HOOK.yaml使用了错误的事件名称

## Gateway 事件名称（正确）

Gateway Hooks使用以下事件名称：

| 事件 | 触发时机 | 用途 |
|------|---------|------|
| `gateway:startup` | Gateway启动时 | 发送启动通知 |
| `session:start` | 会话开始时 | 初始化会话状态 |
| `agent:start` | Agent开始处理消息时 | 注入上下文、提醒 |
| `agent:step` | Agent执行步骤时 | 注入约束、检查状态 |
| `agent:end` | Agent处理完成时 | 记录结果 |
| `session:end` | 会话结束时 | 清理资源、发送通知 |
| `session:reset` | 会话重置时 | 重置状态 |

## Plugin 事件名称（不适用于Gateway Hooks）

以下事件名称用于Plugin Hooks，不适用于Gateway Hooks：

| 事件 | 说明 |
|------|------|
| ~~`pre_llm_call`~~ | Plugin Hook事件 |
| ~~`pre_tool_call`~~ | Plugin Hook事件 |
| ~~`post_tool_call`~~ | Plugin Hook事件 |
| ~~`on_session_end`~~ | Plugin Hook事件 |

## 正确配置示例

```yaml
name: workflow-status-check
description: "Agent开始处理时显示活动工作流状态"
events:
  - agent:start
```

## 错误配置示例

```yaml
# ❌ 错误：使用了Plugin事件名
name: workflow-status-check
description: "LLM调用前显示活动工作流状态"
events:
  - pre_llm_call
```

## 事件映射关系

| 用途 | Gateway事件 | Plugin事件（错误） |
|------|------------|-------------------|
| Agent开始处理 | `agent:start` | ~~`pre_llm_call`~~ |
| Agent执行步骤 | `agent:step` | ~~`pre_tool_call`~~ |
| 会话结束 | `session:end` | ~~`on_session_end`~~ |

## 修复记录

**2026-05-14**：
- 修复了所有workflow hooks的事件名称
- 从`pre_llm_call`等改为`agent:start`等
- Hook成功加载（6个hooks）

## 参考

- Gateway源码：`~/.hermes/hermes-agent/gateway/run.py`
- 搜索关键词：`hooks.emit`
