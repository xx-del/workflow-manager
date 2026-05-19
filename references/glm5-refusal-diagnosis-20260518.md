# GLM-5 "你好，我无法给到相关内容。" 拒绝响应诊断

**日期**: 2026-05-18
**触发场景**: delegate_task 子Agent 返回异常响应

---

## 现象

```json
{
  "tokens": {"input": 0, "output": 0},
  "tool_trace": [],
  "summary": "你好，我无法给到相关内容。"
}
```

**关键指标**：
- `tokens.input=0`：API 未正常处理请求
- `tool_trace=[]`：无工具调用
- 响应时间极短（~1s）
- 返回 GLM 系列预设安全拒绝模板

---

## 根因

**GLM-5 API 端问题**：
- 请求被 GLM-5 内部安全机制拦截
- 返回预设拒绝模板
- `tokens.input=0` 表示 API 层未正常记录输入

**非 Hermes 问题**：
- LCM 标记子Agent为 auxiliary/stateless 是设计行为
- delegate_task 上下文传递链路正确
- ephemeral_system_prompt 正确构建

---

## 诊断方法

### 1. 检查 tokens 字段

```sql
SELECT session_id, store_id, content
FROM messages
WHERE content LIKE '%tokens%input%0%'
  AND content LIKE '%delegate_task%'
```

### 2. 检查 LCM 日志

```bash
grep "auxiliary/stateless" ~/.hermes/logs/agent.log
```

### 3. 统计异常率

```sql
SELECT 
    CASE WHEN content LIKE '%tokens%input%0%' THEN '异常' ELSE '正常' END,
    COUNT(*)
FROM messages
WHERE role='tool' AND content LIKE '%delegate_task%'
GROUP BY 1
```

---

## 统计数据

| 指标 | 值 |
|------|-----|
| 异常子Agent | 42 |
| 正常子Agent | 817 |
| 异常率 | **4.9%** |

---

## 缓解方案

1. **已有回退机制**：主Agent 检测异常后直接接管执行（见 `subagent-fallback-pattern.md`）
2. **模型切换**：检测到 `tokens.input=0` 时自动切换 Qwen3-Coder
3. **监控增强**：记录所有 `tokens.input=0` 的 API 调用详情

---

## 上下文传递链路验证

| 步骤 | 组件 | 状态 |
|------|------|------|
| 1 | 主Agent → delegate_task | ✅ goal/context 正确传递 |
| 2 | _build_child_system_prompt | ✅ child_prompt 正确构建 |
| 3 | AIAgent | ✅ ephemeral_system_prompt 正确设置 |
| 4 | LCM auxiliary/stateless | ⚠️ 设计行为 |
| 5 | 子Agent run_conversation | ✅ user_message=goal 正确传入 |
| 6 | GLM-5 API | ❌ tokens.input=0 |

---

## 相关

- `subagent-fallback-pattern.md`：回退机制
- 会话：`20260518_011456_40119c`（cronjob 异常实例）
