# Hermes Hook机制真相（代码验证版）

**版本**: v1.0  
**验证日期**: 2026-05-13  
**验证方法**: 代码审查 + 实际运行验证

---

## 一、核心结论

**SKILL.md中的hooks声明不生效！**

通过代码验证发现，Hermes不支持从技能的SKILL.md中读取和执行hooks配置。

---

## 二、代码验证证据

### 1. skill_commands.py

**位置**: `~/.hermes/hermes-agent/agent/skill_commands.py`

**验证结果**: ❌ 只读取name和description，不读取hooks

**代码证据**:
```python
# 第 272-278 行
name = frontmatter.get('name', skill_md.parent.name)
description = frontmatter.get('description', '')
# ❌ 没有 frontmatter.get('hooks')
```

### 2. skills_tool.py

**位置**: `~/.hermes/hermes-agent/tools/skills_tool.py`

**验证结果**: ❌ 只返回技能内容，不执行hooks

**代码证据**: 搜索"hook"关键字无结果

### 3. shell_hooks.py

**位置**: `~/.hermes/hermes-agent/gateway/shell_hooks.py`

**验证结果**: ❌ 只从config.yaml读取，不读取SKILL.md

**代码证据**: 只读取 `~/.hermes/config.yaml` 的 `hooks:` 配置

### 4. 执行路径

**验证结果**: ❌ 整个Hermes代码库中无执行SKILL.md hooks的代码

---

## 三、Hermes实际支持的Hook架构

### 1. Gateway Hooks ✅

**配置位置**: `~/.hermes/hooks/<name>/HOOK.yaml`

**配置格式**（正确）:
```yaml
name: workflow-status-check
description: "Hook描述"
events:
  - pre_llm_call
  - pre_tool_call
filter:  # 可选
  tool_name: terminal
# ❌ 不需要 command 字段
```

**触发机制**:
- Hermes检测到events配置
- 自动查找并执行handler.sh脚本
- 脚本位置：`~/.hermes/hooks/<name>/handler.sh`（通常通过符号链接指向技能目录）

**生效条件**:
- HOOK.yaml文件存在
- command指定的脚本存在且可执行
- 触发事件匹配

**示例**:
- `workflow-status-check`: pre_llm_call事件
- `workflow-step-check`: pre_tool_call事件

### 2. Plugin Hooks ✅

**注册位置**: `~/.hermes/plugins/<name>/__init__.py`

**注册方法**:
```python
def initialize(ctx):
    ctx.register_hook("pre_tool_call", my_hook_function)
    ctx.register_hook("post_tool_call", another_hook)
```

**生效条件**:
- ctx.register_hook()注册
- 插件已加载
- 触发事件匹配

**示例**:
- `disk-cleanup`: 注册post_tool_call和on_session_end
- `langfuse`: 注册pre_api_request和post_api_request

### 3. Shell Hooks ✅

**配置位置**: `~/.hermes/config.yaml`

**配置格式**:
```yaml
hooks:
  pre_tool_call:
    - matcher: "terminal|delegate_task"
      command: "bash /path/to/script.sh"
```

**生效条件**:
- config.yaml中有hooks配置
- 命令脚本存在且可执行
- matcher匹配（如果有）

**当前状态**: `hooks: {}`（未配置）

### 4. SKILL.md Hooks ❌

**配置位置**: SKILL.md frontmatter

**状态**: ❌ 不生效

**原因**: 无执行路径

---

## 四、事件对照表

| Hermes事件 | Claude Code事件 | 触发时机 | Gateway Hook示例 |
|-----------|----------------|---------|------------------|
| pre_llm_call | UserPromptSubmit | LLM调用前 | workflow-status-check |
| pre_tool_call | PreToolUse | 工具调用前 | workflow-step-check |
| post_tool_call | PostToolUse | 工具调用后 | （需配置） |
| subagent_stop | Stop | 子agent停止 | （需配置） |
| on_session_end | - | 会话结束 | disk-cleanup |

---

## 五、已配置的Gateway Hooks

### workflow-status-check

**位置**: `~/.hermes/hooks/workflow-status-check/HOOK.yaml`

**配置**:
```yaml
name: workflow-status-check
description: "LLM 调用前显示活动工作流状态概要"
events:
  - pre_llm_call
command: "/home/kali/.hermes/agent-hooks/workflow-status-check.sh"
```

**功能**: 显示活动工作流状态概要

**触发**: 用户发送消息时（LLM调用前）

**对应**: Claude Code的UserPromptSubmit

### workflow-step-check

**位置**: `~/.hermes/hooks/workflow-step-check/HOOK.yaml`

**配置**:
```yaml
name: workflow-step-check
description: "调用 terminal 工具前显示工作流约束提醒"
events:
  - pre_tool_call
filter:
  tool_name: terminal
command: "/home/kali/.hermes/agent-hooks/workflow-step-check.sh"
```

**功能**: 显示工作流约束提醒

**触发**: AI调用terminal工具前

**对应**: Claude Code的PreToolUse

---

## 六、Hook生效三要素

### Gateway Hooks

```
生效 = HOOK.yaml存在 + 命令脚本存在 + 触发条件满足
```

