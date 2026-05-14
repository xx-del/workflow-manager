# Hook Python迁移方案

**日期**：2026-05-14
**状态**：待执行

---

## 背景

工作流Hook当前使用handler.sh（Shell脚本），不符合Hermes网关钩子标准，导致Gateway无法自动触发。

---

## 标准格式（参考gateway-feishu-notify）

**HOOK.yaml**：
```yaml
name: hook-name
description: "描述"
events:
  - pre_llm_call
```

**handler.py**：
```python
"""Hook处理器"""

async def handle(event_type: str, context: Dict[str, Any]) -> Dict[str, str] | None:
    """处理hook事件，返回 {"context": "内容"} 注入上下文"""
    # 逻辑实现
    return {"context": "注入内容"}
```

---

## 当前问题

| 项目 | 当前状态 | 标准状态 |
|------|---------|---------|
| HOOK.yaml | 包含command字段 | 不包含command字段 |
| 处理器 | handler.sh | handler.py |
| 触发方式 | 手动执行 | Gateway自动触发 |

---

## 迁移步骤

**步骤1**：创建handler.py（5个文件）
- workflow-status-check/handler.py
- workflow-step-check/handler.py
- workflow-progress-update/handler.py
- workflow-ai-remind/handler.py
- workflow-session-cleanup/handler.py

**步骤2**：删除handler.sh

**步骤3**：更新安装脚本（支持.py）

**步骤4**：运行安装脚本重新映射

**步骤5**：验证Gateway自动触发

---

## 逻辑迁移要点

**保留现有逻辑**：
- 查找活动工作流（~/.hermes/workflows/）
- 读取status.json/status.md
- 生成状态概要
- 无工作流时返回None

**新增返回值**：
- Shell的echo输出 → Python的return {"context": "内容"}

---

## 参考文件

- 标准示例：`~/.hermes/hooks/gateway-feishu-notify/handler.py`
- 现有逻辑：`~/.hermes/skills/openclaw-imports/workflow-manager/hooks/*/handler.sh`
- 配置修复：`references/hook-config-fix-20260514.md`
