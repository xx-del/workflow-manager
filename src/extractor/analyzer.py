#!/usr/bin/env python3
"""
AI 分析层 - 使用 AI 进行语义理解和抽象

职责：
1. 分析核心步骤，识别意图
2. 识别偏差纠正模式
3. 抽象化参数
4. 生成工作流元数据
"""

from utils.logger import get_logger
import json
import re
from typing import Any, Optional
from pathlib import Path


# 提示词模板
EXTRACT_STEPS_PROMPT = """# 任务：从会话上下文中提取工作流步骤

## 输入数据
{extracted_data}

## 分析要求

### 1. 识别核心步骤
- 哪些工具调用是完成任务的必要步骤？
- 排除失败尝试和调试操作
- 确定步骤的执行顺序

### 2. 步骤命名
为每个步骤起一个简洁的中文名称，格式：
- 获取数据
- 处理结果
- 保存输出

### 3. 依赖关系
哪些步骤之间有依赖关系？
- 输入依赖：步骤 B 需要步骤 A 的输出
- 顺序依赖：步骤 B 必须在步骤 A 之后执行

## 输出格式（JSON）

```json
{
  "core_steps": [
    {
      "id": "1",
      "name": "步骤名称",
      "tool": "工具名称",
      "action": "执行动作描述",
      "arguments": {...},
      "outputs": ["输出文件"],
      "description": "步骤说明"
    }
  ],
  "dependencies": {
    "2": ["1"]
  },
  "excluded_attempts": [
    {
      "reason": "失败尝试",
      "tool_call_id": "..."
    }
  ]
}
```

请分析并输出 JSON：
"""

IDENTIFY_CORRECTIONS_PROMPT = """# 任务：识别偏差纠正路径

## 输入数据
- 失败尝试：{failed_attempts}
- 成功步骤：{core_steps}
- 用户反馈：{user_feedback}

## 分析要求

对于每个失败尝试，分析：

### 1. 失败原因分类
- network_error: 网络问题（超时、连接失败）
- permission_error: 权限问题
- parameter_error: 参数错误
- resource_error: 资源不存在
- logic_error: 逻辑错误
- unknown: 未知原因

### 2. 错误做法
用户/系统最初尝试了什么方法？为什么失败？

### 3. 正确做法
后来采用了什么方法？为什么成功？

### 4. 触发条件
在什么情况下应该应用这个纠正？

## 输出格式（JSON）

```json
{
  "corrections": [
    {
      "step_id": "1",
      "error_type": "network_error",
      "error_description": "网络连接超时",
      "wrong_approach": "直接重试原命令",
      "correct_approach": "检查代理设置，使用备用 API 端点",
      "condition": "当遇到网络超时或连接失败时",
      "confidence": 0.9
    }
  ]
}
```

请分析并输出 JSON：
"""

ABSTRACT_PARAMS_PROMPT = """# 任务：抽象化工作流参数

## 输入数据
{core_steps}

## 分析要求

### 1. 识别可变参数
从工具参数中识别可以抽象化的变量：
- 日期范围：date_range, start_date, end_date
- 文件路径：output_dir, input_file
- URL/端点：api_url, base_url
- 数量限制：limit, count, max_items
- 配置选项：options, flags

### 2. 参数分类
- required: 必须提供的参数
- optional: 可选参数，有默认值
- derived: 从其他参数推导的参数

### 3. 默认值设置
为可选参数设置合理的默认值：
- 日期：{{yesterday}} 或 {{today}}
- 路径：基于常用目录
- 数量：合理的安全值

## 输出格式（JSON）

```json
{
  "parameters": [
    {
      "name": "date_range",
      "type": "string",
      "required": true,
      "default": "{{yesterday}}",
      "description": "数据采集日期范围，格式：YYYYMMDD-YYYYMMDD",
      "example": "20260401-20260410"
    },
    {
      "name": "output_dir",
      "type": "string",
      "required": false,
      "default": "/x/data/",
      "description": "输出文件保存目录"
    }
  ],
  "step_params_map": {
    "1": ["date_range"],
    "2": ["output_dir"]
  }
}
```

请分析并输出 JSON：
"""


def analyze_with_prompt(prompt: str, context: dict) -> dict:
    """
    使用 AI 分析上下文（这里返回结构化提示词，由调用方传入 AI）

    实际使用时，这个函数会被 agent-pool 调用，AI 会处理提示词
    """
    formatted_prompt = prompt.format(**context)
    return {
        "prompt": formatted_prompt,
        "context": context
    }


def extract_core_steps_prompt(extracted_data: dict) -> str:
    """生成提取核心步骤的提示词"""
    return EXTRACT_STEPS_PROMPT.format(
        extracted_data=json.dumps(extracted_data, indent=2, ensure_ascii=False)
    )


def identify_corrections_prompt(
    failed_attempts: list[dict],
    core_steps: list[dict],
    user_feedback: list[dict]
) -> str:
    """生成识别偏差纠正的提示词"""
    return IDENTIFY_CORRECTIONS_PROMPT.format(
        failed_attempts=json.dumps(failed_attempts, indent=2, ensure_ascii=False),
        core_steps=json.dumps(core_steps, indent=2, ensure_ascii=False),
        user_feedback=json.dumps(user_feedback, indent=2, ensure_ascii=False)
    )


def abstract_params_prompt(core_steps: list[dict]) -> str:
    """生成参数抽象的提示词"""
    return ABSTRACT_PARAMS_PROMPT.format(
        core_steps=json.dumps(core_steps, indent=2, ensure_ascii=False)
    )


