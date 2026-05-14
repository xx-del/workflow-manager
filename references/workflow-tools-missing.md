# workflow-tools.js 文件缺失问题

## 问题描述

workflow-manager 技能文档中引用的 `workflow-tools.js` 文件不存在：

```bash
node ~/.hermes/skills/openclaw-imports/workflow-manager/src/workflow-tools.js read "资产收集流程"
# Error: Cannot find module '/home/kali/.hermes/skills/openclaw-imports/workflow-manager/src/workflow-tools.js'
```

## 解决方案

### 方法一：直接读取工作流文件（推荐）

使用 Hermes 内置工具直接读取工作流定义：

```bash
# 读取工作流定义
read_file path="~/.hermes/workflows/<工作流名称>/WORKFLOW.md"
read_file path="~/.hermes/workflows/<工作流名称>/_index.yaml"
```

### 工作流目录结构

```
~/.hermes/workflows/<工作流名称>/
  ├── WORKFLOW.md      # 详细执行步骤（人类可读）
  ├── _index.yaml      # 节点定义和依赖关系（机器可读）
  └── status.json      # 执行状态
```

### 方法二：使用 Python 工具

如果需要编程方式访问工作流，使用 Python 模块：

```bash
# 节点验证
python3 actions/validate_node.py <workflow_path> <node_id>

# 工作流校验
python3 actions/validate_workflow.py <workflow_path>

# 展开串联节点
python3 actions/expand_workflow.py <workflow_path>
```

## 注意事项

- workflow-tools.js 可能是 v3.x 时代的遗留引用
- v4.0 采用 AI-Native 架构，推荐直接读取文件
- 所有 workflow-manager 的 Python 工具都在 `actions/` 目录

## 相关文件

- [references/troubleshooting.md](./troubleshooting.md) - 完整故障排查指南
- [references/migration-v4.md](./migration-v4.md) - v3 到 v4 迁移指南
