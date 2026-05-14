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

# ===== 第一部分：自动创建 status.md 并注入完整约束 =====
if [[ -f "$STATUS_JSON" ]]; then
    status=$(python3 -c "import json; print(json.load(open('$STATUS_JSON')).get('status', ''))" 2>/dev/null || echo "")
    
    # 如果是初始化状态且 status.md 不存在，自动创建
    if [[ "$status" == "initialized" ]] && [[ ! -f "$STATUS_MD" ]]; then
        
        # === 工作流类型识别 ===
        workflow_type="normal"
        workflow_mode="serial"
        breakpoint_steps=""
        sub_workflows=""
        
        # 读取 _index.yaml
        if [[ -f "$WORKFLOW_PATH/_index.yaml" ]]; then
            result=$(python3 -c "
import yaml
import json
import sys
try:
    with open('$WORKFLOW_PATH/_index.yaml') as f:
        data = yaml.safe_load(f)
    
    workflows = data.get('workflows', [])
    if workflows:
        wf = workflows[0]
        nodes = wf.get('nodes', [])
        
        # 识别类型
        workflow_type = 'normal'
        
        # 1. branch
        if wf.get('type') == 'branch':
            workflow_type = 'branch'
        elif all(n.get('calls') == 'workflow-manager' for n in nodes):
            workflow_type = 'branch'
        
        # 2. heartbeat
        if workflow_type == 'normal':
            config = wf.get('config', {})
            if config.get('heartbeat', {}).get('enabled'):
                workflow_type = 'heartbeat'
            elif any(n.get('type') in ['breakpoint', 'auto'] for n in nodes):
                workflow_type = 'heartbeat'
            elif any(n.get('trigger') == 'heartbeat' for n in nodes):
                workflow_type = 'heartbeat'
        
        # 收集断点步骤
        breakpoint_steps = []
        for node in nodes:
            if node.get('type') == 'breakpoint':
                breakpoint_steps.append(node.get('name', '未命名'))
            elif node.get('trigger') == 'heartbeat':
                breakpoint_steps.append(node.get('name', '未命名'))
        
        # 收集子工作流（拼接工作流）
        sub_workflows = []
        for node in nodes:
            if node.get('calls') == 'workflow-manager':
                sub_workflows.append(node.get('name', '未命名'))
        
        # 输出 JSON
        output = {
            'type': workflow_type,
            'mode': wf.get('mode', 'serial'),
            'name': wf.get('name', ''),
            'breakpoints': breakpoint_steps,
            'sub_workflows': sub_workflows
        }
        print(json.dumps(output))
except Exception as e:
    print(json.dumps({'type': 'normal', 'mode': 'serial', 'name': '', 'breakpoints': [], 'sub_workflows': []}))
" 2>/dev/null)
            
            # 解析结果
            workflow_type=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin).get('type', 'normal'))")
            workflow_mode=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin).get('mode', 'serial'))")
            workflow_name=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin).get('name', ''))")
            breakpoint_steps=$(echo "$result" | python3 -c "import json,sys; print(','.join(json.load(sys.stdin).get('breakpoints', [])))")
            sub_workflows=$(echo "$result" | python3 -c "import json,sys; print(','.join(json.load(sys.stdin).get('sub_workflows', [])))")
        fi
        
        # 默认值
        workflow_type=${workflow_type:-"normal"}
        workflow_mode=${workflow_mode:-"serial"}
        workflow_name=${workflow_name:-$WORKFLOW_NAME}
        
        # === 创建 status.md 并注入完整约束 ===
        cat > "$STATUS_MD" << EOF
# ${workflow_name} 工作流执行计划

**生成时间**: $(date '+%Y-%m-%d %H:%M:%S')
**工作流名称**: ${workflow_name}
**工作流类型**: ${workflow_type}
**执行模式**: ${workflow_mode}

---

## 一、执行行为约束

