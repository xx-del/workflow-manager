#!/usr/bin/env python3
"""
Optimization Suggester - 优化建议生成器

职责：
1. 生成优化建议
2. 按风险/收益排序
3. 生成修改 diff
"""

from utils.logger import get_logger
from typing import Dict, List, Any, Optional
from datetime import datetime


class OptimizationSuggester:
    """优化建议生成器"""
    
    def __init__(self):

        self.logger = get_logger(__name__)
        self.risk_levels = {
            'low': '✅',
            'medium': '⚠️',
            'high': '🔴',
        }
    
    def generate_suggestions(
        self,
        workflow_path: str,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        生成优化建议
        
        Args:
            workflow_path: 工作流目录路径
            analysis: 执行分析结果
            
        Returns:
            优化建议列表
        """
        suggestions = []
        
        # 基于瓶颈生成建议
        from .analyzer import execution_analyzer
        bottlenecks = execution_analyzer.identify_bottlenecks(workflow_path)
        
        for b in bottlenecks:
            suggestions.append({
                'id': f'optimize-{len(suggestions) + 1}',
                'type': 'performance',
                'title': f'优化步骤: {b["step"]}',
                'risk': 'medium',
                'step': b['step'],
                'problem': f'执行时间占比 {b["duration_ratio"]}%',
                'suggestion': '考虑拆分步骤或并行执行',
                'expected_benefit': '预计减少执行时间 20-40%',
                'created_at': datetime.now().isoformat(),
            })
        
        # 基于失败生成建议
        failures = execution_analyzer.identify_failures(workflow_path)
        
        for f in failures:
            suggestions.append({
                'id': f'optimize-{len(suggestions) + 1}',
                'type': 'reliability',
                'title': f'增强步骤可靠性: {f["step"]}',
                'risk': 'low',
                'step': f['step'],
                'problem': f'失败 {f["failed_count"]} 次，成功率 {f["success_rate"]}%',
                'suggestion': '增加重试次数或调整超时时间',
                'expected_benefit': '预计提升成功率 10-20%',
                'created_at': datetime.now().isoformat(),
            })
        
        # 排序建议
        suggestions = self.prioritize_suggestions(suggestions)
        
        return suggestions
    
    def prioritize_suggestions(
        self,
        suggestions: List[Dict]
    ) -> List[Dict]:
        """
        按风险/收益排序建议
        
        Args:
            suggestions: 建议列表
            
        Returns:
            排序后的建议列表
        """
        # 风险优先级
        risk_priority = {'low': 1, 'medium': 2, 'high': 3}
        
        # 按风险升序排序（低风险优先）
        suggestions.sort(key=lambda s: risk_priority.get(s.get('risk', 'medium'), 2))
        
        return suggestions
    
    def generate_diff(
        self,
        suggestion: Dict,
        current_config: Dict
    ) -> str:
        """
        生成修改 diff
        
        Args:
            suggestion: 优化建议
            current_config: 当前配置
            
        Returns:
            diff 格式字符串
        """
        lines = []
        suggestion_type = suggestion.get('type', '')
        step = suggestion.get('step', '')
        
        if suggestion_type == 'reliability':
            # 增加重试
            lines.append(f'--- a/_index.yaml')
            lines.append(f'+++ b/_index.yaml')
            lines.append(f'@@ 步骤: {step} @@')
            lines.append(f'- timeout: {current_config.get("timeout", 300)}')
            lines.append(f'+ timeout: {current_config.get("timeout", 300) + 60}')
            lines.append(f'+ retry:')
            lines.append(f'+   enabled: true')
            lines.append(f'+   max_attempts: 3')
            lines.append(f'+   interval: 60')
        
        elif suggestion_type == 'performance':
            # 拆分步骤
            lines.append(f'--- a/_index.yaml')
            lines.append(f'+++ b/_index.yaml')
            lines.append(f'@@ 步骤: {step} @@')
            lines.append(f'- {step} (单步执行)')
            lines.append(f'+ {step}_part1 (并行)')
            lines.append(f'+ {step}_part2 (并行)')
        
        return '\n'.join(lines)
    
    def save_suggestions(
        self,
        workflow_path: str,
        suggestions: List[Dict]
    ) -> bool:
        """
        保存建议到文件
        
        Args:
            workflow_path: 工作流目录路径
            suggestions: 建议列表
            
        Returns:
            是否成功
        """
        import json
        from pathlib import Path
        
        try:
            suggestions_path = Path(workflow_path) / 'optimization_suggestions.json'
            
            data = {
                'workflow_path': workflow_path,
                'created_at': datetime.now().isoformat(),
                'suggestions': suggestions,
                'status': 'pending',
            }
            
            with open(suggestions_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"[OptimizationSuggester] 保存建议失败: {e}")
            return False
    
    def load_suggestions(self, workflow_path: str) -> Optional[Dict]:
        """
        加载建议文件
        
        Args:
            workflow_path: 工作流目录路径
            
        Returns:
            建议数据或 None
        """
        import json
        from pathlib import Path
        
        try:
            suggestions_path = Path(workflow_path) / 'optimization_suggestions.json'
            
            if not suggestions_path.exists():
                return None
            
            with open(suggestions_path, 'r', encoding='utf-8') as f:
                return json.load(f)
            
        except Exception as e:
            self.logger.error(f"[OptimizationSuggester] 加载建议失败: {e}")
            return None


# 单例实例
optimization_suggester = OptimizationSuggester()