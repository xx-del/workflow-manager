#!/usr/bin/env python3
"""
AI 增强器 - 使用 AI 进行语义理解和抽象

职责：
1. 步骤语义化命名
2. 参数语义化命名
3. 纠错深化分析
4. 工作流描述生成

设计原则：
- 规则为主，AI 辅助
- 失败降级到规则输出
- 智能跳过简单场景
"""

from utils.logger import get_logger
import json
import re
from typing import Any, Optional
from pathlib import Path


# ==================== Prompt 模板 ====================

STEP_ENHANCEMENT_PROMPT = """# 任务：语义化步骤名称和描述

## 输入步骤列表

{steps_json}

## 分析要求

### 1. 命名规则
- 使用 2-4 个中文字
- 表达核心操作意图（如：采集数据、解析日志、生成报告）
- 避免 "执行"、"处理"、"操作" 等泛词
- 优先使用业务术语

### 2. 描述规则
- 一句话说明步骤目的（10-20字）
- 包含关键输入或输出
- 说明与其他步骤的关系（如有）

### 3. 意图分类
可选值：数据采集、数据转换、数据分析、数据存储、系统操作、网络请求、文件操作

## 输出格式（仅输出 JSON）

```json
{{
  "steps": [
    {{
      "id": "原步骤ID",
      "name": "语义化名称",
      "description": "步骤描述",
      "intent": "意图分类"
    }}
  ]
}}
```

请分析并输出 JSON："""

PARAM_ENHANCEMENT_PROMPT = """# 任务：参数语义化

## 原始参数列表

{params_json}

## 命名建议

| 参数类型 | 建议名称 | 示例 |
|----------|----------|------|
| 日期范围 | date_range, data_period | 20260401-20260410 |
| 输出路径 | output_dir, result_path | /x/data/ |
| API 端点 | api_url, endpoint | http://api/data |
| 数量限制 | max_count, limit | 100 |
| 输入文件 | input_file, source_file | result.json |

## 分析要求

### 1. 命名规则
- 使用英文下划线命名法
- 表达参数用途
- 简洁明了

### 2. 描述规则
- 说明参数用途
- 提供示例值
- 说明格式要求

### 3. 默认值建议
- 日期类：{{yesterday}}, {{last_7_days}}
- 路径类：合理默认路径
- 数量类：合理安全值

## 输出格式（仅输出 JSON）

```json
{{
  "parameters": [
    {{
      "original_name": "原始名称",
      "name": "语义化名称",
      "description": "参数描述",
      "example": "示例值",
      "default_suggestion": "建议默认值"
    }}
  ]
}}
```

请分析并输出 JSON："""

CORRECTION_ENHANCEMENT_PROMPT = """# 任务：深化偏差纠正分析

## 原始纠正信息

{corrections_json}

## 分析要求

### 1. 错误根因分析
- 分析为什么会发生这个错误
- 识别潜在的环境因素
- 发现可能的依赖问题

### 2. 纠正措施详解
- 具体操作步骤
- 参数调整建议
- 配置修改说明

### 3. 预防措施
- 如何避免类似错误
- 前置检查项
- 环境准备建议

### 4. 诊断命令
- 提供诊断问题的具体命令
- 常用排查方法

## 输出格式（仅输出 JSON）

```json
{{
  "corrections": [
    {{
      "step_id": "步骤ID",
      "error_type": "错误类型",
      "root_cause": "根因分析",
      "detailed_solution": "详细解决方案",
      "prevention": "预防措施",
      "diagnostic_commands": ["诊断命令1", "诊断命令2"]
    }}
  ]
}}
```

请分析并输出 JSON："""

DESCRIPTION_GENERATION_PROMPT = """# 任务：生成工作流描述

## 步骤信息

{steps_summary}

## 纠正信息

{corrections_summary}

## 要求

### 1. 描述格式
- 一句话概述工作流目的（15-30字）
- 列出主要功能点
- 说明适用场景

### 2. 风格
- 专业简洁
- 使用业务术语
- 突出核心价值

## 输出格式（仅输出 JSON）

```json
{{
  "title": "工作流标题",
  "description": "一句话描述",
  "features": ["功能1", "功能2"],
  "use_cases": ["场景1", "场景2"]
}}
```

请分析并输出 JSON："""


