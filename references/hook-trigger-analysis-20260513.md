# Hook 触发机制分析

## 问题

Hook 未自动触发，需要手动执行

## 根本原因

**Hermes 配置错误**：

```yaml
hooks: {}
hooks_auto_accept: false
```

**问题**：
1. `hooks: {}` - 空配置，未注册任何 Hook
2. `hooks_auto_accept: false` - 未启用自动接受

---

## 机制分析

### 预期流程

```
Hermes 启动 → 读取 config.yaml → 加载 hooks 配置 → 注册 Hook → pre_llm_call 触发 → 执行 handler.sh
```

### 实际流程

```
Hermes 启动 → hooks: {} → 未注册 Hook → pre_llm_call 无监听 → Hook 未触发
```

### 为什么符号链接存在但未生效？

- 符号链接只是文件映射
- Hermes 需要读取 config.yaml 中的 hooks 配置
- `hooks: {}` 意味着没有注册任何 Hook
- 即使符号链接存在，也不会执行

---

## 解决方案

### 方案 A：修复 Hook 配置（推荐）

**修改 config.yaml**：

```yaml
hooks:
  workflow-ai-remind:
    event: pre_llm_call
    command: ~/.hermes/agent-hooks/workflow-ai-remind.sh
    enabled: true

hooks_auto_accept: true
```

**优点**：
- Hook 自动触发
- 无需 AI 手动执行

**缺点**：
- 需要修改 Hermes 配置
- 需要重启 Gateway

---

### 方案 B：保持手动触发（当前方案）

**SKILL.md 指导**：

```markdown
**步骤2：注入约束**
```bash
# 手动触发 Hook（如未自动触发）
bash hooks/workflow-ai-remind/handler.sh "/完整路径"
```

**优点**：
- 无需修改 Hermes 配置
- 明确的执行流程

**缺点**：
- 依赖 AI 记住手动触发
- 容易遗忘

---

## 判断

**当前方案**：设计妥协，非最佳实践

**原因**：
- Hook 自动触发机制未正确配置
- 通过 SKILL.md 指导 AI 手动执行
- 可用但非最优

---

## 建议

**短期**：保持手动触发，通过 SKILL.md 明确指导

**长期**：修复 config.yaml，启用 Hook 自动触发

---

## 验证方法

**检查 Hook 配置**：

```bash
grep -A 5 "^hooks:" ~/.hermes/config.yaml
```

**预期结果**：

```yaml
hooks:
  workflow-ai-remind:
    event: pre_llm_call
    command: ~/.hermes/agent-hooks/workflow-ai-remind.sh
    enabled: true
```

**检查符号链接**：

```bash
ls -la ~/.hermes/agent-hooks/workflow-ai-remind.sh
```

**预期结果**：符号链接存在且指向正确路径
