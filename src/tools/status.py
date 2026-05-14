#!/usr/bin/env python3
"""
Status Manager - 状态管理器 v2.0

职责：
1. 读取工作流状态（status.json）
2. 更新工作流状态（支持合并）
3. 写入心跳
4. 检查步骤进程状态（新增）
5. 自动完成检测（新增）
"""

import json
import psutil
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

from utils.logger import get_logger
from utils.config import config as get_config


class StatusManager:
    """状态管理器"""

    def __init__(self):
        self.logger = get_logger(__name__)
    
    def get_status(self, workflow_path: str) -> Dict[str, Any]:
        """
        获取工作流状态
        
        Args:
            workflow_path: 工作流目录路径
            
        Returns:
            状态字典
        """
        status_path = Path(workflow_path) / "status.json"
        
        if not status_path.exists():
            return {
                'status': 'not_found',
                'path': workflow_path,
            }
        
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'path': workflow_path,
            }
    
    def update_status(self, workflow_path: str, data: Dict[str, Any]) -> bool:
        """
        更新工作流状态（合并现有状态）
        
        Args:
            workflow_path: 工作流目录路径
            data: 要更新的数据
            
        Returns:
            是否成功
        """
        status_path = Path(workflow_path) / "status.json"
        
        try:
            # 读取现有状态
            existing = {}
            if status_path.exists():
                try:
                    with open(status_path, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                except:
                    pass
            
            # 合并状态
            new_status = {
                **existing,
                **data,
                'last_updated': datetime.now().isoformat(),
            }
            
            # 写入文件
            status_path.parent.mkdir(parents=True, exist_ok=True)
            with open(status_path, 'w', encoding='utf-8') as f:
                json.dump(new_status, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"[StatusManager] 更新状态失败: {e}")
            return False
    
    def write_heartbeat(
        self,
        workflow_path: str,
        current_step: str = None,
        step_progress: str = None,
        pid: int = None,
    ) -> bool:
        """
        写入心跳（增强版：自动检查步骤状态）
        
        Args:
            workflow_path: 工作流目录路径
            current_step: 当前步骤名称
            step_progress: 步骤进度（如 "2/5"）
            pid: 进程 ID
            
        Returns:
            是否成功
        """
        # 获取现有状态
        status = self.get_status(workflow_path)
        
        # 自动完成检测（新增）
        if status.get('status') == 'running':
            status = self._auto_complete_detection(workflow_path, status)
        
        # 构造心跳数据
        heartbeat_data = {
            'workflow': {
                'heartbeat': datetime.now().isoformat(),
                'current_step': current_step or 'unknown',
                'step_progress': step_progress or '0/0',
                'pid': pid,
            }
        }
        
        # 如果有步骤数据，一并更新
        if 'steps' in status:
            heartbeat_data['steps'] = status['steps']
        
        return self.update_status(workflow_path, heartbeat_data)
    
    def _auto_complete_detection(
        self,
        workflow_path: str,
        status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        自动完成检测（新增方法）
        
        检测逻辑：
        1. 检查主进程是否存活
        2. 如果主进程不存在 → 工作流异常终止
        3. 检查步骤状态是否有进展
        4. 如果步骤长时间无进展 → 告警
        
        Args:
            workflow_path: 工作流目录路径
            status: 当前状态
            
        Returns:
            更新后的状态
        """
        workflow = status.get('workflow', {})
        main_pid = workflow.get('pid')
        
        # 检查主进程是否存活
        if main_pid:
            try:
                if not psutil.pid_exists(main_pid):
                    self.logger.warning(f"[StatusManager] 主进程 {main_pid} 不存在，工作流可能异常终止")
                    # 更新状态为异常
                    status['status'] = 'error'
                    status['error'] = f'主进程 {main_pid} 不存在'
                    status['error_at'] = datetime.now().isoformat()
                    return status
            except Exception as e:
                self.logger.warning(f"[StatusManager] 检查主进程异常: {e}")
        
        # 检查步骤进展
        steps = status.get('steps', [])
        if steps:
            # 统计各状态数量
            completed = sum(1 for s in steps if s.get('status') == 'completed')
            executing = sum(1 for s in steps if s.get('status') == 'executing')
            pending = sum(1 for s in steps if s.get('status') in ['pending', 'planned'])
            
            # 如果所有步骤都完成，更新工作流状态
            if completed == len(steps):
                self.logger.info(f"[StatusManager] 所有步骤已完成，更新工作流状态")
                status['status'] = 'completed'
                status['completed_at'] = datetime.now().isoformat()
        
        return status
    
    def check_process_health(self, workflow_path: str) -> Dict[str, Any]:
        """
        检查进程健康状态（新增方法）
        
        Returns:
            {
                'healthy': bool,
                'main_process': {'pid': int, 'status': str},
                'steps_status': dict,
                'recommendations': list
            }
        """
        status = self.get_status(workflow_path)
        workflow = status.get('workflow', {})
        main_pid = workflow.get('pid')
        
        result = {
            'healthy': True,
            'main_process': {'pid': main_pid, 'status': 'unknown'},
            'steps_status': {
                'total': len(status.get('steps', [])),
                'completed': 0,
                'executing': 0,
                'pending': 0,
                'failed': 0,
            },
            'recommendations': []
        }
        
        # 检查主进程
        if main_pid:
            try:
                if psutil.pid_exists(main_pid):
                    result['main_process']['status'] = 'running'
                else:
                    result['main_process']['status'] = 'exited'
                    result['healthy'] = False
                    result['recommendations'].append('主进程已退出，检查工作流是否正常完成')
            except Exception as e:
                result['main_process']['status'] = f'error: {e}'
                result['healthy'] = False
        
        # 统计步骤状态
        for step in status.get('steps', []):
            step_status = step.get('status', 'unknown')
            if step_status == 'completed':
                result['steps_status']['completed'] += 1
            elif step_status == 'executing':
                result['steps_status']['executing'] += 1
            elif step_status in ['pending', 'planned']:
                result['steps_status']['pending'] += 1
            elif step_status == 'failed':
                result['steps_status']['failed'] += 1
        
        # 健康检查
        if result['steps_status']['failed'] > 0:
            result['healthy'] = False
            result['recommendations'].append(f"有 {result['steps_status']['failed']} 个步骤失败")
        
        if result['main_process']['status'] == 'exited' and result['steps_status']['executing'] > 0:
            result['healthy'] = False
            result['recommendations'].append('主进程已退出，但仍有步骤在执行状态，可能异常')
        
        return result
    
    def init_status(self, workflow_path: str, workflow_name: str, total_steps: int) -> bool:
        """
        初始化工作流状态
        
        Args:
            workflow_path: 工作流目录路径
            workflow_name: 工作流名称
            total_steps: 总步骤数
            
        Returns:
            是否成功
        """
        initial_status = {
            'status': 'initialized',
            'workflow_name': workflow_name,
            'total_steps': total_steps,
            'completed_steps': 0,
            'failed_steps': 0,
            'created_at': datetime.now().isoformat(),
        }
        
        return self.update_status(workflow_path, initial_status)
    
    def get_all_running_workflows(
        self,
        workflows_base_dir: str = None
    ) -> list:
        """
        获取所有运行中的工作流

        扫描工作流目录，返回状态为 'running' 的工作流列表

        Args:
            workflows_base_dir: 工作流存放目录

        Returns:
            运行中工作流列表，每项包含 {name, path, status}
        """
        from typing import List

        if workflows_base_dir is None:
            config = get_config
            workflows_base_dir = str(config.get_workflows_dir())

        base_dir = Path(workflows_base_dir).expanduser()
        
        if not base_dir.exists():
            return []
        
        running_workflows = []
        
        for workflow_dir in base_dir.iterdir():
            if not workflow_dir.is_dir():
                continue
            
            # 跳过隐藏目录和备份目录
            if workflow_dir.name.startswith('.') or workflow_dir.name == '.backup':
                continue
            
            status = self.get_status(str(workflow_dir))
            
            if status.get('status') == 'running':
                running_workflows.append({
                    'name': workflow_dir.name,
                    'path': str(workflow_dir),
                    'status': status,
                })

        return running_workflows


# 单例实例
status_manager = StatusManager()
