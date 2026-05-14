# 提取核心步骤

## 任务描述

从会话上下文中提取工作流的核心步骤，排除试错噪音。

## 输入

会话数据结构：
```json
{
  "tool_sequence": [
    {
      "id": "call_xxx",
      "index": 0,
      "name": "terminal",
      "arguments": {"command": "..."},
      "timestamp": "..."
    }
  ],
  "results": [
    {
      "tool_call_id": "call_xxx",
      "content": "...",
      "is_success": true,
      "timestamp": "..."
    }
  ],
  "user_feedback": [
    {
      "index": 5,
      "content": "好了",
      "feedback_type": "success"
    }
  ]
}
```

## 分析步骤

### 1. 识别成功标记
- 成功的 tool results (is_success: true)
- 用户确认反馈 (feedback_type: success)

### 2. 逆向追踪
从成功标记回溯：
- 哪个工具调用产生了这个成功结果？
- 这个工具调用的输入来自哪里？
- 递归追踪直到找到起点

### 3. 过滤噪音
排除以下类型的调用：
- 失败后未成功的尝试
- 纯调试操作（如查看日志、检查状态）
- 冗余的重复调用

### 4. 确定依赖
- 输入依赖：步骤 B 使用步骤 A 的输出
- 顺序依赖：步骤 B 必须在步骤 A 之后

## 输出格式

```json
{
  "core_steps": [
    {
      "id": "1",
      "name": "步骤名称（中文，简洁）",
      "tool": "工具名称",
      "action": "具体执行动作",
      "arguments": {"key": "value"},
      "outputs": ["output_file.txt"],
      "description": "步骤说明"
    }
  ],
  "dependencies": {
    "2": ["1"],
    "3": ["2"]
  },
  "excluded_attempts": [
    {
      "tool_call_id": "call_xxx",
      "reason": "失败尝试/调试操作/冗余调用"
    }
  ],
  "workflow_summary": "一句话描述工作流目的"
}
```

## 步骤命名规范

| 工具 | 建议命名 |
|------|----------|
| terminal + curl | 获取数据 / 下载数据 |
| terminal + python | 执行脚本 / 处理数据 |
| terminal + git | Git 操作 |
| read_file | 读取文件 |
| write_file | 保存文件 / 写入文件 |
| search_files | 搜索文件 |
| browser_navigate | 打开网页 |
| browser_click | 点击元素 |

## 注意事项

1. 步骤 ID 使用连续整数 (1, 2, 3...)
2. 名称使用中文，简洁明了（2-5字）
3. action 保留原始命令或参数
4. outputs 只列出实际产生的文件
