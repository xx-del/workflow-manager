#!/usr/bin/env python3
"""
Structure Checker - 结构检查器

职责：
1. 检查 WORKFLOW.md 格式
2. 检查依赖完整性
3. 检查配置完整性
"""

from typing import Dict, List, Any, Optional
from pathlib import Path


class StructureChecker:
    """结构检查器"""
    
    def __init__(self):
        self.required_fields = ['name', 'nodes']
        self.node_required_fields = ['id', 'name']
    
    def check_structure(self, workflow: Dict) -> Dict[str, Any]:
        """
        检查工作流结构
        
        Args:
            workflow: 工作流定义
            
        Returns:
            检查结果 {valid, errors, warnings}
        """
        errors = []
        warnings = []
        
        # 检查必需字段
        for field in self.required_fields:
            if field not in workflow:
                errors.append({
                    'type': 'missing_field',
                    'message': f'缺少必需字段: {field}',
                    'field': field,
                })
        
        # 检查节点
        nodes = workflow.get('nodes', [])
        if not nodes:
            errors.append({
                'type': 'empty_nodes',
                'message': '工作流没有定义任何步骤',
            })
        else:
            node_ids = set()
            for i, node in enumerate(nodes):
                # 检查节点必需字段
                for field in self.node_required_fields:
                    if field not in node:
                        errors.append({
                            'type': 'missing_node_field',
                            'message': f'节点 {i + 1} 缺少字段: {field}',
                            'node_index': i,
                            'field': field,
                        })
                
                # 检查 ID 重复
                node_id = str(node.get('id', ''))
                if node_id in node_ids:
                    errors.append({
                        'type': 'duplicate_id',
                        'message': f'节点 ID 重复: {node_id}',
                        'node_id': node_id,
                    })
                node_ids.add(node_id)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
        }
    
    def check_dependencies(self, workflow: Dict) -> Dict[str, Any]:
        """
        检查依赖完整性
        
        Args:
            workflow: 工作流定义
            
        Returns:
            检查结果 {valid, errors, warnings}
        """
        errors = []
        warnings = []
        
        nodes = workflow.get('nodes', [])
        node_ids = {str(n.get('id')) for n in nodes}
        
        for node in nodes:
            node_id = str(node.get('id', ''))
            deps = node.get('depends_on', [])
            
            for dep_id in deps:
                dep_id = str(dep_id)
                
                # 检查依赖的节点是否存在
                if dep_id not in node_ids:
                    errors.append({
                        'type': 'missing_dependency',
                        'message': f'节点 {node_id} 依赖不存在的节点: {dep_id}',
                        'node_id': node_id,
                        'dependency': dep_id,
                    })
                
                # 检查自依赖
                if dep_id == node_id:
                    errors.append({
                        'type': 'self_dependency',
                        'message': f'节点 {node_id} 不能依赖自身',
                        'node_id': node_id,
                    })
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
        }
    
    def check_config(self, workflow: Dict) -> Dict[str, Any]:
        """
        检查配置完整性
        
        Args:
            workflow: 工作流定义
            
        Returns:
            检查结果 {valid, errors, warnings}
        """
        errors = []
        warnings = []
        
        config = workflow.get('config', {})
        
        # 检查重试配置
        if config.get('retry', {}).get('enabled'):
            retry = config['retry']
            if 'max_attempts' not in retry:
                warnings.append({
                    'type': 'missing_retry_config',
                    'message': '重试已启用但未设置 max_attempts',
                })
            if 'interval' not in retry:
                warnings.append({
                    'type': 'missing_retry_config',
                    'message': '重试已启用但未设置 interval',
                })
        
        # 检查通知配置
        notify = config.get('notify', {})
        if notify.get('on_complete') or notify.get('on_fail'):
            if not notify.get('channel'):
                warnings.append({
                    'type': 'missing_notify_config',
                    'message': '通知已启用但未设置 channel',
                })
        
        # 检查守护配置
        guardian = config.get('guardian', {})
        if guardian.get('enabled'):
            if 'interval' not in guardian:
                warnings.append({
                    'type': 'missing_guardian_config',
                    'message': '守护已启用但未设置 interval',
                })
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
        }
    
    def check_all(self, workflow: Dict) -> Dict[str, Any]:
        """
        执行所有检查
        
        Args:
            workflow: 工作流定义
            
        Returns:
            综合检查结果
        """
        structure_result = self.check_structure(workflow)
        dep_result = self.check_dependencies(workflow)
        config_result = self.check_config(workflow)
        
        all_errors = (
            structure_result['errors'] +
            dep_result['errors'] +
            config_result['errors']
        )
        all_warnings = (
            structure_result['warnings'] +
            dep_result['warnings'] +
            config_result['warnings']
        )
        
        return {
            'valid': len(all_errors) == 0,
            'errors': all_errors,
            'warnings': all_warnings,
            'checks': {
                'structure': structure_result,
                'dependencies': dep_result,
                'config': config_result,
            }
        }


# 单例实例
structure_checker = StructureChecker()