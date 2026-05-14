#!/usr/bin/env python3
"""
Workflow Simulator - 工作流模拟执行器

职责：
1. 模拟执行工作流（不真实执行）
2. 检查命令语法、依赖、环境
3. 检查代码逻辑、输入输出
4. 检查文档引用、格式
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional


class WorkflowSimulator:
    """工作流模拟执行器"""
    
    def __init__(self):
        self.command_patterns = {
            'curl': r'^curl\s+',
            'wget': r'^wget\s+',
            'python': r'^python\d*\s+',
            'bash': r'^bash\s+',
            'git': r'^git\s+',
            'ssh': r'^ssh\s+',
            'npm': r'^npm\s+',
            'docker': r'^docker\s+',
        }
    
    def simulate(self, workflow: Dict) -> Dict[str, Any]:
        """
        模拟执行工作流
        
        Args:
            workflow: 工作流定义
            
        Returns:
            模拟结果 {success, issues, suggestions}
        """
        issues = {
            'errors': [],
            'warnings': [],
            'suggestions': [],
        }
        
        # 模拟每个步骤
        for i, node in enumerate(workflow.get('nodes', [])):
            step_issues = self.simulate_step(node, workflow, i + 1)
            issues['errors'].extend(step_issues.get('errors', []))
            issues['warnings'].extend(step_issues.get('warnings', []))
            issues['suggestions'].extend(step_issues.get('suggestions', []))
        
        return {
            'success': len(issues['errors']) == 0,
            'issues': issues,
            'total_steps': len(workflow.get('nodes', [])),
            'error_count': len(issues['errors']),
            'warning_count': len(issues['warnings']),
            'suggestion_count': len(issues['suggestions']),
        }
    
    def simulate_step(
        self,
        step: Dict,
        workflow: Dict,
        step_num: int
    ) -> Dict[str, List]:
        """模拟单个步骤"""
        issues = {
            'errors': [],
            'warnings': [],
            'suggestions': [],
        }
        
        step_name = step.get('name', f'Step {step_num}')
        
        # 检查命令
        if step.get('command'):
            cmd_issues = self.check_command(step['command'], step_num, step_name)
            issues['errors'].extend(cmd_issues.get('errors', []))
            issues['warnings'].extend(cmd_issues.get('warnings', []))
            issues['suggestions'].extend(cmd_issues.get('suggestions', []))
        
        # 检查代码
        if step.get('code'):
            code_issues = self.check_code(step['code'], step_num, step_name)
            issues['errors'].extend(code_issues.get('errors', []))
            issues['warnings'].extend(code_issues.get('warnings', []))
            issues['suggestions'].extend(code_issues.get('suggestions', []))
        
        # 检查文档
        if step.get('document'):
            doc_issues = self.check_document(step['document'], workflow, step_num, step_name)
            issues['errors'].extend(doc_issues.get('errors', []))
            issues['warnings'].extend(doc_issues.get('warnings', []))
            issues['suggestions'].extend(doc_issues.get('suggestions', []))
        
        # 检查能力
        if not step.get('capabilities'):
            issues['warnings'].append({
                'step': step_num,
                'name': step_name,
                'type': 'missing_capabilities',
                'message': '步骤缺少能力定义',
            })
        
        # 检查超时
        if step.get('timeout') and step['timeout'] > 3600:
            issues['suggestions'].append({
                'step': step_num,
                'name': step_name,
                'type': 'long_timeout',
                'message': f"超时时间较长 ({step['timeout']}s)，建议检查是否合理",
            })
        
        return issues
    
    def check_command(
        self,
        command: str,
        step_num: int,
        step_name: str
    ) -> Dict[str, List]:
        """检查命令"""
        issues = {
            'errors': [],
            'warnings': [],
            'suggestions': [],
        }
        
        # 检查语法
        # 检查未闭合的引号
        single_quotes = command.count("'") - command.count("\\'")
        double_quotes = command.count('"') - command.count('\\"')
        
        if single_quotes % 2 != 0:
            issues['errors'].append({
                'step': step_num,
                'name': step_name,
                'type': 'syntax_error',
                'message': '命令中存在未闭合的单引号',
                'command': command[:100],
            })
        
        if double_quotes % 2 != 0:
            issues['errors'].append({
                'step': step_num,
                'name': step_name,
                'type': 'syntax_error',
                'message': '命令中存在未闭合的双引号',
                'command': command[:100],
            })
        
        # 检查参数替换
        param_pattern = r'\{\{(\w+)\}\}'
        params = re.findall(param_pattern, command)
        for param in params:
            issues['warnings'].append({
                'step': step_num,
                'name': step_name,
                'type': 'parameter_reference',
                'message': f'命令引用参数 {{{{{param}}}}}，需确保参数已定义',
                'parameter': param,
            })
        
        # 检查危险命令
        dangerous_patterns = [
            (r'\brm\s+-rf\s+/', '危险：rm -rf / 可能删除系统文件'),
            (r'\brm\s+-rf\s+~', '危险：rm -rf ~ 可能删除用户目录'),
            (r'\bdd\s+if=.*of=/dev/', '危险：dd 写入设备可能破坏数据'),
            (r'\bmkfs\.', '危险：格式化命令'),
            (r'>\s*/dev/sd[a-z]', '危险：直接写入磁盘设备'),
        ]
        
        for pattern, message in dangerous_patterns:
            if re.search(pattern, command):
                issues['errors'].append({
                    'step': step_num,
                    'name': step_name,
                    'type': 'dangerous_command',
                    'message': message,
                    'command': command[:100],
                })
        
        # 检查输出重定向
        redirect_match = re.search(r'>\s*([^\s;|]+)', command)
        if redirect_match:
            output_path = redirect_match.group(1)
            issues['suggestions'].append({
                'step': step_num,
                'name': step_name,
                'type': 'output_redirect',
                'message': f'命令输出到 {output_path}，建议在 outputs 中声明',
                'output': output_path,
            })
        
        return issues
    
    def check_code(
        self,
        code: str,
        step_num: int,
        step_name: str
    ) -> Dict[str, List]:
        """检查代码"""
        issues = {
            'errors': [],
            'warnings': [],
            'suggestions': [],
        }
        
        # 检查语法错误（简单检查）
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            issues['errors'].append({
                'step': step_num,
                'name': step_name,
                'type': 'syntax_error',
                'message': f'代码语法错误: {e.msg} (行 {e.lineno})',
                'line': e.lineno,
            })
        
        # 检查输入输出
        input_pattern = r'(?:open|read_file|load)\s*\(\s*[\'"]([^\'"]+)[\'"]'
        output_pattern = r'(?:open|write_file|dump)\s*\([^)]*[\'"]([^\'"]+)[\'"]'
        
        inputs = re.findall(input_pattern, code)
        outputs = re.findall(output_pattern, code)
        
        for inp in inputs:
            issues['suggestions'].append({
                'step': step_num,
                'name': step_name,
                'type': 'code_input',
                'message': f'代码读取文件 {inp}，需确保文件存在',
                'input': inp,
            })
        
        for out in outputs:
            issues['suggestions'].append({
                'step': step_num,
                'name': step_name,
                'type': 'code_output',
                'message': f'代码写入文件 {out}，建议在 outputs 中声明',
                'output': out,
            })
        
        return issues
    
    def check_document(
        self,
        document: str,
        workflow: Dict,
        step_num: int,
        step_name: str
    ) -> Dict[str, List]:
        """检查文档"""
        issues = {
            'errors': [],
            'warnings': [],
            'suggestions': [],
        }
        
        workflow_path = Path(workflow.get('path', '.'))
        
        # 检查文件是否存在
        if not Path(document).is_absolute():
            doc_path = workflow_path / document
        else:
            doc_path = Path(document)
        
        if not doc_path.exists():
            issues['errors'].append({
                'step': step_num,
                'name': step_name,
                'type': 'document_not_found',
                'message': f'文档不存在: {document}',
                'path': str(doc_path),
            })
        
        return issues


# 单例实例
workflow_simulator = WorkflowSimulator()