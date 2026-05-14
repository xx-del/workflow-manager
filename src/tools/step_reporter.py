#!/usr/bin/env python3
"""
Step Reporter - 步骤执行报告器

职责：
1. 接收主 AI 的步骤执行结果
2. 验证执行结果
3. 更新 status.json
4. 记录历史
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from utils.logger import get_logger
from utils.config import config as get_config


class StepReporter:
    """步骤执行报告器"""

    def __init__(self, workflows_dir: str = None):
        self.logger = get_logger(__name__)
        if workflows_dir is None:
            config = get_config
            workflows_dir = str(config.get_workflows_dir())
        self.workflows_dir = Path(workflows_dir).expanduser()
    
    def report_step(
        self,
        workflow_name: str,
        step_id: str,
        step_name: str,
        success: bool,
        output: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        报告步骤执行结果
        
        Args:
            workflow_name: 工作流名称
            step_id: 步骤 ID
            step_name: 步骤名称
            success: 是否成功
            output: 执行输出（可选）
            error: 错误信息（可选）
            duration: 执行耗时（秒，可选）
        
        Returns:
            更新后的状态
        """
        # 1. 查找工作流目录
        workflow_path = self._find_workflow_path(workflow_name)
        if not workflow_path:
            return {
                'success': False,
                'error': f'工作流未找到: {workflow_name}'
            }
        
        # 2. 读取当前状态
        status = self._read_status(workflow_path)
        
        # 3. 更新状态
        status['last_updated'] = datetime.now().isoformat()
        status['last_step'] = {
            'id': step_id,
            'name': step_name,
            'success': success,
            'error': error,
            'duration': duration
        }
        
        if success:
            status['completed_steps'] = status.get('completed_steps', 0) + 1
        else:
            status['failed_steps'] = status.get('failed_steps', 0) + 1
        
        # 4. 验证输出（如果有）
        validation = self._validate_step_output(step_name, output)
        if not validation['valid']:
            status['last_step']['validation_warning'] = validation['warnings']
        
        # 5. 保存状态
        self._write_status(workflow_path, status)
        
        # 6. 记录历史
        self._append_history(workflow_path, {
            'step_id': step_id,
            'step_name': step_name,
            'success': success,
            'error': error,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        })
        
        # 7. 检查是否所有步骤完成
        total_steps = status.get('total_steps', 0)
        completed_steps = status.get('completed_steps', 0)
        
        if total_steps > 0 and completed_steps >= total_steps:
            # 自动触发汇总
            self._auto_consolidate(workflow_path, workflow_name)
        
        return {
            'success': True,
            'status': status,
            'validation': validation
        }
    
    def _find_workflow_path(self, workflow_name: str) -> Optional[Path]:
        """查找工作流目录"""
        # 检查直接匹配
        direct_path = self.workflows_dir / workflow_name
        if direct_path.exists():
            return direct_path
        
        # 搜索匹配
        for path in self.workflows_dir.iterdir():
            if path.is_dir() and path.name == workflow_name:
                return path
        
        return None
    
    def _read_status(self, workflow_path: Path) -> Dict[str, Any]:
        """读取状态"""
        status_path = workflow_path / "status.json"
        if status_path.exists():
            with open(status_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'status': 'running',
            'workflow_name': workflow_path.name,
            'total_steps': 0,
            'completed_steps': 0,
            'failed_steps': 0
        }
    
    def _write_status(self, workflow_path: Path, status: Dict[str, Any]):
        """写入状态"""
        status_path = workflow_path / "status.json"
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    
    def _validate_step_output(self, step_name: str, output: Optional[Dict]) -> Dict:
        """
        验证步骤输出
        
        Returns:
            {'valid': bool, 'warnings': [str]}
        """
        warnings = []
        
        if output is None:
            return {'valid': True, 'warnings': []}
        
        # 验证关键字段
        if 'success' not in output:
            warnings.append("输出缺少 'success' 字段")
        
        # 根据步骤类型验证
        if '下载' in step_name or 'download' in step_name.lower():
            if 'files' not in output and 'file_count' not in output:
                warnings.append("下载步骤缺少文件信息")
        
        if '扫描' in step_name or 'scan' in step_name.lower():
            if 'results' not in output and 'count' not in output:
                warnings.append("扫描步骤缺少结果信息")
        
        return {
            'valid': len(warnings) == 0,
            'warnings': warnings
        }
    
    def _append_history(self, workflow_path: Path, record: Dict):
        """追加历史记录"""
        history_dir = workflow_path / "history"
        history_dir.mkdir(exist_ok=True)
        
        today = datetime.now().strftime('%Y-%m-%d')
        history_path = history_dir / f"{today}.jsonl"
        
        with open(history_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def _auto_consolidate(self, workflow_path: Path, workflow_name: str):
        """自动汇总结果"""
        import subprocess
        
        self.logger.info(f"\n[StepReporter] 检测到所有步骤完成，自动触发汇总...")
        
        try:
            # 调用 complete.py
            result = subprocess.run([
                'python',
                str(Path(__file__).parent.parent.parent / 'actions' / 'complete.py'),
                workflow_name
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                self.logger.info(f"[StepReporter] 自动汇总完成")
            else:
                self.logger.error(f"[StepReporter] 自动汇总失败: {result.stderr}")
        except Exception as e:
            self.logger.error(f"[StepReporter] 自动汇总异常: {e}")


# 单例实例
step_reporter = StepReporter()
