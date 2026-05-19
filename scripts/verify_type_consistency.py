#!/usr/bin/env python3
"""
verify_type_consistency.py - 验证 Hook 和 loader 类型识别一致性

用法：
    python verify_type_consistency.py [workflow_name]
    
    不带参数：验证所有工作流
    带参数：验证指定工作流
    
验证项：
    1. identify_type.py 识别结果与 loader 一致
    2. status.md 生成正确（包含正确类型）
"""

import json
import subprocess
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from tools.loader import WorkflowLoader

def verify_consistency(workflow_path):
    """验证类型识别一致性"""
    # 代码识别
    loader = WorkflowLoader()
    workflow = loader.load(workflow_path)
    code_type = workflow.get('type', 'normal')
    
    # Hook 识别（通过 CLI）
    cli_path = Path(__file__).parent.parent / 'actions/identify_type.py'
    result = subprocess.run(
        ['python3', str(cli_path), str(workflow_path)],
        capture_output=True, text=True
    )
    
    try:
        hook_info = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"❌ {workflow_path.name}: CLI 返回非 JSON - {result.stdout[:100]}")
        return False
    
    # 检查错误返回
    if 'error' in hook_info:
        print(f"❌ {workflow_path.name}: CLI 返回错误 - {hook_info['error']}")
        return False
    
    hook_type = hook_info.get('type', 'normal')
    
    # 对比
    if code_type == hook_type:
        print(f"✅ {workflow_path.name}: {code_type} (一致)")
        return True
    else:
        print(f"❌ {workflow_path.name}: code={code_type}, hook={hook_type} (不一致)")
        return False

def verify_status_md_generation(workflow_name):
    """验证 status.md 生成正确"""
    workflows_dir = Path.home() / '.hermes' / 'workflows'
    status_md_path = workflows_dir / workflow_name / 'status.md'
    
    if not status_md_path.exists():
        print(f"⚠️  {workflow_name}: status.md 不存在")
        return False
    
    content = status_md_path.read_text()
    
    # 检查必要章节
    required_sections = [
        '执行行为约束',
        '工作流类型',
    ]
    
    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)
    
    if missing_sections:
        print(f"❌ {workflow_name}: 缺少章节 {missing_sections}")
        return False
    else:
        print(f"✅ {workflow_name}: status.md 格式正确")
        return True

def main():
    workflows_dir = Path.home() / '.hermes' / 'workflows'
    
    if len(sys.argv) > 1:
        # 验证指定工作流
        workflow_path = Path(sys.argv[1])
        verify_consistency(workflow_path)
        verify_status_md_generation(workflow_path.name)
    else:
        # 验证所有工作流
        results = []
        for wf_dir in workflows_dir.iterdir():
            if wf_dir.is_dir() and (wf_dir / '_index.yaml').exists():
                results.append(verify_consistency(wf_dir))
                results.append(verify_status_md_generation(wf_dir.name))
        
        print(f"\n总计: {len(results)//2} 个工作流")
        print(f"通过: {sum(results)} 项")
        print(f"失败: {len(results) - sum(results)} 项")

if __name__ == '__main__':
    main()