class AIEnhancer:
    """AI 增强器"""

    def __init__(self, enable_ai: bool = True):
        """
        初始化

        Args:
            enable_ai: 是否启用 AI 增强（默认启用）
        """

        self.logger = get_logger(__name__)
        self.enable_ai = enable_ai
        self._ai_available = None

    def _check_ai_available(self) -> bool:
        """检查 AI 是否可用"""
        if self._ai_available is not None:
            return self._ai_available

        # 检查是否有可用的 AI 接口
        # 这里可以根据实际环境配置
        # 暂时返回 True，实际使用时会通过 delegate_task 调用
        self._ai_available = True
        return self._ai_available

    def _should_use_ai(self, complexity_score: int = 0) -> bool:
        """
        判断是否应该使用 AI

        Args:
            complexity_score: 复杂度评分（0-10）

        Returns:
            是否使用 AI
        """
        if not self.enable_ai:
            return False

        if not self._check_ai_available():
            return False

        # 简单场景跳过 AI
        if complexity_score < 3:
            return False

        return True

    def enhance_steps(self, core_steps: list[dict]) -> list[dict]:
        """
        增强步骤：语义化命名和描述

        Args:
            core_steps: 核心步骤列表

        Returns:
            增强后的步骤列表
        """
        if not core_steps:
            return core_steps

        # 计算复杂度
        complexity = self._calculate_step_complexity(core_steps)

        # 判断是否需要 AI 增强
        if not self._should_use_ai(complexity):
            # 使用本地规则增强
            return self._enhance_steps_locally(core_steps)

        # 准备 AI 分析
        steps_for_ai = []
        for step in core_steps:
            steps_for_ai.append({
                'id': step.get('id'),
                'tool': step.get('name'),
                'action': step.get('action', '')[:200],  # 截断
                'arguments': step.get('arguments', {})
            })

        prompt = STEP_ENHANCEMENT_PROMPT.format(
            steps_json=json.dumps(steps_for_ai, indent=2, ensure_ascii=False)
        )

        # 返回 Prompt 供外部 AI 调用
        # 实际使用时，这里会通过 delegate_task 调用 AI
        # 这里先返回本地增强结果 + prompt
        enhanced = self._enhance_steps_locally(core_steps)
        for step in enhanced:
            step['_ai_prompt'] = prompt

        return enhanced

    def enhance_parameters(self, parameters: list[dict]) -> list[dict]:
        """
        增强参数：语义化命名和描述

        Args:
            parameters: 参数列表

        Returns:
            增强后的参数列表
        """
        if not parameters:
            return parameters

        # 计算复杂度
        complexity = len(parameters)  # 参数越多越复杂

        # 判断是否需要 AI 增强
        if not self._should_use_ai(complexity):
            return self._enhance_params_locally(parameters)

        # 准备 AI 分析
        params_for_ai = []
        for param in parameters:
            params_for_ai.append({
                'original_name': param.get('name'),
                'value': param.get('value'),
                'param_type': param.get('param_type'),
                'full_value': param.get('full_value', '')[:100]
            })

        prompt = PARAM_ENHANCEMENT_PROMPT.format(
            params_json=json.dumps(params_for_ai, indent=2, ensure_ascii=False)
        )

        # 返回本地增强 + prompt
        enhanced = self._enhance_params_locally(parameters)
        for param in enhanced:
            param['_ai_prompt'] = prompt

        return enhanced

    def enhance_corrections(self, corrections: list[dict]) -> list[dict]:
        """
        增强纠错：深入分析

        Args:
            corrections: 纠正列表

        Returns:
            增强后的纠正列表
        """
        if not corrections:
            return corrections

        # 有纠错就必须 AI 增强
        if not self._should_use_ai(5):
            return self._enhance_corrections_locally(corrections)

        # 准备 AI 分析
        corrections_for_ai = []
        for c in corrections:
            corrections_for_ai.append({
                'step_id': c.get('step_id'),
                'error_type': c.get('error_type'),
                'wrong_approach': c.get('wrong_approach'),
                'correct_approach': c.get('correct_approach'),
                'condition': c.get('condition')
            })

        prompt = CORRECTION_ENHANCEMENT_PROMPT.format(
            corrections_json=json.dumps(corrections_for_ai, indent=2, ensure_ascii=False)
        )

        enhanced = self._enhance_corrections_locally(corrections)
        for c in enhanced:
            c['_ai_prompt'] = prompt

        return enhanced

    def generate_description(
        self,
        core_steps: list[dict],
        corrections: list[dict] = None
    ) -> dict:
        """
        生成工作流描述

        Args:
            core_steps: 核心步骤
            corrections: 纠正列表

        Returns:
            描述信息
        """
        steps_summary = "\n".join([
            f"- {s.get('name', '未命名')}: {s.get('action', '')[:50]}"
            for s in core_steps
        ])

        corrections_summary = ""
        if corrections:
            corrections_summary = "\n".join([
                f"- {c.get('error_type')}: {c.get('correct_approach', '')[:50]}"
                for c in corrections
            ])
        else:
            corrections_summary = "无"

        prompt = DESCRIPTION_GENERATION_PROMPT.format(
            steps_summary=steps_summary,
            corrections_summary=corrections_summary
        )

        # 本地生成基础描述
        description = self._generate_description_locally(core_steps, corrections)
        description['_ai_prompt'] = prompt

        return description

    # ==================== 本地增强方法（降级方案）====================

    def _enhance_steps_locally(self, core_steps: list[dict]) -> list[dict]:
        """本地规则增强步骤"""
        enhanced = []

        # 操作类型关键词映射
        action_keywords = {
            'curl': {'name': '获取数据', 'intent': '数据采集'},
            'wget': {'name': '下载数据', 'intent': '数据采集'},
            'python': {'name': '执行脚本', 'intent': '数据处理'},
            'ssh': {'name': '远程执行', 'intent': '系统操作'},
            'git': {'name': '版本操作', 'intent': '系统操作'},
            'cat': {'name': '读取文件', 'intent': '文件操作'},
            'grep': {'name': '搜索过滤', 'intent': '数据分析'},
            'awk': {'name': '数据处理', 'intent': '数据转换'},
            'sed': {'name': '文本处理', 'intent': '数据转换'},
            'jq': {'name': 'JSON处理', 'intent': '数据转换'},
            'rsync': {'name': '同步数据', 'intent': '数据存储'},
            'scp': {'name': '传输文件', 'intent': '数据存储'},
        }

        for step in core_steps:
            enhanced_step = step.copy()
            action = step.get('action', '').lower()

            # 根据关键词确定名称和意图
            found = False
            for keyword, mapping in action_keywords.items():
                if keyword in action:
                    enhanced_step['name'] = mapping['name']
                    enhanced_step['intent'] = mapping['intent']
                    found = True
                    break

            if not found:
                # 保持原名称或使用工具名
                enhanced_step['name'] = step.get('name', '执行操作')
                enhanced_step['intent'] = '系统操作'

            # 生成描述
            enhanced_step['description'] = self._generate_step_description(step)

            enhanced.append(enhanced_step)

        return enhanced

    def _enhance_params_locally(self, parameters: list[dict]) -> list[dict]:
        """本地规则增强参数"""
        enhanced = []

        # 参数类型到名称的映射
        type_name_map = {
            'date_range': 'date_range',
            'output_path': 'output_path',
            'api_url': 'api_url',
            'number': 'limit'
        }

        # 参数类型到描述的映射
        type_desc_map = {
            'date_range': '数据采集日期范围',
            'output_path': '输出文件保存路径',
            'api_url': 'API 请求端点',
            'number': '处理数量上限'
        }

        used_names = set()

        for param in parameters:
            enhanced_param = param.copy()

            # 根据类型确定名称
            param_type = param.get('param_type', '')
            base_name = type_name_map.get(param_type, 'param')

            # 确保名称唯一
            if base_name not in used_names:
                enhanced_param['name'] = base_name
                used_names.add(base_name)
            else:
                # 添加序号
                counter = 2
                while f"{base_name}_{counter}" in used_names:
                    counter += 1
                enhanced_param['name'] = f"{base_name}_{counter}"
                used_names.add(enhanced_param['name'])

            # 设置描述
            enhanced_param['description'] = type_desc_map.get(
                param_type,
                param.get('description', '参数')
            )

            enhanced.append(enhanced_param)

        return enhanced

    def _enhance_corrections_locally(self, corrections: list[dict]) -> list[dict]:
        """本地规则增强纠错"""
        enhanced = []

        # 错误类型到解决方案的映射
        error_solutions = {
            'network_error': {
                'root_cause': '网络连接问题，可能是代理配置、防火墙或目标服务器问题',
                'detailed_solution': '1. 检查网络连接状态\n2. 验证代理配置\n3. 尝试备用端点',
                'prevention': '执行前检查网络连通性，配置备用端点',
                'diagnostic_commands': ['ping target_host', 'curl -v url', 'netstat -an | grep port']
            },
            'permission_error': {
                'root_cause': '权限不足，可能是用户权限或文件权限问题',
                'detailed_solution': '1. 检查当前用户权限\n2. 使用 sudo 或切换用户\n3. 修改文件权限',
                'prevention': '执行前检查权限，准备 sudo 或 root 账户',
                'diagnostic_commands': ['whoami', 'ls -la target_file', 'id']
            },
            'api_error': {
                'root_cause': 'API 调用问题，可能是认证、配额或参数错误',
                'detailed_solution': '1. 验证 API Key\n2. 检查配额\n3. 确认参数格式',
                'prevention': '准备多个 API Key，添加请求间隔',
                'diagnostic_commands': ['curl -H "Authorization: Bearer $KEY" url']
            },
            'parameter_error': {
                'root_cause': '参数错误，可能是格式、缺失或值范围问题',
                'detailed_solution': '1. 检查参数格式\n2. 确认必需参数\n3. 验证值范围',
                'prevention': '执行前验证所有参数',
                'diagnostic_commands': ['echo $PARAM']
            }
        }

        for c in corrections:
            enhanced_c = c.copy()
            error_type = c.get('error_type', 'unknown')

            # 获取预设解决方案
            solution = error_solutions.get(error_type, {
                'root_cause': '未知错误',
                'detailed_solution': c.get('correct_approach', ''),
                'prevention': '执行前检查相关配置',
                'diagnostic_commands': []
            })

            enhanced_c['root_cause'] = solution['root_cause']
            enhanced_c['detailed_solution'] = solution['detailed_solution']
            enhanced_c['prevention'] = solution['prevention']
            enhanced_c['diagnostic_commands'] = solution['diagnostic_commands']

            enhanced.append(enhanced_c)

        return enhanced

    def _generate_description_locally(
        self,
        core_steps: list[dict],
        corrections: list[dict] = None
    ) -> dict:
        """本地生成描述"""
        step_names = [s.get('name', '') for s in core_steps]

        # 生成标题
        if len(step_names) == 1:
            title = f"{step_names[0]}工作流"
        elif len(step_names) == 2:
            title = f"{step_names[0]}与{step_names[1]}工作流"
        else:
            title = f"{step_names[0]}等{len(step_names)}步工作流"

        # 生成描述
        description = f"自动执行 {' → '.join(step_names[:3])}"
        if len(step_names) > 3:
            description += f" 等 {len(step_names)} 个步骤"

        # 提取功能点
        features = list(set(s.get('intent', '') for s in core_steps if s.get('intent')))
        features = [f for f in features if f][:3]

        # 使用场景
        use_cases = []
        if '数据采集' in features:
            use_cases.append('定时采集数据')
        if '数据处理' in features:
            use_cases.append('批量处理文件')
        if '数据分析' in features:
            use_cases.append('生成分析报告')

        return {
            'title': title,
            'description': description,
            'features': features,
            'use_cases': use_cases
        }

    def _calculate_step_complexity(self, core_steps: list[dict]) -> int:
        """计算步骤复杂度"""
        score = 0

        # 步骤数量
        score += min(len(core_steps), 5)

        # 步骤类型多样性
        intents = set(s.get('intent', '') for s in core_steps)
        score += min(len(intents), 3)

        # 是否有复杂命令（管道、重定向等）
        for step in core_steps:
            action = step.get('action', '')
            if '|' in action or '>' in action or '<' in action:
                score += 1

        return min(score, 10)

    def _generate_step_description(self, step: dict) -> str:
        """生成步骤描述"""
        action = step.get('action', '')
        tool = step.get('name', '')

        # 简化命令描述
        if len(action) > 50:
            # 提取关键部分
            if 'curl' in action:
                match = re.search(r'curl\s+([^\s>]+)', action)
                if match:
                    return f"从 {match.group(1)[:30]} 获取数据"
            elif 'python' in action:
                match = re.search(r'python\s+(\S+)', action)
                if match:
                    return f"执行脚本 {match.group(1)}"
            return f"使用 {tool} 执行操作"
        else:
            return action[:50] if action else f"使用 {tool} 执行操作"


