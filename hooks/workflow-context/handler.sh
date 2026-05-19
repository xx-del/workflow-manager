#!/bin/bash
# Workflow Context Hook - 显示活动工作流状态 + 提醒使用agent-pool
# 事件: pre_llm_call (UserPromptSubmit)
# 会话标记机制: 只在工作流会话中触发
# 增强版：识别工作流类型（normal/branch/heartbeat）

WORKFLOW_DIR="$HOME/.hermes/workflows"
MARKER_FILE="$WORKFLOW_DIR/.active_session"

# 检查会话标记
if [[ ! -f "$MARKER_FILE" ]]; then
    exit 0  # 非工作流会话，静默退出
fi

# 读取标记信息
WORKFLOW_NAME=$(python3 -c "import json; print(json.load(open('$MARKER_FILE'))['workflow_name'])" 2>/dev/null)

if [[ -z "$WORKFLOW_NAME" ]]; then
    exit 0
fi

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

# === 工作流类型识别 ===
INDEX_YAML="$WF_DIR/_index.yaml"
WORKFLOW_TYPE="normal"

if [[ -f "$INDEX_YAML" ]]; then
    WORKFLOW_TYPE=$(python3 -c "
import yaml
import sys

try:
    with open('$INDEX_YAML') as f:
        index = yaml.safe_load(f)
    
    nodes = index.get('nodes', [])
    config = index.get('config', {})
    
    # 1. branch 类型
    if index.get('type') == 'branch':
        print('branch')
        sys.exit(0)
    
    if all(n.get('calls') == 'workflow-manager' for n in nodes):
        print('branch')
        sys.exit(0)
    
    # 2. heartbeat 类型
    if config.get('heartbeat', {}).get('enabled'):
        print('heartbeat')
        sys.exit(0)
    
    if any(n.get('type') in ['breakpoint', 'auto'] for n in nodes):
        print('heartbeat')
        sys.exit(0)
    
    # 3. normal 类型
    print('normal')
    
except Exception as e:
    print('normal')
" 2>/dev/null)
fi

# === 根据类型注入不同内容 ===
case "$WORKFLOW_TYPE" in
    branch)
        echo "🔄 拼接工作流检测"
        echo ""
        echo "工作流: $WF_NAME"
        echo "类型: branch"
        echo "目录: $WF_DIR"
        echo ""
        echo "子工作流路径："
        python3 -c "
import yaml
try:
    with open('$INDEX_YAML') as f:
        index = yaml.safe_load(f)
    for i, node in enumerate(index.get('nodes', []), 1):
        if node.get('calls') == 'workflow-manager':
            name = node.get('name', '未命名')
            print(f'{i}. {name}: ~/.hermes/workflows/{name}/WORKFLOW.md')
except:
    pass
" 2>/dev/null
        echo ""
        echo "📋 主AI任务：按顺序读取上述WORKFLOW.md，合并生成统一status.md"
        echo ""
        ;;
    heartbeat)
        echo "💓 断点工作流检测"
        echo ""
        echo "工作流: $WF_NAME"
        echo "类型: heartbeat"
        echo "目录: $WF_DIR"
        echo ""
        echo "断点步骤："
        python3 -c "
import yaml
try:
    with open('$INDEX_YAML') as f:
        index = yaml.safe_load(f)
    for node in index.get('nodes', []):
        if node.get('type') == 'breakpoint':
            print(f\"- 步骤{node.get('id', '?')}: {node.get('name', '未命名')}\")
except:
    pass
" 2>/dev/null
        echo ""
        echo "自动步骤（心跳接管）："
        python3 -c "
import yaml
try:
    with open('$INDEX_YAML') as f:
        index = yaml.safe_load(f)
    for node in index.get('nodes', []):
        if node.get('type') == 'auto':
            print(f\"- 步骤{node.get('id', '?')}: {node.get('name', '未命名')}\")
except:
    pass
" 2>/dev/null
        echo ""
        echo "📋 主AI任务：执行到断点步骤后停止，等待心跳接管"
        echo ""
        ;;
    normal)
        # 普通工作流：无需额外提示
        ;;
esac

# === 注入 status.md 前30行（所有类型都执行）===
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
