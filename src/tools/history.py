#!/usr/bin/env python3
"""
History Manager - 历史记录管理器

职责：
1. 追加执行记录到历史文件
2. 获取最近的执行记录
3. 计算执行统计
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from utils.logger import get_logger


class HistoryManager:
    """历史记录管理器"""
    
    def __init__(self):

        self.logger = get_logger(__name__)
        pass
    
    def append(self, workflow_path: str, record: Dict[str, Any]) -> bool:
        """
        追加执行记录到历史文件
        
        Args:
            workflow_path: 工作流目录路径
            record: 执行记录
            
        Returns:
            是否成功
        """
        history_dir = Path(workflow_path) / "history"
        today = datetime.now().strftime("%Y-%m-%d")
        history_file = history_dir / f"{today}.json"
        
        try:
            # 确保目录存在
            history_dir.mkdir(parents=True, exist_ok=True)
            
            # 读取现有历史
            history = []
            if history_file.exists():
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                        if not isinstance(history, list):
                            history = []
                except:
                    history = []
            
            # 添加时间戳
            if 'timestamp' not in record:
                record['timestamp'] = datetime.now().isoformat()
            
            # 追加记录
            history.append(record)
            
            # 写入文件
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"[HistoryManager] 追加记录失败: {e}")
            return False
    
    def get_recent(self, workflow_path: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的执行记录
        
        Args:
            workflow_path: 工作流目录路径
            limit: 最大记录数
            
        Returns:
            执行记录列表
        """
        history_dir = Path(workflow_path) / "history"
        
        if not history_dir.exists():
            return []
        
        records = []
        
        try:
            # 遍历历史文件（按日期倒序）
            history_files = sorted(
                history_dir.glob("*.json"),
                key=lambda p: p.stem,
                reverse=True
            )
            
            for hf in history_files:
                try:
                    with open(hf, 'r', encoding='utf-8') as f:
                        file_records = json.load(f)
                        if isinstance(file_records, list):
                            records.extend(file_records)
                except:
                    pass
                
                if len(records) >= limit:
                    break
            
            # 按时间戳排序并截取
            records = sorted(
                records,
                key=lambda r: r.get('timestamp', ''),
                reverse=True
            )[:limit]
            
            return records
            
        except Exception as e:
            self.logger.error(f"[HistoryManager] 获取记录失败: {e}")
            return []
    
    def get_statistics(self, workflow_path: str, days: int = 30) -> Dict[str, Any]:
        """
        获取执行统计
        
        Args:
            workflow_path: 工作流目录路径
            days: 统计天数
            
        Returns:
            统计数据
        """
        history_dir = Path(workflow_path) / "history"
        
        if not history_dir.exists():
            return {
                'total_runs': 0,
                'success_rate': 0,
                'avg_duration': 0,
                'total_success': 0,
                'total_failed': 0,
            }
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        stats = {
            'total_runs': 0,
            'success_runs': 0,
            'failed_runs': 0,
            'partial_runs': 0,
            'total_duration': 0,
            'durations': [],
        }
        
        try:
            for hf in history_dir.glob("*.json"):
                # 检查日期
                try:
                    file_date = datetime.strptime(hf.stem, "%Y-%m-%d")
                    if file_date < cutoff_date:
                        continue
                except:
                    continue
                
                try:
                    with open(hf, 'r', encoding='utf-8') as f:
                        records = json.load(f)
                        if not isinstance(records, list):
                            continue
                        
                        for r in records:
                            stats['total_runs'] += 1
                            
                            status = r.get('status', '')
                            if status == 'completed':
                                stats['success_runs'] += 1
                            elif status == 'failed':
                                stats['failed_runs'] += 1
                            elif status == 'partial':
                                stats['partial_runs'] += 1
                            
                            duration = r.get('duration', 0)
                            if duration > 0:
                                stats['total_duration'] += duration
                                stats['durations'].append(duration)
                                
                except:
                    pass
            
            # 计算统计值
            avg_duration = 0
            if stats['durations']:
                avg_duration = sum(stats['durations']) / len(stats['durations'])
            
            success_rate = 0
            if stats['total_runs'] > 0:
                success_rate = stats['success_runs'] / stats['total_runs'] * 100
            
            return {
                'total_runs': stats['total_runs'],
                'success_runs': stats['success_runs'],
                'failed_runs': stats['failed_runs'],
                'partial_runs': stats['partial_runs'],
                'success_rate': round(success_rate, 2),
                'avg_duration': round(avg_duration, 2),
                'total_success': stats['success_runs'],
                'total_failed': stats['failed_runs'] + stats['partial_runs'],
            }
            
        except Exception as e:
            self.logger.error(f"[HistoryManager] 统计失败: {e}")
            return {
                'total_runs': 0,
                'success_rate': 0,
                'avg_duration': 0,
                'total_success': 0,
                'total_failed': 0,
                'error': str(e),
            }


# 单例实例
history_manager = HistoryManager()
