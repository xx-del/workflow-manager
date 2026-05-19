# execute.py --init 空模板问题

**发现日期**: 2026-05-18
**影响**: 工作流初始化后需手动构建步骤节点

---

## 问题描述

`python actions/execute.py <工作流名> --init` 创建的 status.json 中 nodes 为空对象 `{}`，不包含任何步骤。

## 实际输出

```json
{
  "workflow": "月报生成",
  "status": "initialized",
  "workflow_dir": "/home/kali/.hermes/workflows/月报生成",
  "nodes": {},
  "created_at": "2026-05-18T14:25:24.187903",
  "updated_at": "2026-05-18T14:25:24.187926"
}
```

## 期望行为

--init 应解析 WORKFLOW.md，自动生成步骤节点：

```json
{
  "nodes": {
    "step1_prepare": {
      "name": "准备阶段",
      "description": "参数解析 + 数据库更新检查",
      "status": "pending",
      "type": "action",
      "depends_on": []
    },
    ...
  }
}
```

## 临时解决方案

手动根据 WORKFLOW.md 构建 status.json：

1. 读取 WORKFLOW.md，提取步骤名称和描述
2. 为每个步骤创建节点，包含：name, description, status(pending), type, depends_on
3. type 映射：`read_and_execute` → 保留原值，`breakpoint` → breakpoint，其他 → action
4. depends_on：串行工作流前一步骤

## 影响范围

所有使用 `execute.py --init` 的工作流都会遇到此问题。当前需要主 AI 手动构建节点，增加上下文消耗和出错概率。

## 建议修复

execute.py 的 --init 逻辑应：
1. 读取 WORKFLOW.md
2. 解析 `### 步骤 N:` 格式的标题
3. 提取步骤名称、描述、类型
4. 自动填充 nodes