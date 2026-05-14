# 工作流定义不一致问题

**日期**：2026-05-14
**工作流**：凭证检测
**问题**：_index.yaml 定义 3 个节点，WORKFLOW.md 定义 12 个步骤

---

## 问题详情

### _index.yaml 定义

```yaml
nodes:
- id: 1
  name: 环境准备
  calls: agent-pool
  depends_on: []
  
- id: 2
  name: 执行检测
  calls: agent-pool
  depends_on: []
  
- id: 3
  name: 结果处理
  calls: agent-pool
  depends_on: []
```

**节点数**：3 个

### WORKFLOW.md 定义

```markdown
### 步骤 1: 验证输入文件
### 步骤 2: 检查工作目录
### 步骤 3: 检查Node.js依赖
### 步骤 4: 安装npm依赖
### 步骤 5: 安装Playwright浏览器
### 步骤 6: 复制URL文件
### 步骤 7: 验证input.txt
### 步骤 8: 执行凭证检测
### 步骤 9: 检查检测结果文件
### 步骤 10: 提取有效凭证
### 步骤 11: 统计检测结果
### 步骤 12: 记录执行历史
```

**步骤数**：12 个

---

## 架构设计原理

### _index.yaml 的作用

**定位**：工作流的结构定义（骨架）

**内容**：
- 节点列表（nodes）
- 节点依赖关系（depends_on）
- 节点调用方式（calls: agent-pool）
- 执行模式（mode: serial）

**读取者**：workflow-manager 代码（loader.py, executor.py）

### WORKFLOW.md 的作用

**定位**：详细执行指南（血肉）

**内容**：
- 每个步骤的具体命令
- 输入输出文件路径
- 执行指令
- 验证清单

**读取者**：AI agent（理解执行细节）

### 关系

```
_index.yaml（结构）
    ↓ 决定
节点数量、依赖关系、调用方式
    ↓
AI 读取 WORKFLOW.md
    ↓ 映射
节点 → 步骤集合
    ↓
执行每个步骤
```

---

## 映射规则

### 规则1：按功能分组

**节点1: 环境准备** → 步骤1-7
- 步骤1: 验证输入文件
- 步骤2: 检查工作目录
- 步骤3: 检查Node.js依赖
- 步骤4: 安装npm依赖
- 步骤5: 安装Playwright浏览器
- 步骤6: 复制URL文件
- 步骤7: 验证input.txt

**节点2: 执行检测** → 步骤8
- 步骤8: 执行凭证检测

**节点3: 结果处理** → 步骤9-12
- 步骤9: 检查检测结果文件
- 步骤10: 提取有效凭证
- 步骤11: 统计检测结果
- 步骤12: 记录执行历史

### 规则2：在 _index.yaml 添加映射注释

**推荐做法**：

```yaml
nodes:
- id: 1
  name: 环境准备
  calls: agent-pool
  depends_on: []
  # 映射到 WORKFLOW.md 步骤1-7
  
- id: 2
  name: 执行检测
  calls: agent-pool
  depends_on: []
  # 映射到 WORKFLOW.md 步骤8
  
- id: 3
  name: 结果处理
  calls: agent-pool
  depends_on: []
  # 映射到 WORKFLOW.md 步骤9-12
```

---

## AI 执行策略

### 策略1：先读 _index.yaml，再读 WORKFLOW.md

```python
# 1. 读取 _index.yaml
nodes = load_index_yaml()

# 2. 对每个节点
for node in nodes:
    # 3. 读取 WORKFLOW.md
    steps = read_workflow_md()
    
    # 4. 映射节点到步骤
    node_steps = map_node_to_steps(node, steps)
    
    # 5. 执行步骤
    for step in node_steps:
        execute_step(step)
```

### 策略2：使用 delegate_task 执行节点

```python
delegate_task(
    goal=f"执行工作流节点{node_id}: {node_name}（步骤{start}-{end}）",
    context={
        "工作目录": "...",
        "步骤定义": "从 WORKFLOW.md 提取"
    },
    role="leaf",
    toolsets=["terminal"]
)
```

---

## 验证标准

**定义一致性标准**：
- ✅ 每个节点都有对应的步骤集合
- ✅ 步骤不遗漏、不重复
- ✅ 映射关系明确（注释或文档）

**执行一致性标准**：
- ✅ 按节点顺序执行
- ✅ 每个节点的所有步骤都执行
- ✅ 步骤执行结果符合预期

---

## 相关文档

- `references/workflow-type-expansion-strategy.md`：工作流展开策略
- `references/loader-workflow-md-override-fix-20260512.md`：WORKFLOW.md 加载修复
