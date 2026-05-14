#!/usr/bin/env python3
"""
Result Consolidator - 结果汇总器

职责：
1. 汇总所有步骤结果
2. 确定整体状态
3. 收集输出文件
4. 生成执行报告
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from utils.logger import get_logger


class ResultConsolidator:
    """结果汇总器"""
    
    def __init__(self):

        self.logger = get_logger(__name__)
        pass
    
    async def consolidate(
        self,
        results: List[Dict],
        workflow: Dict
    ) -> Dict[str, Any]:
        """
        汇总结果
        
        Args:
            results: 执行结果数组
            workflow: 工作流信息
            
        Returns:
            汇总结果
        """
        consolidated = {
            'workflow': workflow['name'],
            'status': self._determine_status(results),
            'total_steps': len(results),
            'successful_steps': sum(1 for r in results if r.get('success')),
            'failed_steps': sum(1 for r in results if not r.get('success')),
            'duration': self._calculate_total_duration(results),
            'steps': self._format_steps(results),
            'outputs': await self._collect_outputs(workflow),
            'summary': '',
            'timestamp': datetime.now().isoformat(),
        }
        
        # 生成摘要
        consolidated['summary'] = self._generate_summary(consolidated)
        
        self.logger.info(f"    状态: {consolidated['status']}")
        self.logger.info(f"    成功: {consolidated['successful_steps']}/{consolidated['total_steps']}")
        
        return consolidated
    
    def _determine_status(self, results: List[Dict]) -> str:
        """确定整体状态"""
        if not results:
            return 'unknown'
        
        if all(r.get('success') for r in results):
            return 'completed'
        
        if any(r.get('success') for r in results):
            return 'partial'
        
        return 'failed'
    
    def _calculate_total_duration(self, results: List[Dict]) -> Dict:
        """计算总耗时"""
        total = sum(r.get('duration') or 0 for r in results)
        
        return {
            'seconds': total,
            'formatted': self._format_duration(total),
        }
    
    def _format_duration(self, seconds: int) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}m {secs}s"
        else:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            return f"{hours}h {mins}m"
    
    def _format_steps(self, results: List[Dict]) -> List[Dict]:
        """格式化步骤结果"""
        formatted = []
        
        for i, r in enumerate(results):
            step = {
                'step': i + 1,
                'id': r.get('id'),
                'name': r.get('name', f'Step {i + 1}'),
                'status': 'success' if r.get('success') else 'failed',
                'duration': r.get('duration', 0),
                'agent_id': r.get('agent_id'),
                'output': None,
                'error': None,
            }
            
            if r.get('output'):
                output = str(r['output'])
                step['output'] = output[:500] if len(output) > 500 else output
            
            if r.get('error'):
                step['error'] = str(r['error'])
            
            formatted.append(step)
        
        return formatted
    
    async def _collect_outputs(self, workflow: Dict) -> List[Dict]:
        """收集输出文件"""
        outputs = []
        output_dir = Path(workflow['path']) / 'outputs'
        
        if not output_dir.exists():
            return outputs
        
        try:
            for file_path in output_dir.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    outputs.append({
                        'name': file_path.name,
                        'path': str(file_path),
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
        except Exception as e:
            self.logger.error(f"[ResultConsolidator] 收集输出失败: {e}")
        
        return outputs
    
    def _generate_summary(self, consolidated: Dict) -> str:
        """生成摘要"""
        lines = [
            '## 工作流执行报告',
            '',
            f"**工作流**: {consolidated['workflow']}",
        ]
        
        status = consolidated['status']
        if status == 'completed':
            lines.append('**状态**: ✅ 成功完成')
        elif status == 'partial':
            lines.append('**状态**: ⚠️ 部分成功')
        else:
            lines.append('**状态**: ❌ 失败')
        
        lines.extend([
            f"**总步骤**: {consolidated['total_steps']}",
            f"**成功**: {consolidated['successful_steps']}",
            f"**失败**: {consolidated['failed_steps']}",
            f"**耗时**: {consolidated['duration']['formatted']}",
            '',
        ])
        
        if consolidated['outputs']:
            lines.append('**输出文件**:')
            for output in consolidated['outputs']:
                size_kb = output['size'] / 1024
                lines.append(f"  - {output['name']} ({size_kb:.2f} KB)")
        
        return '\n'.join(lines)
    
    def generate_markdown_report(self, consolidated: Dict) -> str:
        """生成 Markdown 格式报告"""
        lines = [
            f"# 工作流执行报告",
            '',
            f"**工作流**: {consolidated['workflow']}",
            f"**状态**: {consolidated['status']}",
            f"**时间**: {consolidated['timestamp']}",
            f"**耗时**: {consolidated['duration']['formatted']}",
            '',
            '## 步骤详情',
            '',
        ]
        
        for step in consolidated['steps']:
            status_icon = '✅' if step['status'] == 'success' else '❌'
            lines.append(f"### {status_icon} 步骤 {step['step']}: {step['name']}")
            lines.append(f"- 状态: {step['status']}")
            lines.append(f"- 耗时: {step['duration']}s")
            
            if step.get('agent_id'):
                lines.append(f"- Agent: {step['agent_id']}")
            
            if step.get('error'):
                lines.append(f"- 错误: {step['error']}")
            
            lines.append('')
        
        if consolidated['outputs']:
            lines.append('## 输出文件')
            lines.append('')
            for output in consolidated['outputs']:
                size_kb = output['size'] / 1024
                lines.append(f"- `{output['name']}` ({size_kb:.2f} KB)")
            lines.append('')
        
        return '\n'.join(lines)


# 单例实例
result_consolidator = ResultConsolidator()
