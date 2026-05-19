#!/usr/bin/env python3
"""
集成测试：资产收集工作流展开验证

验证修复后的 expander 能否正确处理真实的嵌套工作流
"""

import sys
from pathlib import Path
import yaml

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from expander import workflow_expander
from tools.loader import loader


def test_asset_collection_workflow():
    """测试资产收集工作流的展开"""
    print("=" * 60)
    print("集成测试：资产收集工作流")
    print("=" * 60)
    
    # 重置 expander 状态
    workflow_expander.reset()
    
    # 加载资产收集工作流
    workflow = loader.load("资产收集流程")
    
    if not workflow:
        print("❌ 工作流未找到: 资产收集流程")
        return False
    
    print(f"\n工作流信息:")
    print(f"  名称: {workflow.get('name')}")
    print(f"  模式: {workflow.get('mode')}")
    print(f"  节点数: {len(workflow.get('nodes', []))}")
    
    # 展开工作流
    print("\n展开工作流...")
    expanded = workflow_expander.expand(workflow["nodes"])
    
    print(f"\n展开结果:")
    print(f"  展开后节点数: {len(expanded)}")
    print(f"  ID映射数量: {len(workflow_expander.id_mapping)}")
    print(f"  工作流出口: {list(workflow_expander.workflow_exits.keys())}")
    
    # 显示映射表
    print(f"\nID映射表:")
    for old_id, new_id in list(workflow_expander.id_mapping.items())[:10]:
        print(f"  {old_id} → {new_id}")
    if len(workflow_expander.id_mapping) > 10:
        print(f"  ... 共 {len(workflow_expander.id_mapping)} 个映射")
    
    # 显示所有节点依赖
    print(f"\n展开后节点依赖关系:")
    for node in expanded:
        node_id = node.get("id", "?")
        deps = node.get("depends_on", [])
        source = node.get("_source_workflow", "root")
        print(f"  {node_id}")
        print(f"    来源: {source}")
        print(f"    依赖: {deps}")
    
    # 验证依赖完整性
    print("\n验证依赖完整性...")
    validation = workflow_expander.validate_dependencies(expanded)
    
    if validation["valid"]:
        print("✅ 所有依赖关系正确")
    else:
        print("❌ 依赖验证失败:")
        for err in validation["errors"]:
            print(f"  - {err}")
    
    # 分析执行层级
    print("\n分析执行层级...")
    level_map = {}
    
    for node in expanded:
        node_id = node.get("id")
        deps = node.get("depends_on", [])
        
        # 计算层级：依赖节点的最大层级 + 1
        if not deps:
            level = 0
        else:
            level = max(level_map.get(str(d), 0) for d in deps) + 1
        
        level_map[str(node_id)] = level
    
    # 按层级分组
    levels = {}
    for node_id, level in level_map.items():
        if level not in levels:
            levels[level] = []
        levels[level].append(node_id)
    
    print(f"执行层级分布:")
    for level in sorted(levels.keys()):
        nodes_at_level = levels[level]
        print(f"  Level {level}: {len(nodes_at_level)} 个节点")
        for node_id in nodes_at_level[:3]:
            print(f"    - {node_id}")
        if len(nodes_at_level) > 3:
            print(f"    ... 共 {len(nodes_at_level)} 个节点")
    
    # 判断串行/并行
    max_concurrency = max(len(nodes) for nodes in levels.values())
    total_levels = len(levels)
    
    print(f"\n执行模式分析:")
    print(f"  总层级数: {total_levels}")
    print(f"  最大并发度: {max_concurrency}")
    
    if total_levels == 1 and len(expanded) > 1:
        print("  ⚠️ 所有节点在同一层级 → 将并行执行（错误）")
        result = False
    else:
        print(f"  ✅ 节点分布在 {total_levels} 个层级 → 正确的串行/并行混合")
        result = True
    
    return result


def test_simple_nested_workflow():
    """测试简单的嵌套工作流（电力数据）"""
    print("\n" + "=" * 60)
    print("集成测试：电力数据工作流（子工作流）")
    print("=" * 60)
    
    # 重置 expander 状态
    workflow_expander.reset()
    
    # 加载电力数据工作流
    workflow = loader.load("电力数据")
    
    if not workflow:
        print("❌ 工作流未找到: 电力数据")
        return False
    
    print(f"\n工作流信息:")
    print(f"  名称: {workflow.get('name')}")
    print(f"  模式: {workflow.get('mode')}")
    print(f"  节点数: {len(workflow.get('nodes', []))}")
    
    # 展开工作流
    print("\n展开工作流...")
    expanded = workflow_expander.expand(workflow["nodes"])
    
    print(f"\n展开结果:")
    print(f"  展开后节点数: {len(expanded)}")
    
    # 显示所有节点依赖
    print(f"\n展开后节点依赖关系:")
    for node in expanded:
        node_id = node.get("id", "?")
        deps = node.get("depends_on", [])
        print(f"  {node_id}: depends_on={deps}")
    
    # 验证
    validation = workflow_expander.validate_dependencies(expanded)
    
    # 检查是否为串行
    if len(expanded) == 3:
        # 期望：步骤1 → 步骤2 → 步骤3
        step1 = expanded[0]
        step2 = expanded[1]
        step3 = expanded[2]
        
        if (not step1.get("depends_on") and
            step2.get("depends_on") == [step1.get("id")] and
            step3.get("depends_on") == [step2.get("id")]):
            print("✅ 串行依赖关系正确")
            return True
        else:
            print("❌ 串行依赖关系不正确")
            return False
    else:
        print(f"⚠️ 节点数量不符合预期（期望3，实际{len(expanded)}）")
        return False


if __name__ == "__main__":
    results = {
        "电力数据（子工作流）": test_simple_nested_workflow(),
        "资产收集（主工作流）": test_asset_collection_workflow(),
    }
    
    print("\n" + "=" * 60)
    print("集成测试结果汇总")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\n总计: {passed}/{total} 通过")
    
    sys.exit(0 if all(results.values()) else 1)
