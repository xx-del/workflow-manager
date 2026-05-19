# Hook机制优化记录

**日期**: 2026-05-16
**问题**: 工作流执行时Hook未触发，约束未注入，导致主AI违规

## 问题根因

**标记文件缺失**：
- Hook触发条件：`~/.hermes/workflows/.active_session` 存在
- 实际情况：未调用 `execute.py --init`，标记文件不存在
- 结果：Hook静默退出，约束未注入

## 优化方案

### 方案一：Hook阻断模式

**目标**：无标记但存在活跃工作流时强制阻断

**实现**（handler.sh）：
```bash
if [[ ! -f "$MARKER_FILE" ]]; then
    # 检测活跃工作流
    ACTIVE_WORKFLOW=$(find "$WORKFLOW_DIR" -maxdepth 2 -name "status.json" -exec grep -l -E '"status": "(running|initialized)"' {} \; 2>/dev/null | head -1)
    
    if [[ -n "$ACTIVE_WORKFLOW" ]]; then
        # 输出block消息并退出
        ...
    fi
fi
```

### 方案二+三：强制确认机制

**目标**：无标记但有status.md时，显示约束摘要并阻断

**关键修正**：
- ❌ 错误：`CONSTRAINTS_SAFE=$(... | jq ...)` 后直接拼接，破坏JSON结构
- ✅ 正确：用Python完整生成JSON，避免shell拼接

```bash
python3 << PYEOF
import json
constraints = open("$STATUS_MD_CANDIDATE").read()[:300]
payload = {
    "action": "block",
    "message": f"...约束摘要：\n{constraints}"
}
print(json.dumps(payload, ensure_ascii=False))
PYEOF
```

### 方案五：串行模式检查

**目标**：检查前一步是否完成

**关键修正**：
- ❌ 错误：`d.get('steps', {}).get($PREV_STEP, {})` - 整数键
- ✅ 正确：`d.get('steps', {}).get(str($PREV_STEP), {})` - 字符串键

```bash
PREV_STATUS=$(python3 -c "import json; d=json.load(open('$STATUS_JSON')); print(d.get('steps', {}).get(str($PREV_STEP), {}).get('status', 'pending'))")
```

## 审计过程

**第一轮审计**：
1. grep正则错误：`"running\|initialized"` 应为 `-E` + `"(running|initialized)"`
2. heredoc变量不展开：单引号heredoc不展开变量
3. 仅警告不阻断：应改为 `action: block`
4. 方案五进程检测错误：delegate_task不是系统进程

**第二轮审计**：
1. JSON注入破坏：status.md内容含换行/引号，直接拼接破坏JSON
2. 代码不可达：方案一exit后，方案二代码永不执行
3. 键类型问题：JSON键为字符串，$PREV_STEP为整数

## 最终实现

**handler.sh 修改位置**：第14行后

**新增内容**：
1. 会话标记检查（场景1：status.json，场景2：status.md）
2. 串行模式检查（基于status.json步骤状态）

## 测试验证

创建测试工作流 `hook-mechanism-test`，验证：
- ✅ 无标记+status.json → 阻断
- ✅ 无标记+status.md → 阻断+显示约束
- ✅ 初始化后 → 标记文件创建
- ✅ 串行模式 → 状态检查生效

## 教训

1. **初始化不可跳过**：execute.py --init 是必须步骤
2. **JSON安全**：shell变量拼接到JSON时必须用Python json.dumps
3. **逻辑分支**：多个检查应在同一if块内用elif，避免exit后代码不可达
4. **类型匹配**：JSON键始终为字符串，Python访问时需str()转换
