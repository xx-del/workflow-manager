#!/usr/bin/env python3
"""
Step Analyzer - 步骤分析器

职责：
1. 构建依赖图
2. 计算执行层级（拓扑排序）
3. 识别可并行执行的组
4. 检测循环依赖
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from collections import deque
from utils.logger import get_logger


class StepAnalyzer:
    """步骤分析器"""
    
    def __init__(self):

        self.logger = get_logger(__name__)
        pass
    
    def analyze(self, nodes: List[Dict[str, Any]], connections: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        分析步骤依赖
        
        Args:
            nodes: 工作流节点列表
            connections: 连接关系列表（可选）
            
        Returns:
            执行计划 {serial, parallel, total_steps, max_concurrency}
        """
        # 构建依赖图
        graph = self._build_dependency_graph(nodes, connections)
        
        # 检测循环依赖
        has_cycle, cycle_path = self.detect_circular_dependency(graph)
        if has_cycle:
            raise ValueError(f"检测到循环依赖: {' → '.join(cycle_path)}")
        
        # 计算层级
        self._calculate_levels(graph)
        
        # 找出可并行执行的组
        parallel_groups = self._find_parallel_groups(graph)
        
        # 创建执行计划
        plan = self._create_execution_plan(graph, parallel_groups)
        
        return plan
    
    def _build_dependency_graph(self, nodes: List[Dict], connections: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """构建依赖图
        
        Args:
            nodes: 节点列表
            connections: 连接关系列表（可选），格式: [{from, to, type}, ...]
        """
        graph = {
            'nodes': {},
            'edges': [],
            'root_nodes': [],
        }
        
        # 添加节点
        for node in nodes:
            node_id = str(node.get('id', ''))
            graph['nodes'][node_id] = {
                'id': node_id,
                'name': node.get('name', ''),
                'task': node.get('task', node.get('description', '')),
                'capabilities': node.get('capabilities', []),
                'dependencies': node.get('depends_on', []),
                'calls': node.get('calls'),  # 保留 calls 字段
                'level': 0,
                '_source_workflow': node.get('_source_workflow'),  # 子工作流来源
            }
        
        # 添加边（优先从 depends_on）
        for node in nodes:
            node_id = str(node.get('id', ''))
            deps = node.get('depends_on', [])
            
            for dep_id in deps:
                dep_id = str(dep_id)
                graph['edges'].append({
                    'from': dep_id,
                    'to': node_id,
                })
            
            # 记录根节点
            if not deps:
                graph['root_nodes'].append(node_id)
        
        # 处理 connections 参数（额外依赖关系）
        if connections:
            for conn in connections:
                from_id = str(conn.get('from', conn.get('source', '')))
                to_id = str(conn.get('to', conn.get('target', '')))
                
                if from_id and to_id and from_id in graph['nodes'] and to_id in graph['nodes']:
                    # 添加连接边
                    graph['edges'].append({
                        'from': from_id,
                        'to': to_id,
                    })
                    
                    # 更新依赖关系
                    if from_id not in graph['nodes'][to_id]['dependencies']:
                        graph['nodes'][to_id]['dependencies'].append(from_id)
                    
                    # 如果 to_id 在 root_nodes 中，移除它
                    if to_id in graph['root_nodes']:
                        graph['root_nodes'].remove(to_id)
        
        return graph
    
    def _calculate_levels(self, graph: Dict) -> None:
        """计算节点层级（Kahn 算法拓扑排序）
        
        修复：原 BFS 实现未正确处理依赖顺序，导致层级计算错误
        """
        # 1. 计算入度
        in_degree = {node_id: 0 for node_id in graph['nodes']}
        for edge in graph['edges']:
            target_id = edge.get('to')
            if target_id in in_degree:
                in_degree[target_id] += 1
        
        # 2. 初始化队列（入度为0的节点）
        queue = deque([node_id for node_id, deg in in_degree.items() if deg == 0])
        
        # 3. 拓扑排序
        while queue:
            node_id = queue.popleft()
            node = graph['nodes'].get(node_id)
            if not node:
                continue
            
            # 更新后继节点的层级和入度
            for edge in graph['edges']:
                if edge['from'] == node_id:
                    target = graph['nodes'].get(edge['to'])
                    if target:
                        # 层级 = 前驱节点层级 + 1
                        target['level'] = max(target['level'], node['level'] + 1)
                        in_degree[edge['to']] -= 1
                        # 入度降为0时加入队列
                        if in_degree[edge['to']] == 0:
                            queue.append(edge['to'])
    
    def _find_parallel_groups(self, graph: Dict) -> List[Dict]:
        """找出可并行执行的组"""
        # 按层级分组
        level_groups: Dict[int, List] = {}
        
        for node_id, node in graph['nodes'].items():
            level = node['level']
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(node)
        
        # 转换为数组并排序
        groups = []
        for level in sorted(level_groups.keys()):
            nodes = level_groups[level]
            groups.append({
                'level': level,
                'nodes': nodes,
                'can_parallel': len(nodes) > 1,
            })
        
        return groups
    
    def _create_execution_plan(
        self,
        graph: Dict,
        parallel_groups: List[Dict]
    ) -> Dict[str, Any]:
        """创建执行计划"""
        plan = {
            'serial': [],
            'parallel': [],
            'total_steps': len(graph['nodes']),
            'max_concurrency': 1,
        }
        
        for group in parallel_groups:
            if group['can_parallel'] and len(group['nodes']) > 1:
                # 可并行执行的组
                plan['parallel'].append({
                    'level': group['level'],
                    'steps': [
                        {
                            'id': n['id'],
                            'name': n['name'],
                            'task': n['task'],
                            'capabilities': n['capabilities'],
                            'calls': n.get('calls'),  # 保留 calls 字段
                            '_source_workflow': n.get('_source_workflow'),  # 子工作流来源
                        }
                        for n in group['nodes']
                    ],
                })
                plan['max_concurrency'] = max(
                    plan['max_concurrency'],
                    len(group['nodes'])
                )
            else:
                # 串行执行
                for node in group['nodes']:
                    plan['serial'].append({
                        'id': node['id'],
                        'name': node['name'],
                        'task': node['task'],
                        'capabilities': node['capabilities'],
                        'calls': node.get('calls'),  # 保留 calls 字段
                        'level': group['level'],
                        '_source_workflow': node.get('_source_workflow'),  # 子工作流来源
                    })
        
        return plan
    
    def detect_circular_dependency(self, graph: Dict) -> tuple:
        """
        检测循环依赖（DFS）
        
        Args:
            graph: 依赖图
            
        Returns:
            (是否存在循环依赖, 循环链列表)
        """
        visited = set()
        recursion_stack = set()
        
        def dfs(node_id: str, path: List[str]) -> tuple:
            visited.add(node_id)
            recursion_stack.add(node_id)
            path.append(node_id)
            
            for edge in graph['edges']:
                if edge['from'] == node_id:
                    target_id = edge['to']
                    
                    if target_id not in visited:
                        found, cycle = dfs(target_id, path.copy())
                        if found:
                            return True, cycle
                    elif target_id in recursion_stack:
                        # 发现循环，返回循环链
                        cycle_start = path.index(target_id)
                        return True, path[cycle_start:] + [target_id]
            
            recursion_stack.remove(node_id)
            return False, []
        
        for node_id in graph['nodes']:
            if node_id not in visited:
                found, cycle = dfs(node_id, [])
                if found:
                    self.logger.info(f"[!] 检测到循环依赖: {' → '.join(cycle)}")
                    return True, cycle
        
        return False, []
    
    def get_execution_order(self, plan: Dict) -> List[Dict]:
        """
        获取执行顺序（扁平化）
        
        Args:
            plan: 执行计划
            
        Returns:
            执行顺序列表
        """
        order = []
        
        # 收集所有步骤及其层级
        all_steps = []
        
        for step in plan.get('serial', []):
            all_steps.append(step)
        
        for group in plan.get('parallel', []):
            for step in group.get('steps', []):
                step_copy = step.copy()
                step_copy['parallel_group'] = group['level']
                all_steps.append(step_copy)
        
        # 按层级排序
        all_steps.sort(key=lambda s: s.get('level', 0) or s.get('parallel_group', 0))
        
        return all_steps


# 单例实例
step_analyzer = StepAnalyzer()
