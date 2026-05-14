#!/usr/bin/env python3
"""
工作流提取管道 - 集成所有模块的完整提取流程

职责：
1. 协调各模块工作
2. 提供统一接口
3. 处理错误和边界情况
4. 输出最终 WORKFLOW.md
"""

from utils.logger import get_logger
import json
import sys
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

# 直接导入同级模块（避免循环导入）
from .extractor import (
    extract_from_messages,
    find_success_indicators,
    backward_trace,
    identify_dependencies,
    identify_failed_attempts
)
from .correction_analyzer import CorrectionAnalyzer
from .param_abstractor import ParameterAbstractor
from .generator import WorkflowGenerator, generate_workflow_name
from .ai_enhancer import AIEnhancer


class WorkflowExtractorPipeline:
    """工作流提取管道"""

    def __init__(self, output_dir: str = None, enable_ai: bool = True):
        """
        初始化管道

        Args:
            output_dir: 输出目录
            enable_ai: 是否启用 AI 增强
        """
        self.logger = get_logger(__name__)
        if output_dir is None:
            from utils.config import config as get_config
            output_dir = str(get_config.get_workflows_dir())
        self.output_dir = output_dir
        self.correction_analyzer = CorrectionAnalyzer()
        self.param_abstractor = ParameterAbstractor()
        self.generator = WorkflowGenerator()
        self.ai_enhancer = AIEnhancer(enable_ai=enable_ai)

    def extract(self, messages: list[dict], workflow_name: str = None) -> dict:
        """
        完整提取流程

        Args:
            messages: 会话消息列表
            workflow_name: 工作流名称（可选）

        Returns:
            提取结果
        """
        result = {
            'success': False,
            'workflow_name': workflow_name,
            'workflow_content': None,
            'workflow_path': None,
            'analysis': {},
            'errors': []
        }

        try:
            # Step 1: 提取会话上下文
            self.logger.info("[1/6] 提取会话上下文...")
            extracted = extract_from_messages(messages)

            if not extracted['tool_sequence']:
                result['errors'].append("会话中没有检测到工具调用")
                return result

            result['analysis']['extracted'] = {
                'total_tools': extracted['metadata']['total_tools'],
                'total_results': extracted['metadata']['total_results'],
                'total_feedback': extracted['metadata']['total_feedback']
            }

            # Step 2: 识别核心步骤
            self.logger.info("[2/6] 识别核心步骤...")
            success_indicators = find_success_indicators(extracted)

            if not success_indicators:
                result['errors'].append("未检测到成功完成的任务")
                return result

            core_steps = backward_trace(
                success_indicators,
                extracted['tool_sequence'],
                extracted['results']
            )

            # 为步骤添加名称和动作描述
            for step in core_steps:
                step['name'] = self._infer_step_name(step)
                step['action'] = self._format_action(step)
                step['outputs'] = self._infer_outputs(step, extracted['results'])

            dependencies = identify_dependencies(core_steps)

            result['analysis']['core_steps'] = {
                'count': len(core_steps),
                'step_names': [s.get('name') for s in core_steps]
            }

            # Step 3: 分析偏差纠正
            self.logger.info("[3/6] 分析偏差纠正...")
            correction_result = self.correction_analyzer.analyze(
                extracted['tool_sequence'],
                extracted['results'],
                extracted['user_feedback']
            )
            corrections = correction_result.get('corrections', [])

            result['analysis']['corrections'] = {
                'count': len(corrections),
                'types': list(set(c.get('error_type') for c in corrections))
            }

            # Step 4: 抽象参数
            self.logger.info("[4/8] 抽象参数...")
            param_result = self.param_abstractor.abstract(core_steps)
            parameters = param_result.get('parameters', [])

            result['analysis']['parameters'] = {
                'count': len(parameters),
                'names': [p.get('name') for p in parameters]
            }

            # Step 5: AI 增强（新增）
            self.logger.info("[5/8] AI 增强...")
            core_steps = self.ai_enhancer.enhance_steps(core_steps)
            parameters = self.ai_enhancer.enhance_parameters(parameters)
            corrections = self.ai_enhancer.enhance_corrections(corrections)

            # 更新分析结果
            result['analysis']['core_steps']['step_names'] = [s.get('name') for s in core_steps]
            result['analysis']['parameters']['names'] = [p.get('name') for p in parameters]

            # Step 6: 生成工作流名称和描述
            self.logger.info("[6/8] 生成工作流...")
            if not workflow_name:
                workflow_name = generate_workflow_name(core_steps)

            desc_result = self.ai_enhancer.generate_description(core_steps, corrections)
            description = desc_result.get('description', self._generate_description(core_steps, corrections))

            # Step 7: 生成 WORKFLOW.md
            self.logger.info("[7/8] 生成 WORKFLOW.md...")
            workflow_content = self.generator.generate(
                workflow_name=workflow_name,
                description=description,
                core_steps=core_steps,
                parameters=parameters,
                corrections=corrections,
                dependencies=dependencies
            )

            result['success'] = True
            result['workflow_name'] = workflow_name
            result['workflow_content'] = workflow_content
            result['analysis']['description'] = description
            result['analysis']['title'] = desc_result.get('title', workflow_name)
            result['analysis']['features'] = desc_result.get('features', [])

            # Step 8: 打印摘要
            self.logger.info("[8/8] 完成提取...")

        except Exception as e:
            result['errors'].append(f"提取过程出错: {str(e)}")
            import traceback
            traceback.print_exc()

        return result

    def save(self, result: dict, workflow_name: str = None) -> dict:
        """
        保存工作流

        Args:
            result: 提取结果
            workflow_name: 工作流名称（可选，覆盖 result 中的）

        Returns:
            保存结果
        """
        if not result.get('success'):
            return {'success': False, 'error': '提取结果无效'}

        name = workflow_name or result.get('workflow_name', 'unnamed-workflow')
        output_path = Path(self.output_dir) / name / 'WORKFLOW.md'

        saved = self.generator.save(result['workflow_content'], str(output_path))

        return {
            'success': saved,
            'workflow_name': name,
            'workflow_path': str(output_path)
        }

    def _infer_step_name(self, step: dict) -> str:
        """推断步骤名称"""
        tool = step.get('name', '')
        args = step.get('arguments', {})

        # 工具名称映射
        tool_names = {
            'terminal': '执行命令',
            'read_file': '读取文件',
            'write_file': '写入文件',
            'search_files': '搜索文件',
            'browser_navigate': '打开网页',
            'browser_click': '点击元素',
            'browser_type': '输入文本',
        }

        base_name = tool_names.get(tool, tool)

        # 根据参数细化
        if tool == 'terminal':
            command = args.get('command', '')
            if 'curl' in command:
                return '获取数据'
            elif 'python' in command:
                return '执行脚本'
            elif 'git' in command:
                return 'Git 操作'
            elif 'ssh' in command:
                return '远程执行'

        return base_name

    def _format_action(self, step: dict) -> str:
        """格式化动作描述"""
        tool = step.get('name', '')
        args = step.get('arguments', {})

        if tool == 'terminal':
            return args.get('command', '')
        elif tool == 'read_file':
            return f"读取文件: {args.get('path', '')}"
        elif tool == 'write_file':
            return f"写入文件: {args.get('path', '')}"
        elif tool == 'search_files':
            return f"搜索: {args.get('pattern', '')}"
        else:
            return json.dumps(args, ensure_ascii=False)[:100]

    def _infer_outputs(self, step: dict, results: list[dict]) -> list[str]:
        """推断步骤输出"""
        outputs = []
        tool = step.get('name', '')
        args = step.get('arguments', {})

        # 从工具参数推断
        if tool == 'write_file':
            path = args.get('path')
            if path:
                outputs.append(path)

        elif tool == 'terminal':
            command = args.get('command', '')
            # 从重定向推断
            import re
            redirect = re.search(r'>\s*([^\s;|]+)', command)
            if redirect:
                outputs.append(redirect.group(1))

        return outputs

    def _generate_description(self, core_steps: list[dict], corrections: list[dict]) -> str:
        """生成工作流描述"""
        step_names = [s.get('name', '') for s in core_steps]

        if len(step_names) == 0:
            return "自动生成的工作流"

        if len(step_names) == 1:
            return f"执行: {step_names[0]}"

        if len(step_names) == 2:
            return f"{step_names[0]}并{step_names[1]}"

        # 更多的步骤
        return f"执行 {len(step_steps)} 个步骤: {' → '.join(step_names[:3])}..."

    def print_summary(self, result: dict) -> None:
        """打印提取摘要"""
        self.logger.info("\n" + "=" * 50)
        self.logger.info("工作流提取摘要")
        self.logger.info("=" * 50)

        if not result.get('success'):
            self.logger.error("❌ 提取失败")
            for error in result.get('errors', []):
                self.logger.error(f"  - {error}")
            return

        analysis = result.get('analysis', {})

        self.logger.info(f"📋 工作流名称: {result.get('workflow_name')}")
        if analysis.get('title'):
            self.logger.info(f"📌 标题: {analysis.get('title')}")

        extracted = analysis.get('extracted', {})
        self.logger.info(f"📊 会话分析: {extracted.get('total_tools', 0)} 工具调用, "
                         f"{extracted.get('total_feedback', 0)} 用户反馈")

        steps = analysis.get('core_steps', {})
        self.logger.info(f"📝 核心步骤: {steps.get('count', 0)} 个")
        for name in steps.get('step_names', []):
            self.logger.info(f"   - {name}")

        corrections = analysis.get('corrections', {})
        if corrections.get('count', 0) > 0:
            self.logger.info(f"🔧 偏差纠正: {corrections.get('count', 0)} 处")
            for t in corrections.get('types', []):
                self.logger.info(f"   - {t}")

        params = analysis.get('parameters', {})
        if params.get('count', 0) > 0:
            self.logger.info(f"⚙️ 参数: {params.get('count', 0)} 个")
            for name in params.get('names', []):
                self.logger.info(f"   - {name}")

        if analysis.get('features'):
            self.logger.info(f"✨ 功能: {', '.join(analysis.get('features', []))}")

        self.logger.info("=" * 50)

        self.logger.info(f"\n✅ 工作流提取成功: {result.get('workflow_name')}")


