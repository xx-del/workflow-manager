#!/usr/bin/env python3
"""
偏差纠正分析器 - 从失败尝试和成功做法中提取经验教训

职责：
1. 识别失败尝试
2. 匹配对应的成功做法
3. 提取纠正模式
4. 生成偏差纠正指南
"""

from utils.logger import get_logger
import json
import re
from datetime import datetime
from typing import Any, Optional
from pathlib import Path


class CorrectionAnalyzer:
    """偏差纠正分析器"""

    # 错误类型关键词映射
    ERROR_PATTERNS = {
        'network_error': [
            'timeout', 'connection', 'refused', 'unreachable',
            'network', 'dns', 'socket', 'errno 111', 'errno 113',
            '连接超时', '网络错误', '无法连接'
        ],
        'permission_error': [
            'permission denied', 'forbidden', 'unauthorized',
            'access denied', '403', '权限', '拒绝访问'
        ],
        'parameter_error': [
            'invalid', 'missing', 'argument', 'parameter',
            'syntax error', 'valueerror', 'typeerror',
            '参数错误', '无效参数', '缺少参数'
        ],
        'resource_error': [
            'not found', 'does not exist', 'no such',
            '404', '资源不存在', '未找到'
        ],
        'api_error': [
            'rate limit', 'quota', 'banned', 'too many requests',
            '429', 'api key', '认证失败', '限流'
        ],
        'logic_error': [
            'assertion', 'unexpected', 'invalid state',
            '逻辑错误', '断言失败'
        ],
        'encoding_error': [
            'unicode', 'encode', 'decode', 'utf-8', 'gbk',
            '编码错误', '乱码'
        ],
        'disk_error': [
            'no space', 'disk full', 'io error',
            '磁盘空间不足', '写入失败'
        ]
    }

    # 常见纠正模式库
    CORRECTION_PATTERNS = {
        'network_error': {
            'proxy': {
                'condition': '网络直连失败或超时',
                'wrong': '直接请求目标地址',
                'correct': '配置代理服务器后重试'
            },
            'retry': {
                'condition': '网络波动导致临时失败',
                'wrong': '失败后放弃',
                'correct': '等待后重试（建议间隔60秒）'
            },
            'backup_endpoint': {
                'condition': '主端点不可达',
                'wrong': '反复请求同一端点',
                'correct': '切换到备用端点'
            },
            'timeout_adjust': {
                'condition': '操作耗时超过默认超时',
                'wrong': '使用默认超时设置',
                'correct': '增加超时时间参数'
            }
        },
        'permission_error': {
            'sudo': {
                'condition': '需要管理员权限',
                'wrong': '以普通用户执行',
                'correct': '使用 sudo 或切换到 root 用户'
            },
            'chmod': {
                'condition': '文件权限不足',
                'wrong': '直接读写文件',
                'correct': '修改文件权限后重试'
            }
        },
        'parameter_error': {
            'check_format': {
                'condition': '参数格式不符合预期',
                'wrong': '直接传入原始值',
                'correct': '验证并转换参数格式'
            },
            'check_path': {
                'condition': '文件路径不存在',
                'wrong': '直接使用路径',
                'correct': '检查路径是否存在，必要时创建目录'
            }
        },
        'api_error': {
            'rate_limit': {
                'condition': 'API 请求频率超限',
                'wrong': '连续快速请求',
                'correct': '添加请求间隔，使用指数退避'
            },
            'key_rotation': {
                'condition': 'API Key 失效或配额用尽',
                'wrong': '继续使用同一 Key',
                'correct': '切换到备用 API Key'
            }
        }
    }

    def __init__(self):

        self.logger = get_logger(__name__)
        pass

    def analyze(
        self,
        tool_sequence: list[dict],
        results: list[dict],
        user_feedback: list[dict]
    ) -> dict:
        """
        分析偏差纠正

        Args:
            tool_sequence: 工具调用序列
            results: 执行结果
            user_feedback: 用户反馈

        Returns:
            偏差纠正分析结果
        """
        # 1. 构建结果映射
        result_map = {r.get('tool_call_id'): r for r in results}

        # 2. 识别失败尝试
        failed_attempts = self._identify_failed_attempts(tool_sequence, result_map)

        # 3. 识别成功步骤
        successful_steps = self._identify_successful_steps(tool_sequence, result_map, user_feedback)

        # 4. 匹配失败-成功对
        correction_pairs = self._match_correction_pairs(failed_attempts, successful_steps)

        # 5. 提取纠正模式
        corrections = self._extract_corrections(correction_pairs, tool_sequence, result_map)

        return {
            'corrections': corrections,
            'failed_attempts': failed_attempts,
            'successful_steps': successful_steps,
            'correction_summary': self._generate_summary(corrections)
        }

    def _identify_failed_attempts(
        self,
        tool_sequence: list[dict],
        result_map: dict
    ) -> list[dict]:
        """识别失败的尝试"""
        failed = []

        for call in tool_sequence:
            call_id = call.get('id')
            result = result_map.get(call_id)

            if result and not result.get('is_success', True):
                error_content = result.get('content', '')
                failed.append({
                    'tool_call_id': call_id,
                    'tool_name': call.get('name'),
                    'arguments': call.get('arguments', {}),
                    'error_type': self._classify_error(error_content),
                    'error_content': error_content[:500],
                    'timestamp': call.get('timestamp'),
                    'index': call.get('index', 0)
                })

        return failed

    def _identify_successful_steps(
        self,
        tool_sequence: list[dict],
        result_map: dict,
        user_feedback: list[dict]
    ) -> list[dict]:
        """识别成功的步骤"""
        successful = []

        # 从用户反馈中找成功确认
        success_indices = set()
        for feedback in user_feedback:
            if feedback.get('feedback_type') == 'success':
                success_indices.add(feedback.get('index', -1))

        for call in tool_sequence:
            call_id = call.get('id')
            result = result_map.get(call_id)

            # 成功的结果
            if result and result.get('is_success'):
                successful.append({
                    'tool_call_id': call_id,
                    'tool_name': call.get('name'),
                    'arguments': call.get('arguments', {}),
                    'timestamp': call.get('timestamp'),
                    'index': call.get('index', 0)
                })

        return successful

    def _match_correction_pairs(
        self,
        failed_attempts: list[dict],
        successful_steps: list[dict]
    ) -> list[dict]:
        """匹配失败尝试和成功纠正"""
        pairs = []

        for failed in failed_attempts:
            # 找到同工具的成功尝试
            matching_success = None
            min_index_diff = float('inf')

            for success in successful_steps:
                if success.get('tool_name') == failed.get('tool_name'):
                    # 成功步骤应该在失败之后
                    index_diff = success.get('index', 0) - failed.get('index', 0)
                    if index_diff > 0 and index_diff < min_index_diff:
                        min_index_diff = index_diff
                        matching_success = success

            if matching_success:
                pairs.append({
                    'failed': failed,
                    'success': matching_success,
                    'index_diff': min_index_diff
                })

        return pairs

    def _extract_corrections(
        self,
        correction_pairs: list[dict],
        tool_sequence: list[dict],
        result_map: dict
    ) -> list[dict]:
        """提取纠正模式"""
        corrections = []

        for pair in correction_pairs:
            failed = pair['failed']
            success = pair['success']

            # 比较参数差异
            arg_diff = self._compare_arguments(
                failed.get('arguments', {}),
                success.get('arguments', {})
            )

            # 提取纠正模式
            error_type = failed.get('error_type', 'unknown')
            correction_pattern = self._match_correction_pattern(error_type, arg_diff)

            correction = {
                'step_id': self._find_step_id(tool_sequence, failed.get('tool_call_id')),
                'error_type': error_type,
                'error_description': self._describe_error(failed.get('error_content', '')),
                'wrong_approach': self._describe_approach(failed),
                'correct_approach': self._describe_approach(success, arg_diff),
                'condition': correction_pattern.get('condition', f'当遇到{error_type}时'),
                'arg_changes': arg_diff,
                'confidence': self._calculate_confidence(pair, arg_diff)
            }

            corrections.append(correction)

        return corrections

    def _classify_error(self, error_content: str) -> str:
        """分类错误类型"""
        error_lower = error_content.lower()

        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in error_lower:
                    return error_type

        return 'unknown'

    def _compare_arguments(self, failed_args: dict, success_args: dict) -> dict:
        """比较参数差异"""
        diff = {}

        all_keys = set(failed_args.keys()) | set(success_args.keys())

        for key in all_keys:
            failed_val = failed_args.get(key)
            success_val = success_args.get(key)

            if failed_val != success_val:
                diff[key] = {
                    'failed': failed_val,
                    'success': success_val
                }

        return diff

    def _match_correction_pattern(self, error_type: str, arg_diff: dict) -> dict:
        """匹配纠正模式"""
        patterns = self.CORRECTION_PATTERNS.get(error_type, {})

        # 根据参数变化匹配模式
        if error_type == 'network_error':
            if any('proxy' in str(v) for v in arg_diff.values() if v.get('success')):
                return patterns.get('proxy', {})
            elif any('timeout' in str(k) for k in arg_diff.keys()):
                return patterns.get('timeout_adjust', {})
            elif any('http' in str(v.get('success', '')) for v in arg_diff.values() if v.get('success')):
                return patterns.get('backup_endpoint', {})

        elif error_type == 'api_error':
            if any('key' in str(k).lower() for k in arg_diff.keys()):
                return patterns.get('key_rotation', {})
            else:
                return patterns.get('rate_limit', {})

        return {}

    def _describe_error(self, error_content: str) -> str:
        """生成错误描述"""
        # 提取关键错误信息
        lines = error_content.split('\n')
        for line in lines[:3]:
            line = line.strip()
            if line and len(line) > 10:
                return line[:100]
        return '执行失败'

    def _describe_approach(self, step: dict, arg_diff: dict = None) -> str:
        """描述方法"""
        tool = step.get('tool_name', 'unknown')
        args = step.get('arguments', {})
        error_type = step.get('error_type')

        # 如果是失败步骤
        if error_type:
            desc = f"使用 {tool} 执行"
            if args:
                key_args = list(args.keys())[:2]
                desc += f"，参数: {', '.join(key_args)}"
            return desc

        # 如果是成功步骤，强调修正的参数
        if arg_diff:
            changes = []
            for key, vals in arg_diff.items():
                if vals.get('success'):
                    changes.append(f"{key}={vals['success']}")
            if changes:
                return f"使用 {tool} 执行，修正参数: {', '.join(changes[:2])}"

        return f"使用 {tool} 执行成功"

    def _find_step_id(self, tool_sequence: list[dict], tool_call_id: str) -> str:
        """根据 tool_call_id 找到步骤 ID"""
        for i, call in enumerate(tool_sequence):
            if call.get('id') == tool_call_id:
                return str(i + 1)
        return 'unknown'

    def _calculate_confidence(self, pair: dict, arg_diff: dict) -> float:
        """计算置信度"""
        confidence = 0.5

        # 有参数差异，置信度更高
        if arg_diff:
            confidence += 0.2

        # 失败和成功之间间隔越小，置信度越高
        index_diff = pair.get('index_diff', 10)
        if index_diff <= 2:
            confidence += 0.2
        elif index_diff <= 5:
            confidence += 0.1

        # 有明确的错误类型
        if pair['failed'].get('error_type') != 'unknown':
            confidence += 0.1

        return min(confidence, 1.0)

    def _generate_summary(self, corrections: list[dict]) -> str:
        """生成纠正摘要"""
        if not corrections:
            return "未检测到偏差纠正"

        error_types = [c.get('error_type') for c in corrections]
        unique_types = set(error_types)

        summary = f"检测到 {len(corrections)} 处偏差纠正"
        if len(unique_types) > 0:
            summary += f"，类型: {', '.join(unique_types)}"

        return summary


def main():
    """测试函数"""
    analyzer = CorrectionAnalyzer()

    # 测试数据
    tool_sequence = [
        {
            'id': 'call_1',
            'name': 'terminal',
            'arguments': {'command': 'curl http://api/data'},
            'index': 1
        },
        {
            'id': 'call_2',
            'name': 'terminal',
            'arguments': {'command': 'curl --proxy http://proxy:8080 http://api/data'},
            'index': 2
        }
    ]

    results = [
        {
            'tool_call_id': 'call_1',
            'content': 'Connection timeout',
            'is_success': False
        },
        {
            'tool_call_id': 'call_2',
            'content': '{"success": true, "data": [...]}',
            'is_success': True
        }
    ]

    user_feedback = [
        {
            'content': '好了',
            'feedback_type': 'success',
            'index': 3
        }
    ]

    analysis = analyzer.analyze(tool_sequence, results, user_feedback)
    self.logger.info(json.dumps(analysis, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
