#!/usr/bin/env python3
"""
WORKFLOW.md 生成器 - 从分析结果生成工作流定义文件

职责：
1. 加载 Jinja2 模板
2. 填充工作流数据
3. 生成 WORKFLOW.md 文件
4. 验证生成结果
"""

from utils.logger import get_logger
import json
from datetime import datetime
from typing import Any, Optional
from pathlib import Path
from string import Template


# 工作流模板 - 使用简单字符串模板语法
WORKFLOW_TEMPLATE = '''---
name: {workflow_name}
description: {description}
version: 1.0.0
created_from: session_extraction
created_at: {timestamp}
---

# 概述

{description}

# 参数定义

{parameters_section}

# 执行步骤

{steps_section}

{corrections_section}

# 配置

```yaml
retry:
  enabled: true
  max_attempts: 3
  interval: 60
  backoff: exponential

notify:
  on_start: false
  on_complete: true
  on_fail: true
  channel: feishu

guardian:
  enabled: true
  interval: 1800
  stuck_threshold: 1800
  max_repair_attempts: 3

stats:
  total_runs: 0
  success_count: 0
  fail_count: 0
  success_rate: 0%
  avg_duration: "-"
```

# 执行历史

工作流创建后，执行记录将保存在 `history/` 目录中。
'''


class WorkflowGenerator:
    """工作流生成器"""

    def __init__(self, template: str = WORKFLOW_TEMPLATE):

        self.logger = get_logger(__name__)
        self.template = template

    def generate(
        self,
        workflow_name: str,
        description: str,
        core_steps: list[dict],
        parameters: list[dict] = None,
        corrections: list[dict] = None,
        dependencies: dict = None,
        timestamp: str = None
    ) -> str:
        """
        生成 WORKFLOW.md 内容

        Args:
            workflow_name: 工作流名称
            description: 描述
            core_steps: 核心步骤列表
            parameters: 参数列表
            corrections: 偏差纠正列表
            dependencies: 步骤依赖关系
            timestamp: 创建时间

        Returns:
            WORKFLOW.md 文本内容
        """
        if parameters is None:
            parameters = []

        if corrections is None:
            corrections = []

        if dependencies is None:
            dependencies = {}

        if timestamp is None:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 处理步骤依赖
        for step in core_steps:
            step_id = str(step.get('id', ''))
            if step_id in dependencies:
                step['dependencies'] = dependencies[step_id]
            else:
                step['dependencies'] = []

        # 使用简单的字符串替换（避免 Jinja2 依赖）
        content = self._render_template(
            workflow_name=workflow_name,
            description=description,
            timestamp=timestamp,
            parameters=parameters,
            core_steps=core_steps,
            corrections=corrections
        )

        return content

    def _render_template(self, **kwargs) -> str:
        """渲染模板（简化版，不依赖 Jinja2）"""

        # 构建参数部分
        params = kwargs.get('parameters', [])
        if params:
            param_rows = ["| 参数名 | 类型 | 必需 | 默认值 | 说明 |", "|--------|------|------|--------|------|"]
            for p in params:
                required = "是" if p.get('required') else "否"
                param_rows.append(f"| `{p.get('name')}` | {p.get('type', 'string')} | {required} | `{p.get('default', '')}` | {p.get('description', '')} |")
            parameters_section = "\n".join(param_rows)
        else:
            parameters_section = "*无需参数*"

        # 构建步骤部分
        steps = kwargs.get('core_steps', [])
        steps_content = []
        for step in steps:
            steps_content.append(self._render_step(step))
        steps_section = "\n".join(steps_content)

        # 构建纠正部分
        corrections = kwargs.get('corrections', [])
        if corrections:
            corrections_content = ["# 偏差纠正指南", "", "> 以下是从实际执行中提取的经验教训", ""]
            for c in corrections:
                corrections_content.append(f"## {c.get('error_type', '错误处理')}")
                corrections_content.append(f"")
                corrections_content.append(f"**触发条件**: {c.get('condition', '未知')}")
                corrections_content.append(f"")
                corrections_content.append(f"**错误做法**: {c.get('wrong_approach', '未知')}")
                corrections_content.append(f"")
                corrections_content.append(f"**正确做法**: {c.get('correct_approach', '未知')}")
                corrections_content.append("")
            corrections_section = "\n".join(corrections_content)
        else:
            corrections_section = ""

        # 使用字符串格式化
        content = self.template.format(
            workflow_name=kwargs.get('workflow_name', '未命名工作流'),
            description=kwargs.get('description', ''),
            timestamp=kwargs.get('timestamp', ''),
            parameters_section=parameters_section,
            steps_section=steps_section,
            corrections_section=corrections_section
        )

        return content

    def _render_step(self, step: dict) -> str:
        """渲染单个步骤"""
        step_id = step.get('id', '?')
        name = step.get('name', '未命名步骤')
        tool = step.get('tool', 'unknown')
        action = step.get('action', '')
        outputs = step.get('outputs', [])
        dependencies = step.get('dependencies', [])

        output_md = ""
        if outputs:
            output_lines = [f"- `{o}`" for o in outputs]
            output_md = "\n**输出**:\n" + "\n".join(output_lines) + "\n"

        dep_md = ""
        if dependencies:
            dep_md = f"\n**依赖**: 步骤 {', '.join(map(str, dependencies))}\n"

        return f"""## 步骤 {step_id}: {name}

**工具**: `{tool}`

**动作**:
```
{action}
```
{output_md}{dep_md}"""

    def save(self, content: str, output_path: str) -> bool:
        """
        保存 WORKFLOW.md 到文件

        Args:
            content: 工作流内容
            output_path: 输出路径

        Returns:
            是否成功
        """
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except Exception as e:
            self.logger.error(f"Error saving workflow: {e}")
            return False


