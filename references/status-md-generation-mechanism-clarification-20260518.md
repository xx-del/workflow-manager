# status.md 生成机制澄清

**日期**: 2026-05-18

---

## 最初设计（架构文档 v6.4）

**职责划分**：

| 层级 | 职责 | 执行者 |
|------|------|--------|
| **代码静态层** | 生成空 status.json | execute.py --init |
| **AI动态层** | 读取 WORKFLOW.md，分解任务，**生成 status.md** | AI |
| **AI动态层** | 执行步骤，更新状态 | AI |

**execute.py 返回的 ai_steps**：
```
1. 读取 WORKFLOW.md
2. 分解任务，生成 status.md  ← 期望 AI 生成
3. 调用 agent_pool_client.execute()
4. 执行 pending_instructions
5. 更新 status.json 节点状态
```

---

## 现阶段实现

**实际流程**：

```
execute.py --init → status.json（空模板）
    ↓
PreToolUse Hook 检测
    ↓
status.json 存在但 status.md 不存在
    ↓
Hook 自动创建 status.md（注入约束）
    ↓
AI 看到 status.md 前 30 行（约束）
```

**关键代码**（PreToolUse Hook 第 123 行）：
```bash
# 如果是初始化状态且 status.md 不存在，自动创建
if [[ "$status" == "initialized" ]] && [[ ! -f "$STATUS_MD" ]]; then
    # 创建 status.md 并注入完整约束（约 300 行）
    cat > "$STATUS_MD" << EOF
    # ... 约束内容 ...
EOF
fi
```

---

## 问题

1. PreToolUse Hook 自动生成 status.md，**覆盖了 AI 生成的设计**
2. 前 30 行只包含约束，不包含执行指令
3. 违背了最初的设计原则（AI 动态生成）

---

## 拼接工作流 vs 叶子工作流

| 工作流类型 | status.md 生成者 | 是否正常 |
|------------|------------------|----------|
| 拼接工作流 | execute.py --init（第 514 行） | ✅ 会生成 |
| 叶子工作流 | PreToolUse Hook（第 123 行） | ⚠️ Hook 生成，不是 AI |

**拼接工作流**：execute.py 展开子工作流后生成整合的 status.md（包含所有步骤），主 AI 读取并执行这个统一的 status.md。

**叶子工作流**：如果是拼接工作流的子工作流，不需要单独的 status.md（步骤已整合到父工作流）。

---

## 状态追踪方案对比

### 方案 A：status.json + status.md（现阶段）

- status.json：机器可读的状态数据
- status.md：人类可读的执行计划
- **问题**：双文件维护，可能不一致

### 方案 B：只用 status.md（参考 planning-with-files）

- status.md：既是执行计划，也是状态追踪
- 状态直接记录在 Markdown 中（如 `**Status:** in_progress`）
- **优点**：单文件，无一致性问题；AI 直接更新 status.md

**推荐方案 B**：参考 planning-with-files 的成功设计。
