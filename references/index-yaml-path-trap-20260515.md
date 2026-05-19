# _index.yaml 路径陷阱与修复

**日期**：2026-05-15
**状态**：已修复

---

## 问题描述

### 陷阱现象

`generate_status_md` 函数读取 `workflow_dir / '_index.yaml'`（子目录的 _index.yaml），但子目录的 _index.yaml 的 `workflows` 列表为空。

### 实际结构

```
~/.hermes/workflows/
├── _index.yaml           # 主 _index.yaml（包含所有工作流定义）
│   workflows:
│     - name: 资产收集流程
│       nodes: [...]
│     - name: home漏扫
│       nodes: [...]
│
├── 资产收集流程/
│   └── _index.yaml       # 子目录 _index.yaml（workflows 为空）
│       workflows: []
│
└── home漏扫/
    └── _index.yaml       # 子目录 _index.yaml（workflows 为空）
        workflows: []
```

### 错误代码

```python
# 错误：读取子目录的 _index.yaml
index_path = workflow_dir / '_index.yaml'  # workflow_dir = workflows_dir / workflow_name
with open(index_path) as f:
    index_data = yaml.safe_load(f)
workflows = index_data.get('workflows', [])  # 返回空列表
```

### 正确代码

```python
# 正确：读取主 _index.yaml
index_path = workflows_dir / '_index.yaml'  # workflows_dir = Path.home() / '.hermes' / 'workflows'
with open(index_path) as f:
    index_data = yaml.safe_load(f)
workflows = index_data.get('workflows', [])  # 返回所有工作流定义
```

---

## 修复方案

### 修改位置

`actions/execute.py` 的 `generate_status_md` 函数

### 修改内容

```python
# 修改前
index_path = workflow_dir / '_index.yaml'

# 修改后
index_path = workflows_dir / '_index.yaml'
```

---

## 验证方法

```python
import yaml
from pathlib import Path

# 检查子目录 _index.yaml
sub_index = Path.home() / '.hermes/workflows/资产收集流程/_index.yaml'
with open(sub_index) as f:
    data = yaml.safe_load(f)
    print('子目录 workflows 数量:', len(data.get('workflows', [])))  # 输出: 0

# 检查主 _index.yaml
main_index = Path.home() / '.hermes/workflows/_index.yaml'
with open(main_index) as f:
    data = yaml.safe_load(f)
    print('主 workflows 数量:', len(data.get('workflows', [])))  # 输出: 17
```

---

## 教训总结

1. **不要假设子目录有完整数据**：子目录的 _index.yaml 可能只是占位文件
2. **明确数据来源**：工作流定义统一在主 _index.yaml
3. **路径语义**：`workflow_dir` 是子目录，`workflows_dir` 是主目录

---

## 相关参考

- `references/hook-type-identification-consistency-20260515.md` - 类型识别一致性问题
- `references/workflow-type-identification.md` - 类型识别机制
