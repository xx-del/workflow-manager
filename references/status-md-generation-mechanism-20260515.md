# status.md 生成机制分析

**创建时间**: 2026-05-15
**问题**: 拼接工作流execute.py --init后主AI未生成status.md

---

## 问题现象

**症状**：
- execute.py --init成功执行
- status.json正确生成（包含所有合并步骤）
- status.md未生成（仍是旧文件）
- 主AI直接执行工作流任务，跳过生成status.md

**影响**：
- 主AI无法看到完整执行计划
- 无法有效追踪步骤执行状态
- 违反"主AI任务：按顺序读取WORKFLOW.md，合并生成统一status.md"的要求

---

## 根因分析

### 原因1：execute.py返回值缺失

**对比**：

| 工作流类型 | execute.py返回值 | ai_steps字段 |
|------------|------------------|--------------|
| 普通工作流 | 包含ai_steps | ✅ 有 |
| 拼接工作流 | 不包含ai_steps | ❌ 无 |

**代码位置**：execute.py拼接工作流return语句（约第XXX行）

**缺失内容**：
```python
'ai_steps': [
    '1. 读取所有子工作流的WORKFLOW.md',
    '2. 合并所有步骤，生成统一status.md',
    '3. 使用agent-pool执行步骤',
    '4. 更新status.json节点状态'
]
```

---

### 原因2：SKILL.md职责未明确

**现状**：SKILL.md未明确说明主AI必须生成status.md

**问题**：
- 主AI无法从技能文档中获知职责
- 依赖Hook的隐式提示
- 违反"文档即规则"原则

---

### 原因3：Hook提示不够强制

**现状**：Hook输出"主AI任务：按顺序读取上述WORKFLOW.md，合并生成统一status.md"

**问题**：
- 提示在Hook输出中，容易被忽略
- 没有强制约束
- 主AI可能理解为可选

---

## 修复方案

### 方案A：修改execute.py（推荐）

**修改位置**：execute.py拼接工作流return语句

**修改内容**：
```python
return {
    'success': True,
    'workflow': workflow_name,
    'type': 'branch',
    'workflow_dir': str(workflow_dir),
    'status_file': str(status_file),
    'message': '拼接工作流初始化成功',
    'total_steps': len(expanded_steps),
    'sub_workflows': sub_workflows,
    'ai_steps': [  # 新增
        '1. 读取所有子工作流的WORKFLOW.md',
        '2. 合并所有步骤，生成统一status.md',
        '3. 使用agent-pool执行步骤',
        '4. 更新status.json节点状态'
    ]
}
```

---

### 方案B：增强SKILL.md

**修改位置**：workflow-manager/SKILL.md

**新增章节**：
```markdown
## 主AI职责（强制）

**execute.py --init后必须执行**:
1. 读取返回的ai_steps字段
2. 按ai_steps执行，生成status.md
3. 无status.md则禁止执行工作流任务

**status.md生成规则**:
- 拼接工作流：合并所有子工作流WORKFLOW.md
- 普通工作流：读取单个WORKFLOW.md
- 格式：参考planning-with-files的task_plan.md模板
```

---

### 方案C：增强Hook提示（可选）

**修改位置**：workflow-context/handler.sh第114行

**修改内容**：
```bash
echo "📋 主AI任务：按顺序读取上述WORKFLOW.md，合并生成统一status.md"
echo "⚠️  强制要求：无status.md则禁止执行工作流任务"  # 新增
```

---

## 验证方法

修复后验证：
1. 运行execute.py --init
2. 检查返回值包含ai_steps
3. 主AI按ai_steps生成status.md
4. 验证status.md内容正确（包含所有子工作流步骤）

---

## 相关文件

- execute.py: workflow-manager/actions/execute.py
- SKILL.md: workflow-manager/SKILL.md
- handler.sh: workflow-manager/hooks/workflow-context/handler.sh
- planning-with-files: openclaw-imports/planning-with-files/SKILL.md（参考模板）

---

**状态**: 待修复
**优先级**: P0（影响所有拼接工作流执行）
