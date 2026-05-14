# Hermes 三种 Hook 系统详解

**日期**: 2026-05-14
**来源**: 官方文档 + 实践总结

---

## 一、三种 Hook 系统对比

| 系统 | 注册方式 | 运行环境 | 事件名 | 用途 |
|------|---------|---------|--------|------|
| **Gateway Hooks** | `~/.hermes/hooks/` + HOOK.yaml | Gateway only | `agent:start`, `agent:step`, `session:end` | 日志、告警、webhook |
| **Plugin Hooks** | `ctx.register_hook()` 或 SKILL.md frontmatter | CLI + Gateway | `pre_llm_call`, `pre_tool_call`, `post_tool_call` | 工具拦截、守卫、上下文注入 |
| **Shell Hooks** | `config.yaml` 的 `hooks:` 块 | CLI + Gateway | 同 Plugin 事件名 | 阻塞、格式化、上下文注入 |

---

## 二、Gateway Hooks

### 特点
- **只在 Gateway 运行**：CLI 会话中不触发
- **事件名**：`gateway:startup`, `session:start`, `agent:start`, `agent:step`, `session:end`, `command:*`
- **配置方式**：在 `~/.hermes/hooks/` 目录创建 HOOK.yaml + handler.py

### 示例
```yaml
# ~/.hermes/hooks/my-hook/HOOK.yaml
name: my-hook
description: Log all agent activity
events:
  - agent:start
  - agent:step
```

### 适用场景
- 日志记录
- 告警通知
- Webhook 调用
- Gateway 生命周期监控

---

## 三、Plugin Hooks

### 特点
- **在 CLI + Gateway 都运行**：全局生效
- **事件名**：`pre_llm_call`, `pre_tool_call`, `post_tool_call`, `on_session_end`
- **配置方式**：
  1. 通过插件代码 `ctx.register_hook()`
  2. 通过 SKILL.md frontmatter（skill-hook-bridge 翻译）

### Claude Code 事件名映射

| Claude Code 事件 | Hermes 事件 | 触发时机 |
|-----------------|------------|---------|
| `UserPromptSubmit` | `pre_llm_call` | LLM 调用前 |
| `PreToolUse` | `pre_tool_call` | 工具调用前 |
| `PostToolUse` | `post_tool_call` | 工具调用后 |
| `Stop` | `on_session_end` | 会话结束时 |

### SKILL.md frontmatter 配置示例
```yaml
---
name: my-skill
description: Skill with hooks
hooks:
  UserPromptSubmit:
    - hooks:
        - type: python
          module: hooks.my-handler.handler
  PreToolUse:
    - matcher: "terminal|write_file"
      hooks:
        - type: python
          module: hooks.my-guard.handler
---
```

### skill-hook-bridge 工作原理

1. 扫描技能目录的 SKILL.md 文件
2. 解析 `hooks:` frontmatter
3. 翻译 Claude Code 事件名为 Hermes 事件名
4. 注册到 Plugin Hooks 系统

**重要**：skill-hook-bridge **只扫描 SKILL.md frontmatter**，不扫描 hooks/ 目录。

### 适用场景
- 工具调用拦截
- 执行守卫
- 上下文注入
- 约束强制执行

---

## 四、Shell Hooks

### 特点
- **在 CLI + Gateway 都运行**：全局生效
- **事件名**：同 Plugin Hooks
- **配置方式**：在 `~/.hermes/config.yaml` 中配置

### 配置示例
```yaml
# ~/.hermes/config.yaml
hooks:
  pre_llm_call:
    - ~/.hermes/skills/my-skill/hooks/handler.py
  pre_tool_call:
    - matcher: "terminal|delegate_task"
      script: ~/.hermes/skills/my-skill/hooks/guard.py
```

### 适用场景
- 快速配置
- 不需要修改技能文件
- 全局 Hook 管理

---

## 五、常见错误

### 错误1：混用事件名

**错误**：在 Gateway Hooks 中使用 `pre_llm_call`
```yaml
# ❌ 错误：Gateway Hooks 不识别 pre_llm_call
events:
  - pre_llm_call
```

**正确**：
```yaml
# ✅ Gateway Hooks 使用 Gateway 事件名
events:
  - agent:start

# ✅ Plugin Hooks 使用 Plugin 事件名
events:
  - pre_llm_call  # 或 UserPromptSubmit（由 skill-hook-bridge 翻译）
```

### 错误2：错误的 Hook 系统选择

**场景**：需要在 CLI + Gateway 都生效的 Hook

**错误**：使用 Gateway Hooks
```bash
# ❌ 只在 Gateway 触发
ls ~/.hermes/hooks/my-hook/
```

**正确**：使用 Plugin Hooks 或 Shell Hooks
```yaml
# ✅ 方式1：SKILL.md frontmatter
hooks:
  UserPromptSubmit: ...

# ✅ 方式2：config.yaml
hooks:
  pre_llm_call: ...
```

### 错误3：误解 skill-hook-bridge 扫描范围

**错误理解**：skill-hook-bridge 扫描 `hooks/` 目录

**正确理解**：skill-hook-bridge 只扫描 SKILL.md 的 `hooks:` frontmatter

**验证方法**：
```bash
cat ~/.hermes/plugins/skill-hook-bridge/hooks_manifest.json | python3 -m json.tool
```

---

## 六、选择指南

| 需求 | 推荐 Hook 系统 | 原因 |
|------|--------------|------|
| 只在 Gateway 触发 | Gateway Hooks | 专为 Gateway 设计 |
| CLI + Gateway 都触发 | Plugin Hooks 或 Shell Hooks | 全局生效 |
| 技能自包含配置 | Plugin Hooks（SKILL.md frontmatter） | 配置跟随技能 |
| 全局统一管理 | Shell Hooks（config.yaml） | 集中配置 |

---

## 七、参考资源

- 官方文档：https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks
- planning-with-files 技能：SKILL.md frontmatter 配置示例
- skill-hook-bridge 插件：Claude Code → Hermes 翻译器
