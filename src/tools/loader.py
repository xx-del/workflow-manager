#!/usr/bin/env python3
"""
Workflow Loader - 工作流加载器

职责：
1. 加载工作流定义（_index.yaml + WORKFLOW.md）
2. 列出所有工作流
3. 解析工作流路径（支持多个目录）
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

from utils.logger import get_logger
from utils.config import config as get_config


class WorkflowLoader:
    """工作流加载器"""


    def validate_dependencies(self, nodes: List[Dict]) -> List[str]:
        """
        验证 depends_on 引用是否有效
        
        Args:
            nodes: 节点列表
            
        Returns:
            错误列表（空列表表示通过）
        """
        errors = []
        
        # 收集所有节点名称和ID
        node_names = {node.get('name', '') for node in nodes}
        node_ids = {str(node.get('id', '')) for node in nodes}
        valid_refs = node_names | node_ids  # 名称和ID都可作为引用
        
        # 检查每个节点的 depends_on
        for node in nodes:
            node_name = node.get('name', '未命名节点')
            depends_on = node.get('depends_on', [])
            
            # 转换为列表
            if isinstance(depends_on, str):
                depends_on = [depends_on] if depends_on else []
            
            for dep in depends_on:
                # 检查引用是否存在（名称或ID）
                if dep and dep not in valid_refs:
                    errors.append(
                        f"节点 '{node_name}' 的 depends_on 引用了不存在的步骤: '{dep}'"
                    )
        
        return errors
    
    def validate_workflow_structure(self, workflow_data: Dict) -> List[str]:
        """
        验证工作流定义是否完整
        
        Args:
            workflow_data: 工作流数据
            
        Returns:
            缺失章节列表（空列表表示通过）
        """
        missing_sections = []
        
        # 检查 WORKFLOW.md 内容
        content = workflow_data.get('content', '')
        
        required_sections = ['目标', '执行步骤']
        
        for section in required_sections:
            if f'## {section}' not in content and f'# {section}' not in content:
                missing_sections.append(section)
        
        return missing_sections
    
    def validate_step_definitions(self, steps: List[Dict]) -> List[str]:
        """
        验证步骤定义是否完整
        
        Args:
            steps: 步骤列表
            
        Returns:
            缺失字段警告列表
        """
        warnings = []
        
        for i, step in enumerate(steps, 1):
            step_name = step.get('name', f'步骤 {i}')
            content = step.get('content') or ''  # 修复: None 转空字符串
            
            # 检查必需字段
            required_fields = ['做什么', '执行指令']
            
            for field in required_fields:
                if field not in content:
                    warnings.append(
                        f"步骤 '{step_name}' 缺少 '{field}' 定义"
                    )
        
        return warnings
    
    def _is_branch_workflow(self, nodes: List[Dict]) -> bool:
        """
        判断是否为拼接工作流
        
        拼接工作流特征：
        1. 所有节点都有 calls: workflow-manager
        2. 用于编排子工作流，不需要定义"做什么"和"执行指令"
        
        Args:
            nodes: 节点列表
            
        Returns:
            是否为拼接工作流
        """
        if not nodes:
            return False
        
        # 检查是否所有节点都是嵌套调用
        for node in nodes:
            if node.get("calls") != "workflow-manager":
                return False
        
        return True
    
    def _is_heartbeat_workflow(self, nodes: List[Dict]) -> bool:
        """
        判断是否为心跳驱动工作流
        
        心跳驱动工作流特征：
        1. 节点有 trigger: heartbeat 标记
        2. 节点有 type: breakpoint/auto 标记
        3. 用于长时间运行的后台任务
        
        Args:
            nodes: 节点列表
            
        Returns:
            是否为心跳驱动工作流
        """
        if not nodes:
            return False
        
        # 检查是否有心跳驱动节点
        for node in nodes:
            if node.get('trigger') == 'heartbeat':
                return True
            if node.get('type') in ['breakpoint', 'auto']:
                return True
            if node.get('heartbeat', {}).get('enabled'):
                return True
        
        return False
    
    def _identify_workflow_type(self, index: Dict, nodes: List[Dict]) -> str:
        """
        识别工作流类型
        
        类型判定优先级：
        1. branch（拼接）：type: branch 或所有节点 calls: workflow-manager
        2. heartbeat（心跳驱动）：有 heartbeat 配置或 breakpoint/auto 节点
        3. normal（普通）：其他
        
        Args:
            index: _index.yaml 内容
            nodes: 节点列表
            
        Returns:
            'branch' | 'heartbeat' | 'normal'
        """
        if not nodes:
            return 'normal'
        
        # 1. branch 类型
        if index.get('type') == 'branch':
            return 'branch'
        if all(n.get('calls') == 'workflow-manager' for n in nodes):
            return 'branch'
        
        # 2. heartbeat 类型
        config = index.get('config', {})
        if config.get('heartbeat', {}).get('enabled'):
            return 'heartbeat'
        if any(n.get('type') in ['breakpoint', 'auto'] for n in nodes):
            return 'heartbeat'
        if any(n.get('trigger') == 'heartbeat' for n in nodes):
            return 'heartbeat'
        if any(n.get('heartbeat', {}).get('enabled') for n in nodes):
            return 'heartbeat'
        
        # 3. normal 类型
        return 'normal'

    def _merge_workflow_md_commands(self, nodes: List[Dict], parsed_steps: List[Dict]) -> int:
        """
        将 WORKFLOW.md 解析的命令合并到 _index.yaml 节点
        
        合并规则：
        1. 保留 _index.yaml 的节点结构（breakpoint、auto、trigger 等类型）
        2. 通过名称匹配补充命令
        3. 不覆盖已有字段
        
        Args:
            nodes: _index.yaml 定义的节点列表
            parsed_steps: WORKFLOW.md 解析的步骤列表
            
        Returns:
            合并的节点数量
        """
        if not parsed_steps:
            return 0
        
        # 构建步骤名称到命令的映射
        step_commands = {}
        for step in parsed_steps:
            step_name = step.get('name', '')
            command = step.get('command', '')
            if step_name and command:
                step_commands[step_name] = command
        
        # 合并到节点
        merged_count = 0
        for node in nodes:
            node_name = node.get('name', '')
            node_task = node.get('task', '')
            
            # 尝试匹配：精确匹配
            if node_name in step_commands and not node.get('command'):
                node['command'] = step_commands[node_name]
                merged_count += 1
                continue
            
            # 尝试匹配：任务名匹配
            if node_task in step_commands and not node.get('command'):
                node['command'] = step_commands[node_task]
                merged_count += 1
                continue
            
            # 尝试匹配：包含匹配（节点名包含步骤名或反之）
            for step_name, command in step_commands.items():
                if not node.get('command'):
                    if step_name in node_name or node_name in step_name:
                        node['command'] = command
                        merged_count += 1
                        break
        
        return merged_count
    
    def _rebuild_depends_on(self, steps: List[Dict], logic_nodes: List[Dict]) -> None:
        """
        重建执行步骤的依赖关系（1对多模式）
        
        基于逻辑节点的串行关系，为执行步骤建立 depends_on
        
        Args:
            steps: 执行步骤列表（将被修改）
            logic_nodes: 逻辑节点列表
        """
        if not logic_nodes or not steps:
            return
        
        # 清除原始 depends_on（来自 WORKFLOW.md 解析，可能引用不存在的 ID）
        # 重新建立串行依赖链
        
        # 为每个步骤设置 depends_on
        for i, step in enumerate(steps):
            # 确保 ID 正确
            if not step.get('id'):
                step['id'] = f'step_{i+1}'
            
            if i == 0:
                # 第一个步骤：无依赖
                step['depends_on'] = []
            else:
                # 后续步骤：依赖前一个步骤的 ID
                prev_id = steps[i-1].get('id', f'step_{i}')
                step['depends_on'] = [prev_id]

    def __init__(self, workflows_dir: str = None, workspace_dir: str = None):
        """
        初始化

        Args:
            workflows_dir: 工作流目录（默认从配置读取）
            workspace_dir: 工作空间目录（默认从配置读取）
        """
        self.logger = get_logger(__name__)
        config = get_config
        self.workflows_dir = Path(workflows_dir or config.get_workflows_dir())
        self.workspace_dir = Path(workspace_dir or config.get_workspace_dir())
        
    def load(self, name: str) -> Optional[Dict[str, Any]]:
        """
        加载工作流定义
        
        Args:
            name: 工作流名称
            
        Returns:
            工作流定义字典，未找到返回 None
        """
        # 尝试从多个位置加载
        locations = [
            self.workspace_dir / name / "_index.yaml",
            self.workflows_dir / name / "_index.yaml",
            self.workspace_dir / "_index.yaml",  # 根目录索引
            self.workflows_dir / "_index.yaml",
        ]
        
        for idx_path in locations:
            if idx_path.exists():
                workflow = self._load_from_path(idx_path, name)
                if workflow:
                    return workflow
        
        return None
    
    def _load_from_path(self, idx_path: Path, name: str) -> Optional[Dict[str, Any]]:
        """从指定路径加载工作流"""
        try:
            with open(idx_path, 'r', encoding='utf-8') as f:
                index = yaml.safe_load(f)
            
            # 检查是否是根目录索引
            if 'workflows' in index and isinstance(index['workflows'], list):
                # 从根目录索引中查找
                for wf in index['workflows']:
                    if wf.get('name') == name or wf.get('id') == name:
                        return self._build_workflow(wf, idx_path.parent)
                return None
            
            # 子目录索引
            return self._build_workflow(index, idx_path.parent)
            
        except Exception as e:
            self.logger.error(f"[WorkflowLoader] 加载失败: {e}")
            return None
    
    def _build_workflow(self, index: Dict, base_path: Path) -> Dict[str, Any]:
        """构建工作流定义"""
        # 如果有 path 字段，使用它确定工作流目录
        if 'path' in index:
            workflow_path = Path(index['path'])
            if workflow_path.is_absolute():
                workflow_dir = workflow_path
            else:
                path_str = index['path']
                if path_str.startswith('workflows/'):
                    path_str = path_str[len('workflows/'):]
                workflow_dir = base_path / path_str
        else:
            workflow_dir = base_path
        
        workflow = {
            'name': index.get('name') or index.get('workflow', {}).get('name', 'unnamed'),
            'description': index.get('description') or index.get('workflow', {}).get('description', ''),
            'version': index.get('version') or index.get('workflow', {}).get('version', '1.0.0'),
            'path': str(workflow_dir),
            'nodes': index.get('nodes', []),
            'config': index.get('config', {}),
            'mode': index.get('mode') or index.get('workflow', {}).get('mode', 'serial'),
            'connections': index.get('connections', []),
            'workflow_md': None,
            'type': 'normal',  # 默认类型
        }
        
        # === 类型识别 ===
        workflow['type'] = self._identify_workflow_type(index, workflow['nodes'])
        self.logger.info(f"    工作流类型: {workflow['type']}")
        
        # 加载 WORKFLOW.md
        md_path = workflow_dir / "WORKFLOW.md"
        if md_path.exists():
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    workflow['workflow_md'] = f.read()
                    
                # 解析 WORKFLOW.md 步骤
                parsed_steps = self.parse_workflow_steps(workflow['workflow_md'])
                if parsed_steps:
                    workflow['parsed_steps'] = parsed_steps
                    
                    # === 根据类型选择展开策略 ===
                    wf_type = workflow['type']
                    
                    if wf_type == 'branch':
                        # 拼接工作流：不处理 WORKFLOW.md，保持 nodes 引用
                        pass
                    
                    elif wf_type == 'heartbeat':
                        # 心跳驱动：保留双层结构
                        # nodes = 逻辑层（_index.yaml 节点）
                        # execution_steps = 执行层（WORKFLOW.md 步骤）
                        workflow['execution_steps'] = parsed_steps
                        self.logger.info(f"    心跳驱动工作流：保留双层结构 "
                                        f"({len(workflow['nodes'])} 逻辑节点 + "
                                        f"{len(parsed_steps)} 执行步骤)")
                    
                    elif wf_type == 'normal':
                        # 普通工作流：判断节点-步骤对应关系
                        nodes_count = len(workflow['nodes'])
                        steps_count = len(parsed_steps)
                        
                        if nodes_count == steps_count:
                            # 1对1：补充命令到节点
                            merged = self._merge_workflow_md_commands(
                                workflow['nodes'], parsed_steps)
                            self.logger.info(f"    1对1模式：补充 {merged}/{nodes_count} 个节点命令")
                        elif nodes_count < steps_count:
                            # 1对多：使用 WORKFLOW.md 步骤作为 nodes
                            # 保留原始节点作为逻辑层
                            workflow['logic_nodes'] = workflow['nodes']
                            # 重建 depends_on 基于原始节点的串行关系
                            self._rebuild_depends_on(parsed_steps, workflow['nodes'])
                            workflow['nodes'] = parsed_steps
                            self.logger.info(f"    1对多模式：使用 {steps_count} 个执行步骤 "
                                            f"(原始 {nodes_count} 个逻辑节点)")
                        else:
                            # 节点比步骤多（罕见）：补充命令
                            merged = self._merge_workflow_md_commands(
                                workflow['nodes'], parsed_steps)
                            self.logger.info(f"    多对1模式：补充 {merged}/{nodes_count} 个节点命令")
            except:
                pass
        

        # === 验证阶段 ===
        # 1. 验证依赖引用
        if workflow.get('nodes'):
            dep_errors = self.validate_dependencies(workflow['nodes'])
            if dep_errors:
                error_msg = "\n".join(dep_errors)
                self.logger.error(f"工作流 '{workflow['name']}' 依赖验证失败:\n{error_msg}")
                raise ValueError(f"工作流依赖验证失败:\n{error_msg}")
        
        # 2. 验证工作流结构
        if workflow.get('workflow_md'):
            missing_sections = self.validate_workflow_structure({'content': workflow['workflow_md']})
            if missing_sections:
                error_msg = f"工作流 '{workflow['name']}' 缺少章节: {', '.join(missing_sections)}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
        
        # 3. 验证步骤定义（拼接/心跳驱动跳过）
        if workflow.get('nodes'):
            wf_type = workflow.get('type', 'normal')
            if wf_type == 'branch':
                self.logger.info(f"拼接工作流 '{workflow['name']}' 跳过步骤定义验证")
            elif wf_type == 'heartbeat':
                self.logger.info(f"心跳驱动工作流 '{workflow['name']}' 跳过步骤定义验证")
            else:
                steps = [{'name': n.get('name', ''), 'content': workflow.get('workflow_md', '')} 
                         for n in workflow['nodes']]
                step_warnings = self.validate_step_definitions(steps)
                if step_warnings:
                    warning_msg = "\n".join(step_warnings)
                    self.logger.warning(f"工作流 '{workflow['name']}' 步骤定义警告:\n{warning_msg}")
        
        return workflow
    
    def parse_workflow_steps(self, workflow_md_content: str) -> List[Dict]:
        """
        从 WORKFLOW.md 解析步骤
        
        解析格式：
        ### 步骤 N: 名称
        **做什么**: ...
        **执行指令**:
        ```bash
        命令
        ```
        """
        import re
        
        steps = []
        
        # 正则匹配步骤
        pattern = r'### 步骤\s+(\d+):\s*(.+?)\n(.+?)(?=### 步骤|\Z)'
        matches = re.findall(pattern, workflow_md_content, re.DOTALL)
        
        for match in matches:
            step_num = match[0]
            step_name = match[1].strip()
            step_content = match[2]
            
            # 提取命令
            command_match = re.search(r'```bash\n(.+?)\n```', step_content, re.DOTALL)
            command = command_match.group(1).strip() if command_match else ''
            
            # 提取描述
            desc_match = re.search(r'\*\*做什么\*\*:\s*(.+?)(?:\n|$)', step_content)
            description = desc_match.group(1).strip() if desc_match else step_name
            
            # 提取输入输出
            input_match = re.search(r'\*\*输入\*\*:\s*(.+?)(?:\n|$)', step_content)
            output_match = re.search(r'\*\*输出\*\*:\s*(.+?)(?:\n|$)', step_content)
            
            steps.append({
                'id': f'step_{step_num}',
                'name': step_name,
                'task': step_name,
                'description': description,
                'command': command,
                'input': input_match.group(1).strip() if input_match else '',
                'output': output_match.group(1).strip() if output_match else '',
                'capabilities': ['cli']  # 默认 CLI 执行
            })
        
        return steps
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        列出所有工作流
        
        Returns:
            工作流列表
        """
        workflows = []
        seen_names = set()
        
        # 从根目录索引加载
        for base_dir in [self.workspace_dir, self.workflows_dir]:
            root_idx = base_dir / "_index.yaml"
            if root_idx.exists():
                try:
                    with open(root_idx, 'r', encoding='utf-8') as f:
                        index = yaml.safe_load(f)
                    
                    if 'workflows' in index:
                        for wf in index['workflows']:
                            name = wf.get('name') or wf.get('id')
                            if name and name not in seen_names:
                                seen_names.add(name)
                                workflows.append({
                                    'name': name,
                                    'display_name': wf.get('name', name),
                                    'description': wf.get('description', ''),
                                    'version': wf.get('version', 'unknown'),
                                    'nodes_count': len(wf.get('nodes', [])),
                                    'mode': wf.get('mode', 'serial'),
                                })
                except:
                    pass
        
        # 从子目录加载
        for base_dir in [self.workspace_dir, self.workflows_dir]:
            if not base_dir.exists():
                continue
            
            for entry in base_dir.iterdir():
                if not entry.is_dir():
                    continue
                if entry.name.startswith('.') or entry.name == '_templates':
                    continue
                if entry.name in seen_names:
                    continue
                
                idx_path = entry / "_index.yaml"
                if idx_path.exists():
                    try:
                        with open(idx_path, 'r', encoding='utf-8') as f:
                            index = yaml.safe_load(f)
                        
                        name = entry.name
                        seen_names.add(name)
                        workflows.append({
                            'name': name,
                            'display_name': index.get('name', name),
                            'description': index.get('description', ''),
                            'version': index.get('version', 'unknown'),
                            'nodes_count': len(index.get('nodes', [])),
                            'mode': index.get('mode', 'serial'),
                        })
                    except:
                        pass
        
        return workflows
    
    def resolve_path(self, name: str) -> Optional[Path]:
        """
        解析工作流路径
        
        Args:
            name: 工作流名称
            
        Returns:
            工作流目录路径，未找到返回 None
        """
        locations = [
            self.workspace_dir / name,
            self.workflows_dir / name,
        ]
        
        for loc in locations:
            if loc.exists() and (loc / "_index.yaml").exists():
                return loc
        
        return None


# 单例实例
loader = WorkflowLoader()
