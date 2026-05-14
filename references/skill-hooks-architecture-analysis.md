# 技能钩子架构分析（待完善）

**创建日期**: 2026-05-12
**状态**: 待用户澄清

---

## 用户纠正记录

### 纠正 1：planning-with-files 钩子机制

**用户原话**：
> 不可能 plan with file技能是利用heres循环来实现的钩子触发

**理解**：
- planning-with-files 的钩子是通过 Hermes 循环实现的
- 不是 Hermes 核心自动触发，而是通过某种循环机制

### 纠正 2：分析方法

**用户原话**：
> 你先阅读hermes关于hooks的文档 详细分析后再下结论

**教训**：
- 不能仅凭代码搜索就下结论
- 需要深入理解机制后再判断

---

## Hermes 钩子系统架构（已确认）

| 系统 | 注册方式 | 运行环境 | 用途 |
|------|---------|---------|------|
| **Gateway hooks** | `~/.hermes/hooks/` + `HOOK.yaml` | Gateway only | 日志、告警、webhook |
| **Plugin hooks** | `ctx.register_hook()` | CLI + Gateway | 工具拦截、指标、护栏 |
| **Shell hooks** | `config.yaml` 中的 `hooks:` | CLI + Gateway | 单文件脚本、阻止工具调用 |

### 官方文档说明

> Claude Code's `UserPromptSubmit` event is intentionally not a separate Hermes event — `pre_llm_call` fires at the same place and already supports context injection.

来源：`website/docs/user-guide/features/hooks.md:1280`

---

## 待澄清问题

1. **planning-with-files 钩子的"循环"是什么？**
   - 是工具调用循环？
   - 是 AI 主动检查？
   - 是其他机制？

2. **SKILL.md 中的 hooks 配置如何被处理？**
   - Hermes 核心是否读取？
   - AI 是否主动执行？
   - 与 config.yaml hooks 的关系？

---

## 当前理解（待验证）

SKILL.md 中的 `hooks:` 配置可能：
1. 作为指令注入到 AI 上下文
2. AI 根据指令主动执行钩子脚本
3. 不是 Hermes 核心自动触发

**需要用户澄清后完善本文档。**
