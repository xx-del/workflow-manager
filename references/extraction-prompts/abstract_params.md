# 参数抽象化

## 任务描述

从具体参数值中抽象出可复用的参数模板。

## 输入

```json
{
  "core_steps": [
    {
      "id": "1",
      "name": "获取数据",
      "tool": "terminal",
      "arguments": {
        "command": "curl http://api.example.com/data?date=20260401-20260410 > /x/data/result.txt"
      }
    },
    {
      "id": "2",
      "name": "处理数据",
      "tool": "terminal",
      "arguments": {
        "command": "python process.py --input /x/data/result.txt --output /x/data/output.txt --limit 100"
      }
    }
  ]
}
```

## 分析步骤

### 1. 识别可变参数

从参数值中识别可以抽象化的变量：

| 参数类型 | 匹配规则 | 示例 |
|----------|----------|------|
| date_range | \d{8}-\d{8} 或 \d{8} | 20260401-20260410 |
| single_date | \d{4}-\d{2}-\d{2} | 2026-04-01 |
| path | /[a-zA-Z0-9_/-]+ | /x/data/result.txt |
| url | https?://[^\s]+ | http://api.example.com |
| number | \d+ (纯数字) | 100 |
| email | [^@]+@[^@]+ | user@example.com |

### 2. 参数命名规范

| 类型 | 建议名称 | 默认值 |
|------|----------|--------|
| 日期范围 | date_range | {{yesterday}} 或 {{last_n_days:7}} |
| 单个日期 | target_date | {{today}} |
| 输出目录 | output_dir | /x/data/ |
| 输入文件 | input_file | (required) |
| API URL | api_url | (根据上下文) |
| 数量限制 | limit | 100 |
| 超时时间 | timeout | 300 |

### 3. 参数分类

- **required**: 必须提供，无默认值
- **optional**: 可选，有合理默认值
- **derived**: 从其他参数推导

### 4. 参数联动

识别参数间的依赖关系：
- input_file 依赖上一步的 output
- date_range 被多个步骤使用

## 输出格式

```json
{
  "parameters": [
    {
      "name": "date_range",
      "type": "string",
      "required": true,
      "default": "{{yesterday}}",
      "description": "数据采集日期范围，格式：YYYYMMDD-YYYYMMDD",
      "example": "20260401-20260410",
      "validation": {
        "pattern": "^\\d{8}-\\d{8}$",
        "message": "日期格式应为 YYYYMMDD-YYYYMMDD"
      }
    },
    {
      "name": "output_dir",
      "type": "string",
      "required": false,
      "default": "/x/data/",
      "description": "输出文件保存目录"
    },
    {
      "name": "limit",
      "type": "integer",
      "required": false,
      "default": 100,
      "description": "处理数量上限"
    }
  ],
  "step_params_map": {
    "1": {
      "uses": ["date_range", "output_dir"],
      "produces": ["result_file"]
    },
    "2": {
      "uses": ["result_file", "limit", "output_dir"],
      "produces": ["output_file"]
    }
  },
  "internal_variables": {
    "result_file": "{{output_dir}}result.txt",
    "output_file": "{{output_dir}}output.txt"
  }
}
```

## 特殊变量

| 变量 | 说明 | 示例值 |
|------|------|--------|
| {{today}} | 当前日期 | 2026-04-11 |
| {{yesterday}} | 昨天日期 | 2026-04-10 |
| {{last_n_days:N}} | 过去N天 | 2026-04-04-2026-04-10 |
| {{this_week}} | 本周 | 2026-04-07-2026-04-11 |
| {{this_month}} | 本月 | 2026-04-01-2026-04-11 |
| {{timestamp}} | 当前时间戳 | 1712800000 |

## 注意事项

1. 不要过度抽象，保留必要的具体值
2. 默认值应该安全、合理
3. 路径参数使用绝对路径
4. 添加参数验证规则
5. 文档化参数用途
