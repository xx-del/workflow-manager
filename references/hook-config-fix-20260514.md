# HOOK.yaml配置修复（2026-05-14）

## 问题

HOOK.yaml包含command字段，不符合Hermes网关钩子标准。

**错误配置**：
```yaml
name: workflow-ai-remind
description: "提醒 AI 使用 agent-pool 执行"
events:
  - pre_llm_call
command: "/home/kali/.hermes/agent-hooks/workflow-ai-remind.sh"  # ❌ 不需要
```

## 修复

移除command字段，保留events和filter配置。

**正确配置**：
```yaml
name: workflow-ai-remind
description: "提醒 AI 使用 agent-pool 执行"
events:
  - pre_llm_call
# 不需要 command 字段
```

## 触发机制

**事件驱动**：
- Hermes检测到HOOK.yaml中的events配置
- 自动查找并执行handler.sh脚本
- handler.sh位置：`~/.hermes/hooks/<name>/handler.sh`（符号链接）

**关键发现**：
- Hook是事件驱动，不是工作流触发
- 每次事件发生都会触发（pre_llm_call, pre_tool_call等）
- handler.sh内部判断是否有工作流来决定输出内容

## 修复的Hooks

1. workflow-ai-remind (pre_llm_call)
2. workflow-status-check (pre_llm_call)
3. workflow-step-check (pre_tool_call)
4. workflow-progress-update (post_tool_call)
5. workflow-session-cleanup (on_session_end)

## 验证方法

```bash
# 检查配置
cat ~/.hermes/hooks/workflow-ai-remind/HOOK.yaml

# 检查符号链接
ls -la ~/.hermes/hooks/workflow-*
ls -la ~/.hermes/agent-hooks/workflow-*.sh

# 运行安装脚本
cd ~/.hermes/skills/openclaw-imports/workflow-manager
bash hooks-install.sh
```

## 参考

- Hermes Hook触发机制：`references/hermes-hooks-mechanism.md`
- HOOK.yaml格式规范：`references/hooks-format.md`
