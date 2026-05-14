# workflow-tools.js 缺失绕过方案

> 会话: 2026-05-09 凭证检测工作流执行
> 发现者: AI Agent

## 问题

调用 `node workflow-tools.js` 报错：
```
Error: Cannot find module '/home/kali/.hermes/skills/openclaw-imports/workflow-manager/src/workflow-tools.js'
```

## 原因

workflow-tools.js 文件尚未创建，属于技能目录下缺失的工具文件。

## 影响范围

| 工具函数 | 用途 | 状态 |
|---------|------|------|
| `readWorkflow(name)` | 读取工作流定义 | ❌ 不可用 |
| `getStatus(name)` | 查询工作流状态 | ❌ 不可用 |
| `updateStatus(name, data)` | 更新工作流状态 | ❌ 不可用 |
| `listWorkflows()` | 列出所有工作流 | ❌ 不可用 |

## 绕过方案

AI 执行时可使用 Hermes 内置工具替代：

| 原工具调用 | 替代方案 |
|-----------|---------|
| `listWorkflows()` | `search_files(path="~/.hermes/workflows", pattern="WORKFLOW.md")` |
| `readWorkflow(name)` | `read_file(path="~/.hermes/workflows/{name}/WORKFLOW.md")` |
| `getStatus(name)` | `read_file(path="~/.hermes/workflows/{name}/status.json")` |
| `updateStatus(name, data)` | `write_file(path="~/.hermes/workflows/{name}/status.json", content=json_str)` |

## 示例

**场景**: 执行凭证检测工作流

```
步骤1: 列出工作流
- 原方案: node workflow-tools.js list
- 绕过方案: search_files(path="~/.hermes/workflows", pattern="WORKFLOW.md")

步骤2: 读取工作流定义
- 原方案: node workflow-tools.js read "凭证检测"
- 绕过方案: read_file(path="~/.hermes/workflows/凭证检测/WORKFLOW.md")

步骤3: 更新状态
- 原方案: node workflow-tools.js update "凭证检测" '{"status":"completed"}'
- 绕过方案: write_file(path="~/.hermes/workflows/凭证检测/status.json", content='...')
```

## 验证方式

```bash
ls -la ~/.hermes/skills/openclaw-imports/workflow-manager/src/workflow-tools.js
```

如果文件不存在，使用绕过方案。

## 注意事项

- 此问题仅影响 Node.js 工具调用
- 不影响 AI 原生执行能力
- AI 可直接使用 Hermes 内置工具完成工作流管理
- 工作流执行（delegate_task）不受影响

## 后续行动

创建 workflow-tools.js 文件，或更新 SKILL.md 说明直接使用 Hermes 内置工具。
