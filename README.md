# Workflow Manager

AI-Native 工作流管理系统 - 为 Hermes Agent 提供智能工作流编排能力。

## 特性

- **AI-Native 设计**: 工作流定义使用自然语言，AI 自动解析执行
- **智能展开**: 自动处理分支、心跳、拼接等复杂工作流类型
- **约束注入**: Hook 机制自动注入执行约束，确保 AI 遵守执行规范
- **Agent Pool 集成**: 支持并行执行、任务分发、Handoff 接力
- **状态追踪**: 实时进度记录、断点恢复、异常检测

## 核心组件

```
src/
├── core/           # 核心执行引擎
│   ├── executor.py       # 主执行器
│   ├── analyzer.py       # 工作流分析器
│   ├── expander.py       # 工作流展开器
│   └── agent_pool_client.py  # Agent Pool 客户端
├── extractor/      # 工作流提取器（AI 增强）
├── optimizer/      # 工作流优化器
├── validator/      # 工作流验证器
├── tools/          # 工具集（loader, status, history）
└── utils/          # 工具函数

hooks/              # Hook 机制（约束注入、进度追踪）
scripts/            # 辅助脚本
templates/          # 工作流模板
references/         # 设计文档与最佳实践
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 安装 Hooks

```bash
./hooks-install.sh
```

### 定义工作流

创建 `WORKFLOW.md` 文件：

```yaml
---
name: 示例工作流
type: serial
---

## 步骤

### 1. 步骤一
- 命令: echo "Hello"
- 验证: 检查输出

### 2. 步骤二
- 命令: echo "World"
- 依赖: 步骤一
```

### 执行工作流

通过 Hermes Agent 调用：

```python
from workflow_manager import WorkflowManager

wm = WorkflowManager()
result = wm.execute("/path/to/workflow")
```

## 工作流类型

| 类型 | 说明 | 使用场景 |
|------|------|----------|
| serial | 串行执行 | 步骤有依赖关系 |
| parallel | 并行执行 | 独立任务同时执行 |
| branch | 分支节点 | 拼接子工作流 |
| heartbeat | 心跳触发 | 长时间运行任务 |

## Hook 机制

Hook 自动注入执行约束，确保 AI 遵守规范：

- **workflow-context**: 注入约束到 status.md
- **workflow-progress**: 追踪执行进度
- **workflow-step-check**: 验证步骤完成
- **workflow-cleanup**: 清理会话标记

## 设计文档

`references/` 目录包含详细设计文档：

- 执行架构: `execution-architecture.md`
- Hook 机制: `hermes-dual-hook-mechanism-20260514.md`
- 约束注入: `hook-constraint-injection-mechanism.md`
- 最佳实践: `execution-best-practices.md`

## 开发

### 运行测试

```bash
pytest tests/
```

### 代码规范

- Python 3.8+
- 类型注解
- 文档字符串

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request。

## 相关项目

- [Hermes Agent](https://github.com/nousresearch/hermes) - AI Agent 框架
- [Agent Pool](https://github.com/openclaw/agent-pool) - Agent 池管理系统
