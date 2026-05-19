#!/usr/bin/env python3
"""
WorkflowAgentPoolAdapter 测试文件

测试用例矩阵：
1. plan模式成功场景
2. execute模式无delegate_task注入（降级）
3. 必填参数缺失
4. 无效能力值
5. 超时场景
6. 废弃参数使用（DeprecationWarning）
7. 能力推断（多个场景）
8. 批量执行
9. 异常处理
10. 返回格式验证

创建时间: 2026-05-14
"""

import pytest
import warnings
import sys
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Any, Optional

# 添加路径
sys.path.insert(0, '/home/kali/.hermes/skills/openclaw-imports/workflow-manager/src/core')


class TestWorkflowAgentPoolAdapterBasic:
    """基础功能测试"""
    
    @pytest.fixture
    def mock_orchestrator(self):
        """创建模拟的 Orchestrator"""
        mock = MagicMock()
        mock.execute.return_value = {
            "success": True,
            "type": "execution_plan",
            "task_id": "task-123",
            "agent_id": "agent-456",
            "strategy": "reuse_specialist",
            "execution": {
                "type": "tool_call_request",
                "tool": "delegate_task",
                "params": {
                    "goal": "验证输入文件",
                    "context": {},
                    "toolsets": ["terminal", "file"],
                    "max_iterations": 50
                }
            },
            "agent_info": {
                "id": "agent-456",
                "name": "Specialist: cli_execution",
                "role": "worker",
                "capabilities": ["cli_execution"]
            }
        }
        mock.get_status.return_value = {
            "mode": "plan",
            "active_agents": 5
        }
        return mock
    
    @pytest.fixture
    def adapter(self, mock_orchestrator):
        """创建适配器实例（带模拟 orchestrator）"""
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import WorkflowAgentPoolAdapter
            adapter = WorkflowAgentPoolAdapter(mode="plan")
            adapter.orchestrator = mock_orchestrator
            return adapter
    
    def test_plan_mode_success(self, adapter, mock_orchestrator):
        """测试1: plan模式成功场景"""
        result = adapter.execute(
            workflow_name='凭证检测',
            node_id=1,
            node_name='环境准备',
            task_description='验证输入文件、检查工作目录',
            context={'work_dir': '/tmp/test'}
        )
        
        # 验证调用
        mock_orchestrator.execute.assert_called_once()
        call_args = mock_orchestrator.execute.call_args
        
        assert call_args.kwargs['task_description'] == '验证输入文件、检查工作目录'
        assert 'required_capabilities' in call_args.kwargs
        assert call_args.kwargs['timeout'] == 300
        
        # 验证返回格式
        assert result['success'] == True
        assert result['type'] == 'execution_plan'
        assert result['workflow_name'] == '凭证检测'
        assert result['node_id'] == 1
        assert 'execution' in result
    
    def test_execute_mode_without_delegate_fn(self, mock_orchestrator):
        """测试2: execute模式无delegate_task注入（降级）"""
        # 设置降级响应
        mock_orchestrator.execute.return_value = {
            "success": True,
            "type": "execution_plan",
            "mode_degraded": True,
            "warning": "execute模式需要delegate_task函数，已降级为plan模式"
        }
        
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import WorkflowAgentPoolAdapter
            adapter = WorkflowAgentPoolAdapter(mode="execute")
            adapter.orchestrator = mock_orchestrator
            
            result = adapter.execute(
                workflow_name='凭证检测',
                node_id=2,
                node_name='执行检测',
                task_description='运行安全扫描',
                context={}
            )
        
        assert result['mode_degraded'] == True
        assert result['type'] == 'execution_plan'
        assert 'warning' in result
    
    def test_missing_required_parameter(self, adapter):
        """测试3: 缺少必填参数（task_description为空字符串）"""
        # 空字符串应该被接受，但可能导致下游错误
        result = adapter.execute(
            workflow_name='凭证检测',
            node_id=1,
            node_name='环境准备',
            task_description='',  # 空字符串
            context=None
        )
        
        # 适配器应该正常返回，但下游可能返回错误
        assert 'success' in result
        assert 'workflow_name' in result
    
    def test_invalid_capabilities(self, mock_orchestrator):
        """测试4: 无效能力值"""
        # 设置能力不可用的响应
        mock_orchestrator.execute.return_value = {
            "success": False,
            "type": "error",
            "error": "required_capabilities_unavailable",
            "error_message": "所需能力 [invalid_capability] 在现有Agent池中不可用",
            "suggestion": "请使用 --generate 参数生成新Agent",
            "available_capabilities": ["cli_execution", "data_analysis", "security"]
        }
        
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import WorkflowAgentPoolAdapter
            adapter = WorkflowAgentPoolAdapter()
            adapter.orchestrator = mock_orchestrator
            
            # 通过上下文传递无效能力
            result = adapter.execute(
                workflow_name='测试工作流',
                node_id=1,
                node_name='测试节点',
                task_description='测试任务',
                context={'required_capabilities': ['invalid_capability']}
            )
        
        assert result['success'] == False
        assert result['type'] == 'error'
        assert result['error'] == 'required_capabilities_unavailable'
        assert 'available_capabilities' in result
    
    def test_timeout_scenario(self, mock_orchestrator):
        """测试5: 超时场景"""
        mock_orchestrator.execute.return_value = {
            "success": False,
            "type": "error",
            "error": "timeout_exceeded",
            "error_message": "任务执行超过最大超时时间（1秒）",
            "suggestion": "增加timeout参数",
            "elapsed_time": 1
        }
        
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import WorkflowAgentPoolAdapter
            adapter = WorkflowAgentPoolAdapter()
            adapter.orchestrator = mock_orchestrator
            
            result = adapter.execute(
                workflow_name='长时间工作流',
                node_id=1,
                node_name='长时间任务',
                task_description='执行大量计算',
                context={}
            )
        
        assert result['success'] == False
        assert result['error'] == 'timeout_exceeded'


