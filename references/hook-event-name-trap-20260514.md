# Hook 事件名陷阱（已修正）

**日期**: 2026-05-14
**修正日期**: 2026-05-14
**重要程度**: ⚠️ 极高

---

## ⚠️ 原文档错误

原文档（已废弃）声称 `agent:start`、`agent:step`、`session:end` 是错误的事件名，这是**错误的结论**。

---

## 正确理解

**Hermes 有两种 Hook 机制，事件名不同**：

| 机制 | 事件名 | 配置位置 | 源码 |
|------|--------|---------|------|
| **Gateway Hooks** | `agent:start`, `agent:step`, `session:end` | `~/.hermes/hooks/` | `gateway/run.py` |
| **Plugin Hooks** | `pre_llm_call`, `pre_tool_call`, `post_tool_call` | SKILL.md frontmatter | `hermes_cli/plugins.py` |

---

## workflow-manager 使用 Gateway Hooks

**配置位置**：`~/.hermes/hooks/` 目录（符号链接到技能目录）

**正确事件名**：

| Hook | 事件 | 说明 |
|------|------|------|
| workflow-ai-remind | `agent:start` | ✅ 正确 |
| workflow-status-check | `agent:start` | ✅ 正确 |
| workflow-step-check | `agent:step` | ✅ 正确 |
| workflow-progress-update | `agent:step` | ✅ 正确 |
| workflow-session-cleanup | `session:end` | ✅ 正确 |

---

## 常见错误

### 错误：混用事件名

```yaml
# ❌ 错误：Gateway Hook 使用 Plugin 事件名
# 文件：~/.hermes/hooks/workflow-ai-remind/HOOK.yaml
events:
  - pre_llm_call    # Gateway 不识别，Hook 永不触发
```

### 正确做法

```yaml
# ✅ 正确：Gateway Hook 使用 Gateway 事件名
events:
  - agent:start
```

---

## 判断方法

| Hook 配置位置 | 使用的事件名 |
|--------------|------------|
| `~/.hermes/hooks/` 目录 | Gateway 事件：`agent:start`, `agent:step`, `session:end` |
| SKILL.md frontmatter `hooks:` | Plugin 事件：`pre_llm_call`, `pre_tool_call` 等 |

---

## 详见

完整机制说明：`references/hermes-dual-hook-mechanism-20260514.md`
