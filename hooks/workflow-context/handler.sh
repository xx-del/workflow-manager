#!/bin/bash
# Workflow Context Hook - 显示活动工作流状态 + 提醒使用agent-pool
# 事件: pre_llm_call (UserPromptSubmit)
# 会话标记机制: 只在工作流会话中触发

WORKFLOW_DIR="$HOME/.hermes/workflows"
MARKER_FILE="$WORKFLOW_DIR/.active_session"

# 检查会话标记
if [[ ! -f "$MARKER_FILE" ]]; then
    exit 0  # 非工作流会话，静默退出
fi

# 读取标记信息
WORKFLOW_NAME=$(python3 -c "import json; print(json.load(open('$MARKER_FILE'))['workflow_name'])" 2>/dev/null)

# 查找活动工作流（支持 status.md 和 status.json）
STATUS_FILE="$WORKFLOW_DIR/$WORKFLOW_NAME/status.md"
if [[ ! -f "$STATUS_FILE" ]]; then
    STATUS_FILE="$WORKFLOW_DIR/$WORKFLOW_NAME/status.json"
fi

if [[ ! -f "$STATUS_FILE" ]]; then
    # 尝试全局搜索
    STATUS_FILE=$(find "$WORKFLOW_DIR" -name "status.md" -type f 2>/dev/null | head -1)
    if [[ -z "$STATUS_FILE" ]]; then
        STATUS_FILE=$(find "$WORKFLOW_DIR" -name "status.json" -type f 2>/dev/null | head -1)
    fi
fi

if [[ -z "$STATUS_FILE" ]]; then
    exit 0
fi

WF_DIR=$(dirname "$STATUS_FILE")
WF_NAME=$(basename "$WF_DIR")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 工作流上下文"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [[ "$STATUS_FILE" == *.md ]]; then
    # status.md 格式
    head -30 "$STATUS_FILE"
else
    # status.json 格式
    python3 -c "
import json
with open('$STATUS_FILE') as f:
    d = json.load(f)
print(f\"📦 {d.get('workflow_name', '$WF_NAME')}\")
print(f\"   状态: {d.get('status', 'unknown')}\")
print(f\"   当前步骤: {d.get('current_step', 'unknown')}\")
" 2>/dev/null
fi

echo ""
echo "💡 请使用 agent-pool 执行工作流任务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
