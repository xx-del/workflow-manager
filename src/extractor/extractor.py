#!/usr/bin/env python3
"""
会话上下文提取器 - 从 Hermes 会话中提取工作流相关信息

职责：
1. 获取当前会话的 messages
2. 过滤 tool_calls + tool_results
3. 提取 user feedback（成功/失败指示）
4. 结构化为 JSON
"""

from utils.logger import get_logger
import json
import re
import sys
from datetime import datetime
from typing import Any, Optional
from pathlib import Path


def extract_from_messages(messages: list[dict]) -> dict:
    """
    从 messages 列表中提取工作流相关结构化数据

    Args:
        messages: 会话消息列表

    Returns:
        结构化的会话数据
    """
    tool_sequence = []
    results = []
    user_feedback = []
    timestamps = []

    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", datetime.now().isoformat())

        # 提取 tool calls（来自 assistant）
        if role == "assistant" and "tool_calls" in msg:
            for tool_call in msg.get("tool_calls", []):
                tool_info = {
                    "id": tool_call.get("id", f"call_{i}"),
                    "index": i,
                    "name": tool_call.get("function", {}).get("name", ""),
                    "arguments": parse_tool_arguments(tool_call.get("function", {}).get("arguments", "{}")),
                    "timestamp": timestamp
                }
                tool_sequence.append(tool_info)
                timestamps.append(timestamp)

        # 提取 tool results（来自 tool）
        if role == "tool":
            result_info = {
                "tool_call_id": msg.get("tool_call_id", ""),
                "content": truncate_content(content, 2000),  # 截断过长内容
                "is_success": is_success_result(content),
                "timestamp": timestamp
            }
            results.append(result_info)

        # 提取 user feedback
        if role == "user":
            feedback = extract_user_feedback(content)
            if feedback:
                user_feedback.append({
                    "index": i,
                    "content": content[:500],  # 保留前500字符
                    "feedback_type": feedback,
                    "timestamp": timestamp
                })

    return {
        "tool_sequence": tool_sequence,
        "results": results,
        "user_feedback": user_feedback,
        "timestamps": timestamps,
        "metadata": {
            "total_tools": len(tool_sequence),
            "total_results": len(results),
            "total_feedback": len(user_feedback),
            "extracted_at": datetime.now().isoformat()
        }
    }


def parse_tool_arguments(arguments: str) -> dict:
    """解析工具参数 JSON"""
    try:
        return json.loads(arguments)
    except json.JSONDecodeError:
        return {"raw": arguments}


def truncate_content(content: str, max_length: int = 2000) -> str:
    """截断过长内容"""
    if len(content) <= max_length:
        return content
    return content[:max_length] + f"\n... [truncated, total {len(content)} chars]"


def is_success_result(content: str) -> bool:
    """判断工具执行结果是否成功"""
    # 常见成功标志
    success_patterns = [
        r'"success":\s*true',
        r'"exit_code":\s*0',
        r'completed successfully',
        r'操作成功',
        r'执行成功',
        r'已创建',
        r'已保存',
    ]

    # 常见失败标志
    failure_patterns = [
        r'"success":\s*false',
        r'"exit_code":\s*[1-9]',
        r'error',
        r'failed',
        r'错误',
        r'失败',
        r'exception',
    ]

    content_lower = content.lower()

    # 先检查失败标志
    for pattern in failure_patterns:
        if re.search(pattern, content_lower):
            return False

    # 再检查成功标志
    for pattern in success_patterns:
        if re.search(pattern, content_lower):
            return True

    # 默认认为有内容就是成功
    return len(content) > 0


def extract_user_feedback(content: str) -> Optional[str]:
    """
    提取用户反馈类型

    Returns:
        'success' | 'failure' | 'correction' | 'clarification' | None
    """
    content_lower = content.lower()

    # 成功反馈
    success_patterns = [
        r'(完成|好了|谢谢|可以了|搞定|成功|完美|正确)',
        r'(good|great|perfect|thanks|done|success)',
    ]

    # 失败反馈
    failure_patterns = [
        r'(失败|错误|不对|不行|问题|报错)',
        r'(fail|error|wrong|issue|problem)',
    ]

    # 纠正反馈
    correction_patterns = [
        r'(不对|改一下|修改|调整|应该|其实是|换成)',
        r'(wrong|change|modify|adjust|should|actually)',
    ]

    # 澄清反馈
    clarification_patterns = [
        r'(什么|为什么|怎么|如何|解释)',
        r'(what|why|how|explain)',
    ]

    for pattern in success_patterns:
        if re.search(pattern, content_lower):
            return 'success'

    for pattern in failure_patterns:
        if re.search(pattern, content_lower):
            return 'failure'

    for pattern in correction_patterns:
        if re.search(pattern, content_lower):
            return 'correction'

    for pattern in clarification_patterns:
        if re.search(pattern, content_lower):
            return 'clarification'

    return None


