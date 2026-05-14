# Hermes 钩子系统完整指南

**更新日期**：2026-05-13  
**来源**：深入代码分析 + 用户反馈

---

## 一、核心结论

**SKILL.md frontmatter 中的 `hooks:` 配置在 Hermes 中不会触发。**

**原因**：
1. Hermes `VALID_HOOKS` 不包含 Claude Code 格式的事件名（UserPromptSubmit/PreToolUse）
2. `shell_hooks.py` 只从 `config.yaml` 读取，不读取 SKILL.md
3. 技能加载流程（`skill_commands.py`）不处理 hooks 字段

---

## 二、Hermes 支持的钩子事件

| Hermes 事件 | 触发时机 | 等效 Claude Code 事件 |
|------------|---------|---------------------|
| `pre_llm_call` | 用户消息处理前、LLM 调用前 | UserPromptSubmit |
| `post_llm_call` | LLM 返回结果后 | - |
| `pre_tool_call` | 工具调用前 | PreToolUse |
| `post_tool_call` | 工具调用后 | PostToolUse |
| `transform_tool_result` | 工具返回结果转换 | - |
| `transform_llm_output` | LLM 输出转换 | - |
| `on_session_start` | 会话开始时 | - |
| `on_session_end` | 会话结束时 | Stop |
| `on_session_reset` | 会话重置时 | - |
| `subagent_stop` | 子 agent 停止时 | - |
| `pre_gateway_dispatch` | Gateway 消息分发前 | - |
| `pre_approval_request` | 危险命令审批前 | - |
| `post_approval_response` | 审批响应后 | - |

---

## 三、三种钩子实现方式

### 方式 1：Gateway Hooks（推荐用于消息平台）

**配置位置**：`~/.hermes/hooks/<hook-name>/`

**文件结构**：
```
~/.hermes/hooks/
└── my-hook/
    ├── HOOK.yaml      # 钩子声明
    └── handler.py     # Python 处理函数
```

**HOOK.yaml 示例**：
```yaml
name: my-hook
description: "在 LLM 调用前注入上下文"
events:
  - pre_llm_call
command: "/home/user/.hermes/agent-hooks/my-hook.py"
```

---

### 方式 2：Plugin Hooks（推荐用于复杂逻辑）

**配置位置**：`~/.hermes/plugins/<plugin-name>/`

**示例**：
```python
# ~/.hermes/plugins/my-plugin/__init__.py

def register(ctx):
    """插件入口点"""
    
    @ctx.hook("pre_llm_call")
    def inject_context(user_message: str, session_id: str, **kwargs):
        """用户消息处理前注入上下文"""
        if "工作流" in user_message:
            return {"context": "检测到工作流任务..."}
        return None
    
    @ctx.hook("pre_tool_call")
    def check_tool(tool_name: str, tool_input: dict, session_id: str, **kwargs):
        """工具调用前检查"""
        if tool_name == "terminal":
            command = tool_input.get("command", "")
            if "rm -rf" in command:
                return {"error": "禁止执行删除命令"}
        return None
```

---

### 方式 3：Shell Hooks（推荐用于简单脚本）

**配置位置**：`~/.hermes/config.yaml`

**示例**：
```yaml
hooks:
  pre_llm_call:
    - command: "bash ~/.hermes/agent-hooks/inject-context.sh"
  
  pre_tool_call:
    - matcher: "terminal|delegate_task"
      command: "bash ~/.hermes/agent-hooks/check-command.sh"
      timeout: 30
```

---

## 四、matcher 机制（仅 Shell Hooks）

**作用**：精准匹配工具名，避免过多干扰

**配置**：
```yaml
hooks:
  pre_tool_call:
    - matcher: "terminal|delegate_task"  # 正则表达式
      command: "bash ~/.hermes/agent-hooks/check.sh"
```

**匹配逻辑**：
- `matcher` 使用正则表达式匹配工具名
- 匹配成功 → 执行钩子
- 匹配失败 → 跳过钩子

---

## 五、阻断机制（仅 pre_tool_call）

**实现方式**：钩子脚本返回 `exit 1` 或 `{"decision": "block"}`

**效果**：阻止工具调用执行

**示例**：
```bash
#!/bin/bash
payload=$(cat -)
tool_name=$(echo "$payload" | jq -r '.tool_name')

if [[ "$tool_name" == "terminal" ]]; then
    echo '{"decision": "block", "reason": "Terminal disabled"}'
    exit 0
fi

# 非零退出码也会阻断
exit 1
```

---

## 六、钩子输出格式

### stdin（脚本接收）

```json
{
    "hook_event_name": "pre_tool_call",
    "tool_name": "terminal",
    "tool_input": {"command": "..."},
    "session_id": "sess_xxx",
    "cwd": "/home/user/project"
}
```

### stdout（脚本返回）

```json
// 阻止执行（仅 pre_tool_call）
{"decision": "block", "reason": "Forbidden command"}

// 注入上下文（仅 pre_llm_call）
{"context": "Today is Friday"}

// 无操作
{}
```

---

## 七、环境变量注入

Hermes 自动注入以下环境变量：

| 变量 | 说明 | 示例值 |
|------|------|---------|
| `$HERMES_HOME` | Hermes 根目录 | `~/.hermes` |
| `$SESSION_ID` | 当前会话 ID | `sess_xxx` |
| `$HERMES_TOOL_NAME` | 工具名（仅 pre_tool_call） | `terminal` |

**注意**：`$SKILL_DIR` 不是 Hermes 自动注入的，需要自行传递。

---

## 八、故障排查

### 钩子不触发

1. **检查事件名**：确保在 `VALID_HOOKS` 中
2. **检查配置位置**：Gateway hooks 在 `~/.hermes/hooks/`，Shell hooks 在 `config.yaml`
3. **检查脚本权限**：`chmod +x hooks/*.sh`
4. **检查日志**：`hermes logs --follow`

### 部分触发

1. **matcher 不匹配**：检查正则表达式
2. **插件未加载**：检查 `plugins/` 目录
3. **Gateway 未启动**：检查 Gateway 进程

---

## 九、代码证据

### VALID_HOOKS 定义

```python
# hermes_cli/plugins.py:78-118
VALID_HOOKS: Set[str] = {
    "pre_tool_call",
    "post_tool_call",
    "transform_terminal_output",
    "transform_tool_result",
    "transform_llm_output",
    "pre_llm_call",
    "post_llm_call",
    "pre_api_request",
    "post_api_request",
    "on_session_start",
    "on_session_end",
    "on_session_finalize",
    "on_session_reset",
    "subagent_stop",
    "pre_gateway_dispatch",
    "pre_approval_request",
    "post_approval_response",
}
```

**注意**：`UserPromptSubmit` 和 `PreToolUse` 不在列表中。

### shell_hooks.py 只读取 config.yaml

```python
# agent/shell_hooks.py:174
specs = _parse_hooks_block(cfg.get("hooks"))  # ← 从 config.yaml 读取
```

---

## 十、参考资料

- Hermes 官方文档：`website/docs/user-guide/features/hooks.md`
- 插件系统：`hermes_cli/plugins.py`
- Shell Hooks：`agent/shell_hooks.py`
- VALID_HOOKS 定义：`hermes_cli/plugins.py:78-118`
