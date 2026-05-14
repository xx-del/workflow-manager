# 技能钩子架构断层诊断

**发现日期**：2026-05-12  
**影响范围**：所有在 SKILL.md 中定义 hooks: 的技能  
**严重程度**：高（功能完全失效）

---

## 问题现象

用户要求验证工作流技能钩子是否正常触发，发现：

- ✅ 钩子配置格式正确（SKILL.md frontmatter）
- ✅ 钩子脚本权限正确（-rwxrwxr-x）
- ✅ 钩子脚本逻辑正确（手动执行可工作）
- ❌ **钩子不会自动触发**

---

## 根本原因

### 架构断层

```
workflow-manager SKILL.md
├── hooks:                    # ← 钩子配置声明
│   ├── UserPromptSubmit      # ← 用户发送消息时触发
│   └── PreToolUse            # ← AI 调用工具前触发
└── hooks/*.sh                # ← 钩子脚本实现

Hermes 核心
├── plugins.py                # ← 插件钩子系统
│   ├── pre_tool_call         # ← 插件钩子（已实现）
│   ├── post_tool_call        # ← 插件钩子（已实现）
│   └── ...                   # ← 其他插件钩子
└── skill_commands.py         # ← 技能加载（无钩子处理）
    └── _load_skill_payload() # ← 只加载技能内容，不处理钩子
```

**结论**：Hermes 有插件钩子系统，但**没有技能钩子系统**。

---

## 诊断过程

### 1. 验证钩子配置

```yaml
# SKILL.md frontmatter
hooks:
  UserPromptSubmit:
    - hooks:
        - type: command
          command: bash $SKILL_DIR/hooks/user_prompt_submit.sh
  PreToolUse:
    - matcher: "terminal|delegate_task"
      hooks:
        - type: command
          command: bash $SKILL_DIR/hooks/pre_tool_use.sh
```

**结果**：格式正确，符合 planning-with-files 规范

---

### 2. 验证钩子脚本

```bash
# 手动执行 UserPromptSubmit 钩子
bash ~/.hermes/skills/openclaw-imports/workflow-manager/hooks/user_prompt_submit.sh

# 输出：
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔔 检测到未完成工作流: test-progress-log
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**结果**：脚本可执行，逻辑正确

---

### 3. 验证 Hermes 钩子加载

```bash
# 搜索 Hermes 钩子相关代码
grep -r "skill.*hook\|hook.*skill" ~/.hermes/hermes-agent/ --include="*.py"

# 结果：无匹配（除第三方库）
```

```bash
# 搜索 Hermes 插件钩子
grep -r "pre_tool_call\|post_tool_call" ~/.hermes/hermes-agent/hermes_cli/plugins.py

# 结果：VALID_HOOKS 包含插件钩子，但不包含技能钩子
```

**结论**：Hermes 无技能钩子加载逻辑

---

## 影响范围

### 受影响的技能

所有在 SKILL.md 中定义 `hooks:` 的技能，包括：

1. **workflow-manager**：定义了 UserPromptSubmit 和 PreToolUse 钩子
2. **planning-with-files**：定义了 UserPromptSubmit 钩子（可能）

### 失效的功能

- **注意力操控机制**：无法在工具调用前注入约束
- **工作流检测**：无法自动检测未完成工作流
- **状态同步**：无法在用户消息时自动同步状态

---

## 解决方案

### 方案 A：实现技能钩子系统（推荐）

**修改位置**：
1. `hermes_cli/plugins.py`：扩展 VALID_HOOKS 支持技能钩子
2. `agent/skill_commands.py`：在 `_load_skill_payload()` 中读取 SKILL.md frontmatter
3. `run_agent.py`：在工具调用前检查技能钩子并执行

**实现要点**：
- 注入 `$SKILL_DIR` 环境变量
- 支持 matcher 匹配工具名
- 支持多个钩子按顺序执行
- 错误处理（钩子失败不阻止工具调用）

---

### 方案 B：转换为插件

将钩子逻辑转换为 Hermes 插件：

```python
# ~/.hermes/plugins/workflow-manager-hooks/__init__.py
def register(ctx):
    ctx.register_hook("pre_tool_call", pre_tool_call_handler)

def pre_tool_call_handler(tool_name, **kwargs):
    if tool_name in ["terminal", "delegate_task"]:
        # 执行钩子逻辑
        pass
```

**优点**：
- 使用现有插件系统
- 无需修改 Hermes 核心

**缺点**：
- 需要创建插件（非技能）
- 无法在 SKILL.md 中声明钩子

---

### 方案 C：手动触发（临时方案）

在需要时手动执行钩子脚本：

```bash
# 检测未完成工作流
bash ~/.hermes/skills/openclaw-imports/workflow-manager/hooks/user_prompt_submit.sh

# 工具调用前检查
bash ~/.hermes/skills/openclaw-imports/workflow-manager/hooks/pre_tool_use.sh
```

**适用场景**：
- 调试时验证钩子逻辑
- 紧急情况下手动触发

---

## 验证方法

### 验证钩子是否触发

```bash
# 1. 创建测试工作流
python ~/.hermes/skills/openclaw-imports/workflow-manager/actions/execute.py test --plan-only

# 2. 发送消息触发 UserPromptSubmit 钩子
# 预期：显示"检测到未完成工作流"

# 3. 调用 terminal 工具触发 PreToolUse 钩子
# 预期：显示"当前步骤"和约束清单
```

### 当前状态

- ❌ UserPromptSubmit 不触发
- ❌ PreToolUse 不触发
- ✅ 手动执行脚本可工作

---

## 相关文档

- `references/hooks-format.md` - Hermes 钩子配置格式规范
- `references/hooks-architecture.md` - 钩子架构说明
- `references/hooks-implementation.md` - 钩子实现详解

---

## 时间线

- **2026-05-12**：发现技能钩子架构断层，创建此文档
