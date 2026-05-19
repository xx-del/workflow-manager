#!/usr/bin/env python3
"""
Expander 依赖映射测试

测试用例：
1. 单层工作流：依赖不变
2. 嵌套工作流：内部依赖正确映射
3. 跨工作流依赖：末节点正确识别
4. 多层嵌套：递归映射正确
"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from expander import WorkflowExpander


def test_single_layer_workflow():
    """测试1：单层工作流，依赖应该不变"""
    print("\n=== 测试1：单层工作流 ===")
    
    expander = WorkflowExpander()
    
    nodes = [
        {"id": "1", "name": "步骤1", "depends_on": []},
        {"id": "2", "name": "步骤2", "depends_on": ["1"]},
        {"id": "3", "name": "步骤3", "depends_on": ["2"]},
    ]
    
    expanded = expander.expand(nodes)
    
    print(f"展开后节点数: {len(expanded)}")
    print(f"ID映射表: {expander.id_mapping}")
    
    # 验证
    validation = expander.validate_dependencies(expanded)
    print(f"验证结果: {'✅ 通过' if validation['valid'] else '❌ 失败'}")
    
    if not validation['valid']:
        for err in validation['errors']:
            print(f"  - {err}")
    
    # 检查依赖关系
    for node in expanded:
        print(f"  {node['id']}: depends_on={node.get('depends_on', [])}")
    
    return validation['valid']


def test_nested_workflow():
    """测试2：嵌套工作流，内部依赖应该正确映射"""
    print("\n=== 测试2：嵌套工作流（模拟） ===")
    
    expander = WorkflowExpander()
    
    # 模拟已展开的子工作流节点
    sub_nodes = [
        {"id": "root_电力数据_1", "name": "准备", "depends_on": [], "_source_workflow": "电力数据"},
        {"id": "root_电力数据_2", "name": "下载", "depends_on": ["root_电力数据_1"], "_source_workflow": "电力数据"},
        {"id": "root_电力数据_3", "name": "分析", "depends_on": ["root_电力数据_2"], "_source_workflow": "电力数据"},
    ]
    
    # 手动建立映射
    expander.id_mapping["1"] = "root_电力数据_1"
    expander.id_mapping["2"] = "root_电力数据_2"
    expander.id_mapping["3"] = "root_电力数据_3"
    
    # 找出口节点
    exit_node = expander._find_exit_node(sub_nodes)
    expander.workflow_exits["电力数据"] = exit_node
    
    print(f"子工作流出口节点: {exit_node}")
    
    # 验证内部依赖
    validation = expander.validate_dependencies(sub_nodes)
    print(f"验证结果: {'✅ 通过' if validation['valid'] else '❌ 失败'}")
    
    for node in sub_nodes:
        print(f"  {node['id']}: depends_on={node.get('depends_on', [])}")
    
    return validation['valid']


def test_id_mapping():
    """测试3：ID映射机制"""
    print("\n=== 测试3：ID映射机制 ===")
    
    expander = WorkflowExpander()
    
    # 测试 _apply_id_mapping 方法
    node = {"id": "5", "name": "测试节点", "depends_on": ["4"]}
    
    mapped = expander._apply_id_mapping(node, "测试工作流")
    
    print(f"原始ID: {node['id']}")
    print(f"映射后ID: {mapped['id']}")
    print(f"映射表: {expander.id_mapping}")
    
    # 验证映射
    success = (
        mapped['id'] == "root_测试工作流_5" and
        expander.id_mapping["5"] == "root_测试工作流_5"
    )
    
    print(f"验证结果: {'✅ 通过' if success else '❌ 失败'}")
    
    return success


def test_dependency_update():
    """测试4：依赖更新逻辑"""
    print("\n=== 测试4：依赖更新逻辑 ===")
    
    expander = WorkflowExpander()
    
    # 建立映射
    expander.id_mapping = {
        "1": "root_工作流_1",
        "2": "root_工作流_2",
        "3": "root_工作流_3",
    }
    
    # 测试节点
    nodes = [
        {"id": "root_工作流_1", "name": "步骤1", "depends_on": []},
        {"id": "root_工作流_2", "name": "步骤2", "depends_on": ["1"]},  # 应该被更新
        {"id": "root_工作流_3", "name": "步骤3", "depends_on": ["2"]},  # 应该被更新
    ]
    
    updated = expander._update_dependencies(nodes, {"_sub_workflow": "工作流"})
    
    print("更新后的依赖:")
    for node in updated:
        print(f"  {node['id']}: depends_on={node.get('depends_on', [])}")
    
    # 验证
    expected = [
        {"id": "root_工作流_1", "depends_on": []},
        {"id": "root_工作流_2", "depends_on": ["root_工作流_1"]},
        {"id": "root_工作流_3", "depends_on": ["root_工作流_2"]},
    ]
    
    success = True
    for i, node in enumerate(updated):
        if node.get('depends_on') != expected[i]['depends_on']:
            success = False
            print(f"❌ 节点 {node['id']} 依赖不正确")
    
    print(f"验证结果: {'✅ 通过' if success else '❌ 失败'}")
    
    return success


def test_exit_node_finding():
    """测试5：出口节点识别"""
    print("\n=== 测试5：出口节点识别 ===")
    
    expander = WorkflowExpander()
    
    # 测试节点：节点3是出口（不被依赖）
    nodes = [
        {"id": "node_1", "name": "步骤1", "depends_on": []},
        {"id": "node_2", "name": "步骤2", "depends_on": ["node_1"]},
        {"id": "node_3", "name": "步骤3", "depends_on": ["node_2"]},
    ]
    
    exit_node = expander._find_exit_node(nodes)
    
    print(f"出口节点: {exit_node}")
    
    success = exit_node == "node_3"
    print(f"验证结果: {'✅ 通过' if success else '❌ 失败'}")
    
    return success


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Expander 依赖映射测试")
    print("=" * 60)
    
    results = {
        "单层工作流": test_single_layer_workflow(),
        "嵌套工作流": test_nested_workflow(),
        "ID映射机制": test_id_mapping(),
        "依赖更新逻辑": test_dependency_update(),
        "出口节点识别": test_exit_node_finding(),
    }
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\n总计: {passed}/{total} 通过")
    
    return all(results.values())


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
