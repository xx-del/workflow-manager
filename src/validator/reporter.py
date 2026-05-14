#!/usr/bin/env python3
"""
Validation Reporter - 校验报告生成器

职责：
1. 生成校验报告
2. 格式化错误、警告、建议
3. 生成交互式修复建议
"""

from typing import Dict, List, Any, Optional


class ValidationReporter:
    """校验报告生成器"""
    
    def __init__(self):
        pass
    
    def generate_report(
        self,
        workflow_name: str,
        structure_result: Dict,
        simulation_result: Dict = None
    ) -> str:
        """
        生成校验报告
        
        Args:
            workflow_name: 工作流名称
            structure_result: 结构检查结果
            simulation_result: 模拟执行结果（可选）
            
        Returns:
            Markdown 格式报告
        """
        lines = [
            f'# 工作流校验报告',
            '',
            f'**工作流**: {workflow_name}',
        ]
        
        # 判断整体状态
        has_errors = (
            not structure_result.get('valid', True) or
            (simulation_result and not simulation_result.get('success', True))
        )
        
        if has_errors:
            lines.append('**状态**: 🔴 无法执行')
        elif structure_result.get('warnings') or (simulation_result and simulation_result.get('issues', {}).get('warnings')):
            lines.append('**状态**: 🟡 可能失败')
        else:
            lines.append('**状态**: ✅ 可以执行')
        
        lines.append('')
        lines.append('---')
        lines.append('')
        
        # 错误部分
        errors = structure_result.get('errors', [])
        if simulation_result:
            errors.extend(simulation_result.get('issues', {}).get('errors', []))
        
        if errors:
            lines.append(f'### 🔴 错误 ({len(errors)} 个)')
            lines.append('')
            
            for i, error in enumerate(errors, 1):
                lines.append(f'#### {i}. {self._get_error_title(error)}')
                lines.append(f'**步骤**: {error.get("step", "-")} - {error.get("name", "-")}')
                lines.append(f'**问题描述**: {error.get("message", str(error))}')
                
                fix = self._suggest_fix(error)
                if fix:
                    lines.append(f'**修复方案**: {fix}')
                
                lines.append('')
        
        # 警告部分
        warnings = structure_result.get('warnings', [])
        if simulation_result:
            warnings.extend(simulation_result.get('issues', {}).get('warnings', []))
        
        if warnings:
            lines.append(f'### 🟡 警告 ({len(warnings)} 个)')
            lines.append('')
            
            for i, warning in enumerate(warnings, 1):
                lines.append(f'#### {i}. {self._get_warning_title(warning)}')
                lines.append(f'**建议**: {warning.get("message", str(warning))}')
                lines.append('')
        
        # 建议部分
        suggestions = []
        if simulation_result:
            suggestions = simulation_result.get('issues', {}).get('suggestions', [])
        
        if suggestions:
            lines.append(f'### 🔵 建议 ({len(suggestions)} 个)')
            lines.append('')
            
            for i, suggestion in enumerate(suggestions, 1):
                lines.append(f'#### {i}. {self._get_suggestion_title(suggestion)}')
                lines.append(f'**预期收益**: {suggestion.get("message", str(suggestion))}')
                lines.append('')
        
        lines.append('---')
        lines.append('')
        
        # 总结
        lines.append('## 总结')
        lines.append('')
        lines.append(f'- 错误: {len(errors)} 个')
        lines.append(f'- 警告: {len(warnings)} 个')
        lines.append(f'- 建议: {len(suggestions)} 个')
        
        return '\n'.join(lines)
    
    def _get_error_title(self, error: Dict) -> str:
        """获取错误标题"""
        error_type = error.get('type', 'unknown')
        
        titles = {
            'missing_field': '缺少必需字段',
            'empty_nodes': '没有定义步骤',
            'missing_node_field': '节点缺少字段',
            'duplicate_id': '节点 ID 重复',
            'missing_dependency': '依赖不存在',
            'self_dependency': '自依赖错误',
            'syntax_error': '语法错误',
            'dangerous_command': '危险命令',
            'document_not_found': '文档不存在',
        }
        
        return titles.get(error_type, '未知错误')
    
    def _get_warning_title(self, warning: Dict) -> str:
        """获取警告标题"""
        warning_type = warning.get('type', 'unknown')
        
        titles = {
            'missing_capabilities': '缺少能力定义',
            'parameter_reference': '参数引用',
            'missing_retry_config': '重试配置不完整',
            'missing_notify_config': '通知配置不完整',
            'missing_guardian_config': '守护配置不完整',
        }
        
        return titles.get(warning_type, '警告')
    
    def _get_suggestion_title(self, suggestion: Dict) -> str:
        """获取建议标题"""
        suggestion_type = suggestion.get('type', 'unknown')
        
        titles = {
            'output_redirect': '输出重定向',
            'code_input': '代码输入文件',
            'code_output': '代码输出文件',
            'long_timeout': '超时时间较长',
        }
        
        return titles.get(suggestion_type, '建议')
    
    def _suggest_fix(self, error: Dict) -> Optional[str]:
        """生成修复建议"""
        error_type = error.get('type', '')
        
        fixes = {
            'missing_field': '在 _index.yaml 中添加缺失的字段',
            'empty_nodes': '在 _index.yaml 中定义至少一个步骤',
            'missing_node_field': '为节点添加缺失的字段',
            'duplicate_id': '修改节点 ID 使其唯一',
            'missing_dependency': '检查 depends_on 字段，确保引用的节点 ID 正确',
            'self_dependency': '移除节点的自依赖',
            'syntax_error': '检查命令或代码语法',
            'dangerous_command': '移除或修改危险命令',
            'document_not_found': '检查文档路径是否正确',
        }
        
        return fixes.get(error_type)
    
    def format_error(self, error: Dict) -> str:
        """格式化单个错误"""
        return f"🔴 [{error.get('type', 'error')}] {error.get('message', str(error))}"
    
    def format_warning(self, warning: Dict) -> str:
        """格式化单个警告"""
        return f"🟡 [{warning.get('type', 'warning')}] {warning.get('message', str(warning))}"
    
    def format_suggestion(self, suggestion: Dict) -> str:
        """格式化单个建议"""
        return f"🔵 [{suggestion.get('type', 'suggestion')}] {suggestion.get('message', str(suggestion))}"


# 单例实例
validation_reporter = ValidationReporter()