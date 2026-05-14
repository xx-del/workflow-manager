#!/usr/bin/env python3
"""
Execution Analyzer - 执行历史分析器

职责：
1. 分析历史执行记录
2. 识别瓶颈步骤
3. 识别高频失败
4. 计算统计数据
"""

from typing import Dict, List, Any, Optional
from collections import defaultdict
from pathlib import Path
import json

# 绝对导入（兼容 CLI 调用）
import sys
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.history import history_manager


class ExecutionAnalyzer:
    """执行历史分析器"""
    
    def __init__(self):
        pass
    
    def analyze_history(self, workflow_path: str, days: int = 30) -> Dict[str, Any]:
        """
        分析历史执行记录
        
        Args:
            workflow_path: 工作流目录路径
            days: 分析天数
            
        Returns:
            分析结果
        """
        
        stats = history_manager.get_statistics(workflow_path, days)
        recent = history_manager.get_recent(workflow_path, limit=50)
        
        # 分析步骤级数据
        step_stats = self._analyze_steps(recent)
        
        return {
            'statistics': stats,
            'step_statistics': step_stats,
            'recent_runs': len(recent),
            'analysis_period_days': days,
        }
    
    def _analyze_steps(self, records: List[Dict]) -> Dict[str, Any]:
        """分析步骤级数据"""
        step_data = defaultdict(lambda: {
            'count': 0,
            'success': 0,
            'failed': 0,
            'total_duration': 0,
            'durations': [],
        })
        
        for record in records:
            steps = record.get('steps', [])
            for step in steps:
                step_name = step.get('name', 'unknown')
                step_data[step_name]['count'] += 1
                
                if step.get('success'):
                    step_data[step_name]['success'] += 1
                else:
                    step_data[step_name]['failed'] += 1
                
                duration = step.get('duration', 0)
                step_data[step_name]['total_duration'] += duration
                step_data[step_name]['durations'].append(duration)
        
        # 计算统计值
        result = {}
        for step_name, data in step_data.items():
            durations = data['durations']
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            result[step_name] = {
                'count': data['count'],
                'success_rate': round(data['success'] / data['count'] * 100, 2) if data['count'] > 0 else 0,
                'failed_count': data['failed'],
                'avg_duration': round(avg_duration, 2),
                'total_duration': data['total_duration'],
            }
        
        return result
    
    def identify_bottlenecks(
        self,
        workflow_path: str,
        threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        识别瓶颈步骤
        
        Args:
            workflow_path: 工作流目录路径
            threshold: 阈值（占总时间的比例）
            
        Returns:
            瓶颈步骤列表
        """
        analysis = self.analyze_history(workflow_path)
        step_stats = analysis.get('step_statistics', {})
        
        if not step_stats:
            return []
        
        # 计算总时间
        total_duration = sum(
            s['total_duration'] for s in step_stats.values()
        )
        
        if total_duration == 0:
            return []
        
        bottlenecks = []
        
        for step_name, stats in step_stats.items():
            ratio = stats['total_duration'] / total_duration
            
            if ratio >= threshold:
                bottlenecks.append({
                    'step': step_name,
                    'duration_ratio': round(ratio * 100, 2),
                    'avg_duration': stats['avg_duration'],
                    'suggestion': f'该步骤占总执行时间的 {round(ratio * 100, 1)}%，考虑优化或并行化',
                })
        
        # 按时间占比排序
        bottlenecks.sort(key=lambda x: x['duration_ratio'], reverse=True)
        
        return bottlenecks
    
    def identify_failures(
        self,
        workflow_path: str,
        min_count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        识别高频失败步骤
        
        Args:
            workflow_path: 工作流目录路径
            min_count: 最小失败次数
            
        Returns:
            高频失败步骤列表
        """
        analysis = self.analyze_history(workflow_path)
        step_stats = analysis.get('step_statistics', {})
        
        failures = []
        
        for step_name, stats in step_stats.items():
            if stats['failed_count'] >= min_count:
                failures.append({
                    'step': step_name,
                    'failed_count': stats['failed_count'],
                    'success_rate': stats['success_rate'],
                    'suggestion': f'该步骤失败 {stats["failed_count"]} 次，建议检查配置或增加重试',
                })
        
        # 按失败次数排序
        failures.sort(key=lambda x: x['failed_count'], reverse=True)
        
        return failures
    
    def calculate_statistics(self, workflow_path: str) -> Dict[str, Any]:
        """
        计算详细统计数据
        
        Args:
            workflow_path: 工作流目录路径
            
        Returns:
            统计数据
        """
        from ..tools.history import history_manager
        
        stats = history_manager.get_statistics(workflow_path, days=30)
        
        # 添加趋势分析
        recent = history_manager.get_recent(workflow_path, limit=10)
        
        if len(recent) >= 3:
            # 计算成功率趋势
            recent_success = sum(1 for r in recent[:3] if r.get('status') == 'completed')
            older_success = sum(1 for r in recent[3:6] if r.get('status') == 'completed')
            
            if older_success > 0:
                trend = (recent_success / 3) - (older_success / 3)
                stats['success_rate_trend'] = round(trend * 100, 2)
            else:
                stats['success_rate_trend'] = 0
        else:
            stats['success_rate_trend'] = 0
        
        return stats


# 单例实例
execution_analyzer = ExecutionAnalyzer()