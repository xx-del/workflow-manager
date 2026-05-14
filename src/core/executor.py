#!/usr/bin/env python3
"""
Workflow Executor - 工作流执行器

职责：
1. 编排工作流执行（5阶段）
2. 执行单个步骤（调用 agent-pool）
3. 并行执行步骤组
4. 心跳管理
"""

import time
import os
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from tools.loader import loader
from tools.status import status_manager
from tools.history import history_manager
from utils.config import config
from utils.logger import get_logger
from utils.heartbeat import HeartbeatManager
from core.analyzer import StepAnalyzer, step_analyzer
from core.consolidator import ResultConsolidator, result_consolidator
from core.agent_pool_client import agent_pool_client


class WorkflowExecutor:
    """工作流执行器"""

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        self.analyzer = StepAnalyzer()
        self.consolidator = ResultConsolidator()
        self.terminal_timeout = config.get_terminal_timeout()
        self.context = context or {}
        self.logger = get_logger('executor')

        # 执行状态
        self.current_workflow_path = None
        self.current_workflow_name = None
        self.current_step = None
        self.completed_steps = 0
        self.total_steps = 0

        # 心跳生命周期配置（Phase 2: 心跳生命周期绑定）
        # 默认保持心跳运行，直到工作流完成
        self._keep_heartbeat_on_return = True

        # 统一心跳管理器
        self._heartbeat = HeartbeatManager(
            interval=300,
            status_manager=status_manager
        )
        self._heartbeat.on_fail(self._on_heartbeat_failed)
    
    def _generate_constraint_sections(self, workflow: Dict[str, Any]) -> List[str]:
        """生成约束清单章节（动态注入）"""
        sections = []
        workflow_type = workflow.get('type', 'normal')
        workflow_mode = workflow.get('mode', 'serial')
        
        # B-F类
        sections.append(self._generate_execution_behavior_constraints())
        sections.append(self._generate_ai_responsibility_constraints())
        sections.append(self._generate_exception_handling_constraints())
        sections.append(self._generate_progress_tracking_constraints())
        sections.append(self._generate_completion_criteria_constraints())
        
        # G类：拼接工作流
        if workflow_type == 'branch':
            sections.append(self._generate_composite_workflow_constraints(workflow))
        elif workflow_mode == 'serial':
            sections.append(self._generate_serial_workflow_constraints())
        elif workflow_mode == 'parallel':
            sections.append(self._generate_parallel_workflow_constraints())
        
        if workflow_type == 'heartbeat':
            sections.append(self._generate_heartbeat_workflow_constraints())
        
        return sections

    def _generate_execution_behavior_constraints(self) -> str:
        return """### 执行行为约束

**绝对禁止**:
- ❌ 禁止修改命令
- ❌ 禁止添加 timeout 参数
- ❌ 禁止跳过步骤

**必须遵守**:
- ✅ 严格按指令执行
- ✅ 验证每个输出
- ✅ 每步执行后更新状态"""

    def _generate_ai_responsibility_constraints(self) -> str:
        return """### 主AI职责边界约束

**禁止行为**:
- ❌ 禁止自己读取 _index.yaml
- ❌ 禁止自己判断步骤顺序
- ❌ 禁止直接调用 delegate_task 未通过 execute.py"""

    def _generate_exception_handling_constraints(self) -> str:
        return """### 异常处理约束

**处理流程**:
- 立即停止工作流（不诊断、不修复、不跳过）
- 上报异常现象
- 等待用户指示"""

    def _generate_progress_tracking_constraints(self) -> str:
        return """### 进度记录约束

**必须记录**:
- 更新 status.json
- 记录执行日志"""

    def _generate_completion_criteria_constraints(self) -> str:
        return """### 完成判定约束

**完成标准**:
- 所有步骤状态 = completed
- 所有预期输出文件存在"""

    def _generate_composite_workflow_constraints(self, workflow: Dict[str, Any]) -> str:
        nodes = workflow.get('nodes', [])
        sub_workflows = []
        for node in nodes:
            if node.get('calls') == 'workflow-manager':
                sub_workflows.append({'name': node.get('name'), 'depends_on': node.get('depends_on', [])})
        
        table = "| 序号 | 子工作流 | 依赖 | 状态 |\n|------|---------|------|------|\n"
        for i, sf in enumerate(sub_workflows, 1):
            dep = ", ".join(sf['depends_on']) if sf['depends_on'] else "无"
            table += f"| {i} | {sf['name']} | {dep} | ⏳ |\n"
        
        return f"""### 拼接工作流特殊约束（type: branch）

**核心规则**:
- ⚠️ 子工作流必须串行执行（禁止并行启动）
- ⚠️ 当前子工作流完成后自动执行下一个（禁止询问用户）
- ⚠️ 所有子工作流完成后工作流才算完成

**禁止行为**:
- ❌ 禁止询问"是否继续执行下一个子工作流"
- ❌ 禁止并行启动存在依赖关系的子工作流

**子工作流执行状态追踪**:
{table}
**状态更新规则**:
- 主 AI 在执行子工作流前更新状态为 running
- 主 AI 在子工作流完成后更新状态为 completed
- 所有子工作流状态 = completed → 工作流完成"""

    def _generate_serial_workflow_constraints(self) -> str:
        return """### 串行工作流约束

**核心规则**:
- 步骤必须按顺序执行
- 当前步骤完成后再执行下一步"""

    def _generate_parallel_workflow_constraints(self) -> str:
        return """### 并行工作流约束

**核心规则**:
- 无依赖步骤可并行执行
- 最大并发数：3"""

    def _generate_heartbeat_workflow_constraints(self) -> str:
        return """### 心跳驱动工作流约束

**特征**:
- 包含断点步骤
- 执行由心跳脚本自动接管"""



    def generate_execution_plan_md(self, workflow: Dict[str, Any]) -> str:
        """
        生成执行计划 status.md（AI可读格式）
        
        类似 planning-with-files 的 task_plan.md
        在执行前生成一次，包含所有步骤详情和约束
        
        Args:
            workflow: 工作流定义字典
            
        Returns:
            status.md 文件路径
        """
        from datetime import datetime
        
        workflow_path = workflow['path']
        workflow_name = workflow['name']
        nodes = workflow['nodes']
        
        # 读取 WORKFLOW.md 获取目标
        workflow_md_path = Path(workflow_path) / "WORKFLOW.md"
        goal = ""
        if workflow_md_path.exists():
            md_content = workflow_md_path.read_text(encoding='utf-8')
            if "## 目标" in md_content:
                goal_section = md_content.split("## 目标")[1].split("##")[0].strip()
                # 取第一行非空内容
                for line in goal_section.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("|") and not line.startswith("-"):
                        goal = line[:200]
                        break
        
        # 生成 Markdown
        md_lines = [
            f"# 工作流执行计划：{workflow_name}",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**执行模式**: 串行严格模式",
            f"**总步骤**: {len(nodes)}",
            "",
            "---",
            "",
            "## 目标",
            goal or "（未定义）",
            "",
            "---",
            "",
            "## 执行步骤",
            "",
        ]
        
        # 添加每个步骤
        for i, node in enumerate(nodes, 1):
            step_name = node.get('name', f'步骤{i}')
            description = node.get('description', node.get('task', '无描述'))
            command = node.get('command', '（无命令）')
            input_desc = node.get('input', '无')
            output_desc = node.get('output', '无')
            
            md_lines.extend([
                f"### 步骤 {i}: {step_name}",
                f"- **做什么**: {description}",
                f"- **执行指令**: ",
                f"  ```bash",
                f"  {command}",
                f"  ```",
                f"- **输入**: {input_desc}",
                f"- **输出**: {output_desc}",
                f"- **状态**: ⏳ 待执行",
                "",
            ])
        
        # 添加约束章节（动态注入）
        md_lines.extend(["---", ""])
        
        # 动态生成约束章节
        constraint_sections = self._generate_constraint_sections(workflow)
        for section in constraint_sections:
            md_lines.append(section)
            md_lines.append("")
        
        # 添加错误日志
        md_lines.extend([
            "---",
            "",
            "## 错误日志（执行时填写）",
            "",
            "| 错误 | 步骤 | 尝试 | 解决方案 |",
            "|------|------|------|----------|",
            "| (执行时填写) | | | |",
            "",
        ])
        
        md_content = "\n".join(md_lines)
        
        # 写入文件
        status_md_path = Path(workflow_path) / "status.md"
        status_md_path.write_text(md_content, encoding='utf-8')
        
        self.logger.info(f"已生成执行计划: {status_md_path}")
        return str(status_md_path)

    async def get_execution_plans(self, workflow_name: str) -> Dict[str, Any]:
        """
        获取执行计划（不执行）
        
        用于 --plan-only 模式，返回待执行的步骤列表
        
        Args:
            workflow_name: 工作流名称
            
        Returns:
            执行计划字典
        """
        # 加载工作流
        workflow = loader.load(workflow_name)
        if not workflow:
            raise ValueError(f"工作流未找到: {workflow_name}")
        
        # 生成 status.md
        status_md_path = self.generate_execution_plan_md(workflow)
        self.logger.info(f"已生成执行计划: {status_md_path}")
        
        # 展开嵌套节点
        from expander import workflow_expander
        expanded_nodes = workflow_expander.expand(workflow['nodes'])
        
        # 分析步骤依赖
        plan = self.analyzer.analyze(expanded_nodes, workflow.get('connections'))
        
        # 构建 pending_instructions
        pending_instructions = []
        for i, node in enumerate(expanded_nodes, 1):
            pending_instructions.append({
                'step_id': node.get('id', i),
                'step_name': node.get('name', f'步骤{i}'),
                'action': 'execute_step',
                'description': node.get('task', '无描述'),
                'command': node.get('command', '（无命令）')
            })
        
        return {
            'workflow': workflow_name,
            'total_steps': len(expanded_nodes),
            'mode': workflow.get('mode', 'serial'),
            'pending_instructions': pending_instructions,
            'status_md_path': status_md_path
        }

    async def execute(
        self,
        workflow_name: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行工作流（5阶段）
        
        Args:
            workflow_name: 工作流名称
            options: 执行选项
                - dry_run: 只返回执行计划
                - serial: 强制串行执行
                - max_agents: 最大并发数
                - continue_on_error: 步骤失败后继续
                
        Returns:
            执行结果
        """
        options = options or {}
        start_time = time.time()
        
        # Phase 2: 心跳生命周期绑定 - 从 options 读取配置
        self._keep_heartbeat_on_return = options.get('keep_heartbeat', True)
        
        self.logger.info(f"\n{'=' * 50}")
        self.logger.info(f"执行工作流: {workflow_name}")
        self.logger.info(f"{'=' * 50}")
        
        try:
            # Phase 1: 加载工作流
            self.logger.info(f"[1/6] 加载工作流...")
            workflow = loader.load(workflow_name)
            
            # ⭐ 生成执行计划 status.md（AI可读格式）
            status_md_path = self.generate_execution_plan_md(workflow)
            self.logger.info(f"[0/6] 已生成执行计划: {status_md_path}")
            
            if not workflow:
                raise ValueError(f"工作流未找到: {workflow_name}")
            
            self.logger.info(f"    名称: {workflow['name']}")
            self.logger.info(f"    原始节点: {len(workflow['nodes'])}")
            
            # Phase 1.5: 展开嵌套节点
            self.logger.info(f"[2/6] 展开嵌套节点...")
            from expander import workflow_expander
            
            # 获取执行参数
            params = options.get('params', {})
            
            # 展开节点
            expanded_nodes = workflow_expander.expand(
                workflow['nodes'],
                parent_context=params
            )
            
            self.logger.info(f"    展开后原子步骤: {len(expanded_nodes)}")
            
            # 更新 workflow
            workflow['nodes'] = expanded_nodes
            workflow['_expanded'] = True
            
            self.current_workflow_path = workflow['path']
            self.current_workflow_name = workflow['name']
            self.total_steps = len(expanded_nodes)
            self.completed_steps = 0
            
            # 初始化状态
            status_manager.init_status(
                workflow['path'],
                workflow['name'],
                self.total_steps
            )
            
            # 创建执行追踪表（约束机制）
            self._tracking_id = f"wf-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            tracking_dir = Path.home() / ".hermes" / "workflow-tracking"
            tracking_dir.mkdir(parents=True, exist_ok=True)
            self._tracking_file = tracking_dir / f"{self._tracking_id}.json"
            
            tracking_data = {
                "tracking_id": self._tracking_id,
                "workflow_name": workflow['name'],
                "workflow_path": workflow['path'],
                "total_steps": self.total_steps,
                "planned_steps": [],  # 新增：计划收集阶段
                "completed_steps": [],  # 实际执行完成阶段
                "skipped_steps": [],
                "violations": [],
                "status": "planning",  # 修改：初始状态为 planning
                "created_at": datetime.now().isoformat(),
            }
            self._tracking_file.write_text(json.dumps(tracking_data, ensure_ascii=False, indent=2))
            self.logger.info(f"    追踪文件: {self._tracking_file}")
            
            # Phase 2: 分析步骤依赖
            self.logger.info(f"[3/6] 分析步骤依赖...")
            plan = self.analyzer.analyze(expanded_nodes, workflow.get('connections'))

            self.logger.info(f"    串行步骤: {len(plan['serial'])}")
            self.logger.info(f"    并行组: {len(plan['parallel'])}")
            self.logger.info(f"    最大并发: {plan['max_concurrency']}")

            # Phase 3: 检查 dry-run 模式
            if options.get('dry_run'):
                self.logger.info(f"[dry-run] 返回执行计划")
                return {
                    'dry_run': True,
                    'plan': plan,
                    'workflow': workflow,
                    'expanded_nodes': len(expanded_nodes),
                }
            
            # 检查是否禁用 executor 心跳（断点工作流使用自身心跳）
            config = workflow.get('config', {})
            executor_heartbeat = config.get('executor_heartbeat', True)
            
            if executor_heartbeat:
                # 启动心跳
                await self._start_heartbeat()
                self.logger.info("[Executor] 心跳已启动")
            else:
                self.logger.info("[Executor] 已禁用默认心跳（工作流使用独立心跳）")
            
            # 守护监控不在此启动
            # 守护Agent由 heartbeat-monitor.py 按需唤醒（心跳超时后触发）
            # 参考：references/guardian.md
            
            self.logger.info(f"[4/6] 收集执行计划...")
            workflow_result = await self._execute_workflow(workflow, plan, options)

            # Phase 5: 判断执行模式
            self.logger.info(f"[5/6] 返回执行计划")
            
            all_instructions = workflow_result.get('all_instructions', [])
            
            # 检测是否为严格串行
            # 规则：工作流定义为 serial 模式，或者无并行组，或者只有一个并行组但仅含单节点
            is_strict_serial = (
                workflow.get('mode') == 'serial' or 
                len(plan.get('parallel', [])) == 0 or
                all(len(g.get('steps', [])) <= 1 for g in plan.get('parallel', []))
            )
            
            # 判断是否有真正的并行步骤（同层级多个节点）
            has_real_parallel = not is_strict_serial and any(
                len(g.get('steps', [])) > 1 for g in plan.get('parallel', [])
            )
            
            # 判断是否为混合模式（有并行组，但也有串行依赖）
            # 规则：并行步骤数 < 总步骤数 - 并行组数（每个并行组最后一步可能是汇总）
            total_nodes = len(workflow.get('nodes', []))
            parallel_groups = plan.get('parallel', [])
            parallel_nodes = sum(len(g.get('steps', [])) for g in parallel_groups)
            # 混合模式：有并行组，但总节点数 > 并行节点数 + 并行组数（表示有独立的串行步骤）
            is_mixed = has_real_parallel and total_nodes > parallel_nodes + len(parallel_groups)
            
            # 追加 finalize 指令（发送完成通知）
            finalize_instruction = {
                'step': 'finalize',
                'action': 'terminal',
                'description': f'发送工作流完成通知并生成报告',
                'command': f'python actions/complete.py {workflow["name"]}',
                'is_final': True
            }
            all_instructions.append(finalize_instruction)
            
            return {
                'status': 'execution_required',
                'workflow': workflow['name'],
                'total_steps': len(all_instructions),
                'mode': workflow.get('mode', 'serial'),
                'pending_instructions': all_instructions,
                'planning_results': workflow_result.get('step_results', []),
                'execution_status': 'awaiting_delegate_task',
                '_tracking_id': getattr(self, '_tracking_id', None),
                '_tracking_file': str(self._tracking_file) if hasattr(self, '_tracking_file') else None,
                
                # 新增：强制使用标记（方案 C）
                '_enforcement': {
                    'plan_id': getattr(self, '_tracking_id', None),
                    'must_use_instructions': True,
                    'bypass_detection': True,
                    'code_implemented': [
                        'loader.load',
                        'expander.expand',
                        'analyzer.analyze',
                        'analyzer._calculate_levels',
                        'analyzer._find_parallel_groups',
                        'analyzer.detect_circular_dependency',
                        'agent_pool_client.execute_full',
                        'agent_pool_client._build_instructions'
                    ]
                },
                
                # 新增：违规检测
                'violation_detection': {
                    'message': '检测到绕过行为将记录到 guardian 日志',
                    'tracking_file': str(self._tracking_file) if hasattr(self, '_tracking_file') else None,
                    'bypass_actions': [
                        '直接读取 _index.yaml',
                        '直接调用 delegate_task 未通过 execute.py',
                        '自己判断步骤顺序',
                        '自己处理 Handoff/Feedback'
                    ]
                },
                
                'execution_mode': {
                    'type': 'strict_serial' if is_strict_serial else ('serial' if is_mixed else 'parallel'),
                    'delegate_task_usage': 'single' if is_strict_serial else ('single' if is_mixed else 'batch'),
                    'reason': '链式依赖，必须逐个执行' if is_strict_serial else ('部分步骤可并行，但有串行依赖' if is_mixed else '存在可并行组'),
                    'warning': '⚠️ 禁止使用 delegate_task(tasks=[...]) 批量并行执行' if is_strict_serial else ('⚠️ 部分步骤可并行，部分需串行执行' if is_mixed else None)
                },
                'message': '⚠️ 必须使用返回的 pending_instructions，禁止绕过代码工具',
                'ai_action_required': {
                    'tool': 'delegate_task',
                    'usage': '逐个调用 delegate_task(task=...)' if is_strict_serial else '批量调用 delegate_task(tasks=[...])' if has_real_parallel else '逐个调用',
                    'instructions_count': len(all_instructions),
                    'mandatory_check': {
                        'question': '你是否正在使用返回的 pending_instructions？',
                        'if_no': '立即停止，重新阅读 workflow-manager SKILL.md「执行约束」章节',
                        'bypass_detection': '检测到绕过行为将记录到 guardian 日志'
                    }
                },
                'tracking_update_guide': {
                    'note': '主 AI 应在每个步骤执行完成后更新追踪状态',
                    'method': '创建 WorkflowExecutor 实例后调用 update_step_status()',
                    'example': {
                        'step_id': '从 pending_instructions 获取',
                        'status': 'completed | failed | skipped',
                        'duration': '执行耗时（秒）',
                        'error': '错误信息（可选）'
                    }
                },
                # Phase 2: 心跳生命周期绑定 - 返回 finalize 信息
                'return_info': {
                    'heartbeat_running': self._keep_heartbeat_on_return,
                    'finalize_required': self._keep_heartbeat_on_return,  # 提醒主 AI 调用完成方法
                    'finalize_command': f'python actions/complete.py {workflow["name"]}',
                    'note': '工作流完成后必须调用 finalize 方法停止心跳和守护监控'
                }
            }
            
        except Exception as e:
            self.logger.error(f"工作流执行失败: {e}")
            
            # 更新状态为失败
            if self.current_workflow_path:
                status_manager.update_status(self.current_workflow_path, {
                    'status': 'failed',
                    'error': str(e),
                })
            
            raise
            
        finally:
            # Phase 2: 心跳生命周期绑定
            # 只有在 keep_heartbeat=False 时才停止心跳
            # 否则心跳继续运行，直到工作流完成
            if not self._keep_heartbeat_on_return:
                await self._stop_heartbeat()
                self.logger.info("[Executor] 心跳已停止（keep_heartbeat=False）")
            else:
                self.logger.info("[Executor] 心跳持续运行中，等待工作流完成")
    
    async def _execute_workflow(
        self,
        workflow: Dict,
        plan: Dict,
        options: Dict
    ) -> Dict:
        """执行工作流（收集执行计划）"""
        all_instructions = []
        step_results = []
        force_serial = options.get('serial', False)
        max_agents = options.get('max_agents', 3)
        continue_on_error = options.get('continue_on_error', False)
        
        # 执行串行部分
        for step in plan['serial']:
            self.logger.info(f"[*] 处理串行步骤: {step['name']}")

            result = await self._execute_step(step, workflow)
            step_results.append(result)
            
            # 收集 instructions
            if result.get('instructions'):
                all_instructions.extend([
                    {
                        'step_id': step['id'],
                        'step_name': step['name'],
                        **inst
                    }
                    for inst in result['instructions']
                ])

            self.completed_steps += 1

            # 更新心跳进度
            self._heartbeat.update(
                current_step=step.get('name'),
                step_progress=f"{self.completed_steps}/{self.total_steps}"
            )

            if not result['success'] and not continue_on_error:
                self.logger.error(f" 步骤失败，停止工作流")
                break
        
        # 执行并行部分
        if not force_serial and plan['parallel']:
            for group in plan['parallel']:
                self.logger.info(f"[*] 处理并行组 (level {group['level']}): {len(group['steps'])} 步骤")

                parallel_results = await self._execute_parallel_group(
                    group['steps'],
                    workflow,
                    max_agents
                )
                
                for result in parallel_results:
                    step_results.append(result)
                    if result.get('instructions'):
                        all_instructions.extend([
                            {
                                'step_id': result['id'],
                                'step_name': result['name'],
                                **inst
                            }
                            for inst in result['instructions']
                        ])

                self.completed_steps += len(parallel_results)

                # 更新心跳进度
                self._heartbeat.update(
                    step_progress=f"{self.completed_steps}/{self.total_steps}"
                )

        return {
            'step_results': step_results,
            'all_instructions': all_instructions
        }
    
    async def _execute_step(
        self,
        step: Dict,
        workflow: Dict
    ) -> Dict[str, Any]:
        """执行单个步骤（返回执行计划）"""
        start_time = time.time()
        
        self.current_step = step
        
        # 注入上下文参数（日期范围等）
        if self.context:
            step['_context'] = self.context
        
        try:
            self.logger.info(f"    能力: {', '.join(step.get('capabilities', []))}")
            
            # 构建任务描述（传入 context 用于替换占位符）
            task_description = self._build_task_description(step, workflow, self.context)
            
            # 调用 agent-pool 获取执行计划
            result = await self._call_agent_pool(
                task_description,
                step.get('capabilities', []),
                step.get('_context')  # 新增：传递上下文参数
            )
            
            duration = round(time.time() - start_time)
            
            # 计划收集阶段不标记 completed，由主 AI 实际执行后标记
            # 修复：区分 planned（计划已收集）和 completed（实际执行完成）
            if result.get('success'):
                self._mark_step_planned(step.get('id', ''), step.get('name', ''))
            
            # 2026-04-23 Handoff 自动执行修复：
            # agent_pool_client 现在只返回一条 delegate_task 指令
            # handoff 处理逻辑已注入到 context 中
            # 主 agent 执行 delegate_task 时会看到 handoff 处理说明
            all_instructions = result.get('pending_instructions', result.get('instructions', []))
            
            # 直接返回所有指令（agent_pool_client 已处理 handoff）
            pending_instructions = all_instructions
            
            return {
                'id': step['id'],
                'name': step['name'],
                'success': result.get('success', False),
                'status': result.get('status'),
                'instructions': pending_instructions if pending_instructions else all_instructions,
                'agent_id': result.get('agent_id'),
                'message': result.get('message'),
                'duration': duration,
                'error': result.get('error'),
            }
            
        except Exception as e:
            duration = round(time.time() - start_time)
            
            # 步骤失败标记
            self._mark_step_failed(step.get('id', ''), step.get('name', ''), str(e))
            
            return {
                'id': step['id'],
                'name': step['name'],
                'success': False,
                'status': 'error',
                'error': str(e),
                'duration': duration,
                'instructions': []
            }
    
    def _mark_step_planned(self, step_id: str, step_name: str):
        """标记步骤计划已收集（新增方法）
        
        区分：
        - planned: 执行计划已收集，等待主 AI 执行
        - completed: 实际执行已完成
        """
        if not hasattr(self, '_tracking_file') or not self._tracking_file:
            return
        
        try:
            data = json.loads(self._tracking_file.read_text())
            
            # 添加 planned_steps 字段（如果不存在）
            if 'planned_steps' not in data:
                data['planned_steps'] = []
            
            data['planned_steps'].append({
                'step_id': step_id,
                'step_name': step_name,
                'planned_at': datetime.now().isoformat()
            })
            
            self._tracking_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            self.logger.debug(f"    步骤计划已收集: {step_name}")
        except Exception as e:
            self.logger.warning(f"    步骤计划标记失败: {e}")
    
    def _mark_step_failed(self, step_id: str, step_name: str, error: str):
        """标记步骤失败"""
        if not hasattr(self, '_tracking_file') or not self._tracking_file:
            return
        
        try:
            data = json.loads(self._tracking_file.read_text())
            data["violations"].append({
                "step_id": step_id,
                "step_name": step_name,
                "error": error,
                "failed_at": datetime.now().isoformat()
            })
            self._tracking_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            self.logger.warning(f"    失败标记失败: {e}")
    
    def update_step_status(
        self,
        step_id: str,
        status: str,
        duration: int = 0,
        error: str = None
    ) -> bool:
        """更新步骤状态（供主 AI 调用）
        
        Args:
            step_id: 步骤 ID
            status: 状态 (completed | failed | skipped)
            duration: 执行耗时（秒）
            error: 错误信息（如果失败）
        
        Returns:
            bool: 更新是否成功
        """
        if not hasattr(self, '_tracking_file') or not self._tracking_file:
            return False
        
        try:
            data = json.loads(self._tracking_file.read_text())
            
            # 查找步骤名称
            step_name = step_id
            for planned in data.get('planned_steps', []):
                if planned.get('step_id') == step_id:
                    step_name = planned.get('step_name', step_id)
                    break
            
            if status == 'completed':
                data['completed_steps'].append({
                    'step_id': step_id,
                    'step_name': step_name,
                    'duration': duration,
                    'completed_at': datetime.now().isoformat()
                })
            elif status == 'failed':
                data['violations'].append({
                    'step_id': step_id,
                    'step_name': step_name,
                    'error': error,
                    'failed_at': datetime.now().isoformat()
                })
            elif status == 'skipped':
                data['skipped_steps'].append({
                    'step_id': step_id,
                    'step_name': step_name,
                    'skipped_at': datetime.now().isoformat()
                })
            
            # 更新整体状态
            completed_count = len(data['completed_steps'])
            if completed_count == data['total_steps']:
                data['status'] = 'completed'
            elif len(data.get('violations', [])) > 0:
                data['status'] = 'failed'
            else:
                data['status'] = 'executing'
            
            self._tracking_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            self.logger.info(f"    步骤状态更新: {step_name} -> {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"更新步骤状态失败: {e}")
            return False
    
    async def _execute_parallel_group(
        self,
        steps: List[Dict],
        workflow: Dict,
        max_concurrency: int
    ) -> List[Dict]:
        """并行执行步骤组"""
        start_time = time.time()
        
        try:
            # 分批执行
            results = []
            for i in range(0, len(steps), max_concurrency):
                batch = steps[i:i + max_concurrency]
                batch_results = await asyncio.gather(
                    *[self._execute_step(step, workflow) for step in batch]
                )
                results.extend(batch_results)
            
            return results
            
        except Exception as e:
            duration = round(time.time() - start_time)
            
            return [
                {
                    'id': s['id'],
                    'name': s['name'],
                    'success': False,
                    'error': str(e),
                    'duration': duration,
                }
                for s in steps
            ]
    
    def _build_task_description(self, step: Dict, workflow: Dict, context: Dict = None) -> str:
        """构建任务描述（包含完整工作流上下文）
        
        v6.1 重构：支持 context 参数替换占位符
        v6.0 重构：传递完整工作流上下文
        - 工作流目标
        - 输入定义
        - 输出定义
        - 执行步骤
        - 执行约束
        
        职责分离：
        - workflow-manager 负责传递完整的工作内容
        - agent-pool 负责能力推断和执行
        
        "职责分离"不等于"信息简陋"，完整的工作内容必须传递。
        """
        parts = []
        
        # 1. 确定 WORKFLOW.md 路径
        source_workflow = step.get('_source_workflow')
        if source_workflow:
            sub_workflow = loader.load(source_workflow)
            if sub_workflow:
                workflow_md_path = Path(sub_workflow['path']) / 'WORKFLOW.md'
                output_dir = Path(sub_workflow['path']) / 'outputs'
            else:
                workflow_md_path = Path(workflow['path']) / 'WORKFLOW.md'
                output_dir = Path(workflow['path']) / 'outputs'
        else:
            workflow_md_path = Path(workflow['path']) / 'WORKFLOW.md'
            output_dir = Path(workflow['path']) / 'outputs'
        
        # 2. 工作流目标（新增）
        if workflow_md_path.exists():
            workflow_goal = self._extract_section(workflow_md_path, '目标')
            if workflow_goal:
                parts.append("## 工作流目标\n" + workflow_goal)
        
        # 3. 输入定义（新增）
        if workflow_md_path.exists():
            input_def = self._extract_section(workflow_md_path, '输入')
            if input_def:
                parts.append("\n## 输入定义\n" + input_def)
        
        # 4. 输出定义（新增）
        if workflow_md_path.exists():
            output_def = self._extract_section(workflow_md_path, '输出')
            if output_def:
                parts.append("\n## 输出定义\n" + output_def)
        
        # 5. 当前步骤
        parts.append(f"\n## 当前步骤：{step.get('name', step.get('step_name', ''))}\n")
        if step.get('task'):
            parts.append(step['task'])
        
        # 6. 执行指令
        if workflow_md_path.exists():
            execution_instructions = self._extract_step_instructions(
                workflow_md_path, 
                step.get('step_name', step.get('name', ''))
            )
            if execution_instructions:
                parts.append("\n## 执行指令\n" + execution_instructions)
        
        # 7. 执行命令（如果有）
        if step.get('command'):
            parts.append(f"\n执行: {step['command']}")
        
        # 8. 工作流特定约束（新增）
        if workflow_md_path.exists():
            workflow_constraints = self._extract_section(workflow_md_path, '执行约束')
            if workflow_constraints:
                parts.append("\n## 执行约束\n" + workflow_constraints)
        
        # 9. 通用约束
        constraints = self._load_executor_constraints()
        if constraints:
            parts.append("\n---\n" + constraints)
        
        # 10. 替换占位符（v6.1 新增）
        task_description = '\n'.join(parts)
        if context:
            task_description = self._replace_placeholders(task_description, context)
        
        return task_description
    
    def _replace_placeholders(self, text: str, context: Dict) -> str:
        """替换占位符（v6.1 新增）
        
        支持的占位符格式：
        - {用户指定的日期} → date_start
        - {日期列表} → date_start date_end ...
        - {{date_start}} → date_start
        - {{date_end}} → date_end
        - {{date_list}} → date_start date_end ...
        - {{#if date_end}}...{{/if}} → 条件块（date_end 存在时显示）
        """
        # 生成日期列表
        date_list = self._generate_date_list(context)
        date_list_str = ' '.join(date_list) if date_list else ''
        
        # 中文占位符（兼容旧格式）
        text = text.replace('{用户指定的日期}', context.get('date_start', ''))
        text = text.replace('{日期列表}', date_list_str)
        
        # 标准占位符
        text = text.replace('{{date_start}}', context.get('date_start', ''))
        text = text.replace('{{date_end}}', context.get('date_end', ''))
        text = text.replace('{{date_list}}', date_list_str)
        
        # 条件块处理：{{#if date_end}}...{{/if}}
        import re
        if context.get('date_end') and context['date_end'] != context.get('date_start'):
            # date_end 存在且与 date_start 不同，保留条件块内容
            text = re.sub(r'\{\{#if date_end\}\}(.*?)\{\{/if\}\}', r'\1', text)
        else:
            # date_end 不存在或与 date_start 相同，移除条件块
            text = re.sub(r'\{\{#if date_end\}\}.*?\{\{/if\}\}', '', text)
        
        return text
    
    def _generate_date_list(self, context: Dict) -> List[str]:
        """生成日期列表（v6.1 新增）"""
        from datetime import datetime, timedelta
        
        date_start = context.get('date_start')
        date_end = context.get('date_end') or date_start
        
        if not date_start:
            return []
        
        try:
            start = datetime.strptime(date_start, '%Y%m%d')
            end = datetime.strptime(date_end, '%Y%m%d')
            
            dates = []
            current = start
            while current <= end:
                dates.append(current.strftime('%Y%m%d'))
                current += timedelta(days=1)
            return dates
        except ValueError:
            return [date_start] if date_start else []
    
    def _extract_section(self, workflow_md_path: Path, section_name: str) -> str:
        """从 WORKFLOW.md 提取指定章节内容
        
        Args:
            workflow_md_path: WORKFLOW.md 文件路径
            section_name: 章节名称（如 "目标"、"输入"、"输出"、"执行约束"）
        
        Returns:
            该章节的内容（markdown 格式）
        """
        import re
        
        try:
            content = workflow_md_path.read_text(encoding='utf-8')
            
            # 匹配 ## 章节名称，提取到下一个 ## 或 --- 或文件结束
            pattern = rf'##\s*{re.escape(section_name)}.*?\n(.*?)(?=##|\n---|\Z)'
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                return match.group(1).strip()
            return ""
            
        except Exception as e:
            self.logger.warning(f"无法提取章节 {section_name}: {e}")
            return ""
    
    def _extract_step_instructions(self, workflow_md_path: Path, step_name: str) -> str:
        """从 WORKFLOW.md 提取指定步骤的执行指令
        
        Args:
            workflow_md_path: WORKFLOW.md 文件路径
            step_name: 步骤名称（如 "准备阶段"、"分析处理"）
        
        Returns:
            该步骤的执行指令内容（markdown 格式）
        """
        import re
        
        try:
            content = workflow_md_path.read_text(encoding='utf-8')
            
            # 匹配步骤标题（支持多种格式）
            # 格式1: ### 步骤 1: 准备阶段
            # 格式2: ### 步骤1: 准备阶段
            # 格式3: ### 准备阶段
            
            # 尝试匹配包含步骤名称的章节
            pattern = rf'### 步骤\s*\d+[:：]\s*{re.escape(step_name)}.*?\n(.*?)(?=### 步骤|\n---|\Z)'
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            
            if match:
                return match.group(1).strip()
            
            # 尝试匹配只有步骤名称的章节
            pattern2 = rf'###\s*{re.escape(step_name)}.*?\n(.*?)(?=###|\n---|\Z)'
            match2 = re.search(pattern2, content, re.DOTALL)
            
            if match2:
                return match2.group(1).strip()
            
            return ""
            
        except Exception as e:
            self.logger.warning(f"无法读取 WORKFLOW.md: {e}")
            return ""
    
    def _load_executor_constraints(self) -> str:
        """读取执行约束文件"""
        try:
            skill_dir = Path(__file__).parent.parent.parent
            constraints_path = skill_dir / "references" / "executor-constraints.md"
            if constraints_path.exists():
                return constraints_path.read_text(encoding='utf-8')
        except Exception as e:
            self.logger.warning(f"无法读取约束文件: {e}")
        return ""
    
    # v5.2 legacy code removed 2026-04-20
    # 已废弃的 _execute_instruction 方法已删除
    # 执行逻辑移交给主 AI，通过返回 pending_instructions 实现
    
    async def _call_agent_pool(
        self,
        task_description: str,
        capabilities: List[str],  # 保留参数但不再传递
        context: Dict = None  # 新增：接收上下文参数
    ) -> Dict[str, Any]:
        """
        调用 agent-pool（全量模式），返回执行计划供主 AI 执行
        
        职责分离：工作流不干预Agent池的能力推断
        Agent池全权负责：能力推断、Agent匹配、复用优化
        
        Returns:
            Dict: 执行计划，包含 instructions 列表
        """
        try:
            # 调用 agent-pool（全量模式）
            # 不传递 capabilities，Agent池从任务描述推断
            plan = agent_pool_client.execute_full(
                task_description=task_description,
                # Agent池全权推断能力，工作流不干预
                timeout=300,
                max_iterations=50,
                source_workflow=self.current_workflow_name,
                context=context  # 新增：传递上下文参数
            )
            
            if not plan.get('success'):
                return {
                    'success': False,
                    'status': 'error',
                    'error': plan.get('error', 'Unknown error'),
                    'plan': plan
                }
            
            # 收集 instructions，不执行
            instructions = plan.get('pending_instructions', plan.get('instructions', []))
            
            if not instructions:
                # 无 instructions，返回基本信息
                return {
                    'success': True,
                    'status': 'plan_ready',
                    'agent_id': plan.get('agent_id'),
                    'strategy': plan.get('strategy'),
                    'instructions': [],
                    'message': '无需执行额外指令'
                }
            
            self.logger.info(f"    [Executor] 收集到 {len(instructions)} 条指令，返回执行计划")
            
            # 返回执行计划供主 AI 执行
            result = {
                'success': True,
                'status': 'execution_required',
                'agent_id': plan.get('agent_id'),
                'strategy': plan.get('strategy'),
                'task_id': plan.get('task_id'),
                'pending_instructions': instructions,
                'execution_status': 'awaiting_delegate_task',
                'message': '⚠️ 必须调用 delegate_task 执行以上指令'
            }
            
            # 传递字段补全信息（修复 2026-04-20）
            if plan.get('field_completion_needed'):
                result['field_completion_needed'] = True
                result['missing_fields'] = plan.get('missing_fields', [])
                result['field_prompts'] = plan.get('field_prompts', {})
                result['field_completion_instruction'] = plan.get('field_completion_instruction', '')
            
            return result
            
        except Exception as e:
            self.logger.error(f": {e}")
            return {
                'success': False,
                'status': 'error',
                'error': str(e)
            }
    
    async def _start_heartbeat(self, interval: int = 300):
        """启动心跳（使用统一心跳管理器）"""
        await self._heartbeat.start(
            workflow_path=self.current_workflow_path,
            current_step=self.current_step.get('name') if self.current_step else None,
            step_progress=f"{self.completed_steps}/{self.total_steps}",
        )

    async def _stop_heartbeat(self):
        """停止心跳"""
        await self._heartbeat.stop()

    async def _finalize_workflow(self):
        """工作流完成时调用，停止心跳和守护监控（Phase 2 新增）
        
        主 AI 在工作流完成后应调用此方法，确保：
        1. 停止心跳监控
        2. 停止守护监控
        3. 清理资源
        
        使用示例：
            executor = WorkflowExecutor()
            result = await executor.execute('workflow-name')
            # ... 执行 delegate_task ...
            await executor._finalize_workflow()
        """
        self.logger.info("[Executor] 工作流完成，清理资源...")
        
        # 停止心跳
        await self._stop_heartbeat()
        self.logger.info("[Executor] 心跳已停止")
        
        # 生成汇总报告
        try:
            if hasattr(self, 'step_results') and self.step_results:
                consolidated = self.consolidator.consolidate(self.step_results)
                report = self.consolidator.generate_markdown_report(consolidated)
                
                # 保存报告
                if hasattr(self, 'current_workflow_path') and self.current_workflow_path:
                    report_path = self.current_workflow_path / 'execution_report.md'
                    report_path.write_text(report, encoding='utf-8')
                    self.logger.info(f"[Executor] 汇总报告已生成: {report_path}")
        except Exception as e:
            self.logger.error(f"[Executor] 生成汇总报告失败: {e}")
        
        self.logger.info("[Executor] 工作流资源清理完成")

    def _on_heartbeat_failed(self, error: str):
        """心跳失败回调"""
        self.logger.error(f"[Executor] 心跳失败: {error}")
        # 可以在这里添加恢复逻辑


# 单例实例
workflow_executor = WorkflowExecutor()
