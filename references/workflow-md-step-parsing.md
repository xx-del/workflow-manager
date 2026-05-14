# WORKFLOW.md 步骤解析机制

## 设计原则

**核心理念**：
- _index.yaml 只是索引，不是具体步骤
- WORKFLOW.md 才是步骤、流程、规范的来源
- 即使 _index.yaml 有节点，也必须读取 WORKFLOW.md

## 标准格式

WORKFLOW.md 步骤必须符合以下格式：

```markdown
### 步骤 N: 步骤名称

**做什么**: 步骤描述

**执行指令**:
```bash
具体命令
```

**输入**: 输入说明

**输出**: 输出说明

**Agent要求**: CLI执行/浏览器/其他
```

## 解析机制

**loader.parse_workflow_steps() 方法**：

```python
def parse_workflow_steps(self, workflow_md_content: str) -> List[Dict]:
    """
    从 WORKFLOW.md 解析步骤
    
    正则匹配：
    - 步骤编号：### 步骤 (\d+):
    - 步骤名称：第二行
    - 执行命令：```bash 代码块
    - 输入输出：**输入**: / **输出**: 字段
    """
```

**自动替换规则**：
- 如果 _index.yaml 节点为空，使用 WORKFLOW.md 步骤
- 如果 _index.yaml 节点是占位符（有 task 无 command），使用 WORKFLOW.md 步骤

## 验证结果

| 工作流 | 原始节点 | 解析步骤 | 结果 |
|--------|----------|----------|------|
| 凭证检测 | 3 | 12 | ✅ 自动展开 |
| 资产收集流程 | 5 | 15 | ✅ 拼接展开 |
| 通用漏洞扫描 | 4 | 48 | ✅ 拼接展开 |

## 注意事项

1. **格式严格要求**：必须使用 `### 步骤 N:` 格式
2. **bash 代码块**：命令必须在 ` ```bash ` 代码块内
3. **占位符识别**：`calls: agent-pool` + 无 command = 占位符
