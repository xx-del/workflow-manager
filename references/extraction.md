# 工作流识别规范

## 概述

识别工作流是从会话上下文中自动提取可复用工作流定义的过程。

## 触发方式

| 触发词 | 说明 |
|--------|------|
| "识别工作流" | 仅识别，不创建 |
| "提取工作流" | 仅识别，不创建 |
| "生成工作流" | 识别 + 创建 |
| "保存为工作流" | 识别 + 创建 + 等待保存确认 |

## 识别流程

```
[1] 提取会话上下文
    - tool calls（工具调用）
    - tool results（执行结果）
    - user feedback（用户反馈）

[2] 识别核心步骤（逆向追踪）
    - 从成功输出回溯
    - 过滤试错噪音
    - 确定步骤依赖

[3] 分析偏差纠正
    - 识别失败尝试
    - 匹配成功做法
    - 提取纠正模式

[4] 抽象参数
    - 识别可变参数
    - 设置默认值
    - 建立参数映射

[5] AI 增强
    - 步骤语义化命名
    - 参数语义化命名
    - 纠错深化分析

[6] 生成草案
    - WORKFLOW.md 格式
    - 展示给用户确认
```

## 核心模块

| 模块 | 文件 | 职责 |
|------|------|------|
| 提取器 | `src/extractor/pipeline.py` | 主入口 |
| 会话提取 | `src/extractor/extractor.py` | 提取会话上下文 |
| 纠正分析 | `src/extractor/correction_analyzer.py` | 偏差纠正识别 |
| 参数抽象 | `src/extractor/param_abstractor.py` | 参数抽象化 |
| AI 增强 | `src/extractor/ai_enhancer.py` | 语义化增强 |
| 生成器 | `src/extractor/generator.py` | WORKFLOW.md 生成 |

## 使用方式

### 方式 1：命令行

```bash
~/.hermes/skills/openclaw-imports/workflow-manager/actions/extract.sh
```

### 方式 2：Python 模块

```python
import sys
sys.path.insert(0, '~/.hermes/skills/openclaw-imports/workflow-manager/src/extractor')

from pipeline import WorkflowExtractorPipeline

pipeline = WorkflowExtractorPipeline()
result = pipeline.extract(messages)

if result['success']:
    pipeline.print_summary(result)
    # 用户确认后保存
    pipeline.save(result)
```

### 方式 3：自然语言

```
用户: 生成工作流

助手: 
[1/8] 提取会话上下文...
[2/8] 识别核心步骤...
[3/8] 分析偏差纠正...
[4/8] 抽象参数...
[5/8] AI 增强...
[6/8] 生成工作流...
[7/8] 生成 WORKFLOW.md...
[8/8] 完成提取...

工作流草案已生成，确认保存？
```

## 输出格式

生成的 WORKFLOW.md 包含：

| 部分 | 说明 |
|------|------|
| 参数定义 | 语义化参数名称和描述 |
| 执行步骤 | 步骤名称、工具、动作 |
| 偏差纠正 | 错误类型、触发条件、正确做法 |
| 配置 | 重试、通知、守护等配置 |

## AI 增强策略

| 场景 | 是否启用 AI |
|------|------------|
| 步骤 > 2 个 | 是 |
| 检测到纠错 | 是 |
| 参数 > 3 个 | 是 |
| 简单单步骤 | 否 |

## 错误处理

| 情况 | 处理 |
|------|------|
| 无工具调用 | 提示"会话中没有检测到工具调用" |
| 无成功输出 | 提示"未检测到成功完成的任务" |
| AI 增强失败 | 降级到规则输出 |
