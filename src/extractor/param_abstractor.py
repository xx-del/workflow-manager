#!/usr/bin/env python3
"""
参数抽象器 - 从具体值中提取可复用的参数模板

职责：
1. 识别可变参数
2. 分类参数类型
3. 设置默认值
4. 建立参数映射
"""

from utils.logger import get_logger
import re
import json
from datetime import datetime, timedelta
from typing import Any, Optional
from pathlib import Path


class ParameterAbstractor:
    """参数抽象器"""

    # 参数模式匹配规则（按优先级排序）
    PARAMETER_PATTERNS = {
        'date_range': {
            'patterns': [
                (r'\b(\d{8}-\d{8})\b', 'YYYYMMDD-YYYYMMDD 格式'),
            ],
            'default': '{{yesterday}}',
            'description': '日期范围',
            'priority': 1
        },
        'output_path': {
            'patterns': [
                (r'>(\s*)(/[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)', '输出重定向文件'),
                (r'--output\s+(/[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)', '--output 参数'),
                (r'--input\s+(/[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)', '--input 参数'),
            ],
            'default': '/x/data/',
            'description': '文件路径',
            'priority': 2
        },
        'api_url': {
            'patterns': [
                (r'(https?://[a-zA-Z0-9_\-./]+(?:/[a-zA-Z0-9_\-./]*)?)', 'HTTP/HTTPS URL'),
            ],
            'default': '',
            'description': 'API 端点',
            'priority': 3
        },
        'number': {
            'patterns': [
                (r'--limit\s+(\d+)', 'limit 参数'),
                (r'--count\s+(\d+)', 'count 参数'),
                (r'--timeout\s+(\d+)', 'timeout 参数'),
            ],
            'default': '100',
            'description': '数量参数',
            'priority': 4
        }
    }

    # 特殊占位符
    SPECIAL_PLACEHOLDERS = {
        '{{today}}': {
            'value': lambda: datetime.now().strftime('%Y%m%d'),
            'description': '今天日期'
        },
        '{{yesterday}}': {
            'value': lambda: (datetime.now() - timedelta(days=1)).strftime('%Y%m%d'),
            'description': '昨天日期'
        },
        '{{last_7_days}}': {
            'value': lambda: f"{(datetime.now() - timedelta(days=7)).strftime('%Y%m%d')}-{datetime.now().strftime('%Y%m%d')}",
            'description': '过去7天'
        },
        '{{this_week}}': {
            'value': lambda: f"{(datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y%m%d')}-{datetime.now().strftime('%Y%m%d')}",
            'description': '本周'
        },
        '{{this_month}}': {
            'value': lambda: f"{datetime.now().replace(day=1).strftime('%Y%m%d')}-{datetime.now().strftime('%Y%m%d')}",
            'description': '本月'
        },
        '{{timestamp}}': {
            'value': lambda: str(int(datetime.now().timestamp())),
            'description': '当前时间戳'
        }
    }

    # 参数命名建议
    PARAM_NAMING = {
        'date': ['date_range', 'start_date', 'end_date', 'target_date', 'date'],
        'path': ['output_dir', 'input_file', 'output_file', 'log_path', 'data_dir'],
        'url': ['api_url', 'base_url', 'endpoint', 'webhook_url'],
        'number': ['limit', 'count', 'max_items', 'timeout', 'retry_count'],
        'host': ['server', 'host', 'target_host', 'remote_host']
    }

    def __init__(self):

        self.logger = get_logger(__name__)
        self.extracted_params = []
        self.param_counter = {}

    def abstract(self, core_steps: list[dict]) -> dict:
        """
        抽象化参数

        Args:
            core_steps: 核心步骤列表

        Returns:
            参数抽象结果
        """
        self.extracted_params = []
        self.param_counter = {}

        # 1. 从每个步骤提取参数
        step_params_map = {}
        for i, step in enumerate(core_steps):
            step_id = step.get('id', str(i + 1))
            args = step.get('arguments', {})

            extracted = self._extract_from_arguments(args, step.get('tool', ''))
            step_params_map[step_id] = {
                'uses': [p['name'] for p in extracted],
                'produces': []
            }

            self.extracted_params.extend(extracted)

        # 2. 去重和合并
        unique_params = self._deduplicate_params()

        # 3. 推断参数类型和默认值
        for param in unique_params:
            self._infer_param_properties(param)

        # 4. 推断内部变量（步骤间的输出）
        internal_vars = self._infer_internal_variables(core_steps)

        return {
            'parameters': unique_params,
            'step_params_map': step_params_map,
            'internal_variables': internal_vars,
            'param_summary': self._generate_summary(unique_params)
        }

    def _extract_from_arguments(self, arguments: dict, tool_name: str) -> list[dict]:
        """从参数中提取可变量"""
        extracted = []

        for key, value in arguments.items():
            if not isinstance(value, str):
                continue

            # 按优先级尝试匹配参数模式
            matched_positions = set()  # 记录已匹配的位置，避免重复

            for param_type, config in sorted(
                self.PARAMETER_PATTERNS.items(),
                key=lambda x: x[1].get('priority', 99)
            ):
                for pattern, desc in config['patterns']:
                    for match in re.finditer(pattern, value):
                        # 检查是否与已匹配的重叠
                        match_start, match_end = match.span()
                        
                        # 跳过重叠的匹配
                        if any(start <= match_start < end or start < match_end <= end 
                               for start, end in matched_positions):
                            continue
                        
                        matched_positions.add((match_start, match_end))

                        match_value = match.group(1) if match.lastindex else match.group(0)
                        
                        # 清理匹配值
                        match_value = match_value.strip()

                        param_name = self._suggest_param_name(key, param_type)

                        extracted.append({
                            'name': param_name,
                            'original_key': key,
                            'type': self._infer_type(param_type),
                            'value': match_value,
                            'full_value': value,
                            'param_type': param_type,
                            'pattern_desc': desc,
                            'tool': tool_name,
                            'required': self._is_required(key, tool_name),
                            'priority': config.get('priority', 99)
                        })

        # 按优先级排序，只保留最高优先级的参数
        if extracted:
            extracted.sort(key=lambda x: x.get('priority', 99))
            # 每种类型只保留一个
            seen_types = set()
            filtered = []
            for p in extracted:
                if p['param_type'] not in seen_types:
                    seen_types.add(p['param_type'])
                    filtered.append(p)
            extracted = filtered

        return extracted

    def _suggest_param_name(self, key: str, param_type: str) -> str:
        """建议参数名称"""
        # 如果 key 已经是好的名称，直接使用
        good_names = ['date_range', 'output_dir', 'input_file', 'api_url', 'limit', 'timeout']
        if key in good_names:
            return key

        # 根据类型建议名称
        naming_options = self.PARAM_NAMING.get(param_type, [key])
        for name in naming_options:
            if name not in self.param_counter:
                self.param_counter[name] = 0
            self.param_counter[name] += 1
            if self.param_counter[name] == 1:
                return name
            else:
                return f"{name}_{self.param_counter[name]}"

        return key

    def _infer_type(self, param_type: str) -> str:
        """推断参数类型"""
        type_map = {
            'date_range': 'string',
            'output_path': 'string',
            'api_url': 'string',
            'number': 'integer',
            'host': 'string'
        }
        return type_map.get(param_type, 'string')

    def _is_required(self, key: str, tool_name: str) -> bool:
        """判断参数是否必需"""
        # 常见必需参数
        required_keys = ['command', 'url', 'path', 'file', 'input', 'output']
        return any(rk in key.lower() for rk in required_keys)

    def _deduplicate_params(self) -> list[dict]:
        """去重参数"""
        seen = {}
        unique = []

        for param in self.extracted_params:
            name = param['name']
            value = param['value']

            # 相同名称的参数，保留第一个
            if name not in seen:
                seen[name] = param
                unique.append(param)
            else:
                # 合并使用信息
                if param['tool'] not in seen[name].get('tools', []):
                    seen[name].setdefault('tools', []).append(param['tool'])

        return unique

    def _infer_param_properties(self, param: dict) -> None:
        """推断参数属性"""
        param_type = param.get('param_type', '')

        # 设置默认值
        config = self.PARAMETER_PATTERNS.get(param_type, {})
        default = config.get('default', param.get('value', ''))

        # 特殊处理日期
        if param_type == 'date_range':
            default = '{{yesterday}}'
        elif param_type == 'output_path':
            # 提取目录部分作为默认值
            value = param.get('value', '')
            if '.' in value:
                default = str(Path(value).parent) + '/'
            else:
                default = value

        param['default'] = default

        # 设置描述
        if 'description' not in param:
            param['description'] = config.get('description', param.get('pattern_desc', ''))

        # 添加验证规则
        param['validation'] = self._generate_validation(param)

    def _generate_validation(self, param: dict) -> dict:
        """生成验证规则"""
        param_type = param.get('param_type', '')

        validations = {
            'date_range': {
                'pattern': r'^\d{8}(-\d{8})?$',
                'message': '日期格式应为 YYYYMMDD 或 YYYYMMDD-YYYYMMDD'
            },
            'output_path': {
                'pattern': r'^/[a-zA-Z0-9_\-./]+$',
                'message': '路径应为绝对路径'
            },
            'api_url': {
                'pattern': r'^https?://',
                'message': 'URL 应以 http:// 或 https:// 开头'
            },
            'number': {
                'pattern': r'^\d+$',
                'message': '应为正整数'
            }
        }

        return validations.get(param_type, {})

    def _infer_internal_variables(self, core_steps: list[dict]) -> dict:
        """推断内部变量（步骤输出）"""
        internal_vars = {}

        for step in core_steps:
            outputs = step.get('outputs', [])
            step_id = step.get('id', '?')

            for output in outputs:
                # 生成变量名
                var_name = Path(output).stem
                internal_vars[var_name] = output

        return internal_vars

    def _generate_summary(self, params: list[dict]) -> str:
        """生成参数摘要"""
        if not params:
            return "无需参数"

        required = [p for p in params if p.get('required')]
        optional = [p for p in params if not p.get('required')]

        summary = f"共 {len(params)} 个参数"
        if required:
            summary += f"，必需 {len(required)} 个"
        if optional:
            summary += f"，可选 {len(optional)} 个"

        return summary


def main():
    """测试函数"""
    abstractor = ParameterAbstractor()

    # 测试数据
    core_steps = [
        {
            'id': '1',
            'name': '获取数据',
            'tool': 'terminal',
            'arguments': {
                'command': 'curl http://api.example.com/data?date=20260401-20260410 > /x/data/result.json'
            },
            'outputs': ['/x/data/result.json']
        },
        {
            'id': '2',
            'name': '处理数据',
            'tool': 'terminal',
            'arguments': {
                'command': 'python process.py --input /x/data/result.json --output /x/data/output.txt --limit 100'
            },
            'outputs': ['/x/data/output.txt']
        }
    ]

    result = abstractor.abstract(core_steps)
    self.logger.info(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
