# Hook触发机制完整文档

**版本**: v1.0.0  
**创建时间**: 2026-05-13  
**来源**: 工作流执行过程中Hook触发机制深度分析

---

## 一、Hook配置架构

### 1. Hook定义位置

**技能级别Hook**（workflow-manager）：
- 文件：`~/.hermes/skills/openclaw-imports/workflow-manager/SKILL.md`
- 配置方式：SKILL.md frontmatter 中的 `hooks:` 字段
- 脚本位置：`hooks/` 目录下的 `.sh` 文件

**Hermes全局Hook**：
- 文件：`~/.hermes/config.yaml`
- 当前状态：`hooks: {}`（未配置全局Hook）

### 2. Hook类型

| Hook类型 | 触发时机 | 配置方式 | 脚本文件 |
|---------|---------|---------|---------|
| UserPromptSubmit | 用户发送消息时 | SKILL.md hooks | user_prompt_submit.sh |
| PreToolUse | AI调用工具前 | SKILL.md hooks + matcher | pre_tool_use.sh |
| PostToolUse | AI调用工具后 | SKILL.md hooks | post_tool_use.sh |
| stop | 工作流停止时 | hooks/stop.sh | stop.sh |

---

## 二、Hook触发流程

### UserPromptSubmit Hook触发流程

```
用户发送消息
    ↓
Hermes 接收消息
    ↓
检测已激活技能的 hooks 配置
    ↓
发现 workflow-manager 技能已激活
    ↓
读取 SKILL.md hooks.UserPromptSubmit
    ↓
执行命令: bash $SKILL_DIR/hooks/user_prompt_submit.sh
    ↓
脚本执行逻辑:
    ├─ 查找运行中的工作流 (status.json)
    ├─ 检测 status.md 是否存在
    ├─ 不存在 → 自动生成 (execute.py --plan-only)
    └─ 显示执行计划前60行
    ↓
注入内容到 AI 上下文
    ↓
AI 看到未完成工作流的提示
```

**关键点**：
- `$SKILL_DIR` 是 Hermes 自动注入的环境变量
- Hook脚本有完整的路径信息
- 自动生成机制确保 status.md 存在

### PreToolUse Hook触发流程

```
AI 准备调用工具 (terminal/delegate_task)
    ↓
Hermes 检测工具调用
    ↓
匹配 PreToolUse matcher: "terminal|delegate_task"
    ↓
工具名匹配成功
    ↓
读取 SKILL.md hooks.PreToolUse
    ↓
执行命令: bash $SKILL_DIR/hooks/pre_tool_use.sh
    ↓
脚本执行逻辑:
    ├─ 查找运行中的工作流 (status.json)
    ├─ 强制检查 status.md 是否存在
    ├─ 不存在 → exit 1 阻断执行 ⭐
    ├─ 读取当前步骤 (从 status.json)
    ├─ 显示当前步骤名称
    ├─ 注入 status.md 前30行
    └─ 显示约束清单
    ↓
注入内容到工具调用上下文
    ↓
AI 看到当前步骤和约束
    ↓
执行工具调用
```

**关键点**：
- **matcher 机制**：只匹配特定工具（terminal|delegate_task）
- **阻断机制**：status.md 不存在时 exit 1，阻止工具调用
- **双重注入**：当前步骤 + status.md 前30行

### PostToolUse Hook触发流程

```
AI 完成工具调用
    ↓
工具返回结果
    ↓
Hermes 检测工具完成
    ↓
读取 SKILL.md hooks.PostToolUse
    ↓
执行命令: bash $SKILL_DIR/hooks/post_tool_use.sh
    ↓
脚本执行逻辑:
    ├─ 验证工具执行结果
    ├─ 更新状态（可选）
    └─ 记录日志（可选）
    ↓
AI 看到验证结果
```

---

## 三、Hook触发时间线（实际案例）

### 案例：资产收集流程（20260512）

```
时间线                Hook              触发原因              输出
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10:08:00           UserPromptSubmit   用户发送消息          显示未完成工作流提示
10:08:39           PreToolUse #1      调用 terminal         显示 execute.py 步骤约束
[execute.py 执行]
10:14:07           PreToolUse #2      调用 delegate_task    显示电力数据步骤约束
[子Agent执行电力数据]
10:17:12           PreToolUse #3      调用 delegate_task    显示域名处理步骤约束
[子Agent执行域名处理]
10:26:48           PreToolUse #4      调用 delegate_task    显示URL分析步骤约束
[子Agent执行URL分析]
10:26:49           stop              工作流完成            清理状态
```

### 触发统计

| Hook | 触发次数 | 触发时机 |
|------|---------|---------|
| UserPromptSubmit | 1 | 用户发送消息时 |
| PreToolUse | 4 | 每次工具调用前 |
| PostToolUse | 多次 | 每次工具调用后 |
| stop | 1 | 工作流完成时 |

