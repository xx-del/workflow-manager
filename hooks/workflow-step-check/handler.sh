#!/bin/bash
# Hermes pre_tool_call 钩子：注入 status.md + 约束清单
# 两层注入机制：
# 1. 创建 status.md 并注入完整约束（持久化）
# 2. 注入 status.md 前 30 行（临时提醒，借鉴 planning-with-files）

set -euo pipefail

WORKFLOW_DIR="$HOME/.hermes/workflows"
MARKER_FILE="$WORKFLOW_DIR/.active_session"

# 检查会话标记
if [[ ! -f "$MARKER_FILE" ]]; then
    # ===== 会话标记检查（最高优先级）=====
    # 场景1：检测活跃工作流（status.json）
    ACTIVE_WORKFLOW=$(find "$WORKFLOW_DIR" -maxdepth 2 -name "status.json" -exec grep -l -E '"status": "(running|initialized)"' {} \; 2>/dev/null | head -1)
    
    if [[ -n "$ACTIVE_WORKFLOW" ]]; then
        WF_NAME=$(basename $(dirname "$ACTIVE_WORKFLOW"))
        WF_STATUS=$(python3 -c "import json; print(json.load(open(\"$ACTIVE_WORKFLOW\")).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
        
        cat << BLOCKJSON
{
    "action": "block",
    "message": "⛔ 未完成的工作流但无会话标记。\n\n工作流: $WF_NAME\n状态: $WF_STATUS\n\n解决：python actions/execute.py $WF_NAME --init"
}
BLOCKJSON
        exit 0
    fi
    
    # 场景2：检测计划文件（status.md）- Python安全生成JSON
    STATUS_MD_CANDIDATE=$(find "$WORKFLOW_DIR" -maxdepth 2 -name "status.md" -type f 2>/dev/null | head -1)
    
    if [[ -n "$STATUS_MD_CANDIDATE" ]]; then
        WF_NAME=$(basename $(dirname "$STATUS_MD_CANDIDATE"))
        
        python3 << PYEOF
import json

try:
    with open("$STATUS_MD_CANDIDATE", "r") as f:
        constraints = f.read()[:300]
except:
    constraints = "（无法读取）"

payload = {
    "action": "block",
    "message": f"⚠️ 工作流计划存在但无会话标记。\n\n工作流: $WF_NAME\n\n解决：python actions/execute.py $WF_NAME --init\n\n---\n约束摘要：\n{constraints}"
}
print(json.dumps(payload, ensure_ascii=False))
PYEOF
        exit 0
    fi
    
    exit 0  # 非工作流会话，静默退出
fi

# 读取标记信息
WORKFLOW_NAME=$(python3 -c "import json; print(json.load(open('$MARKER_FILE'))['workflow_name'])" 2>/dev/null)
WORKFLOW_PATH="$WORKFLOW_DIR/$WORKFLOW_NAME"
STATUS_JSON="$WORKFLOW_PATH/status.json"
STATUS_MD="$WORKFLOW_PATH/status.md"

# 读取 Hermes 注入的环境变量
TOOL_NAME="${HERMES_TOOL_NAME:-}"
TOOL_INPUT="${HERMES_TOOL_INPUT:-}"

# ===== 硬约束检测 =====
if [[ -n "$TOOL_NAME" ]]; then
    # 规则 1: 禁止删除工作流目录和文件
    if [[ "$TOOL_NAME" == "terminal" ]]; then
        if echo "$TOOL_INPUT" | grep -qE "(rm -rf|rm -r|rmdir).*workflows"; then
            cat << 'BLOCKJSON'
{
    "action": "block",
    "message": "⛔ 禁止删除工作流目录。\n\n清理状态请使用：\npython actions/execute.py <工作流名称> --init\n\nexecute.py 会自动清理状态文件，不会删除 WORKFLOW.md。"
}
BLOCKJSON
            exit 0
        fi
    fi
fi

# ===== 时间参数拦截 =====
if [[ -f "$MARKER_FILE" ]] && [[ -f "$STATUS_JSON" ]]; then
    # 规则 2: 禁止添加时间参数（timeout/time等，排除sleep）
    if [[ "$TOOL_NAME" == "terminal" ]]; then
        if echo "$TOOL_INPUT" | grep -qiE '(^|[|&;])[[:space:]]*(timeout|time)[[:space:]]+|[[:space:]]--(timeout|max-time|connect-timeout|deadline|time-limit)([= ]|$)|[[:space:]]-[tm][[:space:]]*[0-9]'; then
            VIOLATION=$(echo "$TOOL_INPUT" | grep -oiE '(^|[|&;])[[:space:]]*(timeout|time)[[:space:]]+[0-9]*|[[:space:]]--(timeout|max-time|connect-timeout|deadline|time-limit)([= ]|$)[0-9]*|[[:space:]]-[tm][[:space:]]*[0-9]+' | head -1)
            
            cat << BLOCKJSON
{
    "action": "block",
    "message": "⛔ 工作流执行禁止添加时间参数。\n\n违规参数: $VIOLATION\n\n原因：工作流步骤可能需要长时间运行，时间参数会导致意外中断。\n\n正确做法：直接执行命令，不添加任何时间参数。\n\n参考：~/.hermes/skills/openclaw-imports/workflow-manager/references/workflow_timeout_error_analysis.md"
}
BLOCKJSON
            exit 0
        fi
    fi
fi

# ===== 串行模式检查 =====
if [[ -f "$STATUS_JSON" ]]; then
    WORKFLOW_MODE=$(python3 -c "import json; d=json.load(open('$STATUS_JSON')); print(d.get('mode', 'serial'))" 2>/dev/null || echo "serial")
    CURRENT_STEP=$(python3 -c "import json; d=json.load(open('$STATUS_JSON')); print(d.get('current_step', 1))" 2>/dev/null || echo "1")
    
    if [[ "$WORKFLOW_MODE" == "serial" ]] && [[ "$CURRENT_STEP" -gt 1 ]]; then
        PREV_STEP=$((CURRENT_STEP - 1))
        PREV_STATUS=$(python3 -c "import json; d=json.load(open('$STATUS_JSON')); print(d.get('steps', {}).get(str($PREV_STEP), {}).get('status', 'pending'))" 2>/dev/null || echo "pending")
        
        if [[ "$PREV_STATUS" != "completed" ]] && [[ "$PREV_STATUS" != "skipped" ]]; then
            cat << BLOCKJSON
{
    "action": "block",
    "message": "⛔ 串行模式违规。\n\n当前步骤: $CURRENT_STEP\n前一步骤: $PREV_STEP (状态: $PREV_STATUS)\n\n必须等待前一步完成。"
}
BLOCKJSON
            exit 0
        fi
    fi
fi

# ===== 第一部分：禁用自动创建 status.md =====
# 已禁用：让 AI 生成 status.md（参考 planning-with-files）
# 原逻辑：检测 status.json 存在但 status.md 不存在时自动创建
# 新逻辑：AI 读取 WORKFLOW.md 后生成 status.md

# 保留：约束检查逻辑（禁止删除、禁止 timeout、串行模式检查）
# 这些检查在上方已实现（第 50-120 行）

# ===== 第二部分：注入 status.md 前 30 行（借鉴 planning-with-files）=====
# ===== 第二部分：注入 status.md 前 30 行（借鉴 planning-with-files）=====
if [[ -f "$STATUS_MD" ]]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[workflow-manager] ACTIVE WORKFLOW — $WORKFLOW_NAME"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    head -30 "$STATUS_MD"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

exit 0
