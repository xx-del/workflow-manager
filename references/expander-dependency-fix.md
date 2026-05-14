# Expander 依赖传递 Bug 修复记录

**修复日期**：2026-05-07
**修复文件**：`src/expander.py`

---

## 问题描述

**症状**：串联工作流展开后，所有子工作流内部步骤被判定为可并行执行

**表现**：
- 配置 `mode: serial`
- 展开后显示：串行步骤=0，并行组=2，最大并发=15
- 子工作流内部步骤的 `depends_on` 全为空数组

---

## 根因分析

### 问题链路

1. **loader.py**：正确读取子工作流 `connections` 字段

2. **expander.py** 第 337 行：
   ```python
   return self.expand(sub_workflow["nodes"], child_context, depth + 1)
   ```
   **只传递 nodes，丢弃 connections！**

3. **executor.py** 第 153 行：
   ```python
   plan = self.analyzer.analyze(expanded_nodes, workflow.get('connections'))
   ```
   传递的是主工作流的 connections，而非展开后节点的

4. **子工作流配置**：
   - connections 为空或不完整
   - 电力数据：7节点，connections 只定义 1→2→3

---

## 修复方案

**文件**：`src/expander.py` `_expand_nested_workflow()` 方法

**修复内容**：

1. 将 connections 转换为节点 depends_on
2. 自动推断串行依赖（mode=serial 且 connections 不完整）

**修复代码**：

```python
# 【修复】将 connections 转换为节点的 depends_on
nodes = sub_workflow["nodes"]
connections = sub_workflow.get("connections", [])

# 【增强】如果 connections 为空或不完整，且 mode 为 serial，自动推断依赖
sub_mode = sub_workflow.get("mode", "serial")
if sub_mode == "serial":
    # 检查 connections 是否覆盖所有节点
    node_ids = [str(n.get("id")) for n in nodes]
    connected_to = set()
    for conn in connections:
        connected_to.add(str(conn.get("to")))
    
    # 如果有节点未被 connections 覆盖，自动推断串行依赖
    unconnected = [nid for nid in node_ids if nid not in connected_to and nid != node_ids[0]]
    
    if unconnected or len(connections) < len(nodes) - 1:
        # 自动生成完整串行依赖：1→2→3→...→n
        for i in range(1, len(nodes)):
            prev_id = str(nodes[i-1].get("id"))
            curr_id = str(nodes[i].get("id"))
            
            if "depends_on" not in nodes[i]:
                nodes[i]["depends_on"] = []
            
            if prev_id not in nodes[i]["depends_on"]:
                nodes[i]["depends_on"].append(prev_id)
else:
    # 非串行模式，只处理显式 connections
    for conn in connections:
        from_id = str(conn.get("from"))
        to_id = str(conn.get("to"))
        
        for n in nodes:
            if str(n.get("id")) == to_id:
                if "depends_on" not in n:
                    n["depends_on"] = []
                if from_id not in n["depends_on"]:
                    n["depends_on"].append(from_id)
```

---

## 验证结果

**修复前**：
- 串行步骤: 0
- 并行组: 2
- 最大并发: 15

**修复后**：
- 串行步骤: 19
- 并行组: 0
- 最大并发: 1

**依赖关系验证**：
```
电力数据内部依赖:
  1: []
  2: ['root_电力数据_1']
  3: ['root_电力数据_2']
  4: ['root_电力数据_3']
  5: ['root_电力数据_4']
  6: ['root_电力数据_5']
  7: ['root_电力数据_6']

跨工作流依赖:
  root_域名处理_1: ['root_电力数据_7']
```

---

## 设计原则

**自动推断优于手动配置**：
- 符合 `mode: serial` 语义
- 减少配置维护负担
- 兼容不完整的 connections 定义

**向后兼容**：
- 显式 connections 优先
- 仅在 serial 模式下自动推断
- 不影响 parallel 模式工作流