**验证方法**:
```bash
# 1. 检查HOOK.yaml
ls ~/.hermes/hooks/<name>/HOOK.yaml

# 2. 检查脚本
cat ~/.hermes/hooks/<name>/HOOK.yaml | grep command

# 3. 检查触发
# 实际运行观察是否有输出
```

### Plugin Hooks

```
生效 = ctx.register_hook()注册 + 触发条件满足
```

**验证方法**:
```bash
# 检查插件代码
grep "register_hook" ~/.hermes/plugins/<name>/__init__.py
```

### Shell Hooks

```
生效 = config.yaml配置 + 触发条件满足
```

**验证方法**:
```bash
# 检查config.yaml
grep -A 10 "^hooks:" ~/.hermes/config.yaml
```

---

## 七、常见误解纠正

### ❌ 错误认知

**误解**: SKILL.md中声明hooks会自动执行

**错误公式**: `生效 = 脚本存在 + SKILL.md声明 + 触发条件满足`

**原因**: 假设Hermes会读取和执行SKILL.md中的hooks配置

### ✅ 正确认知

**真相**: SKILL.md中的hooks声明是"死配置"

**正确公式**:
- Gateway Hooks: `生效 = HOOK.yaml存在 + 命令脚本存在 + 触发条件满足`
- Plugin Hooks: `生效 = ctx.register_hook()注册 + 触发条件满足`
- Shell Hooks: `生效 = config.yaml配置 + 触发条件满足`

**证据**: 代码验证显示无执行路径

---

## 八、实际触发案例

### 案例：资产收集流程（2026-05-12）

**观察到的"Hook触发"**:
- UserPromptSubmit触发1次
- PreToolUse触发4次

**实际触发机制**:

| 观察到的Hook | 实际触发 | 配置位置 |
|-------------|---------|---------|
| UserPromptSubmit | pre_llm_call | Gateway Hook |
| PreToolUse | pre_tool_call | Gateway Hook |

**证据**:
- Gateway Hook配置存在：`~/.hermes/hooks/workflow-status-check/HOOK.yaml`
- Gateway Hook配置存在：`~/.hermes/hooks/workflow-step-check/HOOK.yaml`
- SKILL.md中的hooks声明未被执行

---

## 九、建议

### 1. 删除SKILL.md中的无效hooks声明

**原因**: 避免误导（声明了但不生效）

**位置**: workflow-manager/SKILL.md frontmatter

### 2. 使用Gateway Hooks配置所有hook

**方法**: 创建`~/.hermes/hooks/<name>/HOOK.yaml`

**示例**:
```yaml
name: workflow-post-tool-check
events:
  - post_tool_call
command: "/home/kali/.hermes/agent-hooks/post-tool-check.sh"
```

### 3. 补全post_tool_call的Gateway Hook

**当前状态**: 未配置

**建议配置**:
```yaml
name: workflow-post-tool-check
events:
  - post_tool_call
command: "/home/kali/.hermes/agent-hooks/post-tool-check.sh"
```

### 4. 同步hooks目录和Gateway配置

**避免**: 重复维护两套配置

**建议**: 删除`hooks/`目录下的脚本，统一使用`/home/kali/.hermes/agent-hooks/`

---

## 十、验证方法

### 验证Gateway Hooks是否生效

```bash
# 1. 检查配置
ls ~/.hermes/hooks/*/HOOK.yaml

# 2. 触发事件（如发送消息）
# 3. 观察是否有hook输出
# 4. 检查日志
tail -f ~/.hermes/logs/agent.log | grep -i hook
```

### 验证Plugin Hooks是否生效

```bash
# 1. 检查注册
grep -r "register_hook" ~/.hermes/plugins/

# 2. 触发事件
# 3. 观察插件行为
```

### 验证Shell Hooks是否生效

```bash
# 1. 检查配置
cat ~/.hermes/config.yaml | grep -A 10 "^hooks:"

# 2. 触发事件
# 3. 观察是否有hook输出
```

---

## 十一、总结

### 核心发现

1. **SKILL.md hooks机制不存在**: Hermes不支持从SKILL.md读取和执行hooks
2. **实际生效的是Gateway Hooks**: 通过HOOK.yaml配置，由Gateway自动执行
3. **事件名称不一致**: Hermes用pre_llm_call/pre_tool_call，Claude Code用UserPromptSubmit/PreToolUse

### 架构对比

| Claude Code | Hermes | 生效方式 |
|-------------|--------|---------|
| SKILL.md hooks | ❌ 不支持 | 无执行路径 |
| - | Gateway Hooks | ✅ HOOK.yaml配置 |
| - | Plugin Hooks | ✅ ctx.register_hook() |
| - | Shell Hooks | ✅ config.yaml配置 |

### 修复优先级

1. **删除SKILL.md中的无效hooks声明**（避免误导）
2. **补全Gateway Hooks**（如post_tool_call）
3. **同步配置**（避免重复维护）

---

## 参考资料

- Hermes Gateway代码: `~/.hermes/hermes-agent/gateway/`
- Plugin示例: `~/.hermes/hermes-agent/plugins/disk-cleanup/`
- Gateway Hooks示例: `~/.hermes/hooks/`
- 验证报告: `/tmp/hooks_truth_analysis.md`
