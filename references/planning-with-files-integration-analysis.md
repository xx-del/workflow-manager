# Planning-with-Files 机制融合分析

> 本文档记录 workflow-manager 与 planning-with-files 技能的融合决策分析。

## 分析日期

2026-05-11

## 背景

planning-with-files 是 Manus（被 Meta 以 $2B 收购）的核心技术，通过钩子机制实现注意力操控。

## 核心机制对比

### planning-with-files 三大机制

| 机制 | 实现方式 | 效果 |
|------|----------|------|
| **注意力操控** | PreToolUse 钩子注入 task_plan.md | 目标自动出现在注意力窗口 |
| **状态持久化** | task_plan.md + findings.md + progress.md | 不受上下文限制 |
| **错误追踪** | 3-Strike 协议 + 错误日志表格 | 防止重复错误 |

### workflow-manager 现状

| 维度 | 现状 | 差距 |
|------|------|------|
| 注意力操控 | ❌ 无钩子机制 | 依赖AI自觉 |
| 状态持久化 | status.json（机器可读） | AI不友好 |
| 会话恢复 | 守护Agent + 心跳 | 无法处理 /clear 场景 |

## 关键洞察

**planning-with-files 本质**：
> 把目标写入文件，通过钩子**强制注入注意力窗口**

**workflow-manager 现状**：
> 定义了严格的流程，但**依赖AI自觉遵守**

**融合核心**：
> 用钩子机制把"自觉遵守"变成"强制注入"

## 融合决策

### 方案对比

| 方案 | 说明 | 问题 |
|------|------|------|
| **A. 组合使用** | 执行工作流时同时加载两个技能 | 钩子冲突、约束矛盾、状态冗余 |
| **B. 融合** ⭐ | 将机制融入 workflow-manager | 单一约束体系、性能优化 |

### 决策：方案B（融合）

**核心理由**：
1. 工作流执行不需要"规划能力"，只需要"执行能力"
2. 避免两套约束体系冲突
3. 单次钩子注入，减少上下文消耗
4. 一套状态文件，易于维护

### 技能定位分离

| 场景 | 使用技能 |
|------|----------|
| 执行预定义工作流 | workflow-manager（融合后） |
| 研究性任务（无预设流程） | planning-with-files |
| 复杂开发任务 | planning-with-files |
| 快速原型探索 | planning-with-files |

## 融合实施路径

### Phase 1: 钩子机制（核心）

```yaml
# workflow-manager SKILL.md 添加 hooks 配置

hooks:
  UserPromptSubmit:
    - hooks:
        - type: command
          command: |
            # 检测运行中的工作流，显示进度摘要
            
  PreToolUse:
    - matcher: "terminal|delegate_task"
      hooks:
        - type: command
          command: |
            # 注入当前步骤 + 约束清单
            # 来源：status.md（AI可读）
```

### Phase 2: 状态文件优化

```
现状：status.json（机器可读）
改进：status.md（AI可读）

内容：
- 当前进度
- 约束清单
- 错误日志
```

### Phase 3: 会话恢复

```bash
# UserPromptSubmit 时检测未完成工作流
workflow-recover.py
```

## 钩子机制实现示例

```yaml
# PreToolUse 钩子示例

PreToolUse:
  - matcher: "terminal|delegate_task"
    hooks:
      - type: command
        command: |
          STATUS_FILE=$(find ~/.hermes/workflows -name "status.json" -exec grep -l '"status": "running"' {} \; 2>/dev/null | head -1)
          if [ -n "$STATUS_FILE" ]; then
            echo "[workflow-manager] 当前步骤约束："
            python3 -c "
import json
d = json.load(open('$STATUS_FILE'))
print(f'步骤: {d[\"workflow\"][\"current_step\"]}')
print(f'进度: {d[\"workflow\"][\"step_progress\"]}')
print('约束: 严格按WORKFLOW.md执行，禁止修改命令/添加参数/添加步骤')
"
          fi
```

## 预期收益

| 改进项 | 效果 |
|--------|------|
| 注意力操控 | 解决长会话后偏离目标问题 |
| 约束强制执行 | AI 无法"忘记"约束 |
| 状态可见性 | AI 可直接理解当前状态 |
| 会话恢复 | /clear 后可恢复进度 |

## 参考资料

- planning-with-files 技能：`~/.hermes/skills/openclaw-imports/planning-with-files/`
- Manus Context Engineering：https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
- Lance Martin 分析：Multi-agent context engineering strategies
