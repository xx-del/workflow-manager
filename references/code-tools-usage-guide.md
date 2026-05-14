# workflow-manager 代码工具使用指南

## 重要定位

**技能文档是使用说明书**：告诉你如何调用代码执行功能，而非解释代码机制。

---

## 可直接执行的代码工具

| 工具 | 命令 | 功能 | 何时使用 |
|------|------|------|----------|
| 获取执行计划 | `python actions/execute.py <名称> --plan-only` | 加载、展开、分析依赖、返回指令 | **执行前必须调用** |
| 完成工作流 | `python actions/complete.py <名称>` | 停止心跳、生成报告 | 工作流完成后 |
| 心跳监控 | `python actions/heartbeat-monitor.py` | 检测假死工作流 | cronjob 定时执行 |
| 验证工作流 | `python actions/validate.py <名称>` | 检查定义完整性 | 创建工作流后 |

---

## 正确执行流程（必须严格遵守）

**步骤 1：获取执行计划（必须）**

```bash
python actions/execute.py <工作流名称> --plan-only --json
```

返回：pending_instructions（待执行指令列表）

**步骤 2：执行 pending_instructions**

逐个调用 delegate_task 执行指令

**步骤 3：完成工作流**

```bash
python actions/complete.py <工作流名称>
```

---

## 代码自动完成的功能

主AI **不需要** 自己实现以下功能：

| 功能 | 代码实现位置 |
|------|-------------|
| 加载工作流 | loader.load() |
| 展开嵌套节点 | expander.expand() |
| 依赖分析 | analyzer.analyze() |
| 拓扑排序 | analyzer._calculate_levels() |
| 循环依赖检测 | analyzer.detect_circular_dependency() |
| 并行组识别 | analyzer._find_parallel_groups() |
| 生成 status.md | executor.generate_execution_plan_md() |
| Agent 能力匹配 | agent_pool_client.execute_full() |
| Handoff 处理 | agent_pool_client._build_instructions() |

---

## 主AI 必须执行的操作

| 操作 | 说明 | 如何执行 |
|------|------|----------|
| 执行 pending_instructions | 调用 delegate_task | delegate_task(goal, context) |
| 更新追踪状态 | 步骤完成后更新 | executor.update_step_status() 或修改 status.json |
| 汇总结果 | 收集执行结果 | 自己整理 |
| 完成工作流 | 停止心跳 | python actions/complete.py <名称> |

---

## 常见错误模式

| 错误 | 正确做法 |
|------|----------|
| 自己读取 _index.yaml | 使用 execute.py --plan-only |
| 自己判断步骤顺序 | 使用 execute.py 返回的计划 |
| 直接调用 delegate_task | 先获取 pending_instructions |
| 自己管理 status.json | 使用 execute.py 自动生成的 status.md |

---

## 关键发现（2026-05-11）

### 代码实现清单

- executor.py：1113 行，工作流编排
- agent_pool_client.py：438 行，agent-pool 调用
- analyzer.py：301 行，依赖分析、拓扑排序
- loader.py：212 行，工作流加载
- execute.py：125 行，CLI 入口

### agent_pool_client 功能

execute_full() 方法自动完成：
1. Agent 能力匹配
2. Handoff 检测和处理（注入到 context）
3. Feedback 回传（触发 Evolver）
4. 心跳更新指令注入

### 分析器功能

analyzer.analyze() 自动完成：
1. 构建依赖图
2. 拓扑排序（Kahn 算法）
3. 循环依赖检测（DFS）
4. 并行组识别