# Hook 标记文件陷阱（2026-05-16）

## 问题发现

执行通用漏洞扫描工作流时，Hook 全部失效，导致主AI违规执行。

## 根本原因

**Hook 触发条件**：
```bash
# handler.sh 第 11-14 行
MARKER_FILE="$WORKFLOW_DIR/.active_session"
if [[ ! -f "$MARKER_FILE" ]]; then
    exit 0  # 非工作流会话，静默退出
fi
```

**问题**：
- 标记文件 `.active_session` 不存在
- Hook 检测不到标记，静默退出
- 约束未注入，主AI无强制约束

## 触发场景

**错误流程**：
```
读取已存在的 status.json  →  直接执行步骤  →  无标记文件  →  Hook 失效
```

**正确流程**：
```
execute.py --init  →  创建标记文件  →  Hook 检测到标记  →  注入约束  →  执行步骤
```

## 后果

Hook 失效后，主AI可能违规：
1. 直接使用 terminal 执行步骤（应使用 agent-pool）
2. 并行执行工作流（应串行执行）
3. 不更新 status.json 状态
4. 自行决定跳过步骤

## 解决方案

**执行前检查**：
```bash
# 检查标记文件是否存在
ls -la ~/.hermes/workflows/.active_session

# 不存在则初始化
python actions/execute.py <工作流名称> --init
```

**标记文件内容**：
```json
{
  "workflow_name": "通用漏洞扫描",
  "session_id": "xxx",
  "created_at": "2026-05-16T09:44:36"
}
```

## 改进建议

1. **Hook 警告模式**：检测到 status.json 存在但无标记时，输出警告而非静默退出
2. **status.md 自检清单**：添加"标记文件检查"项
3. **SKILL.md 明确**：`execute.py --init` 是必须步骤

## 相关文件

- Hook 配置：`hooks/workflow-context/HOOK.yaml`
- Hook 处理器：`hooks/workflow-context/handler.sh`
- 标记文件：`~/.hermes/workflows/.active_session`