---

## 四、Hook注入机制

### 1. 内容注入位置

**UserPromptSubmit**：
- 注入位置：AI上下文开头
- 内容：未完成工作流提示 + 执行计划前60行
- 效果：AI立即知道有未完成任务

**PreToolUse**：
- 注入位置：工具调用参数前
- 内容：当前步骤 + status.md 前30行 + 约束清单
- 效果：AI每次工具调用前都看到约束

**PostToolUse**：
- 注入位置：工具返回结果后
- 内容：验证结果 + 状态更新
- 效果：AI知道工具调用是否成功

### 2. 环境变量注入

Hermes 自动注入以下环境变量：

| 变量 | 说明 | 示例值 |
|------|------|---------|
| $SKILL_DIR | 技能目录路径 | ~/.hermes/skills/openclaw-imports/workflow-manager |
| $HERMES_HOME | Hermes根目录 | ~/.hermes |
| $SESSION_ID | 当前会话ID | session-xxx |

### 3. matcher 匹配机制

PreToolUse Hook的 matcher 配置：

```yaml
matcher: "terminal|delegate_task"
```

**匹配逻辑**：
- Hermes 检测工具调用名称
- 与 matcher 正则表达式匹配
- 匹配成功 → 执行Hook
- 匹配失败 → 跳过Hook

**效果**：
- 只在 terminal/delegate_task 调用前触发
- 其他工具调用（如 read_file）不触发
- 精准注入，避免过多干扰

---

## 五、Hook执行环境

### 1. 脚本执行方式

```bash
bash $SKILL_DIR/hooks/pre_tool_use.sh
```

**执行环境**：
- Shell: bash
- 工作目录: 当前会话工作目录
- 环境变量: Hermes注入的变量
- 输出: 捕获并注入到AI上下文

### 2. 脚本权限要求

```bash
chmod +x hooks/*.sh
```

**必须可执行**：
- user_prompt_submit.sh
- pre_tool_use.sh
- post_tool_use.sh
- stop.sh

### 3. 脚本依赖

**系统命令**：
- find: 查找 status.json
- grep: 过滤运行中的工作流
- python3: 执行 execute.py
- jq/json: 读取 JSON 文件

**Python脚本**：
- execute.py: 生成执行计划
- status.json: 读取当前步骤

---

## 六、Hook阻断机制 ⭐

### PreToolUse 的阻断设计

```bash
if [ ! -f "$WORKFLOW_DIR/status.md" ]; then
    echo "❌ 错误：必须先生成执行计划"
    exit 1  # ⭐ 阻断执行
fi
```

**阻断逻辑**：
1. 检测 status.md 是否存在
2. 不存在 → 输出错误信息
3. exit 1 → 返回非零退出码
4. Hermes 检测到非零退出码
5. **阻止工具调用**

**效果**：
- 强制要求先生成执行计划
- 防止 AI 绕过代码工具直接执行
- 类似"门禁"机制

---

## 七、Hook自动生成机制

### 双重保障

**UserPromptSubmit**：
```bash
if [ ! -f "$WORKFLOW_DIR/status.md" ]; then
    python3 execute.py "$WORKFLOW_NAME" --plan-only
fi
```

**PreToolUse**：
```bash
if [ ! -f "$WORKFLOW_DIR/status.md" ]; then
    echo "❌ 错误：必须先生成执行计划"
    exit 1
fi
```

**双重保障**：
- UserPromptSubmit：自动生成（容错）
- PreToolUse：强制检查（严格）

**效果**：
- AI直接执行 → UserPromptSubmit自动生成
- AI绕过UserPromptSubmit → PreToolUse阻断
- 确保status.md一定存在

---

## 八、Hook与status文件的关系

### status.md 生成时机

```
execute.py --plan-only
    ↓
生成 status.md（静态）
    ↓
Hook读取 status.md
    ↓
注入到 AI 上下文
```

### status.json 更新时机

```
工作流执行开始
    ↓
生成 status.json（动态）
    ↓
Hook读取 status.json
    ↓
获取当前步骤信息
    ↓
工作流步骤完成
    ↓
更新 status.json
```

### Hook读取顺序

**PreToolUse Hook**：
1. 读取 status.json → 获取当前步骤
2. 读取 status.md → 获取约束清单
3. 合并输出 → 注入到 AI

---

## 九、Hook触发时机详解

### UserPromptSubmit 触发条件

1. **技能已激活**：workflow-manager技能已加载
2. **hooks配置存在**：SKILL.md中有hooks.UserPromptSubmit
3. **用户发送消息**：任何消息都会触发

