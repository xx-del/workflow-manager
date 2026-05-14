# Hermes 钩子配置格式规范

> ⚠️ **重要发现（2026-05-14）**：HOOK.yaml配置应仅包含events和filter，不需要command字段。Hermes会自动查找并执行handler.py脚本。

## Gateway Hooks 正确格式

**配置位置**：`~/.hermes/hooks/<name>/HOOK.yaml`

```yaml
name: workflow-status-check
description: "Hook描述"
events:
  - agent:start    # ✅ Gateway事件名
  - agent:step     # ✅ Gateway事件名
filter:  # 可选
  tool_name: terminal
# ❌ 不需要 command 字段
```

**⚠️ 重要：事件名称**

Gateway Hooks 和 Plugin Hooks 使用不同的事件名称：

| Gateway事件 | Plugin事件 | 触发时机 |
|------------|-----------|---------|
| agent:start | pre_llm_call | Agent开始处理消息 |
| agent:step | pre_tool_call/post_tool_call | Agent执行步骤 |
| session:end | on_session_end | 会话结束 |

详见：`references/hook-event-names-20260514.md`

**脚本位置**：
- handler.py在技能目录：`~/.hermes/skills/openclaw-imports/workflow-manager/hooks/<name>/handler.py`
- 通过符号链接映射到：`~/.hermes/hooks/<name>/`

**安装方式**：
```bash
cd ~/.hermes/skills/openclaw-imports/workflow-manager
bash hooks-install.sh
```

## 关键规则

| 规则 | 说明 |
|------|------|
| **钩子配置位置** | `~/.hermes/hooks/<name>/HOOK.yaml` |
| **处理器要求** | 必须使用handler.py（Python异步函数） |
| **事件名称** | 使用Gateway事件名（agent:start等），不是Plugin事件名 |
| **不需要command** | Gateway自动查找handler.py |

## ❌ 常见错误

**错误1：使用Plugin事件名**
```yaml
events:
  - pre_llm_call    # ❌ 错误：Plugin事件名
```

**正确：使用Gateway事件名**
```yaml
events:
  - agent:start     # ✅ 正确：Gateway事件名
```

**错误2：使用handler.sh**
```bash
handler.sh    # ❌ 错误：Shell脚本不会被Gateway自动执行
```

**正确：使用handler.py**
```python
async def handle(event_type: str, context: Dict) -> Dict | None:
    # ✅ 正确：Python异步函数
    return {"context": "注入内容"}
```

## 发现日期

- 2026-05-12：发现 workflow-manager SKILL.md hooks 声明无效
- 2026-05-14：发现事件名称错误，Gateway使用不同的事件名

## 相关文档

- `references/hook-event-names-20260514.md` - Gateway vs Plugin事件名称对照表
- `references/hermes-skill-hooks-gap.md` - 详细分析和修复方案
- `website/docs/user-guide/features/hooks.md` - Hermes 官方钩子文档