def find_success_indicators(extracted_data: dict) -> list[dict]:
    """
    找到成功输出的指标

    Returns:
        成功输出列表
    """
    success_indicators = []

    # 检查成功的 tool results
    for result in extracted_data.get("results", []):
        if result.get("is_success"):
            # 查找对应的 tool call
            tool_call_id = result.get("tool_call_id")
            matching_call = find_tool_call_by_id(
                extracted_data.get("tool_sequence", []),
                tool_call_id
            )

            success_indicators.append({
                "tool_call_id": tool_call_id,
                "tool_name": matching_call.get("name") if matching_call else None,
                "result_preview": result.get("content", "")[:200],
                "timestamp": result.get("timestamp")
            })

    # 检查用户成功反馈
    for feedback in extracted_data.get("user_feedback", []):
        if feedback.get("feedback_type") == "success":
            success_indicators.append({
                "type": "user_confirmation",
                "content": feedback.get("content", "")[:200],
                "timestamp": feedback.get("timestamp")
            })

    return success_indicators


def find_tool_call_by_id(tool_sequence: list[dict], tool_call_id: str) -> Optional[dict]:
    """根据 ID 查找 tool call"""
    for call in tool_sequence:
        if call.get("id") == tool_call_id:
            return call
    return None


def backward_trace(
    success_indicators: list[dict],
    tool_sequence: list[dict],
    results: list[dict]
) -> list[dict]:
    """
    逆向追踪核心步骤

    从成功输出回溯依赖的工具调用
    """
    core_steps = []
    visited_ids = set()

    # 构建结果映射
    result_map = {r.get("tool_call_id"): r for r in results}

    # 从成功标记开始
    queue = []
    for indicator in success_indicators:
        if indicator.get("tool_call_id"):
            queue.append(indicator["tool_call_id"])

    # BFS 逆向追踪
    while queue:
        current_id = queue.pop(0)

        if current_id in visited_ids:
            continue

        visited_ids.add(current_id)

        # 找到对应的 tool call
        call = find_tool_call_by_id(tool_sequence, current_id)
        if call:
            core_steps.append(call)

            # 分析参数中的依赖（简化版）
            args = call.get("arguments", {})
            for key, value in args.items():
                # 如果参数引用了之前的输出，添加依赖
                if isinstance(value, str) and value in [r.get("tool_call_id") for r in results]:
                    queue.append(value)

    # 按执行顺序排序（原始索引）
    core_steps.sort(key=lambda x: x.get("index", 0))

    return core_steps


def identify_dependencies(core_steps: list[dict]) -> dict[str, list[str]]:
    """
    识别步骤间的依赖关系

    Returns:
        {step_id: [dependency_step_ids]}
    """
    dependencies = {}

    for i, step in enumerate(core_steps):
        step_id = step.get("id", str(i))
        dependencies[step_id] = []

        # 简单规则：每个步骤依赖于前一个步骤
        if i > 0:
            prev_step_id = core_steps[i - 1].get("id", str(i - 1))
            dependencies[step_id].append(prev_step_id)

    return dependencies


def identify_failed_attempts(
    tool_sequence: list[dict],
    results: list[dict],
    user_feedback: list[dict]
) -> list[dict]:
    """
    识别失败的尝试
    """
    failed_attempts = []
    result_map = {r.get("tool_call_id"): r for r in results}

    for call in tool_sequence:
        call_id = call.get("id")
        result = result_map.get(call_id)

        if result and not result.get("is_success"):
            failed_attempts.append({
                "tool_call_id": call_id,
                "tool_name": call.get("name"),
                "arguments": call.get("arguments"),
                "error_preview": result.get("content", "")[:300],
                "timestamp": call.get("timestamp")
            })

    return failed_attempts


def main():
    """主函数 - 用于测试"""
    # 示例输入
    sample_messages = [
        {"role": "user", "content": "帮我获取数据"},
        {"role": "assistant", "tool_calls": [{
            "id": "call_1",
            "function": {"name": "terminal", "arguments": '{"command": "curl http://api/data"}'}
        }]},
        {"role": "tool", "tool_call_id": "call_1", "content": '{"success": true, "data": [...], "exit_code": 0}'},
        {"role": "user", "content": "好了，保存为工作流"},
    ]

    extracted = extract_from_messages(sample_messages)
    self.logger.info(json.dumps(extracted, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
