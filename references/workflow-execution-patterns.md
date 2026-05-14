# 工作流执行实操模式

## 工作流发现与执行全流程

### 标准执行流程

```
1. 加载技能: skill_view(name="workflow-manager")
2. 发现工作流: ls ~/.hermes/workflows/
3. 读取定义: cat ~/.hermes/workflows/<名称>/WORKFLOW.md
4. 分析步骤: 依赖关系、串行/并行、条件步骤
5. 匹配 Agent: agent-pool execute "<任务描述>" --capabilities <能力>
6. 执行步骤: delegate_task(goal=..., context=..., toolsets=[...])
7. 验证结果: 确认步骤输出
8. 生成报告: 汇总所有步骤结果
```

### Agent 匹配方法

**推荐：使用 `execute` 命令**

```bash
python ~/.hermes/skills/openclaw-imports/agent-pool/bin/agent-pool execute "验证输入文件是否存在且非空" --capabilities cli_execution
```

返回匹配策略和 Agent 信息，比 `match` 更稳定。

**映射表：能力 → 工具集**

| 能力 | 工具集 |
|------|--------|
| cli_execution | terminal |
| web_research | web, browser |
| security | terminal, file |
| data_analysis | terminal, file |

### 条件步骤处理

工作流中某些步骤有条件执行逻辑（如"依赖不存在则安装"）：

```
步骤 3: 检查依赖 → 依赖存在？
  ├─ 是 → 跳过步骤 4、5（安装步骤）
  └─ 否 → 执行步骤 4（安装依赖）→ 执行步骤 5（安装浏览器）
```

**判断规则**：当前步骤的验证结果显示前置条件已满足时，标记后续安装步骤为"跳过"而非"跳过"。

### delegate_task 构造模板

```json
{
  "goal": "## 任务\n<具体任务描述>\n\n## 你的角色\n你是一个 cli-executor\n\n## 执行指令\n```bash\n<WORKFLOW.md 中定义的命令>\n```\n\n## 验证要求\n1. <验证条件>",
  "context": "工作流：<名称>\n步骤：<n>/<total>",
  "toolsets": ["terminal"]
}
```

### 步骤合并优化

对于简单、无依赖的验证步骤（如步骤 9-12），可合并到一次 delegate_task 调用中执行，减少 Agent 开销。

**合并条件**：
- 步骤间无复杂依赖
- 步骤均为简单 CLI 命令
- 步骤不会影响彼此的输出

**不宜合并的情况**：
- 核心执行步骤（如步骤 8 凭证检测）
- 步骤间有数据依赖
- 需要单独验证的步骤
