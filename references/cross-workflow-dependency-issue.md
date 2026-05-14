# 跨工作流依赖解析问题分析

**日期**: 2026-05-12
**状态**: 待修复
**优先级**: 高

---

## 问题现象

```
⚠️ 警告: 跨工作流依赖 启动扫描 无法解析
⚠️ 警告: 跨工作流依赖 断点返回（启动心跳监测） 无法解析
⚠️ 警告: 跨工作流依赖 WIH下载（心跳自动执行） 无法解析
...
```

**步骤数量不匹配**：
- 预期：48 步骤（4 个子工作流 × 12 步骤）
- 实际：25 步骤

---

## 根因分析

### 第一层：依赖引用不匹配

**展开后的节点**：
```
root_home漏扫_step_2: 断点返回（启动心跳监测）
  depends_on: ['启动扫描', 'root_home漏扫_step_1']
```

**问题**：
- `'启动扫描'` 是原始名称，未映射到展开后 ID `'root_home漏扫_step_1'`
- expander 的 `_resolve_cross_workflow_dependency` 无法匹配

### 第二层：步骤数量不匹配

**原因**：expander 使用了 _index.yaml 的节点（合并后），而不是 WORKFLOW.md 详细步骤

**影响**：
- 命令缺失：25 个步骤中大部分是"（无命令）"
- 执行失败：无法执行实际操作

### 第三层：心跳驱动工作流的特殊设计

**home漏扫** 的 _index.yaml 将多个 WORKFLOW.md 步骤合并为少量节点：
- 这是设计意图（心跳驱动模式）
- 但展开器不理解这种设计

---

## 影响评估

**是否会阻止执行？**
- ❌ 不会阻止，但会导致执行不完整

**具体影响**：
1. 命令缺失 → 无法执行实际操作
2. 结果丢失 → 工作流执行但不产生预期结果
3. 依赖断裂 → 后续步骤无法正确触发

---

## 修复方案

### 方案 C：分层展开策略

**策略**：
- 检测心跳驱动工作流 → 保留 _index.yaml 结构
- 检测普通工作流 → 展开详细步骤

**实现**：

```python
def _expand_nested_workflow(self, node, context, depth):
    sub_workflow = loader.load(node['task'])
    
    # 检测是否为心跳驱动工作流
    if self._is_heartbeat_workflow(sub_workflow.get('nodes', [])):
        # 心跳驱动：保留 _index.yaml 结构
        return self._expand_heartbeat_workflow(sub_workflow, node, context)
    else:
        # 普通工作流：展开详细步骤
        return self.expand(sub_workflow['nodes'], context, depth + 1)

def _expand_heartbeat_workflow(self, workflow, node, context):
    # 保留 _index.yaml 的节点结构
    # 不展开 WORKFLOW.md 详细步骤
    # 心跳脚本负责执行详细逻辑
    ...
```

**理由**：
1. 心跳驱动工作流的设计意图：_index.yaml 定义高层结构，心跳脚本执行详细步骤
2. 强制展开会破坏心跳机制
3. 符合"职责分离"原则

---

## 待办事项

- [ ] 修复 expander 的分层展开逻辑
- [ ] 更新依赖映射算法
- [ ] 测试验证修复效果