class TestCapabilityInference:
    """能力推断逻辑测试"""
    
    @pytest.fixture
    def adapter(self):
        """创建适配器实例"""
        mock_orchestrator = MagicMock()
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import WorkflowAgentPoolAdapter
            adapter = WorkflowAgentPoolAdapter()
            adapter.orchestrator = mock_orchestrator
            return adapter
    
    def test_infer_capabilities_environment_keyword(self, adapter):
        """测试6.1: 能力推断 - 环境关键词"""
        caps = adapter._infer_capabilities('环境准备', {})
        assert 'cli_execution' in caps
    
    def test_infer_capabilities_detection_keyword(self, adapter):
        """测试6.2: 能力推断 - 检测关键词"""
        caps = adapter._infer_capabilities('执行检测', {})
        assert 'cli_execution' in caps
        assert 'security' in caps
    
    def test_infer_capabilities_analysis_keyword(self, adapter):
        """测试6.3: 能力推断 - 分析关键词"""
        caps = adapter._infer_capabilities('数据分析', {})
        assert 'data_analysis' in caps
    
    def test_infer_capabilities_unknown_keyword(self, adapter):
        """测试6.4: 能力推断 - 未知关键词（使用默认值）"""
        caps = adapter._infer_capabilities('未知节点', {})
        assert caps == ['cli_execution']  # 默认能力
    
    def test_infer_capabilities_context_override(self, adapter):
        """测试6.5: 能力推断 - 上下文显式指定（最高优先级）"""
        explicit_caps = ['web_research', 'browser_automation']
        caps = adapter._infer_capabilities('任意节点', {'required_capabilities': explicit_caps})
        assert caps == explicit_caps
    
    def test_infer_capabilities_browser_flag(self, adapter):
        """测试6.6: 能力推断 - needs_browser 标志"""
        caps = adapter._infer_capabilities('网络请求', {'needs_browser': True})
        assert 'web_research' in caps
    
    def test_infer_capabilities_security_flag(self, adapter):
        """测试6.7: 能力推断 - needs_security_tools 标志"""
        caps = adapter._infer_capabilities('环境准备', {'needs_security_tools': True})
        # 环境准备匹配 'cli_execution'，加上安全标志应添加 'security'
        assert 'cli_execution' in caps
        assert 'security' in caps


