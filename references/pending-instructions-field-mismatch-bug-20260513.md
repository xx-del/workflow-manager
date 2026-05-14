# pending_instructions 字段名不匹配 Bug

**日期**: 2026-05-13
**严重程度**: 🔴 高
**状态**: 🔧 待修复
**影响范围**: 所有工作流（拼接、断点、普通）

---

## 问题定位

**根因文件**: `src/core/executor.py`
**根因行号**: 第 1158 行
**根因代码**: 字段名不匹配

```python
# ❌ 错误代码（第 1158 行）
instructions = plan.get('instructions', [])

# ✅ 正确代码
instructions = plan.get('pending_instructions', plan.get('instructions', []))
```

---

## 数据流追踪

```
[1] execute() 
    ↓
[2] _execute_workflow()
    ↓ 遍历 plan['serial']
[3] _execute_step()
    ↓
[4] _call_agent_pool()
    ↓
[5] agent_pool_client.execute_full()
    ↓ 返回 {"pending_instructions": [...]}
[6] _call_agent_pool()  ← 读取 'instructions'（错误！）
    ↓ plan.get('instructions', []) → []
[7] 检测到 instructions 为空
    ↓ 返回 {'success': True, 'instructions': []}
[8] _execute_step()
    ↓ result.get('pending_instructions', result.get('instructions', [])) → []
[9] _execute_workflow()
    ↓ if result.get('instructions'): → [] 为 falsy → 跳过
[10] all_instructions 只有 finalize 指令
```

---

## 现象

```python
# 预期返回（21 个步骤）
{
  "status": "execution_required",
  "pending_instructions": [
    {"step_id": "root_电力数据_1", "action": "delegate_task", ...},
    {"step_id": "root_电力数据_2", "action": "delegate_task", ...},
    ...  # 共 21 个
  ]
}

# 实际返回（只有 1 个 finalize 指令）
{
  "status": "execution_required",
  "pending_instructions": [
    {"action": "terminal", "command": "发送工作流完成通知"}
  ]
}
```

---

## 影响范围

| 工作流类型 | 是否受影响 | 说明 |
|-----------|----------|------|
| 拼接工作流 | ✅ 受影响 | 所有子工作流步骤指令丢失 |
| 断点工作流 | ✅ 受影响 | 非断点步骤指令丢失 |
| 普通工作流 | ✅ 受影响 | 所有步骤指令丢失 |

---

## 修复方案

### 方案 A：修复字段名匹配（推荐）

**修改位置**: `src/core/executor.py` 第 1158 行

```python
# 修复前
instructions = plan.get('instructions', [])

# 修复后
instructions = plan.get('pending_instructions', plan.get('instructions', []))
```

**优点**:
- 最小修改，直接修复根因
- 兼容 `_execute_step()` 的逻辑
- 无需修改 agent_pool_client

**缺点**:
- 需要重启 Gateway
- 需要测试所有工作流

---

### 方案 B：agent_pool_client 同时返回两个字段名

**修改位置**: `src/core/agent_pool_client.py` 第 172 行

```python
result = {
    "success": True,
    "pending_instructions": instructions,
    "instructions": instructions,  # 新增：兼容旧代码
}
```

**优点**:
- 向后兼容
- 不需要修改 executor.py

**缺点**:
- 冗余字段
- 治标不治本

---

### 方案 C：统一字段命名规范

**修改范围**: 所有使用 `pending_instructions` 和 `instructions` 的代码

**规范**: 统一使用 `pending_instructions` 作为标准字段名

**优点**:
- 彻底解决命名混乱
- 代码更清晰

**缺点**:
- 修改范围大
- 需要全面测试

---

## 推荐修复

**优先级**: 方案 A > 方案 B > 方案 C

**理由**: 方案 A 最小修改，直接修复根因，风险可控。

---

## 验证步骤

1. 修改 `executor.py` 第 1158 行
2. 重启 Gateway
3. 执行测试：
   ```bash
   python execute.py 资产收集流程 --date-start 20260513
   ```
4. 检查返回的 `pending_instructions` 数量是否正确

---

## 相关代码位置

| 文件 | 行号 | 说明 |
|------|------|------|
| `src/core/executor.py` | 1158 | ❌ 字段名不匹配（根因） |
| `src/core/executor.py` | 713 | ✅ 正确读取（兼容两个字段名） |
| `src/core/agent_pool_client.py` | 172 | 返回 `pending_instructions` 字段 |
| `src/core/agent_pool_client.py` | 381 | 构建单条 delegate_task 指令 |

---

## 历史记录

- 2026-05-13: 发现 Bug，定位根因
- 待修复: 修改 executor.py 第 1158 行
