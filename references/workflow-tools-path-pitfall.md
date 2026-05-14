# Workflow-Tools Path Pitfall

## 问题

SKILL.md 中引用的 workflow-tools.js 路径不存在：

```
❌ 错误路径：~/.hermes/skills/openclaw-imports/workflow-manager/src/workflow-tools.js
✅ 正确路径：~/.hermes/skills/openclaw-imports/bk/workflow-manager/src/workflow-tools.js
```

## 原因

- 当前使用的是 `bk/` 目录下的备份版本
- 主版本工作流管理器尚未迁移完成

## 解决方案

使用正确的路径：

```bash
node ~/.hermes/skills/openclaw-imports/bk/workflow-manager/src/workflow-tools.js read "工作流名称"
```

## 已知限制

| 命令 | 状态 | 说明 |
|------|------|------|
| `read` | ✅ 可用 | 读取工作流定义 |
| `status` | ✅ 可用 | 查询工作流状态 |
| `list` | ✅ 可用 | 列出所有工作流 |
| `update` | ❌ 不可用 | 文档中有但未实现 |

## 发现时间

2026-05-06

## 影响范围

所有调用 workflow-tools.js 的命令
