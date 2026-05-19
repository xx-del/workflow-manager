# Hook 标记检查机制优化记录

**日期**：2026-05-16
**问题**：通用漏洞扫描工作流执行时 Hook 未触发，约束未注入，主AI违规

---

## 问题根因

**现象**：
- status.json 已存在
- 但 `.active_session` 标记文件不存在
- Hook 检测到无标记后静默退出
- 约束未注入，主AI自行决定

**原因**：
- 未调用 `execute.py --init` 创建会话标记
- 误认为 status.json 初始化 = 工作流已启动
- 未区分"数据初始化"和"会话初始化"

---

## 优化方案

### 方案一：无标记阻断（修正版）

**修改文件**：`hooks/workflow-step-check/handler.sh`

**逻辑**：
```bash
if [[ ! -f "$MARKER_FILE" ]]; then
    # 检测活跃工作流
    ACTIVE_WORKFLOW=$(find "$WORKFLOW_DIR" -maxdepth 2 -name "status.json" -exec grep -l -E '"status": "(running|initialized)"' {} \; 2>/dev/null | head -1)
    
    if [[ -n "$ACTIVE_WORKFLOW" ]]; then
        # 阻断并提示初始化
        ...
    fi
fi
```

**修正点**：
- `grep -E` 正确匹配 running 或 initialized
- 路径变量加双引号防空格
- `action: block` 强制阻断

---

### 方案二+三：强制注入约束（修正版）

**问题**：
- JSON注入：status.md 内容直接拼接破坏 JSON 结构
- 代码不可达：方案一命中后 exit，方案二代码不执行

**修正**：
```python
# 使用 Python 安全生成完整 JSON
python3 << PYEOF
import json
payload = {
    "action": "block",
    "message": f"..."
}
print(json.dumps(payload, ensure_ascii=False))
PYEOF
```

---

### 方案五：串行模式检查（修正版）

**问题**：`$PREV_STEP` 是整数，但 JSON 键是字符串

**修正**：
```python
# 使用 str($PREV_STEP)
PREV_STATUS=$(python3 -c "import json; d=json.load(open('$STATUS_JSON')); print(d.get('steps', {}).get(str($PREV_STEP), {}).get('status', 'pending'))" 2>/dev/null)
```

---

## 审计方法论

用户采用四维度审计：

| 维度 | 检查项 |
|------|--------|
| 可行性 | 逻辑是否正确、变量是否定义 |
| 副作用 | 是否引入新问题 |
| 覆盖面 | 是否遗漏场景 |
| 可靠性 | 边界情况、错误处理 |

**关键修正点**：
1. grep 基础正则 vs 扩展正则
2. Shell 变量在 heredoc 中的展开规则
3. JSON 字符串拼接的安全问题
4. Python 字典键类型（int vs str）

---

## 最终代码位置

- **handler.sh 第14-55行**：会话标记检查
- **handler.sh 第84-104行**：串行模式检查
- **SKILL.md 第22-43行**：第0步初始化约束

---

## 教训

1. **Hook 依赖标记文件**：无标记 = 无约束 = 主AI违规风险
2. **JSON 安全生成**：禁止 shell 拼接，必须用 json.dumps
3. **用户审计是高质量保障**：多轮审计发现深层问题
