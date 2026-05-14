#!/usr/bin/env python3
"""
status.json 验证脚本

验证工作流 status.json 文件是否符合规范。

使用方法:
    python validate_status.py <status.json路径>
    python validate_status.py --all  # 验证所有工作流
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


class StatusValidator:
    """status.json 验证器"""
    
    # 必需字段
    REQUIRED_FIELDS = {
        'workflow_id': str,
        'workflow_name': str,
        'status': str,
        'started': (str, type(None)),  # 可以是字符串或 null
        'updated': str,
        'progress': dict,
        'steps': list
    }
    
    # status 有效值
    VALID_STATUS = ['initialized', 'running', 'paused', 'completed', 'failed']
    
    # steps 数组元素必需字段
    STEP_REQUIRED_FIELDS = {
        'step_id': int,
        'step_name': str,
        'status': str
    }
    
    # 步骤状态有效值
    VALID_STEP_STATUS = ['pending', 'running', 'completed', 'failed', 'skipped']
    
    def __init__(self):
        self.issues: List[Dict[str, str]] = []
        self.warnings: List[Dict[str, str]] = []
    
    def validate(self, status_path: Path) -> Dict[str, Any]:
        """验证单个 status.json 文件"""
        self.issues = []
        self.warnings = []
        
        result = {
            'workflow': status_path.parent.name,
            'path': str(status_path),
            'valid': True,
            'issues': [],
            'warnings': [],
            'summary': {}
        }
        
        # 1. 检查文件是否存在
        if not status_path.exists():
            result['valid'] = False
            result['issues'].append({
                'field': 'file',
                'issue': '文件不存在',
                'severity': 'error'
            })
            result['summary'] = {
                'total_issues': 1,
                'errors': 1,
                'warnings': 0
            }
            return result
        
        # 2. 解析 JSON
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            result['valid'] = False
            result['issues'].append({
                'field': 'json',
                'issue': f'JSON解析失败: {e}',
                'severity': 'error'
            })
            result['summary'] = {
                'total_issues': 1,
                'errors': 1,
                'warnings': 0
            }
            return result
        
        # 3. 验证必需字段
        self._validate_required_fields(data)
        
        # 4. 验证 status 值
        if 'status' in data:
            self._validate_status_value(data['status'])
        
        # 5. 验证 steps 数组
        if 'steps' in data:
            self._validate_steps_array(data['steps'])
        
        # 6. 验证时间字段格式
        self._validate_time_fields(data)
        
        # 汇总结果
        result['issues'] = self.issues
        result['warnings'] = self.warnings
        result['valid'] = len(self.issues) == 0
        result['summary'] = {
            'total_issues': len(self.issues),
            'errors': len([i for i in self.issues if i['severity'] == 'error']),
            'warnings': len(self.warnings)
        }
        
        return result
    
    def _validate_required_fields(self, data: Dict):
        """验证必需字段"""
        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field not in data:
                self.issues.append({
                    'field': field,
                    'issue': f'缺少必需字段',
                    'severity': 'error'
                })
            elif not isinstance(data[field], expected_type):
                self.issues.append({
                    'field': field,
                    'issue': f'字段类型错误，期望 {expected_type.__name__}，实际 {type(data[field]).__name__}',
                    'severity': 'error'
                })
    
    def _validate_status_value(self, status: str):
        """验证 status 值"""
        if status not in self.VALID_STATUS:
            self.issues.append({
                'field': 'status',
                'issue': f'status 值无效: {status}，有效值: {self.VALID_STATUS}',
                'severity': 'error'
            })
    
    def _validate_steps_array(self, steps: List):
        """验证 steps 数组"""
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                self.issues.append({
                    'field': f'steps[{i}]',
                    'issue': '步骤记录不是对象',
                    'severity': 'error'
                })
                continue
            
            # 检查步骤必需字段
            for field, expected_type in self.STEP_REQUIRED_FIELDS.items():
                if field not in step:
                    self.issues.append({
                        'field': f'steps[{i}].{field}',
                        'issue': f'缺少必需字段',
                        'severity': 'error'
                    })
                elif not isinstance(step[field], expected_type):
                    self.issues.append({
                        'field': f'steps[{i}].{field}',
                        'issue': f'字段类型错误，期望 {expected_type.__name__}',
                        'severity': 'error'
                    })
            
            # 检查步骤 status 值
            if 'status' in step and step['status'] not in self.VALID_STEP_STATUS:
                self.warnings.append({
                    'field': f'steps[{i}].status',
                    'issue': f'步骤状态值可能无效: {step["status"]}',
                    'severity': 'warning'
                })
    
    def _validate_time_fields(self, data: Dict):
        """验证时间字段格式"""
        time_fields = ['started', 'updated', 'completed_at']
        
        for field in time_fields:
            if field in data and data[field] is not None:
                value = data[field]
                if not isinstance(value, str):
                    self.issues.append({
                        'field': field,
                        'issue': f'时间字段应该是字符串或 null',
                        'severity': 'error'
                    })
                    continue
                
                # 尝试解析 ISO 格式
                try:
                    # 支持多种 ISO 格式
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    self.warnings.append({
                        'field': field,
                        'issue': f'时间格式可能不符合 ISO 标准: {value}',
                        'severity': 'warning'
                    })


def validate_all_workflows():
    """验证所有工作流"""
    workflows_dir = Path.home() / '.hermes' / 'workflows'
    
    if not workflows_dir.exists():
        print(f"❌ 工作流目录不存在: {workflows_dir}")
        return
    
    results = []
    
    # 遍历所有工作流目录
    for workflow_dir in workflows_dir.iterdir():
        if not workflow_dir.is_dir():
            continue
        
        status_file = workflow_dir / 'status.json'
        if status_file.exists():
            validator = StatusValidator()
            result = validator.validate(status_file)
            results.append(result)
    
    # 输出结果
    print(f"\n{'='*70}")
    print(f"工作流状态验证报告")
    print(f"{'='*70}")
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"工作流总数: {len(results)}")
    print(f"\n")
    
    for result in results:
        status_icon = "✅" if result['valid'] else "❌"
        print(f"{status_icon} {result['workflow']}")
        
        if not result['valid']:
            print(f"   问题数: {result['summary']['total_issues']}")
            for issue in result['issues']:
                print(f"   - [{issue['severity']}] {issue['field']}: {issue['issue']}")
        
        print()
    
    # 统计
    valid_count = sum(1 for r in results if r['valid'])
    invalid_count = len(results) - valid_count
    
    print(f"{'='*70}")
    print(f"统计:")
    print(f"  ✅ 符合规范: {valid_count}")
    print(f"  ❌ 不符合规范: {invalid_count}")
    print(f"{'='*70}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("示例:")
        print("  python validate_status.py ~/.hermes/workflows/爆破测试/status.json")
        print("  python validate_status.py --all")
        sys.exit(1)
    
    if sys.argv[1] == '--all':
        validate_all_workflows()
    else:
        status_path = Path(sys.argv[1])
        validator = StatusValidator()
        result = validator.validate(status_path)
        
        # 输出 JSON 结果
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 返回退出码
        sys.exit(0 if result['valid'] else 1)


if __name__ == '__main__':
    main()
