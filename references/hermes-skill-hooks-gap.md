# Hermes 技能钩子架构断层分析

**发现日期**：2026-05-12  
**影响范围**：所有在 SKILL.md frontmatter 中声明 `hooks:` 的技能  
**严重程度**：高 - 导致钩子逻辑完全不执行

---

## 问题概述

**SKILL.md frontmatter 中的 `hooks:` 声明在 Hermes 运行时中不会触发。**

这是 Claude Code 生态的遗留格式，Hermes 使用完全不同的钩子系统。

---

## 证据链

### 1. Hermes 钩子加载代码

```python
# agent/shell_hooks.py - 读取钩子配置
specs = _parse_hooks_block(cfg.get("hooks"))  # ← 从 config.yaml 读取

# hermes_cli/config.py - 默认配置
"hooks": {},  # ← config.yaml 中的 hooks 键
```

**结论**：Hermes 从 `~/.hermes/config.yaml` 的 `hooks:` 键读取钩子配置。

### 2. 技能加载代码不处理 hooks

```python
# agent/skill_commands.py - 技能扫描
frontmatter, body = _parse_frontmatter(content)
name = frontmatter.get('name', ...)
description = frontmatter.get('description', '')
# ❌ 没有 frontmatter.get('hooks', ...) 的处理
# ❌ 没有将 hooks 注册到插件系统的代码
```

**结论**：技能加载流程完全忽略 SKILL.md frontmatter 中的 `hooks:` 字段。

### 3. 官方文档确认

> Claude Code's `UserPromptSubmit` event is intentionally not a separate Hermes event — `pre_llm_call` fires at the same place and already supports context injection.

来源：`website/docs/user-guide/features/hooks.md:1280`

**结论**：Hermes 明确使用不同的事件命名和机制。

### 4. 实际验证

```bash
$ hermes hooks list
No shell hooks configured in ~/.hermes/config.yaml.
```

即使 SKILL.md 声明了 hooks，`hermes hooks list` 仍然显示无配置。

---

## 受影响的技能

| 技能 | SKILL.md hooks 声明 | 实际状态 |
|------|---------------------|----------|
| workflow-manager | UserPromptSubmit, PreToolUse | ❌ 不触发 |
| planning-with-files | UserPromptSubmit, PreToolUse, PostToolUse, Stop | ❌ 不触发 |
| 其他 Claude Code 迁移技能 | 可能存在 | ❌ 不触发 |

---

## 正确的实现方式

### 方式 1：config.yaml 配置（推荐）

```yaml
# ~/.hermes/config.yaml
hooks:
  pre_llm_call:  # 替代 UserPromptSubmit
    - command: "bash ~/.hermes/agent-hooks/workflow-status.sh"
  pre_tool_call: # 替代 PreToolUse
    - matcher: "terminal|delegate_task"
      command: "bash ~/.hermes/agent-hooks/workflow-check.sh"
```

### 方式 2：Python 插件

```python
# ~/.hermes/plugins/workflow-hooks/__init__.py
def register(ctx):
    @ctx.hook("pre_tool_call")
    def check_workflow(tool_name, tool_input, **kwargs):
        # 钩子逻辑
        pass
```

### 方式 3：手动触发（临时）

```bash
# 在需要时手动执行钩子脚本
bash ~/.hermes/skills/openclaw-imports/workflow-manager/hooks/user_prompt_submit.sh
bash ~/.hermes/skills/openclaw-imports/workflow-manager/hooks/pre_tool_use.sh
```

---

## Hermes 钩子事件对照表

| Claude Code 事件 | Hermes 事件 | 触发时机 | 功能 |
|-------------------|-------------|----------|------|
| UserPromptSubmit | pre_llm_call | 用户消息处理前 | context 注入 |
| PreToolUse | pre_tool_call | 工具调用前 | block 决策 |
| PostToolUse | post_tool_call | 工具调用后 | 日志记录 |
| Stop | subagent_stop | 子agent停止时 | 清理操作 |

---

## 钩子脚本输出格式

**stdin**（JSON）：
```json
{
    "hook_event_name": "pre_tool_call",
    "tool_name": "terminal",
    "tool_input": {"command": "..."},
    "session_id": "sess_xxx",
    "cwd": "/home/user/project"
}
```

**stdout**（JSON）：
```json
// 阻止执行
{"decision": "block", "reason": "Forbidden command"}

// 注入上下文
{"context": "Today is Friday"}

// 无操作
{}
```

---

## 修复建议

### 对于技能维护者

1. **更新 SKILL.md**：标记 hooks 声明为非功能，添加正确配置说明
2. **提供 config.yaml 片段**：用户可复制到 `~/.hermes/config.yaml`
3. **或创建插件**：将钩子逻辑移至 `~/.hermes/plugins/`

### 对于 Hermes 核心

长期方案：实现 SKILL.md hooks 自动注册机制：
1. 在 `skill_commands.py` 的 `scan_skill_commands()` 中读取 `frontmatter.get('hooks')`
2. 调用 `shell_hooks.register_from_config()` 注册到插件系统
3. 注入 `$HERMES_SKILL_DIR` 环境变量

---

## 相关文档

- `website/docs/user-guide/features/hooks.md` - Hermes 钩子系统官方文档
- `agent/shell_hooks.py` - Shell 钩子桥接实现
- `hermes_cli/plugins.py` - 插件钩子系统
- `references/hooks-format.md` - 钩子格式规范（需更新）
