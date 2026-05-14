#!/usr/bin/env python3
"""
WorkflowAgentPoolAdapter - 工作流与Agent Pool的适配器

该适配器负责：
1. 将 workflow-manager 期望的接口转换为 agent_pool 实际接口
2. 处理参数映射和能力推断
3. 提供错误处理和日志记录

接口转换：
- workflow-manager 期望: execute(workflow_name, node_id, node_name, task_description, context)
- agent_pool 实际: execute(task_description, required_capabilities, timeout, context, source_workflow)

创建时间: 2026-05-14
"""

import sys
import logging
from typing import Dict, List, Any, Optional

# 导入 agent_pool 的 orchestrator
sys.path.insert(0, '/home/kali/.hermes/skills/openclaw-imports/agent-pool/src')
from orchestrator import Orchestrator


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


class WorkflowAgentPoolAdapter:
    """
    工作流 - Agent Pool 适配器
    
    职责：
    1. 将 workflow-manager 期望的接口转换为 agent_pool 实际接口
    2. 处理参数映射和能力推断
    3. 提供错误处理和日志记录
    
    使用示例：
        from workflow_agent_pool_adapter import workflow_agent_pool_adapter
        
        result = workflow_agent_pool_adapter.execute(
            workflow_name='凭证检测',
            node_id=1,
            node_name='环境准备',
            task_description='验证输入文件、检查工作目录',
            context={'work_dir': '/path/to/work'}
        )
    """
    
    # 节点名称关键词到能力的映射表
    CAPABILITY_KEYWORDS_MAP = {
        '环境': ['cli_execution'],
        '准备': ['cli_execution'],
        '检测': ['cli_execution', 'security'],
        '扫描': ['cli_execution', 'security'],
        '分析': ['data_analysis'],
        '处理': ['data_analysis'],
        '统计': ['data_analysis'],
        '网络': ['web_research'],
        '请求': ['web_research'],
        '代码': ['code_generation'],
        '生成': ['code_generation'],
        '验证': ['cli_execution'],
        '执行': ['cli_execution'],
        '部署': ['cli_execution'],
        '通知': ['cli_execution'],
        '清理': ['cli_execution'],
        '汇总': ['data_analysis'],
        '报告': ['data_analysis'],
    }
    
    # 默认能力集
    DEFAULT_CAPABILITIES = ['cli_execution']
    
    # 默认超时时间（秒）
    DEFAULT_TIMEOUT = 300
    
    # 默认最大迭代次数
    DEFAULT_MAX_ITERATIONS = 50
    
    def __init__(self, mode: str = "plan"):
        """
        初始化适配器
        
        Args:
            mode: orchestrator 执行模式
                - plan: 返回执行计划（推荐）
                - execute: 直接执行（需要注入 delegate_task 函数）
        """
        self.orchestrator = Orchestrator(mode=mode)
        self.logger = get_logger(__name__)
        self.logger.info(f"WorkflowAgentPoolAdapter 初始化完成 (mode={mode})")
    
    def execute(
        self,
        workflow_name: str,
        node_id: int,
        node_name: str,
        task_description: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        工作流接口 → Agent Pool 接口
        
        将 workflow-manager 期望的参数格式转换为 agent_pool 的实际参数格式，
        并执行任务。
        
        Args:
            workflow_name: 工作流名称（用于追踪和日志）
            node_id: 节点ID（用于追踪和上下文传递）
            node_name: 节点名称（用于推断所需能力）
            task_description: 任务描述（传递给 agent 执行）
            context: 上下文信息（工作目录、输入文件等）
        
        Returns:
            Dict: 执行结果，包含以下字段：
                - success: 是否成功
                - type: 结果类型（execution_plan/direct_result/error）
                - workflow_name: 工作流名称（回传）
                - node_id: 节点ID（回传）
                - execution: 执行计划（如果 type=execution_plan）
                - result: 执行结果（如果 type=direct_result）
                - error: 错误信息（如果 success=false）
        
        Raises:
            无直接抛出异常，所有异常都会被捕获并返回错误结果
        """
        self.logger.info(f"开始执行工作流节点: {workflow_name}/{node_name} (node_id={node_id})")
        self.logger.debug(f"任务描述: {task_description}")
        
        # 1. 推断能力
        required_capabilities = self._infer_capabilities(node_name, context)
        self.logger.info(f"推断能力: {required_capabilities}")
        
        # 2. 构建丰富化的上下文
        enriched_context = {
            **(context or {}),
            'workflow_name': workflow_name,
            'node_id': node_id,
            'node_name': node_name
        }
        
        # 3. 调用 orchestrator
        try:
            self.logger.debug(f"调用 orchestrator.execute()")
            result = self.orchestrator.execute(
                task_description=task_description,
                required_capabilities=required_capabilities,
                timeout=self.DEFAULT_TIMEOUT,
                max_iterations=self.DEFAULT_MAX_ITERATIONS,
                context=enriched_context,
                source_workflow=workflow_name
            )
            
            # 4. 转换返回格式（保持 workflow-manager 兼容）
            adapted_result = self._adapt_result(result, workflow_name, node_id, node_name)
            
            self.logger.info(f"节点执行完成: {workflow_name}/{node_name} (success={adapted_result.get('success')})")
            return adapted_result
            
        except Exception as e:
            self.logger.error(
                f"工作流节点执行失败: {workflow_name}/{node_name}",
                exc_info=True
            )
            return {
                "success": False,
                "type": "error",
                "error": type(e).__name__,
                "error_message": str(e),
                "workflow_name": workflow_name,
                "node_id": node_id,
                "node_name": node_name,
                "suggestion": "请检查任务描述和上下文参数是否正确"
            }
    
    def _infer_capabilities(
        self,
        node_name: str,
        context: Optional[Dict] = None
    ) -> List[str]:
        """
        推断节点所需能力
        
        根据节点名称中的关键词推断所需的能力集。
        如果上下文中包含特定标记，也会影响能力推断。
        
        推断优先级：
        1. 上下文中的显式 required_capabilities（最高优先级）
        2. 节点名称关键词匹配
        3. 默认能力集（最低优先级）
        
        Args:
            node_name: 节点名称
            context: 上下文信息
        
        Returns:
            List[str]: 所需能力列表
        """
        # 1. 检查上下文中是否有显式定义
        if context and 'required_capabilities' in context:
            explicit_caps = context['required_capabilities']
            if isinstance(explicit_caps, list) and explicit_caps:
                self.logger.debug(f"使用上下文中显式定义的能力: {explicit_caps}")
                return explicit_caps
        
        # 2. 根据节点名称关键词匹配
        for keyword, capabilities in self.CAPABILITY_KEYWORDS_MAP.items():
            if keyword in node_name:
                self.logger.debug(f"匹配关键词 '{keyword}'，能力: {capabilities}")
                
                # 根据上下文补充额外能力
                result_caps = capabilities.copy()
                
                if context:
                    # 如果需要浏览器
                    if context.get('needs_browser'):
                        if 'web_research' not in result_caps:
                            result_caps.append('web_research')
                    
                    # 如果需要安全工具
                    if context.get('needs_security_tools'):
                        if 'security' not in result_caps:
                            result_caps.append('security')
                
                return result_caps
        
        # 3. 返回默认能力集
        self.logger.debug(f"未匹配到关键词，使用默认能力: {self.DEFAULT_CAPABILITIES}")
        return self.DEFAULT_CAPABILITIES.copy()
    
    def _adapt_result(
        self,
        result: Dict[str, Any],
        workflow_name: str,
        node_id: int,
        node_name: str
    ) -> Dict[str, Any]:
        """
        转换返回格式
        
        将 agent_pool 的返回格式转换为 workflow-manager 期望的格式。
        主要添加 workflow_name、node_id、node_name 等追踪字段。
        
        Args:
            result: agent_pool 返回的结果
            workflow_name: 工作流名称
            node_id: 节点ID
            node_name: 节点名称
        
        Returns:
            Dict: 转换后的结果
        """
        # 保持原有结果的所有字段
        adapted = {
            **result,
            # 添加 workflow-manager 期望的字段
            'workflow_name': workflow_name,
            'node_id': node_id,
            'node_name': node_name
        }
        
        # 确保关键字段存在
        if 'success' not in adapted:
            adapted['success'] = result.get('success', True)
        
        if 'type' not in adapted:
            # 根据结果内容推断类型
            if 'execution' in result:
                adapted['type'] = 'execution_plan'
            elif 'result' in result:
                adapted['type'] = 'direct_result'
            elif 'error' in result:
                adapted['type'] = 'error'
            else:
                adapted['type'] = 'unknown'
        
        return adapted
    
    def batch_execute(
        self,
        tasks: List[Dict[str, Any]],
        parallel: bool = True
    ) -> Dict[str, Any]:
        """
        批量执行任务
        
        Args:
            tasks: 任务列表，每个任务包含：
                - workflow_name: 工作流名称
                - node_id: 节点ID
                - node_name: 节点名称
                - task_description: 任务描述
                - context: 上下文（可选）
            parallel: 是否并行执行
        
        Returns:
            Dict: 批量执行结果
        """
        self.logger.info(f"批量执行 {len(tasks)} 个任务 (parallel={parallel})")
        
        # 转换任务格式
        orchestrator_tasks = []
        for task in tasks:
            node_name = task.get('node_name', '')
            context = task.get('context')
            
            orchestrator_tasks.append({
                'description': task.get('task_description', ''),
                'capabilities': self._infer_capabilities(node_name, context),
                'timeout': task.get('timeout', self.DEFAULT_TIMEOUT),
                'context': {
                    **(context or {}),
                    'workflow_name': task.get('workflow_name'),
                    'node_id': task.get('node_id'),
                    'node_name': node_name
                }
            })
        
        try:
            result = self.orchestrator.batch_execute(orchestrator_tasks, parallel=parallel)
            
            # 添加原始任务信息
            return {
                **result,
                'workflow_tasks': tasks
            }
            
        except Exception as e:
            self.logger.error("批量执行失败", exc_info=True)
            return {
                "success": False,
                "type": "error",
                "error": type(e).__name__,
                "error_message": str(e)
            }
    
    def set_delegate_task_fn(self, fn):
        """
        设置 delegate_task 函数（execute 模式必需）
        
        Args:
            fn: delegate_task 函数
        """
        self.orchestrator.set_delegate_task_fn(fn)
        self.logger.info("已设置 delegate_task 函数")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取适配器状态
        
        Returns:
            Dict: 状态信息
        """
        orchestrator_status = self.orchestrator.get_status()
        return {
            **orchestrator_status,
            'adapter': 'WorkflowAgentPoolAdapter',
            'default_timeout': self.DEFAULT_TIMEOUT,
            'default_max_iterations': self.DEFAULT_MAX_ITERATIONS,
            'default_capabilities': self.DEFAULT_CAPABILITIES
        }


# ============================================================
# 全局实例（workflow-manager 可直接导入使用）
# ============================================================
workflow_agent_pool_adapter = WorkflowAgentPoolAdapter()


# ============================================================
# 便捷函数
# ============================================================
def execute_workflow_node(
    workflow_name: str,
    node_id: int,
    node_name: str,
    task_description: str,
    context: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    执行工作流节点的便捷函数
    
    直接使用全局适配器实例执行任务。
    
    Args:
        workflow_name: 工作流名称
        node_id: 节点ID
        node_name: 节点名称
        task_description: 任务描述
        context: 上下文信息
    
    Returns:
        Dict: 执行结果
    """
    return workflow_agent_pool_adapter.execute(
        workflow_name=workflow_name,
        node_id=node_id,
        node_name=node_name,
        task_description=task_description,
        context=context
    )


# ============================================================
# 测试代码
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("WorkflowAgentPoolAdapter 测试")
    print("=" * 60)
    
    # 测试 1: 基本执行
    print("\n[测试 1] 基本执行")
    result = workflow_agent_pool_adapter.execute(
        workflow_name='凭证检测',
        node_id=1,
        node_name='环境准备',
        task_description='验证输入文件、检查工作目录',
        context={'work_dir': '/tmp/test'}
    )
    print(f"结果类型: {result.get('type')}")
    print(f"工作流: {result.get('workflow_name')}")
    print(f"节点ID: {result.get('node_id')}")
    print(f"成功: {result.get('success')}")
    
    # 测试 2: 能力推断
    print("\n[测试 2] 能力推断")
    caps = workflow_agent_pool_adapter._infer_capabilities('执行检测', {})
    print(f"'执行检测' -> {caps}")
    
    caps = workflow_agent_pool_adapter._infer_capabilities('数据分析', {})
    print(f"'数据分析' -> {caps}")
    
    caps = workflow_agent_pool_adapter._infer_capabilities('未知节点', {})
    print(f"'未知节点' -> {caps}")
    
    # 测试 3: 状态查询
    print("\n[测试 3] 状态查询")
    status = workflow_agent_pool_adapter.get_status()
    print(f"适配器: {status.get('adapter')}")
    print(f"模式: {status.get('mode')}")
    print(f"默认超时: {status.get('default_timeout')}秒")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
