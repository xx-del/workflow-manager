#!/usr/bin/env python3
"""
调试测试：主工作流节点依赖映射
"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from expander import WorkflowExpander
from tools.loader import loader


def debug_main_workflow_deps():
    """调试主工作流依赖映射"""
    print("=" * 60)
    print("调试：主工作流依赖映射")
    print("=" * 60)
    
    expander = WorkflowExpander()
    
    # 加载资产收集工作流
    workflow = loader.load("资产收集流程")
    
    print("\n原始节点定义:")
    for node in workflow["nodes"]:
        print(f"  ID={node.get('id')}, name={node.get('name')}, depends_on={node.get('depends_on')}")
    
    # 展开工作流
    print("\n展开工作流...")
    expanded = expander.expand(workflow["nodes"])
    
    print(f"\n主工作流节点映射:")
    for main_id, exit_node in expander.main_node_mapping.items():
        print(f"  主节点 {main_id} → 子工作流出口 {exit_node}")
    
    print(f"\n工作流出口映射:")
    for name, exit_node in expander.workflow_exits.items():
        print(f"  {name} → {exit_node}")
    
    print(f"\n展开后的节点:")
    for node in expanded:
        print(f"  ID={node.get('id')}, depends_on={node.get('depends_on')}, source={node.get('_source_workflow')}")
    
    # 关键验证：检查跨工作流依赖是否正确
    print("\n关键验证：")
    
    # 域名处理应该依赖电力数据的最后一个节点
    domain_node = next((n for n in expanded if n.get('_source_workflow') == '域名处理'), None)
    if domain_node:
        power_exit = expander.workflow_exits.get('电力数据')
        expected_dep = [power_exit] if power_exit else []
        actual_dep = domain_node.get('depends_on', [])
        
        print(f"域名处理节点: {domain_node.get('id')}")
        print(f"  期望依赖: {expected_dep}")
        print(f"  实际依赖: {actual_dep}")
        
        if expected_dep == actual_dep:
            print("  ✅ 跨工作流依赖正确")
        else:
            print("  ❌ 跨工作流依赖不正确")


if __name__ == "__main__":
    debug_main_workflow_deps()
