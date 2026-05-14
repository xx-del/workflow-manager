#!/usr/bin/env python3
"""
Workflow Expander - 节点展开器（增强版）

职责：
1. 检测嵌套节点（calls: workflow-manager）
2. 递归加载子工作流
3. 展开为原子步骤列表
4. 传递上下文参数
5. 【新增】ID映射与依赖更新
6. 【新增】跨工作流依赖处理
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.loader import loader


class WorkflowExpander:
    """工作流节点展开器（增强版）"""
    
    def __init__(self):
        self.max_depth = 10  # 防止无限递归
        self.id_mapping = {}  # 子工作流内部节点ID映射 {原始ID: 展开后ID}
        self.main_node_mapping = {}  # 主工作流节点ID映射 {主节点ID: 子工作流出口节点ID}
        self.workflow_exits = {}  # 工作流出口节点 {工作流名: 末节点ID}
    
    def expand(
        self,
        nodes: List[Dict],
        parent_context: Dict = None,
        depth: int = 0
    ) -> List[Dict]:
        """
        递归展开嵌套节点（增强版）
        
        Args:
            nodes: 节点列表
            parent_context: 父工作流上下文（参数传递）
            depth: 当前递归深度
            
        Returns:
            展开后的原子步骤列表（所有依赖已正确映射）
        """
        if depth > self.max_depth:
            raise ValueError(f"递归深度超过限制 ({self.max_depth})，可能存在循环引用")
        
        expanded = []
        parent_context = parent_context or {}
        
        # 获取当前工作流名称（用于生成前缀）
        workflow_name = parent_context.get("_sub_workflow", "root")
        
        # 获取继承的依赖（来自父工作流节点）
        inherited_depends = parent_context.get("_inherited_depends", [])
        
        # 标记是否是子工作流的第一个节点
        is_first_node = True
        
        for node in nodes:
            if node.get("calls") == "workflow-manager":
                # 嵌套工作流节点 → 递归展开
                sub_nodes = self._expand_nested_workflow(node, parent_context, depth)
                
                # 记录子工作流的出口节点
                exit_node = self._find_exit_node(sub_nodes)
                if exit_node:
                    # 关键：建立 主工作流节点ID → 子工作流出口节点 的映射
                    # 使用单独的 main_node_mapping 避免与子工作流内部映射冲突
                    node_id = str(node.get("id", ""))
                    if node_id:
                        self.main_node_mapping[node_id] = exit_node
                    self.workflow_exits[node["name"]] = exit_node
                
                expanded.extend(sub_nodes)
                is_first_node = False  # 展开后已经不是第一个节点
            else:
                # 原子节点 → 注入上下文 + ID映射
                expanded_node = self._inject_context(node, parent_context)
                
                # 新增：ID映射处理
                expanded_node = self._apply_id_mapping(expanded_node, workflow_name)
                
                # 新增：如果是子工作流的第一个节点，继承主工作流节点的依赖
                if is_first_node and inherited_depends:
                    # 映射继承的依赖（主工作流节点ID → 展开后ID）
                    mapped_inherited = []
                    for dep in inherited_depends:
                        dep_str = str(dep)
                        # 优先使用 main_node_mapping（跨工作流依赖）
                        if dep_str in self.main_node_mapping:
                            mapped_inherited.append(self.main_node_mapping[dep_str])
                        else:
                            mapped_inherited.append(dep_str)
                    
                    # 合并映射后的依赖和节点自身的依赖
                    existing_deps = expanded_node.get("depends_on", [])
                    expanded_node["depends_on"] = list(set(mapped_inherited + existing_deps))
                    is_first_node = False  # 只有第一个节点继承依赖
                
                expanded.append(expanded_node)
        
        # 新增：更新所有依赖引用
        expanded = self._update_dependencies(expanded, parent_context)
        
        return expanded
    
    def _apply_id_mapping(
        self,
        node: Dict,
        workflow_name: str
    ) -> Dict:
        """
        应用ID映射（增强版：支持名称映射）
        
        Args:
            node: 节点定义
            workflow_name: 工作流名称
            
        Returns:
            ID已映射的节点
        """
        # 复制节点
        mapped = dict(node)
        
        # 获取原始ID和名称
        original_id = str(node.get("id", ""))
        node_name = node.get("name", "")
        
        if not original_id:
            return mapped
        
        # 生成展开后的ID
        expanded_id = f"root_{workflow_name}_{original_id}"
        
        # 记录ID映射关系
        mapping_key = f"{workflow_name}_{original_id}"
        self.id_mapping[mapping_key] = expanded_id
        self.id_mapping[original_id] = expanded_id  # 兼容旧逻辑
        
        # 新增：记录名称映射（支持 depends_on 使用名称引用）
        if node_name:
            name_mapping_key = f"{workflow_name}_{node_name}"
            self.id_mapping[name_mapping_key] = expanded_id
            self.id_mapping[node_name] = expanded_id  # 兼容无前缀查找
        
        # 更新节点ID
        mapped["id"] = expanded_id
        mapped["_original_id"] = original_id
        mapped["_workflow_name"] = workflow_name
        
        return mapped
    
    def _update_dependencies(
        self,
        nodes: List[Dict],
        parent_context: Dict
    ) -> List[Dict]:
        """
        更新所有节点的依赖引用（新增方法）
        
        Args:
            nodes: 节点列表
            parent_context: 父上下文
            
        Returns:
            依赖已更新的节点列表
        """
        updated_nodes = []
        
        for node in nodes:
            updated_node = dict(node)
            
            if "depends_on" not in updated_node:
                updated_nodes.append(updated_node)
                continue
            
            # 获取当前节点的工作流名称（用于构建正确的映射键）
            workflow_name = node.get("_workflow_name", "")
            
            updated_deps = []
            for old_dep in updated_node["depends_on"]:
                old_dep_str = str(old_dep)
                
                # 判断是否为跨工作流依赖（依赖ID已展开）
                is_expanded_id = old_dep_str.startswith("root_")
                
                # 1. 如果依赖ID已展开，直接保留
                if is_expanded_id:
                    updated_deps.append(old_dep_str)
                # 2. 优先查找子工作流内部节点映射（带工作流前缀）
                elif workflow_name:
                    mapping_key = f"{workflow_name}_{old_dep_str}"
                    if mapping_key in self.id_mapping:
                        updated_deps.append(self.id_mapping[mapping_key])
                    else:
                        # 3. 查找主工作流节点映射（跨工作流依赖）
                        if old_dep_str in self.main_node_mapping:
                            updated_deps.append(self.main_node_mapping[old_dep_str])
                        # 4. 尝试解析跨工作流依赖（通过名称）
                        elif self._is_cross_workflow_dependency(old_dep_str, parent_context):
                            resolved = self._resolve_cross_workflow_dependency(old_dep_str, parent_context)
                            if resolved:
                                updated_deps.append(resolved)
                            else:
                                print(f"⚠️ 警告: 跨工作流依赖 {old_dep_str} 无法解析")
                                updated_deps.append(old_dep_str)
                        else:
                            updated_deps.append(old_dep_str)
                # 5. 无工作流名称时的回退逻辑
                elif old_dep_str in self.main_node_mapping:
                    updated_deps.append(self.main_node_mapping[old_dep_str])
                elif old_dep_str in self.id_mapping:
                    updated_deps.append(self.id_mapping[old_dep_str])
                else:
                    updated_deps.append(old_dep_str)
            
            updated_node["depends_on"] = updated_deps
            updated_nodes.append(updated_node)
        
        return updated_nodes
    
    def _is_cross_workflow_dependency(
        self,
        dep_id: str,
        parent_context: Dict
    ) -> bool:
        """
        判断是否为跨工作流依赖（新增方法）
        
        Args:
            dep_id: 依赖ID
            parent_context: 父上下文
            
        Returns:
            是否为跨工作流依赖
        """
        # 如果依赖ID不在当前映射表中，可能是跨工作流依赖
        return dep_id not in self.id_mapping and parent_context.get("_sub_workflow")
    
    def _resolve_cross_workflow_dependency(
        self,
        dep_id: str,
        parent_context: Dict
    ) -> Optional[str]:
        """
        解析跨工作流依赖（新增方法）
        
        Args:
            dep_id: 依赖ID
            parent_context: 父上下文
            
        Returns:
            解析后的节点ID，或None
        """
        # dep_id 可能是子工作流的名称
        if dep_id in self.workflow_exits:
            return self.workflow_exits[dep_id]
        
        # 尝试在工作流名称映射中查找
        for workflow_name, exit_node in self.workflow_exits.items():
            if dep_id in workflow_name or workflow_name in dep_id:
                return exit_node
        
        return None
    
    def _find_exit_node(self, nodes: List[Dict]) -> Optional[str]:
        """
        找到工作流的出口节点（新增方法）
        
        Args:
            nodes: 节点列表
            
        Returns:
            出口节点ID，或None
        """
        if not nodes:
            return None
        
        # 收集所有节点ID
        all_ids = set()
        depended_ids = set()
        
        for node in nodes:
            node_id = node.get("id")
            if node_id:
                all_ids.add(str(node_id))
            
            for dep in node.get("depends_on", []):
                depended_ids.add(str(dep))
        
        # 出口节点：不被任何节点依赖的节点
        exit_candidates = all_ids - depended_ids
        
        if exit_candidates:
            return list(exit_candidates)[0]
        
        # 如果所有节点都被依赖，返回最后一个节点
        return str(nodes[-1].get("id")) if nodes else None
    
    def _expand_nested_workflow(
        self,
        node: Dict,
        parent_context: Dict,
        depth: int
    ) -> List[Dict]:
        """
        展开嵌套工作流节点
        
        Args:
            node: 嵌套节点定义
            parent_context: 父工作流上下文
            depth: 当前递归深度
            
        Returns:
            子工作流的展开节点
        """
        sub_workflow_name = node["name"]
        main_node_depends = node.get("depends_on", [])  # 主工作流节点的依赖
        
        print(f"    [展开] {sub_workflow_name} (depth={depth})")
        
        # 加载子工作流
        sub_workflow = loader.load(sub_workflow_name)
        
        if not sub_workflow:
            raise ValueError(f"子工作流未找到: {sub_workflow_name}")
        
        # 【修复】将 connections 转换为节点的 depends_on
        nodes = sub_workflow["nodes"]
        connections = sub_workflow.get("connections", [])
        
        # 【增强】如果 connections 为空或不完整，且 mode 为 serial，自动推断依赖
        sub_mode = sub_workflow.get("mode", "serial")
        if sub_mode == "serial":
            # 检查 connections 是否覆盖所有节点
            node_ids = [str(n.get("id")) for n in nodes]
            connected_to = set()
            for conn in connections:
                connected_to.add(str(conn.get("to")))
            
            # 如果有节点未被 connections 覆盖，自动推断串行依赖
            unconnected = [nid for nid in node_ids if nid not in connected_to and nid != node_ids[0]]
            
            if unconnected or len(connections) < len(nodes) - 1:
                # 自动生成完整串行依赖：1→2→3→...→n
                for i in range(1, len(nodes)):
                    prev_id = str(nodes[i-1].get("id"))
                    curr_id = str(nodes[i].get("id"))
                    
                    if "depends_on" not in nodes[i]:
                        nodes[i]["depends_on"] = []
                    
                    if prev_id not in nodes[i]["depends_on"]:
                        nodes[i]["depends_on"].append(prev_id)
        else:
            # 非串行模式，只处理显式 connections
            for conn in connections:
                from_id = str(conn.get("from"))
                to_id = str(conn.get("to"))
                
                # 找到目标节点，添加依赖
                for n in nodes:
                    if str(n.get("id")) == to_id:
                        if "depends_on" not in n:
                            n["depends_on"] = []
                        if from_id not in n["depends_on"]:
                            n["depends_on"].append(from_id)
        
        # 合并上下文参数
        child_context = self._merge_context(parent_context, node)
        
        # 添加子工作流标识
        child_context["_sub_workflow"] = sub_workflow_name
        # 传递主工作流节点的依赖给子工作流
        child_context["_inherited_depends"] = main_node_depends
        
        # 递归展开
        return self.expand(nodes, child_context, depth + 1)
    
    def _merge_context(
        self,
        parent_context: Dict,
        node: Dict
    ) -> Dict:
        """
        合并父工作流上下文和节点参数
        
        Args:
            parent_context: 父工作流上下文
            node: 当前节点定义
            
        Returns:
            合并后的上下文
        """
        context = dict(parent_context)  # 复制父上下文
        
        # 节点级别的参数覆盖父级
        if "params" in node:
            context.update(node["params"])
        
        # 从 node 的其他字段提取参数
        for key in ["date_start", "date_end", "input", "output"]:
            if key in node:
                context[key] = node[key]
        
        return context
    
    def _inject_context(
        self,
        node: Dict,
        context: Dict
    ) -> Dict:
        """
        将上下文注入到原子节点
        
        Args:
            node: 原子节点定义
            context: 上下文参数
            
        Returns:
            注入上下文后的节点
        """
        # 复制节点
        injected = dict(node)
        
        # 如果有 task 字段，进行参数替换
        if "task" in injected:
            task = injected["task"]
            for key, value in context.items():
                if not key.startswith("_"):  # 跳过内部字段
                    # 支持 {{params.X}} 格式
                    placeholder = f"{{{{params.{key}}}}}"
                    if placeholder in task:
                        task = task.replace(placeholder, str(value))
                    # 支持 {{X}} 格式（v6.1 新增）
                    placeholder2 = f"{{{{{key}}}}}"
                    if placeholder2 in task:
                        task = task.replace(placeholder2, str(value))
            injected["task"] = task
        
        # 添加上下文元数据
        if context.get("_sub_workflow"):
            injected["_source_workflow"] = context["_sub_workflow"]
        
        return injected
    
    def validate_dependencies(self, nodes: List[Dict]) -> Dict[str, Any]:
        """
        验证所有依赖引用都存在（新增方法）
        
        Args:
            nodes: 节点列表
            
        Returns:
            验证结果 {valid: bool, errors: List[str]}
        """
        all_ids = {str(n.get("id")) for n in nodes}
        errors = []
        
        for node in nodes:
            node_id = node.get("id")
            for dep in node.get("depends_on", []):
                dep_str = str(dep)
                if dep_str not in all_ids:
                    errors.append(f"节点 {node_id} 依赖不存在的节点 {dep_str}")
        
        if errors:
            print("⚠️ 依赖验证失败:")
            for err in errors:
                print(f"  - {err}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def get_expansion_stats(
        self,
        nodes: List[Dict],
        parent_context: Dict = None
    ) -> Dict[str, Any]:
        """
        获取展开统计信息（不实际展开）
        
        Args:
            nodes: 节点列表
            parent_context: 父工作流上下文
            
        Returns:
            统计信息
        """
        stats = {
            "total_nodes": 0,
            "nested_nodes": 0,
            "atomic_nodes": 0,
            "sub_workflows": [],
            "id_mappings": len(self.id_mapping),
            "workflow_exits": list(self.workflow_exits.keys())
        }
        
        for node in nodes:
            stats["total_nodes"] += 1
            
            if node.get("calls") == "workflow-manager":
                stats["nested_nodes"] += 1
                stats["sub_workflows"].append(node["name"])
                
                # 递归统计子工作流
                sub_workflow = loader.load(node["name"])
                if sub_workflow:
                    sub_stats = self.get_expansion_stats(
                        sub_workflow["nodes"],
                        parent_context
                    )
                    stats["total_nodes"] += sub_stats["total_nodes"]
                    stats["nested_nodes"] += sub_stats["nested_nodes"]
                    stats["atomic_nodes"] += sub_stats["atomic_nodes"]
                    stats["sub_workflows"].extend(sub_stats["sub_workflows"])
            else:
                stats["atomic_nodes"] += 1
        
        return stats
    
    def reset(self):
        """
        重置映射状态（用于新的展开任务）
        """
        self.id_mapping = {}
        self.main_node_mapping = {}
        self.workflow_exits = {}


# 单例实例
workflow_expander = WorkflowExpander()
