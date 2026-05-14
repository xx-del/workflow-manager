#!/usr/bin/env python3
"""
Optimization Applicator - 优化建议应用器

职责：
1. 应用优化建议
2. 备份当前版本
3. 回退到上一版本
"""

from utils.logger import get_logger
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class OptimizationApplicator:
    """优化建议应用器"""
    
    def __init__(self):

        self.logger = get_logger(__name__)
        pass
    
    def apply(
        self,
        workflow_path: str,
        suggestion_id: str
    ) -> Dict[str, Any]:
        """
        应用优化建议
        
        Args:
            workflow_path: 工作流目录路径
            suggestion_id: 建议ID
            
        Returns:
            应用结果
        """
        from .suggester import optimization_suggester
        
        # 加载建议
        data = optimization_suggester.load_suggestions(workflow_path)
        
        if not data:
            return {
                'success': False,
                'error': '未找到优化建议文件',
            }
        
        # 查找目标建议
        target = None
        for s in data.get('suggestions', []):
            if s.get('id') == suggestion_id:
                target = s
                break
        
        if not target:
            return {
                'success': False,
                'error': f'未找到建议: {suggestion_id}',
            }
        
        # 备份当前版本
        backup_path = self.backup(workflow_path)
        
        if not backup_path:
            return {
                'success': False,
                'error': '备份失败',
            }
        
        # 应用建议（这里需要根据具体建议类型实现）
        # 目前返回占位结果
        result = {
            'success': True,
            'suggestion': target,
            'backup_path': backup_path,
            'applied_at': datetime.now().isoformat(),
        }
        
        # 更新建议状态
        target['status'] = 'applied'
        target['applied_at'] = datetime.now().isoformat()
        optimization_suggester.save_suggestions(workflow_path, data['suggestions'])
        
        return result
    
    def backup(self, workflow_path: str) -> Optional[str]:
        """
        备份当前版本
        
        Args:
            workflow_path: 工作流目录路径
            
        Returns:
            备份路径或 None
        """
        try:
            workflow_path = Path(workflow_path)
            index_path = workflow_path / '_index.yaml'
            
            if not index_path.exists():
                return None
            
            # 创建备份
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = workflow_path / f'_index.yaml.bak_{timestamp}'
            
            shutil.copy2(index_path, backup_path)
            
            self.logger.info(f"[OptimizationApplicator] 已备份到: {backup_path}")
            
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"[OptimizationApplicator] 备份失败: {e}")
            return None
    
    def rollback(self, workflow_path: str) -> Dict[str, Any]:
        """
        回退到上一版本
        
        Args:
            workflow_path: 工作流目录路径
            
        Returns:
            回退结果
        """
        try:
            workflow_path = Path(workflow_path)
            
            # 查找最新的备份
            backups = sorted(
                workflow_path.glob('_index.yaml.bak_*'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            if not backups:
                return {
                    'success': False,
                    'error': '未找到备份文件',
                }
            
            latest_backup = backups[0]
            index_path = workflow_path / '_index.yaml'
            
            # 恢复
            shutil.copy2(latest_backup, index_path)
            
            return {
                'success': True,
                'backup_used': str(latest_backup),
                'rolled_back_at': datetime.now().isoformat(),
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    def list_backups(self, workflow_path: str) -> list:
        """
        列出所有备份
        
        Args:
            workflow_path: 工作流目录路径
            
        Returns:
            备份列表
        """
        workflow_path = Path(workflow_path)
        
        backups = []
        for backup in workflow_path.glob('_index.yaml.bak_*'):
            stat = backup.stat()
            backups.append({
                'path': str(backup),
                'name': backup.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        
        # 按修改时间排序
        backups.sort(key=lambda x: x['modified'], reverse=True)
        
        return backups


# 单例实例
optimization_applicator = OptimizationApplicator()