**不触发的情况**：
- 技能未激活
- hooks配置缺失
- 工作流已完成（无status.json）

### PreToolUse 触发条件

1. **技能已激活**：workflow-manager技能已加载
2. **matcher匹配**：工具名匹配 "terminal|delegate_task"
3. **工作流运行中**：有status.json且status="running"

**不触发的情况**：
- 技能未激活
- matcher不匹配（如调用read_file）
- 工作流未运行

### matcher 匹配逻辑

```python
# Hermes 内部逻辑（推测）
tool_name = "terminal"  # 或 "delegate_task"
matcher_pattern = "terminal|delegate_task"

if re.match(matcher_pattern, tool_name):
    execute_hook(hook_config)
```

---

## 十、Hook输出注入机制

### 输出捕获

```bash
# Hook脚本输出
echo "⚠️  当前步骤: XXX"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Hermes 捕获输出
stdout = subprocess.run(hook_command, capture_output=True)
```

### 注入位置

**UserPromptSubmit**：
- 注入到系统提示前
- 作为"工作流上下文"

**PreToolUse**：
- 注入到工具调用参数前
- 作为"工具调用约束"

### AI 接收方式

```
AI 收到的内容：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  当前步骤: 电力数据
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 执行计划前30行...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

（然后是工具调用参数）
```

---

## 十一、Hook执行性能分析

### 执行时间

| Hook | 平均耗时 | 主要操作 |
|------|---------|---------|
| UserPromptSubmit | <1秒 | 查找文件 + 显示内容 |
| PreToolUse | <1秒 | 读取JSON + 显示内容 |
| PostToolUse | <1秒 | 验证结果 |

### 性能影响

- **正面**：注入约束，防止错误执行
- **负面**：每次工具调用前增加<1秒延迟
- **总体**：可接受（18分钟工作流，Hook总耗时<5秒）

---

## 十二、Hook故障排查

### 不触发的原因

1. **技能未激活**
   - 解决：加载技能 `skill_view(name='workflow-manager')`

2. **脚本权限不足**
   - 解决：`chmod +x hooks/*.sh`

3. **status.json不存在**
   - 解决：启动工作流

4. **matcher不匹配**
   - 解决：检查工具名是否匹配

### 部分触发的原因

1. **只触发UserPromptSubmit**
   - 原因：PreToolUse matcher不匹配
   - 解决：检查工具调用名称

2. **PreToolUse不触发**
   - 原因：工具名不在matcher列表
   - 解决：更新matcher配置

---

## 十三、Hook配置完整性检查

### 检查清单

执行以下检查确保Hook配置完整：

- [ ] SKILL.md中声明了所有需要的Hook
- [ ] hooks目录中存在对应的.sh脚本
- [ ] 所有脚本都有执行权限（chmod +x）
- [ ] matcher配置正确（如PreToolUse）
- [ ] 脚本路径使用$SKILL_DIR变量

### 配置一致性验证

**SKILL.md声明**：
```yaml
hooks:
  UserPromptSubmit: ...
  PreToolUse: ...
  PostToolUse: ...
```

**hooks目录脚本**：
```bash
ls hooks/
# 应该看到：
# user_prompt_submit.sh
# pre_tool_use.sh
# post_tool_use.sh
```

**不一致的情况**：
- SKILL.md声明了但脚本不存在 → Hook无法执行
- 脚本存在但SKILL.md未声明 → Hook不会触发 ⚠️

---

## 十四、总结

### Hook触发机制本质

**三层触发**：
1. **配置层**：SKILL.md hooks配置
2. **匹配层**：matcher正则匹配
3. **执行层**：bash脚本执行

**双重注入**：
1. **内容注入**：输出捕获并注入到AI上下文
2. **环境注入**：$SKILL_DIR等环境变量

**三重保障**：
1. **规范层**：SKILL.md规定执行流程
2. **代码层**：Hook脚本强制检查
3. **阻断层**：exit 1阻止违规操作

### Hook触发流程总结

```
用户消息 → UserPromptSubmit → 检测未完成工作流
AI工具调用 → matcher匹配 → PreToolUse → 注入约束
工具完成 → PostToolUse → 验证结果
工作流完成 → stop → 清理状态
```

### Hook核心价值

1. **注意力操控**：每次工具调用前都看到约束
2. **强制规范化**：阻断机制防止违规操作
3. **自动化保障**：自动生成status.md
4. **执行可追溯**：Hook触发有明确记录

### Hook是工作流标准化的核心机制！

---

## 相关文档

- `references/hooks-architecture.md` - Hook架构说明
- `references/hooks-implementation.md` - Hook实现文档
- `references/workflow-data-flow-patterns.md` - 工作流数据流向设计模式
- `SKILL.md` - 工作流管理技能主文档