def main():
    """测试函数"""
    enhancer = AIEnhancer(enable_ai=True)

    # 测试步骤增强
    test_steps = [
        {
            'id': '1',
            'name': 'terminal',
            'action': 'curl http://api.example.com/data?date=20260401-20260410 > /x/data/result.json',
            'arguments': {'command': 'curl http://api.example.com/data'}
        },
        {
            'id': '2',
            'name': 'terminal',
            'action': 'python process.py --input result.json --output output.txt --limit 100',
            'arguments': {'command': 'python process.py'}
        }
    ]

    enhanced_steps = enhancer.enhance_steps(test_steps)
    self.logger.info("=== 增强后的步骤 ===")
    for step in enhanced_steps:
        self.logger.info(f"- {step.get('name')}: {step.get('description')} [{step.get('intent')}]")

    # 测试参数增强
    test_params = [
        {'name': 'command', 'param_type': 'date_range', 'value': '20260401-20260410'},
        {'name': 'command_2', 'param_type': 'output_path', 'value': '/x/data/result.json'},
        {'name': 'limit', 'param_type': 'number', 'value': '100'}
    ]

    enhanced_params = enhancer.enhance_parameters(test_params)
    self.logger.info("\n=== 增强后的参数 ===")
    for param in enhanced_params:
        self.logger.info(f"- {param.get('name')}: {param.get('description')}")

    # 测试描述生成
    description = enhancer.generate_description(test_steps)
    self.logger.info("\n=== 工作流描述 ===")
    self.logger.info(f"标题: {description.get('title')}")
    self.logger.info(f"描述: {description.get('description')}")
    self.logger.info(f"功能: {description.get('features')}")


if __name__ == "__main__":
    main()
