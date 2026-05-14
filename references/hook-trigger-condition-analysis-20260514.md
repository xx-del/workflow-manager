# Hook 触发条件分析

**日期**: 2026-05-14
**问题**: workflow-manager Hook 在非工作流会话中也触发

---

## 问题现象

用户发现 workflow-manager 的 Hook 在本次会话（非工作流任务）中也被触发：

| Hook | 触发次数 | 说明 |
|------|----------|------|
| UserPromptSubmit | 2 | 每条用户消息都触发 |
| PreToolUse | 9 | matcher 匹配的工具调用前触发 |
| PostToolUse | 9 | 每次工具调用后都触发 |

---

## 原因分析

### 当前 Hook 触发逻辑

**workflow-manager Hook 定义**：
```yaml
hooks:
  UserPromptSubmit:
    - hooks:
        - type: command
          command: bash hooks/workflow-context/handler.sh
  # 无 matcher，所有用户消息都触发
```

**handler.sh 逻辑**：
```bash
STATUS_FILE=$(find "$WORKFLOW_DIR" -name "status.md" -type f 2>/dev/null | head -1)
if [[ -z "$STATUS_FILE" ]]; then
    exit 0  # 无活动工作流，静默退出
fi
# 有 status 文件 → 输出内容
```

### 问题根源

| 维度 | planning-with-files | workflow-manager | 差异 |
|------|---------------------|------------------|------|
| **触发条件** | 有 plan 文件 | 有 status 文件 | 相同逻辑 |
| **实际差异** | plan 文件主动创建 | status 文件可能残留 | ⚠️ 关键 |

**问题**：workflow-manager 的 `status.md` 可能从上次会话残留，导致本次会话触发 Hook。

---

## 解决方案

### 方案 A：会话标记文件（推荐）

**原理**：工作流初始化时创建会话标记，完成时清理。

**实现**：

```bash
# 1. 修改 execute.py --init
echo "$SESSION_ID" > ~/.hermes/workflows/.active_session

# 2. 修改 handler.sh
ACTIVE_SESSION="$HOME/.hermes/workflows/.active_session"
if [[ ! -f "$ACTIVE_SESSION" ]]; then
    exit 0  # 非工作流会话，静默退出
fi

# 3. 修改 complete.py
rm -f ~/.hermes/workflows/.active_session
```

**优点**：
- 无需修改 Hermes 核心
- 精确控制，无歧义
- 立即可用

**缺点**：
- 需要修改初始化/完成脚本
- 需手动清理残留标记

### 方案 B：意图关键词检测

**原理**：Hook 内检查用户消息是否包含工作流关键词。

```bash
# 修改 handler.sh
USER_MSG="${HERMES_USER_MESSAGE:-}"
if [[ ! "$USER_MSG" =~ (工作流|workflow|执行|运行|启动|继续) ]]; then
    exit 0
fi
```

**优点**：
- 简单直接
- 无需修改初始化脚本

**缺点**：
- 依赖关键词匹配，可能误判
- 需要传递 user_message 到 Hook（当前已支持）

### 方案 C：技能加载检测（不可行）

**原理**：Hook 检测 workflow-manager 技能是否在当前会话加载。

**问题**：Hermes 核心不追踪会话级技能加载状态。

详见：`~/.hermes/skills/devops/hermes-plugin-development/references/skill-load-detection-limitation-20260514.md`

---

## 推荐实施

**短期**：方案 B（意图关键词检测）
- 修改 `hooks/workflow-context/handler.sh`
- 添加关键词检测逻辑

**长期**：方案 A（会话标记文件）
- 修改 `actions/execute.py` 和 `actions/complete.py`
- 添加会话标记管理

---

## 实施示例

### 方案 B 实现

```bash
#!/bin/bash
# hooks/workflow-context/handler.sh - 增强版

WORKFLOW_DIR="$HOME/.hermes/workflows"

# 1. 检查用户消息是否包含工作流关键词（从环境变量获取）
USER_MSG="${HERMES_USER_MESSAGE:-}"
if [[ -n "$USER_MSG" ]]; then
    if [[ ! "$USER_MSG" =~ (工作流|workflow|执行|运行|启动|继续|查看状态|进度|agent-pool) ]]; then
        exit 0  # 非工作流意图，静默退出
    fi
fi

# 2. 检查是否有活动工作流
STATUS_FILE=$(find "$WORKFLOW_DIR" -name "status.md" -type f 2>/dev/null | head -1)
if [[ -z "$STATUS_FILE" ]]; then
    exit 0
fi

# 3. 输出上下文
WF_DIR=$(dirname "$STATUS_FILE")
WF_NAME=$(basename "$WF_DIR")
echo ""
echo "🔄 工作流上下文: $WF_NAME"
head -30 "$STATUS_FILE"
```

**注意**：需要 skill-hook-bridge 传递 `user_message` 到环境变量。当前 `TemplateResolver` 已支持 `{{user_message}}`。
