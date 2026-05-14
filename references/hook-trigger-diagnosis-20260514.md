# Hook 未触发诊断记录

**日期**：2026-05-14
**工作流**：凭证检测
**症状**：PreToolUse Hook 未自动创建 status.md

---

## 诊断过程

### 1. 确认前置条件

```bash
# 会话标记文件存在
ls -la ~/.hermes/workflows/.active_session
# 输出：-rw-rw-r-- 1 kali kali 136 5月14日 14:25 .active_session

# status.json 存在且状态为 initialized
cat ~/.hermes/workflows/凭证检测/status.json | jq '.status'
# 输出："initialized"

# status.md 不存在
ls -la ~/.hermes/workflows/凭证检测/status.md
# 输出：没有那个文件或目录
```

**结论**：前置条件满足，Hook 应该触发

### 2. 检查 Hook 配置

```bash
head -30 ~/.hermes/skills/openclaw-imports/workflow-manager/SKILL.md
```

**输出**：
```yaml
---
hooks:
  UserPromptSubmit:
    - hooks:
        - type: command
          command: bash hooks/workflow-context/handler.sh
  PreToolUse:
    - matcher: "terminal|delegate_task|write_file|patch"
      hooks:
        - type: command
          command: bash hooks/workflow-step-check/handler.sh
---
```

**结论**：Hook 配置正确，使用 Claude Code 事件名

### 3. 手动触发 Hook

```bash
cd ~/.hermes/skills/openclaw-imports/workflow-manager
bash hooks/workflow-step-check/handler.sh
```

**输出**：
```
json.decoder.JSONDecodeError: Expecting value: line 2 column 1 (char 1)
```

**结论**：handler.sh 执行失败，JSON 解析错误

### 4. 根因分析

**问题**：handler.sh 期望从 stdin 读取 JSON 数据，但手动执行时没有提供输入

**实际根因**：skill-hook-bridge 可能未正确调用 handler.sh，或未注入必要的环境变量

---

## 诊断结论

**Hook 未触发的原因**：
1. skill-hook-bridge 未正确扫描 SKILL.md frontmatter
2. 或 Hook 调用时缺少必要的环境变量（HERMES_TOOL_NAME, HERMES_TOOL_INPUT）

**验证方法**：
- 检查 Hermes 日志是否有 Hook 调用记录
- 检查 skill-hook-bridge 是否正确加载

---

## 降级方案

**当 Hook 未触发时，AI 应手动创建 status.md**：

```markdown
# {工作流名称} 工作流执行计划

**生成时间**: {timestamp}
**工作流名称**: {name}
**工作流类型**: {type}
**执行模式**: {mode}

---

## 一、执行行为约束

**绝对禁止**:
- ❌ 禁止修改 WORKFLOW.md 定义的命令
- ❌ 禁止添加 timeout 参数
- ❌ 禁止跳过步骤
...
```

---

## 修复建议

**P0 优先级**：
1. 验证 skill-hook-bridge 是否正确扫描 SKILL.md
2. 添加 Hook 触发诊断日志
3. 在 handler.sh 添加错误处理和日志输出