**绝对禁止**:
- ❌ 禁止修改 WORKFLOW.md 定义的命令
- ❌ 禁止添加 timeout 参数
- ❌ 禁止跳过步骤
- ❌ 禁止使用替代方案
- ❌ 禁止自行决定

**必须遵守**:
- ✅ 严格按指令执行
- ✅ 验证每个输出
- ✅ 每步执行后更新状态

---

## 二、主AI职责边界约束

**禁止行为**:
- ❌ 禁止自己读取 _index.yaml（代码已实现）
- ❌ 禁止自己判断步骤顺序（代码已实现）
- ❌ 禁止自己检测依赖关系（代码已实现）

**允许行为**:
- ✅ 读取 WORKFLOW.md 理解定义
- ✅ 读取 status.md 获取约束
- ✅ 使用 agent-pool 执行步骤
- ✅ 更新 status.md 状态

---

## 二之一、文件操作约束

**绝对禁止删除**:
- ❌ 禁止删除工作流目录
- ❌ 禁止删除 WORKFLOW.md
- ❌ 禁止删除 _index.yaml
- ❌ 禁止删除任何已存在的文件

**只允许清理状态文件**:
- ✅ 清理由 execute.py --init 自动完成
- ✅ 主 AI 不要手动删除任何文件

**清理状态的正确方法**:
\`\`\`bash
# 不要手动删除，使用命令：
python actions/execute.py ${workflow_name} --init  # 清理并初始化
python actions/complete.py ${workflow_name}        # 完成并清理标记
\`\`\`

---

## 三、Agent-Pool 使用约束

**必须使用 agent-pool**:
- ⚠️ 工作流步骤执行必须通过 agent-pool
- ⚠️ 禁止直接使用 terminal 执行工作流步骤

**如何使用 agent-pool**:

**步骤 1：调用 agent_pool_client.execute()**
\`\`\`python
from agent_pool_client import AgentPoolClient

client = AgentPoolClient()
result = client.execute(
    workflow_name="${workflow_name}",
    workflow_dir="${WORKFLOW_PATH}",
    status_file="${STATUS_JSON}"
)
\`\`\`

**步骤 2：获取 pending_instructions**
\`\`\`python
pending_instructions = result.get("pending_instructions", [])
\`\`\`

**步骤 3：使用 delegate_task 执行指令**
\`\`\`python
for instruction in pending_instructions:
    if instruction.get("action") == "delegate_task":
        delegate_task(
            goal=instruction.get("goal"),
            context=instruction.get("context"),
            toolsets=instruction.get("toolsets", ["terminal", "file"])
        )
\`\`\`

**步骤 4：更新 status.json**
\`\`\`python
import json
status_data = json.load(open("${STATUS_JSON}"))
status_data["nodes"][step_name]["status"] = "completed"
json.dump(status_data, open("${STATUS_JSON}", "w"))
\`\`\`

**返回值说明**:
- \`pending_instructions\`: 待执行的指令列表
- \`execution_mode\`: 执行模式（serial/parallel）
- \`workflow_type\`: 工作流类型（normal/branch/heartbeat）

---

## 四、异常处理约束

**处理流程**:
\`\`\`
步骤执行失败
     ↓
[1] 立即停止工作流（不诊断、不修复、不跳过）
     ↓
[2] 记录异常到 status.md 错误日志
     ↓
[3] 上报用户，等待指示
\`\`\`

**禁止行为**:
- ❌ 禁止自行诊断原因
- ❌ 禁止自行尝试修复
- ❌ 禁止跳过失败步骤
- ❌ 禁止静默降级

---

## 五、进度记录约束

**必须记录**:
- 每步执行前：更新 status.json（status: running）
- 每步执行后：更新 status.json（status: completed）
- 执行日志：记录到 progress.md

**更新格式**:
\`\`\`json
{
    "workflow": "${workflow_name}",
    "status": "running",
    "nodes": {
        "步骤名称": {
            "status": "completed",
            "executed_at": "2026-05-14 13:30:00"
        }
    }
}
\`\`\`

---

## 六、完成判定约束

**完成标准**:
- 所有步骤 status = completed
- 所有预期输出文件存在
- 无未处理的错误

**完成命令**:
\`\`\`bash
python actions/complete.py ${workflow_name}
\`\`\`

---

## 执行步骤

(AI 读取 WORKFLOW.md 后填写)

---

## 错误日志

| 错误 | 步骤 | 尝试 | 解决方案 |
|------|------|------|----------|
| (执行时填写) | | | |

EOF
        
        # === 注入类型特殊约束 ===
        if [[ "$workflow_type" == "branch" ]]; then
            cat >> "$STATUS_MD" << 'EOF'

---

## 七、拼接工作流约束

**识别依据**:
- \`type: branch\` 或所有节点 \`calls: workflow-manager\`

**执行要求**:
- ⚠️  必须展开所有子工作流
- ⚠️  子工作流串行执行（禁止并行）
- ⚠️  所有子工作流完成才算完成
- ⚠️  禁止询问"是否继续执行下一个子工作流"

**如何展开**:

**步骤1：读取 _index.yaml**
定位文件：\`$WORKFLOW_DIR/_index.yaml\`

**步骤2：解析子工作流列表**
对每个子工作流：
- 定位目录：\`/x/AI/openclaw/workflows/{子工作流名称}/\`
- 读取 \`_index.yaml\` 或 \`WORKFLOW.md\`

**步骤3：递归处理每个子工作流**
识别类型：
- branch：继续递归展开
- heartbeat：标注断点位置
- normal：直接解析步骤

**步骤4：收集所有断点**
对每个子工作流：
检查是否有断点步骤

**断点标注格式**:
\`\`\`
- ⛔ [子工作流名称] 步骤名称（断点）
\`\`\`

**状态更新规则**:
- 主 AI 在执行子工作流前更新状态为 running
- 主 AI 在子工作流完成后更新状态为 completed
- 所有子工作流状态 = completed → 工作流完成

EOF
            
            # 列出子工作流
            if [[ -n "$sub_workflows" ]]; then
                echo "" >> "$STATUS_MD"
                echo "**子工作流列表**:" >> "$STATUS_MD"
                IFS=',' read -ra WFS <<< "$sub_workflows"
                for wf in "${WFS[@]}"; do
                    echo "- $wf" >> "$STATUS_MD"
                done
                echo "" >> "$STATUS_MD"
                echo "⚠️  注意：展开时需检查每个子工作流是否包含断点" >> "$STATUS_MD"
            fi
        fi
        
        if [[ "$workflow_type" == "heartbeat" ]]; then
            cat >> "$STATUS_MD" << EOF

---

## 七、断点工作流约束

**识别依据**:
- 存在 \`type: breakpoint\` 或 \`trigger: heartbeat\` 的节点

**断点位置**:
EOF
            
            # 标注断点位置
            if [[ -n "$breakpoint_steps" ]]; then
                IFS=',' read -ra STEPS <<< "$breakpoint_steps"
                for step in "${STEPS[@]}"; do
                    echo "- ⛔ $step（断点步骤）" >> "$STATUS_MD"
                done
            else
                echo "- (AI 读取 _index.yaml 后标注)" >> "$STATUS_MD"
            fi
            
            cat >> "$STATUS_MD" << 'EOF'

**执行要求**:
- ⚠️  执行断点步骤后返回，等待心跳触发
- ⚠️  禁止跳过断点检查
- ⚠️  禁止手动继续后续步骤

**心跳机制**:
- 断点步骤完成后写入状态文件
- 心跳 cronjob 检测状态文件
- 心跳自动触发后续步骤

EOF
        fi
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "✅ 已创建 status.md 并注入完整约束"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "   工作流类型: $workflow_type"
        echo "   执行模式: $workflow_mode"
        if [[ -n "$breakpoint_steps" ]]; then
            echo "   断点位置: $breakpoint_steps"
        fi
        if [[ -n "$sub_workflows" ]]; then
            echo "   子工作流: $sub_workflows"
        fi
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
    fi
fi

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
