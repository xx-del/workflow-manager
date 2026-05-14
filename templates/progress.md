# 工作流执行日志：{workflow_name}

**创建时间**: {timestamp}
**工作流版本**: {version}

---

## 会话记录

### {session_timestamp} - 会话开始

**执行环境**：
- 工作流名称：{workflow_name}
- 执行模式：{execution_mode}
- 总步骤数：{total_steps}

**初始状态**：
- 已完成步骤：0
- 待执行步骤：{total_steps}

---

## 步骤执行记录

### 步骤 1: {step_name}

**执行时间**: {step_timestamp}
**状态**: {step_status}
**耗时**: {duration} 秒

**执行命令**:
```bash
{command}
```

**执行结果**:
```
{output}
```

**发现/问题**:
- {findings}

---

### 步骤 2: ...

---

## 错误记录

| 错误 | 步骤 | 尝试 | 解决方案 |
|------|------|------|----------|
| (执行时填写) | | | |

---

## 统计信息

- ✅ 成功步骤：{success_count}
- ❌ 失败步骤：{failed_count}
- ⏭️ 跳过步骤：{skipped_count}
- ⏱️ 总耗时：{total_duration} 秒
