# Hook 硬约束机制实现（v6.6）

**创建时间**: 2026-05-14
**问题**: 软约束（文本提醒）被 AI 忽略，绕过 agent-pool 架构
**解决方案**: PreToolUse Hook 返回 block JSON 强制阻止违规操作

---

## 问题诊断

### 发现的问题

| 问题 | 影响 | 根因 |
|------|------|------|
| Hook 约束被忽略 | AI 绕过 agent-pool 架构 | 约束只是文本输出，非强制 |
| 历史文件干扰 | status.md 未更新 | execute.py 未清理旧文件 |
| 无执行路径验证 | terminal 直接调用绕过规范 | 无检测机制 |

### 违规案例

**错误执行方式**:
```
1. ✅ 读取 WORKFLOW.md
2. ❌ 未分解任务，使用历史 status.md
3. ❌ 未调用 agent_pool_client.execute()
4. ❌ 未生成 pending_instructions
5. ✅ 直接使用 terminal 执行命令  ← 绕过架构
```

**Hook 触发但未生效**:
- UserPromptSubmit: 1 次 → AI 确实读取了 WORKFLOW.md
- PreToolUse: 1 次 → 注入了 status.md，但 AI 忽略
- PostToolUse: 4 次 → 状态已更新

**根本原因**: Hook 输出的约束文本是"注入"，但 AI 可以忽略。没有"阻止"机制。

---

## 实施方案

### Phase 1: 历史文件清理

**修改文件**: `actions/execute.py`

**修改内容**:
```python
def init_workflow(workflow_name: str, workflow_path: str = None) -> dict:
    # ... 现有逻辑 ...
    
    # 清理旧状态文件（避免历史干扰）
    status_md = workflow_dir / 'status.md'
    if status_md.exists():
        status_md.unlink()
        print(f"    已清理旧 status.md")
```

**效果**: 强制 AI 重新分解任务，避免沿用旧状态。

---

### Phase 2: 环境变量注入

**修改文件**: `~/.hermes/plugins/skill-hook-bridge/executor.py`

**修改内容**:
```python
def _build_env(context: dict) -> dict:
    """构建注入 Hermes 上下文的环境变量"""
    env = os.environ.copy()
    if 'tool_name' in context and context['tool_name']:
        env['HERMES_TOOL_NAME'] = str(context['tool_name'])
    if 'tool_input' in context and context['tool_input']:
        val = context['tool_input']
        env['HERMES_TOOL_INPUT'] = json.dumps(val) if isinstance(val, dict) else str(val)
    if 'session_id' in context and context['session_id']:
        env['HERMES_SESSION_ID'] = str(context['session_id'])
    if 'user_message' in context and context['user_message']:
        env['HERMES_USER_MESSAGE'] = str(context['user_message'])
    return env

def execute_hook_command(...):
    env = _build_env(context)
    proc = subprocess.run(..., env=env)
```

**效果**: Hook 可以通过环境变量获取工具名称和输入。

---

### Phase 3: 硬约束检测

**修改文件**: `hooks/workflow-step-check/handler.sh`

**修改内容**:
```bash
#!/bin/bash
# 读取 Hermes 注入的环境变量
TOOL_NAME="${HERMES_TOOL_NAME:-}"
TOOL_INPUT="${HERMES_TOOL_INPUT:-}"

# ===== 硬约束检测 =====
if [[ -n "$TOOL_NAME" ]]; then
    # 规则 1: 禁止直接使用 terminal 执行工作流步骤
    if [[ "$TOOL_NAME" == "terminal" ]]; then
        if echo "$TOOL_INPUT" | grep -qE "(execute\.py|batch-login-detect|node|npm|npx|python.*workflow)"; then
            # 返回 block 指令（JSON 格式）
            cat << 'BLOCKJSON'
{
    "action": "block",
    "message": "⛔ 禁止直接使用 terminal 执行工作流步骤。\n\n正确方式：\n1. 使用 delegate_task 并行执行步骤\n2. 或使用 agent_pool_client.execute()\n\n详见 workflow-manager SKILL.md 第 87-88 行"
}
BLOCKJSON
            exit 0
        fi
    fi
    
    # 规则 2: 禁止添加 timeout 参数
    if echo "$TOOL_INPUT" | grep -qi '"timeout"'; then
        cat << 'BLOCKJSON'
{
    "action": "block",
    "message": "⛔ 工作流执行禁止添加 timeout 参数。\n\n原因：工作流步骤可能需要长时间运行，timeout 会导致意外中断。"
}
BLOCKJSON
        exit 0
    fi
fi

# ===== 软约束：注入 status.md =====
# ... 现有注入逻辑 ...
```

**关键点**:
- PreToolUse Hook 支持 `{"action": "block"}` 返回值
- 返回 block 后，AI 收到明确错误提示
- 必须使用正确方式（delegate_task 或 agent-pool）

---

### Phase 4: 前置检测

**修改文件**: `actions/execute.py`

**修改内容**:
```python
def init_workflow(workflow_name: str, workflow_path: str = None) -> dict:
    # ... 现有逻辑 ...
    
    # 前置检测：agent-pool 是否可用
    agent_pool_path = Path.home() / '.hermes/skills/openclaw-imports/agent-pool'
    if not agent_pool_path.exists():
        return {
            'success': False,
            'error': 'agent-pool 技能未安装',
            'message': 'workflow-manager 需要 agent-pool 技能来执行工作流',
            'install_hint': '请安装 agent-pool 技能'
        }
```

**效果**: 初始化时验证依赖，避免执行时才发现缺失。

---

## 验证结果

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 清理旧 status.md | ✅ 通过 | 初始化时自动删除旧文件 |
| 环境变量注入 | ✅ 通过 | executor.py 正确注入 HERMES_TOOL_NAME |
| 硬约束 block | ✅ 通过 | 检测到 terminal 违规使用并返回 block |

**测试命令**:
```bash
# 测试硬约束
export HERMES_TOOL_NAME="terminal"
export HERMES_TOOL_INPUT='{"command": "python execute.py test --init"}'
bash hooks/workflow-step-check/handler.sh
# 输出: {"action": "block", "message": "⛔ 禁止直接使用 terminal..."}
```

---

## 下次工作流执行的预期行为

```
1. execute.py --init
   - 清理旧 status.md ✅
   - 检查 agent-pool 可用性 ✅
   
2. AI 尝试直接用 terminal 执行步骤
   - Hook 检测到 HERMES_TOOL_NAME=terminal
   - 返回 block JSON
   - AI 收到明确错误提示
   
3. AI 使用正确方式
   - 使用 delegate_task 或 agent_pool_client.execute()
   - Hook 放行
```

---

## 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `actions/execute.py` | 清理旧 status.md + agent-pool 前置检测 |
| `executor.py` | 注入环境变量（HERMES_TOOL_NAME/TOOL_INPUT）|
| `hooks/workflow-step-check/handler.sh` | 硬约束检测（terminal/timeout）→ 返回 block |

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| executor.py 修改影响其他插件 | 中 | 只在 context 包含特定键时注入 |
| block 拦截合法调用 | 高 | 精确检测工作流上下文 |
| 环境变量泄露敏感信息 | 低 | 只注入必要的工具名称 |

---

## 回滚方案

如果硬约束导致问题，可以快速降级：

1. 修改 handler.sh，注释掉 block 逻辑
2. 保留软约束（文本提醒）
3. 重启 Hermes Gateway