class TestResultAdaptation:
    """返回格式转换测试"""
    
    @pytest.fixture
    def adapter(self):
        """创建适配器实例"""
        mock_orchestrator = MagicMock()
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import WorkflowAgentPoolAdapter
            adapter = WorkflowAgentPoolAdapter()
            adapter.orchestrator = mock_orchestrator
            return adapter
    
    def test_adapt_result_execution_plan(self, adapter):
        """测试7.1: 返回格式验证 - execution_plan 类型"""
        original = {
            "success": True,
            "type": "execution_plan",
            "task_id": "task-123",
            "execution": {"tool": "delegate_task"}
        }
        
        result = adapter._adapt_result(original, '测试工作流', 1, '测试节点')
        
        assert result['workflow_name'] == '测试工作流'
        assert result['node_id'] == 1
        assert result['node_name'] == '测试节点'
        assert result['type'] == 'execution_plan'
        assert result['success'] == True
    
    def test_adapt_result_direct_result(self, adapter):
        """测试7.2: 返回格式验证 - direct_result 类型"""
        original = {
            "success": True,
            "result": {"output": "执行完成"}
        }
        
        result = adapter._adapt_result(original, '测试工作流', 2, '执行节点')
        
        assert result['type'] == 'direct_result'
        assert result['workflow_name'] == '测试工作流'
    
    def test_adapt_result_error(self, adapter):
        """测试7.3: 返回格式验证 - error 类型"""
        original = {
            "success": False,
            "error": "test_error",
            "error_message": "测试错误信息"
        }
        
        result = adapter._adapt_result(original, '测试工作流', 3, '错误节点')
        
        assert result['type'] == 'error'
        assert result['success'] == False
    
    def test_adapt_result_missing_fields(self, adapter):
        """测试7.4: 返回格式验证 - 缺失字段自动补充"""
        original = {
            "execution": {"tool": "delegate_task"}
        }
        
        result = adapter._adapt_result(original, '测试工作流', 4, '缺失字段节点')
        
        # 应该自动补充 success 和 type
        assert 'success' in result
        assert result['type'] == 'execution_plan'


class TestBatchExecution:
    """批量执行测试"""
    
    def test_batch_execute_success(self):
        """测试8: 批量执行成功场景"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.batch_execute.return_value = {
            "success": True,
            "type": "batch_result",
            "total": 3,
            "completed": 3,
            "results": []
        }
        
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import WorkflowAgentPoolAdapter
            adapter = WorkflowAgentPoolAdapter()
            adapter.orchestrator = mock_orchestrator
            
            tasks = [
                {'workflow_name': 'W1', 'node_id': 1, 'node_name': '环境准备', 'task_description': 'T1'},
                {'workflow_name': 'W1', 'node_id': 2, 'node_name': '执行检测', 'task_description': 'T2'},
                {'workflow_name': 'W1', 'node_id': 3, 'node_name': '结果汇总', 'task_description': 'T3'},
            ]
            
            result = adapter.batch_execute(tasks, parallel=True)
            
            assert result['success'] == True
            assert 'workflow_tasks' in result
            mock_orchestrator.batch_execute.assert_called_once()


class TestExceptionHandling:
    """异常处理测试"""
    
    def test_exception_in_orchestrator(self):
        """测试9: Orchestrator 抛出异常时的处理"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.execute.side_effect = RuntimeError("模拟的错误")
        
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import WorkflowAgentPoolAdapter
            adapter = WorkflowAgentPoolAdapter()
            adapter.orchestrator = mock_orchestrator
            
            result = adapter.execute(
                workflow_name='异常工作流',
                node_id=1,
                node_name='异常节点',
                task_description='触发异常',
                context={}
            )
        
        # 异常应该被捕获，返回错误结果
        assert result['success'] == False
        assert result['type'] == 'error'
        assert 'error' in result
        assert result['error'] == 'RuntimeError'
        assert 'error_message' in result
    
    def test_batch_execute_exception(self):
        """测试9.2: 批量执行异常处理"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.batch_execute.side_effect = Exception("批量执行失败")
        
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import WorkflowAgentPoolAdapter
            adapter = WorkflowAgentPoolAdapter()
            adapter.orchestrator = mock_orchestrator
            
            result = adapter.batch_execute([
                {'workflow_name': 'W', 'node_id': 1, 'node_name': 'N', 'task_description': 'T'}
            ])
        
        assert result['success'] == False
        assert result['type'] == 'error'


class TestStatusAndConfiguration:
    """状态查询和配置测试"""
    
    def test_get_status(self):
        """测试10: 状态查询"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_status.return_value = {
            "mode": "plan",
            "active_agents": 5,
            "version": "2.0"
        }
        
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import WorkflowAgentPoolAdapter
            adapter = WorkflowAgentPoolAdapter()
            adapter.orchestrator = mock_orchestrator
            
            status = adapter.get_status()
            
            assert 'adapter' in status
            assert status['adapter'] == 'WorkflowAgentPoolAdapter'
            assert 'default_timeout' in status
            assert 'default_max_iterations' in status
            assert 'default_capabilities' in status
    
    def test_set_delegate_task_fn(self):
        """测试10.2: 设置 delegate_task 函数"""
        mock_orchestrator = MagicMock()
        
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import WorkflowAgentPoolAdapter
            adapter = WorkflowAgentPoolAdapter(mode="execute")
            adapter.orchestrator = mock_orchestrator
            
            # 设置 delegate_task 函数
            def mock_delegate_task(goal, context, toolsets, max_iterations):
                return {"success": True}
            
            adapter.set_delegate_task_fn(mock_delegate_task)
            
            mock_orchestrator.set_delegate_task_fn.assert_called_once()