# ==================== 本地分析函数（不依赖 AI）====================

def classify_error_locally(error_content: str) -> str:
    """
    本地分类错误类型（不依赖 AI）

    用于快速分类常见错误
    """
    error_lower = error_content.lower()

    # 网络错误
    if any(kw in error_lower for kw in ['timeout', 'connection', 'network', 'refused', 'unreachable']):
        return 'network_error'

    # 权限错误
    if any(kw in error_lower for kw in ['permission', 'denied', 'forbidden', 'unauthorized', 'access']):
        return 'permission_error'

    # 参数错误
    if any(kw in error_lower for kw in ['invalid', 'missing', 'argument', 'parameter', 'syntax']):
        return 'parameter_error'

    # 资源错误
    if any(kw in error_lower for kw in ['not found', 'does not exist', 'no such', '404']):
        return 'resource_error'

    # 逻辑错误
    if any(kw in error_lower for kw in ['logic', 'assertion', 'unexpected', 'invalid state']):
        return 'logic_error'

    return 'unknown'


def extract_parameters_locally(arguments: dict) -> list[dict]:
    """
    本地提取可变参数（不依赖 AI）

    基于规则识别可参数化的值
    """
    parameters = []
    param_patterns = {
        'date': {
            'patterns': [r'\d{8}', r'\d{4}-\d{2}-\d{2}', r'\d{8}-\d{8}'],
            'param_name': 'date_range',
            'type': 'string',
            'description': '日期范围'
        },
        'path': {
            'patterns': [r'^/[a-zA-Z0-9_/-]+/$', r'^/[a-zA-Z0-9_/-]+\.[a-zA-Z]+$'],
            'param_name': 'output_path',
            'type': 'string',
            'description': '文件路径'
        },
        'url': {
            'patterns': [r'^https?://', r'^http://'],
            'param_name': 'api_url',
            'type': 'string',
            'description': 'API 端点'
        },
        'number': {
            'patterns': [r'^\d+$'],
            'param_name': 'limit',
            'type': 'integer',
            'description': '数量限制'
        }
    }

    extracted_values = set()

    for key, value in arguments.items():
        if not isinstance(value, str):
            continue

        for param_type, config in param_patterns.items():
            for pattern in config['patterns']:
                if re.match(pattern, value) and value not in extracted_values:
                    extracted_values.add(value)
                    parameters.append({
                        'name': config['param_name'],
                        'type': config['type'],
                        'value': value,
                        'source_arg': key,
                        'description': config['description']
                    })
                    break

    return parameters


def infer_step_name(tool_name: str, arguments: dict) -> str:
    """
    推断步骤名称（不依赖 AI）
    """
    # 工具名称映射
    tool_name_map = {
        'terminal': '执行命令',
        'read_file': '读取文件',
        'write_file': '写入文件',
        'search_files': '搜索文件',
        'browser_navigate': '打开网页',
        'browser_click': '点击元素',
        'browser_type': '输入文本',
        'http_request': '发送请求',
    }

    base_name = tool_name_map.get(tool_name, tool_name)

    # 根据参数推断更具体的名称
    if tool_name == 'terminal':
        command = arguments.get('command', '')
        if 'curl' in command:
            return '获取数据'
        elif 'python' in command:
            return '执行脚本'
        elif 'git' in command:
            return 'Git 操作'
        elif 'ssh' in command:
            return '远程执行'

    return base_name


def infer_step_outputs(tool_name: str, arguments: dict, result_content: str = '') -> list[str]:
    """
    推断步骤输出文件（不依赖 AI）
    """
    outputs = []

    if tool_name == 'write_file':
        path = arguments.get('path')
        if path:
            outputs.append(path)

    elif tool_name == 'terminal':
        command = arguments.get('command', '')
        # 从命令中提取输出重定向
        redirect_match = re.search(r'>\s*([^\s;|]+)', command)
        if redirect_match:
            outputs.append(redirect_match.group(1))

        # 从结果中提取文件路径
        file_matches = re.findall(r'(?:saved|written|created|output)[:\s]+([^\s,]+)', result_content, re.I)
        outputs.extend(file_matches)

    return outputs


def analyze_correction_pattern(
    failed_attempt: dict,
    successful_attempts: list[dict]
) -> Optional[dict]:
    """
    分析失败尝试和成功尝试之间的纠正模式
    """
    failed_tool = failed_attempt.get('tool_name')
    failed_args = failed_attempt.get('arguments', {})

    # 找到相同工具的成功尝试
    for success in successful_attempts:
        if success.get('name') == failed_tool:
            success_args = success.get('arguments', {})

            # 比较参数差异
            arg_diff = {}
            for key in set(failed_args.keys()) | set(success_args.keys()):
                if failed_args.get(key) != success_args.get(key):
                    arg_diff[key] = {
                        'failed': failed_args.get(key),
                        'success': success_args.get(key)
                    }

            if arg_diff:
                return {
                    'step_id': failed_attempt.get('tool_call_id'),
                    'error_type': classify_error_locally(failed_attempt.get('error_preview', '')),
                    'wrong_approach': f"使用参数: {failed_args}",
                    'correct_approach': f"修正参数: {arg_diff}",
                    'condition': f"当 {failed_tool} 执行失败时",
                    'arg_diff': arg_diff
                }

    return None


def main():
    """测试函数"""
    test_args = {
        'date': '20260401-20260410',
        'output': '/x/data/result.txt',
        'url': 'http://api.example.com/data'
    }

    params = extract_parameters_locally(test_args)
    self.logger.info("Extracted parameters:")
    self.logger.info(json.dumps(params, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
