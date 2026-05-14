#!/usr/bin/env python3
"""
工作流执行审计脚本

审计工作流执行是否符合技能文档规范。

使用方法:
    python audit_workflow_execution.py <工作流名称>
    python audit_workflow_execution.py --all  # 审计所有工作流
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class WorkflowAuditor:
    """工作流执行审计器"""
    
    def __init__(self):
        self.audit_results = []
    
    def audit(self, workflow_name: str) -> Dict[str, Any]:
        """审计单个工作流"""
        workflows_dir = Path.home() / '.hermes' / 'workflows'
        workflow_dir = workflows_dir / workflow_name
        status_file = workflow_dir / 'status.json'
        
        result = {
            'workflow': workflow_name,
            'audit_time': datetime.now().isoformat(),
            'audits': {},
            'issues': [],
            'summary': {}
        }
        
        if not status_file.exists():
            result['issues'].append({
                'audit': '文件存在性',
                'issue': 'status.json 不存在',
                'severity': 'critical'
            })
            result['summary'] = {
                'total_issues': 1,
                'critical': 1,
                'errors': 0,
                'warnings': 0
            }
            return result
        
        # 读取 status.json
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
        except json.JSONDecodeError as e:
            result['issues'].append({
                'audit': 'JSON解析',
                'issue': f'status.json 解析失败: {e}',
                'severity': 'critical'
            })
            result['summary'] = {
                'total_issues': 1,
                'critical': 1,
                'errors': 0,
                'warnings': 0
            }
            return result
        
        # 执行各项审计
        result['audits']['initialization'] = self._audit_initialization(status)
        result['audits']['status_update'] = self._audit_status_update(status)
        result['audits']['field_completeness'] = self._audit_field_completeness(status)
        result['audits']['forbidden_behaviors'] = self._audit_forbidden_behaviors(status, workflow_dir)
        result['audits']['execution_time'] = self._audit_execution_time(status)
        
        # 汇总问题
        for audit_name, audit_result in result['audits'].items():
            if not audit_result['passed']:
                for issue in audit_result.get('issues', []):
                    result['issues'].append({
                        'audit': audit_name,
                        'issue': issue['issue'],
                        'severity': issue['severity']
                    })
        
        # 统计
        result['summary'] = {
            'total_issues': len(result['issues']),
            'critical': len([i for i in result['issues'] if i['severity'] == 'critical']),
            'errors': len([i for i in result['issues'] if i['severity'] == 'error']),
            'warnings': len([i for i in result['issues'] if i['severity'] == 'warning'])
        }
        
        return result
    
    def _audit_initialization(self, status: Dict) -> Dict:
        """审计初始化"""
        issues = []
        
        # 检查必需字段
        required = ['workflow_id', 'workflow_name', 'status', 'started', 'updated', 'progress', 'steps']
        for field in required:
            if field not in status:
                issues.append({
                    'issue': f'缺少必需字段: {field}',
                    'severity': 'error'
                })
        
        # 检查 updated 字段是否设置
        if 'updated' not in status or not status['updated']:
            issues.append({
                'issue': 'updated 字段未设置，守护机制将失效',
                'severity': 'critical'
            })
        
        # 检查 status 值
        valid_status = ['initialized', 'running', 'paused', 'completed', 'failed']
        if 'status' in status and status['status'] not in valid_status:
            issues.append({
                'issue': f'status 值无效: {status["status"]}',
                'severity': 'error'
            })
        
        return {
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def _audit_status_update(self, status: Dict) -> Dict:
        """审计状态更新"""
        issues = []
        
        # 检查 steps 数组是否为空（已完成工作流应该有步骤记录）
        if status.get('status') == 'completed':
            if 'steps' not in status or len(status['steps']) == 0:
                issues.append({
                    'issue': '已完成工作流缺少步骤记录',
                    'severity': 'warning'
                })
        
        # 检查 steps 数组格式
        if 'steps' in status:
            for i, step in enumerate(status['steps']):
                if not isinstance(step, dict):
                    issues.append({
                        'issue': f'steps[{i}] 不是对象',
                        'severity': 'error'
                    })
                    continue
                
                # 检查步骤必需字段
                step_required = ['step_id', 'step_name', 'status']
                for field in step_required:
                    if field not in step:
                        issues.append({
                            'issue': f'steps[{i}] 缺少字段: {field}',
                            'severity': 'error'
                        })
        
        return {
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def _audit_field_completeness(self, status: Dict) -> Dict:
        """审计字段完整性"""
        issues = []
        
        # 检查 progress 字段
        if 'progress' in status:
            progress = status['progress']
            if not isinstance(progress, dict):
                issues.append({
                    'issue': 'progress 字段不是对象',
                    'severity': 'error'
                })
            else:
                progress_required = ['current_step', 'total_steps', 'message']
                for field in progress_required:
                    if field not in progress:
                        issues.append({
                            'issue': f'progress 缺少字段: {field}',
                            'severity': 'warning'
                        })
        
        # 检查时间字段
        if 'started' in status and status['started'] is not None:
            if not isinstance(status['started'], str):
                issues.append({
                    'issue': 'started 字段应该是字符串或 null',
                    'severity': 'error'
                })
        
        if 'updated' in status:
            if not isinstance(status['updated'], str):
                issues.append({
                    'issue': 'updated 字段应该是字符串',
                    'severity': 'error'
                })
        
        return {
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def _audit_forbidden_behaviors(self, status: Dict, workflow_dir: Path) -> Dict:
        """审计禁止行为"""
        issues = []
        
        # 检查是否使用历史数据（通过检查步骤执行时间）
        if 'steps' in status and len(status['steps']) > 0:
            # 检查步骤执行时间是否合理
            for i, step in enumerate(status['steps']):
                if 'started_at' in step and 'completed_at' in step:
                    try:
                        started = datetime.fromisoformat(step['started_at'].replace('Z', '+00:00'))
                        completed = datetime.fromisoformat(step['completed_at'].replace('Z', '+00:00'))
                        duration = (completed - started).total_seconds()
                        
                        # 如果执行时间异常短（< 1秒），可能是跳过步骤
                        if duration < 1:
                            issues.append({
                                'issue': f'steps[{i}] 执行时间异常短（{duration}秒），疑似跳过步骤',
                                'severity': 'warning'
                            })
                    except:
                        pass
        
        return {
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def _audit_execution_time(self, status: Dict) -> Dict:
        """审计执行时间"""
        issues = []
        
        # 检查 updated 字段是否过期（超过30天）
        if 'updated' in status and status['updated']:
            try:
                updated = datetime.fromisoformat(status['updated'].replace('Z', '+00:00'))
                if datetime.now(updated.tzinfo) - updated > timedelta(days=30):
                    issues.append({
                        'issue': 'status.json 超过30天未更新',
                        'severity': 'warning'
                    })
            except:
                pass
        
        return {
            'passed': len(issues) == 0,
            'issues': issues
        }


def audit_all_workflows():
    """审计所有工作流"""
    workflows_dir = Path.home() / '.hermes' / 'workflows'
    
    if not workflows_dir.exists():
        print(f"❌ 工作流目录不存在: {workflows_dir}")
        return
    
    results = []
    
    # 遍历所有工作流目录
    for workflow_dir in workflows_dir.iterdir():
        if not workflow_dir.is_dir():
            continue
        
        # 跳过 .backup 目录
        if workflow_dir.name.startswith('.'):
            continue
        
        auditor = WorkflowAuditor()
        result = auditor.audit(workflow_dir.name)
        results.append(result)
    
    # 输出 Markdown 报告
    print(f"# 工作流执行审计报告\n")
    print(f"**审计时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"**工作流总数**: {len(results)}\n")
    
    for result in results:
        print(f"## {result['workflow']}\n")
        
        status_icon = "✅" if result['summary']['total_issues'] == 0 else "❌"
        print(f"**状态**: {status_icon} {'符合规范' if result['summary']['total_issues'] == 0 else '发现问题'}\n")
        
        if result['issues']:
            print(f"**问题列表**:\n")
            for issue in result['issues']:
                severity_map = {
                    'critical': '🔴',
                    'error': '❌',
                    'warning': '⚠️'
                }
                icon = severity_map.get(issue['severity'], '•')
                print(f"{icon} [{issue['audit']}] {issue['issue']}")
            print()
        
        print(f"---\n")
    
    # 统计
    passed_count = sum(1 for r in results if r['summary']['total_issues'] == 0)
    failed_count = len(results) - passed_count
    
    print(f"## 统计\n")
    print(f"- ✅ 符合规范: {passed_count}")
    print(f"- ❌ 发现问题: {failed_count}\n")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("示例:")
        print("  python audit_workflow_execution.py 爆破测试")
        print("  python audit_workflow_execution.py --all")
        sys.exit(1)
    
    if sys.argv[1] == '--all':
        audit_all_workflows()
    else:
        workflow_name = sys.argv[1]
        auditor = WorkflowAuditor()
        result = auditor.audit(workflow_name)
        
        # 输出 JSON 结果
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 返回退出码
        sys.exit(0 if result['summary']['total_issues'] == 0 else 1)


if __name__ == '__main__':
    main()
