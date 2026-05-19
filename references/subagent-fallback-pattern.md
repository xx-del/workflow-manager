# Agent 异常响应回退模式

## 场景
Agent（包括主Agent和子Agent）返回异常内容（如"无法给到相关内容"、"你好，我无法给到相关内容"等空泛回复）。

**触发场景**：
- 子Agent（delegate_task）
- 主Agent正常会话
- 飞书会话
- Cronjob 会话

## 问题特征

异常响应的共同特征：
- 空泛回复（"无法给到相关内容"）
- tokens.input = 0, tokens.output = 0（子Agent场景）
- tool_trace = []（未执行任何工具）
- duration_seconds 极短（通常 < 2s）
- api_calls 有值但无实际输出

## 根因分析（2026-05-18 更新）

### 发现1：GLM-5 安全过滤循环
- 异常响应是 GLM 系列预设的安全拒绝模板
- **一旦触发，形成循环**：后续多次用户提问全部返回相同拒绝短语
- 用户换不同问题问，模型仍返回相同拒绝

### 发现2：两种触发场景

| 场景 | 特征 | 原因 |
|------|------|------|
| **主会话** | tokens 有值，但返回拒绝 | GLM-5 内部安全过滤被触发 |
| **子Agent** | tokens.input=0, output=0 | 上下文传递失败，无上下文直接返回拒绝 |

### 发现3：API 本身正常
- 直接 API 调用测试全部通过
- "漏扫"等敏感词未触发过滤
- 上下文长度 900+ tokens 未触发
- 问题与 Gateway 内部状态相关

### 发现4：异常触发规律
- 异常**总是紧跟正常消息**（tool 结果或用户消息）
- 前一条消息正常，后一条突然异常
- 无法通过消息内容预测触发

## 模式

### 识别异常
Agent返回异常特征：
- 空泛回复（"无法给到相关内容"）
- tokens.input = 0, tokens.output = 0
- tool_trace = []（未执行任何工具）
- 响应时间异常短
- 响应内容是固定的 13 字符拒绝模板

### 主Agent回退流程
```
主Agent返回异常
     ↓
[1] 检测异常（空泛内容 + 固定模板）
     ↓
[2] 切换模型（推荐 Qwen3-Coder）或重新发起请求
     ↓
[3] 继续执行任务
```

### 子Agent回退流程
```
子Agent返回异常
     ↓
[1] 主AI识别异常（tokens.input=0 + tool_trace=[]）
     ↓
[2] 主AI直接接管执行
     ↓
[3] 使用 terminal 工具执行原步骤命令
     ↓
[4] 验证输出
     ↓
[5] 继续下一步骤
```

### 实际案例

**场景**：凭证检测工作流步骤9-12
**问题**：子Agent返回"你好，我无法给到相关内容"
**解决**：主AI直接执行：

```bash
# 步骤9
ls -la /x/rank/hwxinxisouji/liuliang/autofill-detector/ | grep -E '\.json|\.txt'

# 步骤10
cat /x/rank/hwxinxisouji/liuliang/autofill-detector/*.json | jq '.'

# 步骤11
echo "=== 凭证检测统计 ===" && echo "总URL数: $(wc -l < /x/rank/hwxinxisouji/liuliang/autofill-detector/input.txt)"

# 步骤12
echo "凭证检测 - $(date) - 完成" >> /x/rank/hwxinxisouji/liuliang/autofill-detector/execution_log.txt
```

**结果**：步骤9-12成功完成，工作流正常结束。

## 最佳实践

1. **及时识别**：检查 delegate_task 返回的 `tokens.input` 和 `tool_trace`，若为0则异常
2. **快速回退**：不重试子Agent，直接由主AI接管
3. **保持连续**：回退后继续执行后续步骤，不中断工作流
4. **记录原因**：在 status.md 中记录子Agent失败原因
5. **切换模型**：若主Agent连续异常，切换到 Qwen3-Coder

## 触发条件

| 条件 | 说明 |
|------|------|
| 空泛回复 | 内容无实际意义，如"无法给到相关内容" |
| 无工具调用 | tool_trace = [] |
| 零token消耗 | tokens.input = 0 或 output = 0 |
| 执行超时 | Agent长时间无响应 |
| GLM-5 安全过滤 | 内部触发，原因不明 |

## 推荐方案

**方案A：监控与日志增强**
- 在 Gateway 添加响应内容监控
- 记录每次异常出现的上下文

**方案B：备用模型切换**
- 检测到异常时自动切换到 Qwen3-Coder
- 已有 fallback 机制支持

**方案C：重试机制**
- 当检测到异常响应时自动重试
- 主Agent场景建议切换模型

## 参考
- 详细分析：references/glm5-abnormal-response-analysis-20260518.md
- 会话：2026-05-18 异常响应诊断（会话ID: 20260518_100550_4f7c43）
- 会话：2026-05-15 凭证检测工作流执行
