# Workflow Manager v6.4 架构重构

## 重构原因

**问题发现**：2026-05-13 资产搜集工作流执行时，AI 绕过了 workflow-manager 机制，直接读取 WORKFLOW.md 执行，导致：
- Hook 未触发
- 计划文件未生成
- 节点状态未追踪
- agent-pool 未使用

**根本原因**：代码尝试分解任务，但任务分解不准确，AI 不信任代码输出，直接绕过整套机制。

---

## 架构原则

**核心理念：代码静态 + AI 动态**

| 代码静态层 | AI 动态层 |
|-----------|----------|
| 路径索引 | 读取 WORKFLOW.md |
| 文件验证 | 分解任务 |
| JSON 解析 | 生成 status.md |
| 初始模板生成 | 调用 agent-pool |
| | 执行 pending_instructions |
| | 更新状态 |

---

## 关键改动

### 1. execute.py 简化

**删除**：任务分解逻辑、--plan-only 模式
**保留**：--init 模式（生成空 status.json）、路径索引

**新流程**：
```bash
python actions/execute.py <工作流名> --init
# 生成空 status.json，等待 AI 分解任务
```

### 2. 新增 Hook：workflow-ai-remind

**事件**：pre_llm_call
**功能**：
- 检测活动工作流
- 提醒 AI 读取 WORKFLOW.md
- 提醒 AI 调用 agent_pool_client

### 3. Hook 安装机制验证

**正确机制**：
- 源文件：`skills/.../hooks/workflow-*/`
- 映射：符号链接到 `~/.hermes/agent-hooks/`
- 安装：`bash hooks-install.sh`

**验证命令**：
```bash
ls -la ~/.hermes/agent-hooks/workflow-*.sh
# 应该全部是符号链接（lrwxrwxrwx）
```

### 4. SKILL.md 优化

**优化方向**：使用者视角，不是开发者视角
**删除内容**：版本更新说明、架构陷阱、Bug 追踪
**压缩效果**：14620 字符 → 2765 字符（-81%）

---

## 执行流程对比

**旧流程（v6.3）**：
```
execute.py --plan-only → executor 分解任务 → 返回 pending_instructions
```

**新流程（v6.4）**：
```
execute.py --init → 生成空模板 → AI 分解任务 → AI 调用 agent-pool
```

---

## 风险与应对

| 风险 | 应对 |
|------|------|
| AI 不遵守新流程 | Hook 注入提醒 |
| 工作流定义不规范 | 提供模板和验证工具 |
| 旧代码依赖 executor 分解 | 逐步迁移，保留备份 |

---

## 参考文档

- `SKILL.md.bak_before_optimization_20260513_202412`：优化前备份
- `.backup_refactor_20260513/`：代码备份