class TestConvenienceFunction:
    """便捷函数测试"""
    
    def test_execute_workflow_node_function(self):
        """测试11: 便捷函数 execute_workflow_node"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.execute.return_value = {
            "success": True,
            "type": "execution_plan",
            "execution": {"tool": "delegate_task"}
        }
        
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import execute_workflow_node
            
            result = execute_workflow_node(
                workflow_name='便捷测试',
                node_id=1,
                node_name='测试节点',
                task_description='便捷函数测试',
                context={}
            )
            
            assert result['success'] == True


class TestCapabilityKeywordsMap:
    """能力关键词映射测试"""
    
    def test_capability_keywords_coverage(self):
        """测试12: 验证所有关键词映射存在"""
        mock_orchestrator = MagicMock()
        
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import WorkflowAgentPoolAdapter
            adapter = WorkflowAgentPoolAdapter()
            adapter.orchestrator = mock_orchestrator
            
            # 验证关键映射存在
            assert hasattr(adapter, 'CAPABILITY_KEYWORDS_MAP')
            assert '环境' in adapter.CAPABILITY_KEYWORDS_MAP
            assert '检测' in adapter.CAPABILITY_KEYWORDS_MAP
            assert '分析' in adapter.CAPABILITY_KEYWORDS_MAP
            assert '网络' in adapter.CAPABILITY_KEYWORDS_MAP
            assert '代码' in adapter.CAPABILITY_KEYWORDS_MAP
            
            # 验证默认值
            assert adapter.DEFAULT_CAPABILITIES == ['cli_execution']
            assert adapter.DEFAULT_TIMEOUT == 300
            assert adapter.DEFAULT_MAX_ITERATIONS == 50


class TestEdgeCases:
    """边界情况测试"""
    
    @pytest.fixture
    def mock_orchestrator(self):
        """创建模拟的 Orchestrator"""
        mock = MagicMock()
        mock.execute.return_value = {
            "success": True,
            "type": "execution_plan"
        }
        mock.get_status.return_value = {"mode": "plan"}
        return mock
    
    @pytest.fixture
    def adapter(self, mock_orchestrator):
        """创建适配器实例"""
        with patch('workflow_agent_pool_adapter.Orchestrator', return_value=mock_orchestrator):
            from workflow_agent_pool_adapter import WorkflowAgentPoolAdapter
            adapter = WorkflowAgentPoolAdapter()
            adapter.orchestrator = mock_orchestrator
            return adapter
    
    def test_context_none(self, adapter, mock_orchestrator):
        """测试13: context 为 None"""
        mock_orchestrator.execute.return_value = {"success": True, "type": "execution_plan"}
        
        result = adapter.execute(
            workflow_name='测试',
            node_id=1,
            node_name='环境准备',
            task_description='测试任务',
            context=None
        )
        
        assert result['success'] == True
    
    def test_empty_context(self, adapter, mock_orchestrator):
        """测试14: 空上下文"""
        mock_orchestrator.execute.return_value = {"success": True, "type": "execution_plan"}
        
        result = adapter.execute(
            workflow_name='测试',
            node_id=1,
            node_name='环境准备',
            task_description='测试任务',
            context={}
        )
        
        assert result['success'] == True
    
    def test_chinese_characters_in_parameters(self, adapter, mock_orchestrator):
        """测试15: 中文字符参数"""
        mock_orchestrator.execute.return_value = {"success": True, "type": "execution_plan"}
        
        result = adapter.execute(
            workflow_name='凭证检测工作流',
            node_id=999,
            node_name='环境准备与初始化',
            task_description='验证输入文件完整性、检查工作目录权限',
            context={'工作目录': '/tmp/测试'}
        )
        
        assert result['workflow_name'] == '凭证检测工作流'
        assert result['node_name'] == '环境准备与初始化'


# ============================================================
# 测试运行入口
# ============================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