def main():
    """测试函数"""
    # 模拟会话数据
    messages = [
        {'role': 'user', 'content': '获取 20260401-20260410 的数据'},
        {'role': 'assistant', 'tool_calls': [{
            'id': 'call_1',
            'function': {'name': 'terminal', 'arguments': '{"command": "curl http://api/data?date=20260401-20260410 > /x/data/result.json"}'}
        }]},
        {'role': 'tool', 'tool_call_id': 'call_1', 'content': '{"success": true}'},
        {'role': 'user', 'content': '处理一下'},
        {'role': 'assistant', 'tool_calls': [{
            'id': 'call_2',
            'function': {'name': 'terminal', 'arguments': '{"command": "python process.py --input /x/data/result.json --output /x/data/output.txt --limit 100"}'}
        }]},
        {'role': 'tool', 'tool_call_id': 'call_2', 'content': '{"success": true}'},
        {'role': 'user', 'content': '好了，保存为工作流'},
    ]

    pipeline = WorkflowExtractorPipeline()
    result = pipeline.extract(messages)
    pipeline.print_summary(result)

    if result['success']:
        self.logger.info("\n--- WORKFLOW.md 预览 ---")
        self.logger.info(result['workflow_content'][:500] + "...")


if __name__ == "__main__":
    main()
