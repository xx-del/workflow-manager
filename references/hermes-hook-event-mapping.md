# Hermes Hook 事件名映射与技术发现

**创建日期**：2026-05-13  
**来源**：planning-with-files 融合方案修订过程中发现

---

## 一、事件名映射关系

### Claude Code vs Hermes

| Claude Code 事件 | Hermes 事件 | 触发时机 |
|-----------------|------------|---------|
| UserPromptSubmit | `pre_llm_call` | 用户消息处理前、LLM 调用前 |
| PreToolUse | `pre_tool_call` | 工具调用前 |
| PostToolUse | `post_tool_call` | 工具调用后 |
| Stop | `on_session_end` | 会话结束时 |

### Hermes VALID_HOOKS 定义

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

**关键发现**：`UserPromptSubmit`、`PreToolUse`、`PostToolUse`、`Stop` 不在 `VALID_HOOKS` 中。

---

## 二、filter 配置机制

### 正确配置方式（HOOK.yaml）

```yaml
name: workflow-step-check
description: "工具调用前注入工作流状态和约束"
events:
  - pre_tool_call
filter:
  tool_name: "terminal|delegate_task|write_file|patch|browser_navigate|browser_click"
command: "/home/kali/.hermes/agent-hooks/workflow-step-check.sh"
```

### 错误配置方式（handler.sh bash 正则）

```bash
# ❌ 这种方式不会生效
MATCHED_TOOLS="Write|Edit|Bash|Read|Glob|Grep|terminal|delegate_task"
if [[ ! "$TOOL_NAME" =~ ^($MATCHED_TOOLS)$ ]]; then
    exit 0
fi
```

**原因**：
- Hermes Gateway Hooks 在配置层面过滤，而非脚本层面
- `filter.tool_name` 使用正则表达式匹配工具名
- `$HERMES_TOOL_NAME` 环境变量虽然自动注入，但脚本中不应二次过滤

---

## 三、Gateway Hooks 架构

### 符号链接机制

```
技能目录（源）                          Hermes 标准路径（链接）
─────────────────────────────────────────────────────────────
~/.hermes/skills/.../hooks/workflow-status-check/
                                       → ~/.hermes/hooks/workflow-status-check/
~/.hermes/skills/.../hooks/.../handler.sh
                                       → ~/.hermes/agent-hooks/workflow-status-check.sh
```

### 安装机制

```bash
# 技能目录下的安装脚本
cd ~/.hermes/skills/openclaw-imports/workflow-manager
bash hooks-install.sh

# 安装脚本自动创建符号链接
```

### 文件结构要求

```
hooks/<hook-name>/
├── HOOK.yaml      # 必需：钩子配置
└── handler.sh     # 必需：钩子脚本（必须有执行权限）
```

---

## 四、数据格式兼容

### 问题背景

| Hook | 现有实现 | 融合要求 |
|------|---------|---------|
| workflow-progress-update | status.json | status.md |
| workflow-session-cleanup | status.json | status.md |
| workflow-step-check | status.md | status.md |
| workflow-status-check | status.md | status.md |

### 兼容方案

```bash
# 优先使用 status.md，回退 status.json
STATUS_FILE=$(find "$WORKFLOW_DIR" -name "status.md" -type f 2>/dev/null | head -1)
if [[ -z "$STATUS_FILE" ]]; then
    STATUS_FILE=$(find "$WORKFLOW_DIR" -name "status.json" -type f 2>/dev/null | head -1)
fi
```

---

## 五、典型错误示例

### 错误1：使用 Claude Code 事件名

```yaml
# ❌ 错误配置
events:
  - PreToolUse      # Hermes 不支持
  - PostToolUse     # Hermes 不支持
```

**结果**：Hook 永远不会触发

### 错误2：在 handler.sh 中使用 bash 正则

```bash
# ❌ 错误脚本
TOOL_NAME="${HERMES_TOOL_NAME:-}"
if [[ "$TOOL_NAME" != "terminal" ]]; then
    exit 0
fi
```

**结果**：即使 HOOK.yaml 中配置了 filter，脚本仍会过滤

### 错误3：覆盖符号链接

```bash
# ❌ 直接在 ~/.hermes/agent-hooks/ 创建文件
touch ~/.hermes/agent-hooks/workflow-step-check.sh
```

**结果**：破坏符号链接，技能更新后需要重新运行 hooks-install.sh

---

## 六、参考资料

- Hermes 钩子系统完整指南：`references/hermes-hooks-system.md`
- Hook 架构说明：`references/hooks-architecture.md`
- Hook 使用指南：`HOOKS_GUIDE.md`