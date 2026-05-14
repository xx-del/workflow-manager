#!/bin/bash
# Stop 钩子：检查工作流完成状态
# 版本：v6.2.0
# 更新时间：2026-05-12
# 作用：会话结束时检查是否有未完成的工作流

STATUS_FILE=$(find ~/.hermes/workflows -name "status.json" -exec grep -l '"status": "running"' {} \; 2>/dev/null | grep -v ".backup" | head -1)

if [ -n "$STATUS_FILE" ]; then
  WORKFLOW_DIR=$(dirname "$STATUS_FILE")
  WORKFLOW_NAME=$(basename "$WORKFLOW_DIR")
  
  # 读取完成状态
  COMPLETED_STEPS=$(python3 -c "
import json
with open('$STATUS_FILE') as f:
    d = json.load(f)
print(len(d['workflow'].get('completed_steps', [])))
" 2>/dev/null || echo "0")
  
  TOTAL_STEPS=$(python3 -c "
import json
with open('$STATUS_FILE') as f:
    d = json.load(f)
print(d['workflow'].get('total_steps', 0))
" 2>/dev/null || echo "0")
  
  # 检查是否完成
  if [ "$COMPLETED_STEPS" -lt "$TOTAL_STEPS" ] 2>/dev/null; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  工作流未完成：$WORKFLOW_NAME"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "进度: $COMPLETED_STEPS / $TOTAL_STEPS 步骤完成"
    echo ""
    echo "下次会话继续执行："
    echo "  python ~/.hermes/skills/openclaw-imports/workflow-manager/actions/execute.py $WORKFLOW_NAME --plan-only"
    echo ""
    echo "查看进度："
    echo "  cat $WORKFLOW_DIR/progress.md"
    echo ""
  else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ 工作流已完成：$WORKFLOW_NAME"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "查看结果："
    echo "  cat $WORKFLOW_DIR/findings.md"
    echo ""
    echo "归档工作流："
    echo "  python ~/.hermes/skills/openclaw-imports/workflow-manager/actions/complete.py $WORKFLOW_NAME"
    echo ""
  fi
fi