def generate_workflow_name(core_steps: list[dict], description: str = '') -> str:
    """
    生成工作流名称

    基于步骤内容自动生成有意义的名称
    """
    if description:
        # 从描述中提取关键词
        words = description.split()[:3]
        return '-'.join(words).lower()

    # 基于步骤推断
    tools = [s.get('tool', '') for s in core_steps]
    actions = [s.get('name', '') for s in core_steps]

    # 尝试组合名称
    if '获取' in str(actions) or 'fetch' in str(tools):
        return 'data-collection-workflow'
    elif '处理' in str(actions) or 'process' in str(tools):
        return 'data-processing-workflow'
    elif '备份' in str(actions) or 'backup' in str(tools):
        return 'backup-workflow'
    else:
        return f'workflow-{datetime.now().strftime("%Y%m%d%H%M")}'


def main():
    """测试函数"""
    generator = WorkflowGenerator()

    test_steps = [
        {
            'id': '1',
            'name': '获取数据',
            'tool': 'terminal',
            'action': 'curl http://api/data > result.json',
            'outputs': ['result.json'],
            'dependencies': []
        },
        {
            'id': '2',
            'name': '处理数据',
            'tool': 'terminal',
            'action': 'python process.py result.json',
            'outputs': ['output.txt'],
            'dependencies': ['1']
        }
    ]

    test_params = [
        {
            'name': 'date_range',
            'type': 'string',
            'required': True,
            'default': '{{yesterday}}',
            'description': '数据日期范围'
        }
    ]

    test_corrections = [
        {
            'error_type': '网络错误',
            'condition': '当遇到网络超时时',
            'wrong_approach': '直接重试',
            'correct_approach': '检查代理设置，使用备用端点'
        }
    ]

    content = generator.generate(
        workflow_name='data-collection-workflow',
        description='自动采集并处理数据',
        core_steps=test_steps,
        parameters=test_params,
        corrections=test_corrections
    )

    self.logger.info(content)


if __name__ == "__main__":
    main()
