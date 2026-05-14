"""
Extractor Module - 工作流提取层

从会话上下文提取工作流定义
"""

# 先导入底层模块，再导入 pipeline（避免循环导入）
from .extractor import (
    extract_from_messages,
    find_success_indicators,
    backward_trace,
    identify_dependencies,
    identify_failed_attempts,
)
from .correction_analyzer import CorrectionAnalyzer
from .param_abstractor import ParameterAbstractor
from .generator import WorkflowGenerator, generate_workflow_name
from .ai_enhancer import AIEnhancer
from .pipeline import WorkflowExtractorPipeline

__all__ = [
    'WorkflowExtractorPipeline',
    'extract_from_messages',
    'find_success_indicators',
    'backward_trace',
    'identify_dependencies',
    'identify_failed_attempts',
    'CorrectionAnalyzer',
    'ParameterAbstractor',
    'WorkflowGenerator',
    'generate_workflow_name',
    'AIEnhancer',
]
