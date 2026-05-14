# Empty Pending Instructions Bug

**日期**: 2026-05-13
**严重程度**: 高
**影响范围**: 所有拼接工作流执行

---

## 问题描述

execute.py返回`execution_required`状态，但`pending_instructions`只包含1个指令（发送完成通知），缺少实际的步骤执行指令。

---

## 现象

```python
# 预期返回
{
  "status": "execution_required",
  "pending_instructions": [
    {"step_id": "root_电力数据_1", "action": "execute_step", ...},
    {"step_id": "root_电力数据_2", "action": "execute_step", ...},
    ...  # 共21个步骤
  ]
}

# 实际返回
{
  "status": "execution_required",
  "pending_instructions": [
    {"action": "terminal", "command": "发送工作流完成通知"}  # 只有1个
  ]
}
```

---

## 失败案例

**工作流**: 资产收集流程（拼接工作流）
**展开步骤**: 21个（电力数据7 + 域名处理3 + 端口扫描3 + URL生成3 + URL分析5）
**实际执行**: 0个步骤被执行

**执行日志**（截断）：
```
[2026-05-13 16:56:34] [workflow-manager.executor] [INFO] [5/6] 返回执行计划
状态: execution_required
总步骤: 1
待执行指令数: 1
```

---

## 根本原因分析

**推测位置**: `executor.py`的`execute()`返回逻辑

可能原因：
1. executor只返回"工作流完成"的通知指令，未生成步骤执行指令
2. 步骤执行指令在代码内部流转，未传递到返回值
3. agent-pool匹配后，执行指令未正确传递回executor

---

## 状态计数不一致

**额外问题**: status.json中total_steps不一致

```json
{
  "progress": {
    "total_steps": 19  // ❌ 错误
  },
  "workflow": {
    "step_progress": "21/21"  // ✅ 正确
  }
}
```

---

## 临时排查方案

1. 查看execute.py第151-164行（execute()主入口返回）
2. 查看execute.py第730-751行（_execute_workflow_full()返回）
3. 检查agent_pool_client返回的pending_instructions格式
4. 验证executor是否正确读取pending_instructions

---

## 影响范围

**受影响场景**：
- 所有拼接工作流（type: branch）
- 所有包含子工作流的工作流
- 所有execution_required状态返回

**不受影响**：
- 直接执行的单步工作流（可能正常）

---

## 待修复

**修复优先级**: 高
**修复位置**: 待定位
**修复方法**: 待确定

---

## 相关文档

- `references/empty-instructions-bug-20260513.md`（已存在）
- `references/execution-required-state-handling.md`