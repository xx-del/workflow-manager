# 识别偏差纠正路径

## 任务描述

从失败尝试和成功纠正中提取经验教训，形成偏差纠正指南。

## 输入

```json
{
  "failed_attempts": [
    {
      "tool_call_id": "call_xxx",
      "tool_name": "terminal",
      "arguments": {"command": "curl http://api/data"},
      "error_preview": "Connection timeout...",
      "timestamp": "..."
    }
  ],
  "core_steps": [
    {
      "id": "1",
      "name": "获取数据",
      "tool": "terminal",
      "arguments": {"command": "curl --proxy http://proxy:8080 http://api/data"}
    }
  ],
  "user_feedback": [
    {
      "content": "网络超时了，试试加代理",
      "feedback_type": "correction"
    }
  ]
}
```

## 分析步骤

### 1. 错误分类

| 类型 | 关键词 | 说明 |
|------|--------|------|
| network_error | timeout, connection, refused | 网络问题 |
| permission_error | permission, denied, forbidden | 权限问题 |
| parameter_error | invalid, missing, argument | 参数错误 |
| resource_error | not found, 404, does not exist | 资源不存在 |
| logic_error | assertion, unexpected | 逻辑错误 |
| api_error | rate limit, quota, banned | API 限制 |
| unknown | - | 未知原因 |

### 2. 对比分析

对于每个失败尝试，找到对应成功的步骤：

```
失败调用:
- 工具: terminal
- 参数: {command: "curl http://api/data"}
- 错误: Connection timeout

成功调用:
- 工具: terminal
- 参数: {command: "curl --proxy http://proxy:8080 http://api/data"}
- 结果: 成功

差异:
- 添加了 --proxy 参数
```

### 3. 提取模式

从差异中提取：
- 错误原因：网络超时（无代理）
- 错误做法：直接请求
- 正确做法：配置代理后请求
- 触发条件：遇到网络超时时

## 输出格式

```json
{
  "corrections": [
    {
      "step_id": "1",
      "error_type": "network_error",
      "error_description": "网络连接超时",
      "wrong_approach": "直接使用 curl 请求 API",
      "correct_approach": "配置代理 (--proxy) 后再请求",
      "condition": "当遇到网络超时或连接失败时",
      "alternative_solutions": [
        "使用备用 API 端点",
        "增加超时时间 (--connect-timeout)",
        "检查网络连接状态"
      ],
      "confidence": 0.9
    }
  ],
  "correction_patterns": [
    {
      "pattern": "添加代理解决网络问题",
      "applicable_tools": ["terminal", "browser_navigate"],
      "frequency": "high"
    }
  ]
}
```

## 质量要求

1. **准确性**: 错误分类必须准确
2. **可操作性**: 正确做法必须具体可执行
3. **通用性**: 触发条件应具有通用性
4. **置信度**: confidence 0-1，表示分析的可信程度

## 特殊情况

| 情况 | 处理方式 |
|------|----------|
| 无法找到对应成功步骤 | 记录为 open_issue |
| 多次失败后成功 | 合并为一条纠正，记录所有尝试 |
| 用户直接给出解决方案 | 标记 confidence=1.0 |
