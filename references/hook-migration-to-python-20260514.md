# Hook迁移到Python处理器（2026-05-14）

## 背景

Workflow hooks使用Shell脚本（handler.sh），但Hermes Gateway Hooks标准要求Python处理器（handler.py）。

## 迁移原因

**问题**：
- handler.sh不被Gateway自动加载
- HOOK.yaml包含command字段（不符合标准）
- 只加载了1个hook（gateway-feishu-notify）

**根因**：
- Hermes Gateway Hooks需要handler.py
- handler.py需要async handle函数
- 返回格式：`{"context": "内容"}` 或 None

## 迁移内容

**创建handler.py（5个）**：
- workflow-status-check/handler.py (pre_llm_call)
- workflow-step-check/handler.py (pre_tool_call)
- workflow-progress-update/handler.py (post_tool_call)
- workflow-ai-remind/handler.py (pre_llm_call)
- workflow-session-cleanup/handler.py (on_session_end)

**修改HOOK.yaml**：
- 移除command字段
- 保留events和filter字段

**更新安装脚本**：
- 支持handler.py
- 移除agent-hooks链接逻辑

## handler.py标准格式

```python
"""Hook处理器"""

import os
import json
from pathlib import Path
from typing import Any, Dict

async def handle(event_type: str, context: Dict[str, Any]) -> Dict[str, str] | None:
    """
    处理hook事件
    
    Args:
        event_type: 事件类型
        context: Hermes传入的上下文
    
    Returns:
        {"context": "注入内容"} 或 None
    """
    # 处理逻辑
    return {"context": "注入内容"}
```

## HOOK.yaml标准格式

```yaml
name: workflow-status-check
description: "显示活动工作流状态概要"
events:
  - pre_llm_call
# 不需要command字段
```

## 事件映射

| Hook | 事件 | 触发时机 |
|------|------|---------|
| workflow-status-check | pre_llm_call | LLM调用前 |
| workflow-step-check | pre_tool_call | 工具调用前 |
| workflow-progress-update | post_tool_call | 工具调用后 |
| workflow-ai-remind | pre_llm_call | LLM调用前 |
| workflow-session-cleanup | on_session_end | 会话结束时 |

## 触发机制

**关键发现**：Hook是事件驱动，不是技能驱动。

- 每次事件发生都会触发（无论是否使用工作流）
- handler.py内部判断是否有活动工作流
- 无工作流时返回None，不影响正常对话

## 常见问题

### 问题1：YAML格式错误

**症状**：
```
while scanning a simple key
could not find expected ':'
```

**原因**：移除command行后留下空行

**解决**：
```bash
sed -i '/^$/d' HOOK.yaml
```

### 问题2：Hook未加载

**检查方法**：
```bash
tail -20 ~/.hermes/logs/gateway.log | grep "hook"
```

**预期输出**：
```
INFO gateway.run: 6 hook(s) loaded
```

### 问题3：handler.py未生效

**验证方法**：
```python
import asyncio
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("handler", Path.home() / ".hermes/hooks/workflow-status-check/handler.py")
handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler)

async def test():
    result = await handler.handle('pre_llm_call', {})
    print(result)

asyncio.run(test())
```

## 测试验证

**手动测试**：
```bash
python3 << 'EOF'
import asyncio
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("handler", Path.home() / ".hermes/hooks/workflow-status-check/handler.py")
handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler)

async def test():
    result = await handler.handle('pre_llm_call', {})
    if result:
        print(result.get('context'))

asyncio.run(test())
EOF
```

**预期结果**：显示活动工作流概要

## 文件位置

- 源码：`~/.hermes/skills/openclaw-imports/workflow-manager/hooks/`
- 映射：`~/.hermes/hooks/workflow-*/`
- 备份：`handler.sh.backup`

## 参考示例

已成功触发的hook：`~/.hermes/hooks/gateway-feishu-notify/`

## 更新日期

2026-05-14
