#!/usr/bin/env python3
"""
Agent Pool Client - agent-pool 调用客户端

职责：
1. 封装 agent-pool 的调用逻辑
2. 管理 plan/execute 模式
3. 支持 execute-full 全量模式（自动 Handoff + Feedback）
4. 处理路径和导入
"""

import sys
import json
import warnings
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加src目录到sys.path（支持独立运行）
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from utils.logger import get_logger

# 从配置获取 agent-pool 路径
from utils.config import config
AGENT_POOL_PATH = config.get_agent_pool_src_path()


class AgentPoolClient:
    """agent-pool 客户端"""

    def __init__(self, mode: str = "plan", auto_handoff: bool = True, auto_feedback: bool = True):
        """
        初始化

        Args:
            mode: 执行模式
                - plan: 返回执行计划（推荐）
                - execute: 直接执行（需要 delegate_task）
            auto_handoff: 自动检测处理 Handoff
            auto_feedback: 自动回传 Feedback 触发 Evolver
        """

        self.logger = get_logger(__name__)
        self.mode = mode
        self.auto_handoff = auto_handoff
        self.auto_feedback = auto_feedback
        self._orchestrator = None
        self._initialized = False

    def _ensure_import(self):
        """确保 agent-pool 模块可导入"""
        if self._initialized:
            return

        agent_pool_path = config.get_agent_pool_src_path()

        if str(agent_pool_path) not in sys.path:
            sys.path.insert(0, str(agent_pool_path))

        try:
            from orchestrator import Orchestrator
            self._orchestrator = Orchestrator(mode=self.mode)
            self._initialized = True
            # 使用 logger 如果可用
            try:
                from utils.logger import get_logger
                logger = get_logger('agent_pool_client')
                logger.info(f"已连接 agent-pool (mode={self.mode}, handoff={self.auto_handoff}, feedback={self.auto_feedback})")
            except ImportError:
                self.logger.info(f"[AgentPoolClient] 已连接 agent-pool (mode={self.mode}, handoff={self.auto_handoff}, feedback={self.auto_feedback})")
        except ImportError as e:
            raise ImportError(f"无法导入 agent-pool: {e}\n路径: {agent_pool_path}")
    
    def execute(
        self,
        task_description: str,
        required_capabilities: List[str] = None,
        timeout: int = 300,
        max_iterations: int = 50,
        context: Dict = None,
        source_workflow: str = None,
        # === 废弃参数（v1.x兼容） ===
        workflow_name: str = None,
        node_id: int = None,
        node_name: str = None
    ) -> Dict[str, Any]:
        """
        执行任务（基础模式）
        
        Args:
            task_description: 任务描述
            required_capabilities: 所需能力
            timeout: 超时时间
            max_iterations: 最大迭代次数
            context: 执行上下文
            source_workflow: 来源工作流名称（用于专家匹配隔离）
        
        Deprecated Args (将在v2.0移除):
            workflow_name: 已废弃，请使用 source_workflow
            node_id: 已废弃，任务ID由系统自动生成
            node_name: 已废弃，请使用 task_description 描述任务
        
        Returns:
            Dict: 执行计划或执行结果
        """
        # === 废弃参数处理 ===
        deprecated_params = []
        
        if workflow_name is not None:
            deprecated_params.append('workflow_name')
            # 映射到新参数
            if source_workflow is None:
                source_workflow = workflow_name
            self.logger.warning(
                f"[DEPRECATED] workflow_name 参数已废弃，请使用 source_workflow。"
                f"映射: workflow_name='{workflow_name}' → source_workflow='{source_workflow}'"
            )
        
        if node_id is not None:
            deprecated_params.append('node_id')
            self.logger.warning(
                f"[DEPRECATED] node_id 参数已废弃，任务ID由系统自动生成。"
                f"node_id={node_id} 将被忽略"
            )
        
        if node_name is not None:
            deprecated_params.append('node_name')
            self.logger.warning(
                f"[DEPRECATED] node_name 参数已废弃，请使用 task_description 描述任务。"
                f"node_name='{node_name}' 将被忽略"
            )
        
        # 输出弃用警告
        if deprecated_params:
            warnings.warn(
                f"参数 {deprecated_params} 已废弃，将在v2.0版本移除。"
                f"请迁移到新参数：source_workflow, task_description。",
                DeprecationWarning,
                stacklevel=2
            )
        
        self._ensure_import()
        
        self.logger.info(f"\n[AgentPoolClient] 执行任务: {task_description[:50]}...")
        self.logger.info(f"[AgentPoolClient] 能力: {required_capabilities}")
        
        result = self._orchestrator.execute(
            task_description=task_description,
            required_capabilities=required_capabilities,
            timeout=timeout,
            max_iterations=max_iterations,
            context=context,
            source_workflow=source_workflow
        )
        
        return result
    
    def execute_full(
        self,
        task_description: str,
        required_capabilities: List[str] = None,
        timeout: int = 300,
        max_iterations: int = 50,
        context: Dict = None,
        model: str = None,
        source_workflow: str = None,
        # === 废弃参数（v1.x兼容） ===
        workflow_name: str = None,
        node_id: int = None,
        node_name: str = None
    ) -> Dict[str, Any]:
        """
        执行任务（全量模式）- 推荐
        
        自动启用：
        1. Handoff 检测和处理
        2. Feedback 回传和 Evolver 优化
        
        Args:
            task_description: 任务描述
            required_capabilities: 所需能力
            timeout: 超时时间
            max_iterations: 最大迭代次数
            context: 执行上下文
            model: 模型名称
            source_workflow: 来源工作流名称（用于专家匹配隔离）
        
        Deprecated Args (将在v2.0移除):
            workflow_name: 已废弃，请使用 source_workflow
            node_id: 已废弃，任务ID由系统自动生成
            node_name: 已废弃，请使用 task_description 描述任务
        
        Returns:
            Dict: 完整执行计划，包含多步指令
        """
        # === 废弃参数处理 ===
        deprecated_params = []
        
        if workflow_name is not None:
            deprecated_params.append('workflow_name')
            # 映射到新参数
            if source_workflow is None:
                source_workflow = workflow_name
            self.logger.warning(
                f"[DEPRECATED] workflow_name 参数已废弃，请使用 source_workflow。"
                f"映射: workflow_name='{workflow_name}' → source_workflow='{source_workflow}'"
            )
        
        if node_id is not None:
            deprecated_params.append('node_id')
            self.logger.warning(
                f"[DEPRECATED] node_id 参数已废弃，任务ID由系统自动生成。"
                f"node_id={node_id} 将被忽略"
            )
        
        if node_name is not None:
            deprecated_params.append('node_name')
            self.logger.warning(
                f"[DEPRECATED] node_name 参数已废弃，请使用 task_description 描述任务。"
                f"node_name='{node_name}' 将被忽略"
            )
        
        # 输出弃用警告
        if deprecated_params:
            warnings.warn(
                f"参数 {deprecated_params} 已废弃，将在v2.0版本移除。"
                f"请迁移到新参数：source_workflow, task_description。",
                DeprecationWarning,
                stacklevel=2
            )
        
        self._ensure_import()
        
        self.logger.info(f"\n[AgentPoolClient] execute-full: {task_description[:50]}...")
        self.logger.info(f"[AgentPoolClient] 能力: {required_capabilities}")
        self.logger.info(f"[AgentPoolClient] auto_handoff={self.auto_handoff}, auto_feedback={self.auto_feedback}")
        
        # 1. 获取基础执行计划
        plan = self._orchestrator.execute(
            task_description=task_description,
            required_capabilities=required_capabilities,
            timeout=timeout,
            max_iterations=max_iterations,
            context=context,
            model=model,
            source_workflow=source_workflow
        )
        
        if not plan.get('success'):
            return plan
        
        # 2. 构建完整执行指令（传入 source_workflow 用于心跳更新）
        instructions = self._build_instructions(plan, source_workflow=source_workflow)
        
        # 3. 返回完整执行计划（包含字段补全信息）
        result = {
            "success": True,
            "type": "execution_plan_with_features",
            "agent_id": plan['agent_id'],
            "task_id": plan['task_id'],
            "strategy": plan['strategy'],
            "execution": plan['execution'],
            "features": {
                "auto_handoff": self.auto_handoff,
                "auto_feedback": self.auto_feedback
            },
            "pending_instructions": instructions  # 统一使用 pending_instructions 字段名
        }
        
        # 传递字段补全信息（供主 AI 判断是否需要回传）
        if plan.get('field_completion_needed'):
            result['field_completion_needed'] = True
            result['missing_fields'] = plan.get('missing_fields', [])
            result['field_prompts'] = plan.get('field_prompts', {})
            result['field_completion_instruction'] = plan.get('field_completion_instruction', '')
        
        return result
    
    def _build_instructions(self, plan: dict, source_workflow: str = None) -> List[Dict]:
        """
        构建多步执行指令
        
        Args:
            plan: 基础执行计划
            source_workflow: 来源工作流名称（用于心跳更新路径）
        
        Returns:
            List[Dict]: 执行指令列表
        """
        instructions = []
        
        # 步骤1: 执行子 Agent（含字段补全和 feedback 注入）
        params = plan['execution']['params'].copy()
        
        # 2026-04-30 心跳更新注入：让子 agent 定期更新心跳
        if source_workflow:
            heartbeat_instruction = f"""
## 心跳更新要求

执行过程中，请定期更新心跳状态（每完成一个主要步骤）：

### 更新方法

在 Python 环境中执行：
```python
import json
from datetime import datetime
from pathlib import Path

status_file = Path("~/.hermes/workflows/{source_workflow}/status.json")
if status_file.exists():
    data = json.loads(status_file.read_text())
    data['workflow']['heartbeat'] = datetime.now().isoformat()
    data['workflow']['current_step'] = "当前步骤名称"
    status_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
```

### 更新时机

- 每完成一个主要步骤
- 遇到长时间操作时（如文件下载、扫描）
- 执行超过5分钟的操作时

**重要**：心跳更新可以防止工作流被判定为卡住。

"""
            # 合并到现有 context
            if 'context' in params and params['context']:
                params['context'] = params['context'] + "\n" + heartbeat_instruction
            else:
                params['context'] = heartbeat_instruction
            
            self.logger.info(f"[AgentPoolClient] 注入心跳更新指令: workflow={source_workflow}")
        
        # 2026-04-21 方案D: 将 feedback 注入到 delegate_task context
        # 子 agent 内部执行 feedback，简化主 AI 职责
        if self.auto_feedback and plan.get('feedback_required'):
            feedback_payload = plan.get('feedback_payload', {})
            agent_id = feedback_payload.get('agent_id', plan.get('agent_id', 'unknown'))
            task_id = feedback_payload.get('task_id', plan.get('task_id', 'unknown'))
            fields_to_complete = feedback_payload.get('fields_to_complete', [])
            
            # 构建 feedback 注入上下文
            feedback_context = f"""
## Agent 元数据

- agent_id: {agent_id}
- task_id: {task_id}

## 任务完成后必做

执行完成后，请调用 terminal 工具运行以下命令回传结果：

```bash
python ~/.hermes/skills/openclaw-imports/agent-pool/bin/agent-pool feedback \\
  --agent-id '{agent_id}' \\
  --result '{{"task_id": "{task_id}", "success": true, "duration": <实际耗时秒数>}}'
```

**注意**：
- success: 任务是否成功（true/false）
- duration: 实际执行耗时（秒）

"""
            
            # 如果有字段补全需求，添加字段补全指令
            if fields_to_complete:
                feedback_context += f"""
### 字段补全

如果任务成功，请在 result 中添加 field_completion 字段：

```json
{{
  "task_id": "{task_id}",
  "success": true,
  "duration": <实际耗时>,
  "field_completion": {{
    "personality": "根据任务推断的人格维度",
    "style": "根据任务推断的输出风格",
    "values": "根据任务推断的价值观优先级"
  }}
}}
```

"""
            
            # 合并到现有 context
            if 'context' in params and params['context']:
                params['context'] = params['context'] + "\n" + feedback_context
            else:
                params['context'] = feedback_context
            
            self.logger.info(f"[AgentPoolClient] 注入 feedback 指令到 context: agent_id={agent_id}")
        
        # 2026-04-23 Handoff 自动执行：
        # 将 handoff 检测和处理逻辑注入到 context 中
        # 让主 AI 知道如何处理子 agent 返回的 handoff 标记
        if self.auto_handoff:
            handoff_context = """
## Handoff 自动处理

如果子 agent 返回结果包含 `"status": "handoff"`，表示需要并行启动孙 agent：

**检测方法**：
```python
# 检查子 agent 返回结果
if result.get("status") == "handoff":
    pending_tasks = result.get("pending_tasks", [])
    final_goal = result.get("final_goal", "")
```

**处理流程**：
1. 调用 `delegate_task(tasks=pending_tasks)` 并行执行孙 agent
2. 等待所有孙 agent 完成
3. 如果有 `final_goal`，调用 `delegate_task(goal=final_goal)` 完成接力

**示例**：
```python
# 子 agent 返回
{
    "status": "handoff",
    "pending_tasks": [
        {"description": "分析batch_1.json", "capabilities": ["data_analysis"]},
        {"description": "分析batch_2.json", "capabilities": ["data_analysis"]}
    ],
    "final_goal": "汇总分析结果，写入输出文件"
}

# 主 agent 执行
delegate_task(tasks=pending_tasks)  # 并行执行孙 agent
delegate_task(goal=final_goal)      # 完成接力
```

"""
            # 合并到现有 context
            if 'context' in params and params['context']:
                params['context'] = params['context'] + "\n" + handoff_context
            else:
                params['context'] = handoff_context
            
            self.logger.info(f"[AgentPoolClient] 注入 handoff 处理指令到 context")
        
        # 如果有字段补全需求（旧逻辑兼容），注入到 context
        if plan.get('field_completion_needed') and not (self.auto_feedback and plan.get('feedback_required')):
            field_prompts = plan.get('field_prompts', {})
            missing_fields = plan.get('missing_fields', [])
            field_instruction = plan.get('field_completion_instruction', '')
            
            # 构建字段补全上下文
            field_context = f"""
## 字段补全任务

以下字段需要根据任务上下文补全：{missing_fields}

{field_instruction}

### 字段提示词
"""
            # 添加每个缺失字段的提示词
            for field in missing_fields:
                if field in field_prompts:
                    field_data = field_prompts[field]
                    field_context += f"\n**{field}**:\n{field_data.get('prompt', '请补全此字段')}\n"
            
            # 合并到现有 context
            if 'context' in params and params['context']:
                params['context'] = params['context'] + "\n" + field_context
            else:
                params['context'] = field_context
            
            self.logger.info(f"[AgentPoolClient] 注入字段补全指令: {missing_fields}")
        
        # 只返回一条 delegate_task 指令
        # handoff 检测和处理逻辑已注入到 context 中
        instructions.append({
            "step": 1,
            "action": "delegate_task",
            "description": "执行子 Agent 任务（含 handoff 自动处理）",
            "params": params,
            "output_key": "subagent_result",
            "auto_handoff": self.auto_handoff  # 标记此指令需要 handoff 处理
        })
        
        # 不再返回 detect_handoff 和 delegate_task_if_handoff 指令
        # 因为这些指令主 agent 无法执行
        # handoff 处理逻辑已注入到 context 中
        
        return instructions
    
    def batch_execute(
        self,
        tasks: List[Dict],
        parallel: bool = True
    ) -> Dict[str, Any]:
        """
        批量执行任务
        
        Args:
            tasks: 任务列表
            parallel: 是否并行
        
        Returns:
            Dict: 执行计划或结果
        """
        self._ensure_import()
        
        self.logger.info(f"\n[AgentPoolClient] 批量执行 {len(tasks)} 个任务 (parallel={parallel})")
        
        return self._orchestrator.batch_execute(tasks, parallel=parallel)
    
    def feedback(
        self,
        agent_id: str,
        result: Dict
    ) -> Dict[str, Any]:
        """
        回传执行结果（触发 Evolver）
        
        Args:
            agent_id: Agent ID
            result: 执行结果
        
        Returns:
            Dict: 反馈处理结果
        """
        self._ensure_import()
        
        return self._orchestrator.feedback(agent_id, result)


# 单例实例（全量模式：自动 Handoff + Feedback）
agent_pool_client = AgentPoolClient(mode="plan", auto_handoff=True, auto_feedback=True)
