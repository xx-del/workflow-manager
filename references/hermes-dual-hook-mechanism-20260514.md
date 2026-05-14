# Hermes 双重 Hook 机制

**日期**: 2026-05-14
**来源**: workflow-manager Hook 事件名修复实践

---

## 核心发现

Hermes 有**两种独立的 Hook 机制**，使用**不同的事件名**。

| 机制 | 事件名 | 加载位置 | 触发范围 | 源码位置 |
|------|--------|---------|---------|---------|
| **Gateway Hooks** | `agent:start`, `agent:step`, `session:end` | `~/.hermes/hooks/` | Gateway 主会话 | `gateway/run.py` |
| **Plugin Hooks** | `pre_llm_call`, `pre_tool_call`, `post_tool_call`, `on_session_end` | SKILL.md frontmatter | 所有 Agent | `hermes_cli/plugins.py` |

---

## Gateway Hooks

### 事件名

```python
# gateway/run.py 源码
await self.hooks.emit("agent:start", {...})  # Agent 开始处理
await self.hooks.emit("agent:step", {...})   # Agent 执行步骤
await self.hooks.emit("session:end", {...})  # 会话结束
```

### 配置方式

**目录结构**：
```
~/.hermes/hooks/
├── workflow-ai-remind/
│   ├── HOOK.yaml      # events: [agent:start]
│   └── handler.py
└── workflow-step-check/
    ├── HOOK.yaml      # events: [agent:step]
    └── handler.py
```

**HOOK.yaml 格式**：
```yaml
name: workflow-ai-remind
description: "提醒使用agent-pool"
events:
  - agent:start        # ⚠️ 使用 Gateway 事件名
```

### 触发条件

**只在 Gateway 主会话触发**：
- ✅ 飞书/Telegram 发送消息
- ✅ Gateway 接收消息后启动的主 Agent

**不触发场景**：
- ❌ CLI 会话（hermes chat）
- ❌ delegate_task 创建的子 agent
- ❌ 独立 Python 脚本

### 返回值协议

```python
# handler.py
async def handle(event_type: str, context: Dict[str, Any]) -> Dict[str, str] | None:
    return {"context": "注入到 AI 上下文的内容"}
```

### 验证方法

```bash
# 检查 Hook 是否加载
tail -30 ~/.hermes/logs/gateway.log | grep hook
# 输出: 6 hook(s) loaded

# 检查 Hook 事件名
for hook in ~/.hermes/hooks/*/; do
    echo "=== $(basename $hook) ==="
    grep "^events:" -A 1 "$hook/HOOK.yaml"
done
```

---

## Plugin Hooks

### 事件名

```python
# hermes_cli/plugins.py 定义
VALID_HOOKS: Set[str] = {
    "pre_tool_call",
    "post_tool_call",
    "pre_llm_call",
    "post_llm_call",
    "on_session_start",
    "on_session_end",
    # ...
}
```

### 配置方式

**在 SKILL.md frontmatter 中配置**：
```yaml
---
name: planning-with-files
hooks:
  UserPromptSubmit:       # Claude Code 事件名
    - hooks:
        - type: command
          command: |
            echo "Hook triggered"
---
```

**skill-hook-bridge 转换**：
- Claude Code `UserPromptSubmit` → Hermes `pre_llm_call`
- Claude Code `PreToolUse` → Hermes `pre_tool_call`
- Claude Code `PostToolUse` → Hermes `post_tool_call`

### 触发条件

**在所有 Agent 中触发**（通过 skill-hook-bridge）。

---

## 常见错误

### 错误 1：混用事件名

```yaml
# ❌ 错误：Gateway Hook 使用 Plugin 事件名
# 文件：~/.hermes/hooks/workflow-ai-remind/HOOK.yaml
events:
  - pre_llm_call    # Gateway 不识别此事件名，Hook 永不触发
```

**后果**：Hook 永远不会触发。

**正确做法**：
```yaml
# ✅ 正确：Gateway Hook 使用 Gateway 事件名
events:
  - agent:start
```

### 错误 2：误以为 VALID_HOOKS 适用于所有 Hook

`VALID_HOOKS` 只适用于 Plugin Hooks，不适用于 Gateway Hooks。

**Gateway 源码使用的是自定义事件名**（`agent:start` 等），不在 `VALID_HOOKS` 中。

---

## 判断方法

**判断使用哪种事件名**：

| Hook 位置 | 使用的事件名 |
|----------|------------|
| `~/.hermes/hooks/` 目录 | Gateway 事件名：`agent:start`, `agent:step`, `session:end` |
| SKILL.md frontmatter `hooks:` 字段 | Plugin 事件名：`pre_llm_call`, `pre_tool_call` 等 |

---

## 实践案例

### 案例：workflow-manager Hook 修复

**问题**：Hook 配置使用了 Plugin 事件名，导致永不触发。

**修复过程**：
1. 第一次修复（错误）：改为 `pre_llm_call` 等 Plugin 事件名
2. 第二次修复（正确）：恢复 `agent:start` 等 Gateway 事件名

**验证**：
```bash
# Gateway 日志显示加载成功
tail -30 ~/.hermes/logs/gateway.log | grep hook
# 输出: 6 hook(s) loaded

# 事件名验证
grep "^events:" -A 1 ~/.hermes/hooks/workflow-*/HOOK.yaml
# 输出: agent:start, agent:step, session:end
```

---

## 参考文档

- Gateway Hooks 源码：`hermes-agent/gateway/run.py`
- Plugin Hooks 定义：`hermes-agent/hermes_cli/plugins.py` VALID_HOOKS
- Hook 事件映射：`references/hermes-hook-event-mapping.md`
