#!/bin/bash
# PostToolUse 钩子：提醒更新进度文件
# 融合 planning-with-files PostToolUse 机制
# 会话标记机制: 只在工作流会话中触发

WORKFLOW_DIR="$HOME/.hermes/workflows"
MARKER_FILE="$WORKFLOW_DIR/.active_session"

# 检查会话标记
if [[ ! -f "$MARKER_FILE" ]]; then
    exit 0  # 非工作流会话，静默退出
fi

# 读取标记信息
WORKFLOW_NAME=$(python3 -c "import json; print(json.load(open('$MARKER_FILE'))['workflow_name'])" 2>/dev/null)

# 查找活动工作流（优先 status.md，回退 status.json）
STATUS_MD="$WORKFLOW_DIR/$WORKFLOW_NAME/status.md"
STATUS_JSON="$WORKFLOW_DIR/$WORKFLOW_NAME/status.json"

if [[ ! -f "$STATUS_MD" ]] && [[ ! -f "$STATUS_JSON" ]]; then
    # 尝试全局搜索
    STATUS_MD=$(find "$WORKFLOW_DIR" -name "status.md" -type f 2>/dev/null | head -1)
    STATUS_JSON=$(find "$WORKFLOW_DIR" -name "status.json" -exec grep -l '"status": "running"' {} \; 2>/dev/null | grep -v ".backup" | head -1)
fi

# ---------- 自动问题记录逻辑 ----------

WORKFLOW_INSTANCE_DIR="$WORKFLOW_DIR/$WORKFLOW_NAME"
FINDINGS_FILE="$WORKFLOW_INSTANCE_DIR/findings.md"
LOCK_FILE="$WORKFLOW_INSTANCE_DIR/.findings.lock"

auto_record_issue() {
    local step="$1"
    local exit_code="$2"
    local error_msg="$3"
    local timestamp=$(date '+%Y-%m-%d %H:%M')
    local issue_line="| $timestamp | $step | 未知错误 | $error_msg | 待分析 | 待解决 | 待处理 |"

    # 使用 flock 保证并发写入安全
    (
        flock -x 200
        # 在 Issues Encountered 表格后插入一行
        if grep -q '<!-- STATS_BLOCK_START' "$FINDINGS_FILE" 2>/dev/null; then
            sed -i "/<!-- STATS_BLOCK_START/i $issue_line" "$FINDINGS_FILE"
            # 更新统计块
            python3 - "$FINDINGS_FILE" << 'PYEOF'
import sys, json, re
from datetime import datetime
path = sys.argv[1]
try:
    with open(path, 'r') as f:
        content = f.read()
    match = re.search(r'<!-- STATS_BLOCK_START\n(.*?)\nSTATS_BLOCK_END -->', content, re.DOTALL)
    if match:
        stats = json.loads(match.group(1))
        stats['total_issues'] = stats.get('total_issues', 0) + 1
        stats['pending'] = stats.get('pending', 0) + 1
        stats['last_issue_time'] = datetime.now().isoformat()
        new_block = f'<!-- STATS_BLOCK_START\n{json.dumps(stats, ensure_ascii=False)}\nSTATS_BLOCK_END -->'
        content = content.replace(match.group(0), new_block)
        with open(path, 'w') as f:
            f.write(content)
except Exception as e:
    pass
PYEOF
        fi
    ) 200>"$LOCK_FILE"
}

# 检查上一步骤是否失败（需要环境变量支持）
# 环境变量由 executor.py 设置：
#   CURRENT_STEP_NAME - 当前步骤名称
#   STEP_EXIT_CODE - 上一步骤退出码
#   STEP_ERROR_MSG - 错误信息（可选）
if [[ "${STEP_EXIT_CODE:-0}" -ne 0 ]]; then
    auto_record_issue "${CURRENT_STEP_NAME:-未知步骤}" "$STEP_EXIT_CODE" "${STEP_ERROR_MSG:-未提供错误信息}"
fi

# ---------- 原有提醒逻辑 ----------

if [[ -n "$STATUS_MD" ]]; then
    WF_DIR=$(dirname "$STATUS_MD")
    WF_NAME=$(basename "$WF_DIR")
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[workflow-manager] 步骤执行完成"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📝 请更新执行记录："
    echo ""
    echo "1. 更新 progress.md（记录执行日志）："
    echo "   - 记录执行的命令、输出、耗时"
    echo "   - 记录遇到的错误和解决方案"
    echo ""
    echo "2. 如果产生了新的子任务或批次，请更新 status.md："
    echo "   - 添加新步骤（如：步骤 3.1、3.2...）"
    echo "   - 更新已有步骤状态（⏳ 待执行 → ✅ 已完成）"
    echo ""
    echo "⚠️  如果遇到问题，系统已自动记录到 findings.md。"
    echo "   手动补充细节："
    echo "   | 时间 | 步骤 | 问题类型 | 描述 | 原因 | 解决方案 | 状态 |"
    echo ""
    echo "💡 提示：findings.md 不会被 --init 清理，使用 --reset-findings 可重置。"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
elif [[ -n "$STATUS_JSON" ]]; then
    # 保留原有的 status.json 逻辑
    WORKFLOW_DIR=$(dirname "$STATUS_JSON")
    WORKFLOW_NAME=$(basename "$WORKFLOW_DIR")
    
    # 检查 progress.md 是否存在
    if [ ! -f "$WORKFLOW_DIR/progress.md" ]; then
        echo ""
        echo "[workflow-manager] progress.md 不存在，建议创建："
        echo "  python ~/.hermes/skills/openclaw-imports/workflow-manager/actions/init_progress.py $WORKFLOW_NAME"
        echo ""
    else
        echo ""
        echo "[workflow-manager] 步骤执行完成，请更新："
        echo "  - progress.md: 记录执行结果和发现"
        echo "  - status.md: 标记当前步骤为 completed（如已完成）"
        echo ""
    fi
    
    # 提醒更新状态
    echo "更新状态命令："
    echo "  python ~/.hermes/skills/openclaw-imports/workflow-manager/actions/update_status.py $WORKFLOW_NAME --step <步骤名> --status completed"
    echo ""
fi
