# W 任务体系实现记录

## 背景

**问题**：工作流执行时总是不稳定，出现奇怪的问题

**根因**：L1 任务等级与工作流执行不匹配
- L1 注入指令过于简略（22行 vs 技能450行）
- L1 定义与工作流特点冲突
- 缺少强制检查机制

## 解决方案

**核心思路**：工作流作为独立的 W 任务体系，硬编码绑定 workflow-manager 技能

**优势**：
- 不污染 L 体系
- 技能绑定精准
- 约束集中管理
- 实现简单（~20行代码）

## 代码修改

### 1. analyzer.py - 6处修改

所有 `detect_workflow_local()` 返回的地方，`task_level` 从 `"L1"` 改为 `"W"`

**修改位置**：
- 第78行：完全匹配
- 第108行：包含"工作流"
- 第129行：包含"流程"
- 第145行：模糊匹配名称
- 第162行：模糊匹配标签

### 2. constants.py - 新增W任务绑定

```python
SKILL_BINDINGS = {
    "W": ["workflow-manager"],  # 工作流任务 - 硬编码绑定
    "L2": ["deep-thinking"],
    "L3": ["deep-thinking", "openclaw-behavior-plan"],
    "L4": ["planning-with-files", "agent-pool"],
}
```

### 3. context_builder.py - 简化执行指令

**修改前**（22行，4个步骤，包含约束）
**修改后**（5行，简短直接）

```python
def build_workflow_directive(workflow_name: str) -> str:
    return f"""【工作流任务】

检测到工作流：{workflow_name}

已自动绑定 workflow-manager 技能。

请严格按照技能中的步骤执行（步骤0-6），技能内包含完整的约束和检查机制。
"""
```

## 设计原则

### 为什么不用 W0/W1/W2/W3 体系？

**用户纠正**：
> "只需要单一的W任务，硬编码绑定工作流技能就可以了，没必要设计复杂化。工作流技能会自己处理复杂的任务。"

**教训**：
- 不要过度设计
- 单一 W 任务足够
- 技能内部处理复杂性

### 为什么不用 L1？

| 维度 | L1 原始定义 | 工作流特点 |
|-----|-----------|-----------|
| 复杂度 | 简单（查看信息） | 复杂（多步骤、多节点） |
| 执行方式 | 直接执行 | 需要严格流程（步骤0-6） |
| 约束要求 | 无特殊约束 | 强约束（agent-pool、禁止行为） |
| 技能绑定 | 无或简单 | 必须绑定 workflow-manager |

**结论**：工作流不是 L1，应该是独立的 W 任务

## 验证

修改后需要重启 Gateway 使生效：

```bash
hermes gateway restart
```

## 影响范围

- L 体系保持纯净，不受影响
- W 任务独立体系，专门处理工作流
- workflow-manager 技能成为工作流执行的唯一权威

## 文件路径

- `~/.hermes/plugins/soul-context-injector/analyzer.py`
- `~/.hermes/plugins/soul-context-injector/constants.py`
- `~/.hermes/plugins/soul-context-injector/context_builder.py`

## 修改日期

2026-05-06
