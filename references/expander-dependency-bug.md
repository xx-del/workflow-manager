# Expander 依赖丢失 Bug

**发现日期**: 2026-05-07

**严重程度**: 🔴 严重

---

## 问题现象

工作流配置 `mode: serial`，但执行结果显示：
- 串行步骤: 0
- 并行组: 2
- 最大并发: 15

所有子工作流内部步骤被判定为 Level 0（可并行执行）。

---

## 根因分析

### 1. 子工作流定义方式

子工作流使用 `connections` 字段定义依赖，而非节点自身的 `depends_on`：

```yaml
# 电力数据/_index.yaml
connections:
- from: 1
  to: 2
- from: 2
  to: 3
```

节点定义中**没有** `depends_on` 字段。

### 2. Expander 忽略 connections

`expander.py` 第 76 行只读取节点的 `depends_on` 字段：

```python
deps = node.get('depends_on', [])  # 忽略了 connections！
```

导致展开后所有节点的 `depends_on` 为空数组。

### 3. 实际展开结果

```python
# 展开后节点
[root_电力数据_1] 解析日期范围 - depends_on: []  # ← 应该依赖前一步
[root_电力数据_2] 备份并清理 - depends_on: []    # ← 应该依赖 _1
[root_电力数据_3] 批量下载JSON - depends_on: []  # ← 应该依赖 _2
...
```

### 4. 跨工作流依赖错误

```python
[root_域名处理_1] 读取域名列表 - depends_on: ['root_电力数据_1']  # ← 错误：依赖第一步
```

应该依赖 `root_电力数据_7`（电力数据的最后一步），而不是第一步。

---

## 修复方案

### 方案 1：在 expander.py 中处理 connections

修改 `_expand_nested_workflow` 方法：

```python
def _expand_nested_workflow(self, node, parent_context, depth):
    # 加载子工作流
    sub_workflow = loader.load(node['name'])
    
    # 新增：将 connections 转换为节点的 depends_on
    for conn in sub_workflow.get('connections', []):
        from_id = str(conn['from'])
        to_id = str(conn['to'])
        
        # 找到目标节点，添加依赖
        for sub_node in sub_workflow['nodes']:
            if str(sub_node['id']) == to_id:
                if 'depends_on' not in sub_node:
                    sub_node['depends_on'] = []
                sub_node['depends_on'].append(from_id)
    
    # 继续展开
    return self.expand(sub_workflow['nodes'], new_context, depth + 1)
```

### 方案 2：在子工作流定义中直接使用 depends_on

修改所有子工作流定义，在节点中直接添加 `depends_on`：

```yaml
nodes:
- id: 1
  name: 解析日期范围
  depends_on: []  # 新增
- id: 2
  name: 备份并清理
  depends_on: [1]  # 新增
- id: 3
  name: 批量下载JSON
  depends_on: [2]  # 新增
```

---

## 验证方法

```bash
cd ~/.hermes/skills/openclaw-imports/workflow-manager/src
python3 -c "
from tools.loader import loader
from expander import workflow_expander

workflow = loader.load('资产收集流程')
expanded = workflow_expander.expand(workflow['nodes'], {})

print('展开后节点:')
for node in expanded:
    print(f\"  [{node['id']}] {node['name']} - depends_on: {node.get('depends_on', [])}\")
"
```

预期结果：
- 子工作流内部步骤有正确的 `depends_on`
- 跨工作流依赖指向最后一步

---

## 影响范围

所有使用 `connections` 字段定义依赖的子工作流：
- 电力数据
- 域名处理
- 端口扫描
- URL生成
- URL分析

---

## 临时解决方案

在修复 expander 前，手动在子工作流节点中添加 `depends_on` 字段。
