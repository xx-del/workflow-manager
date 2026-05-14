# 工作流一致性规范

## 核心约束

WORKFLOW.md 和 _index.yaml 必须保持一致。

## 具体规则

### 规则1：步骤名称一致

WORKFLOW.md:
```
### 步骤 1: 准备阶段
### 步骤 2: 下载数据
### 步骤 3: 分析处理
```

_index.yaml:
```yaml
nodes:
  - id: 1
    name: 准备阶段    # 必须完全一致
  - id: 2
    name: 下载数据    # 必须完全一致
  - id: 3
    name: 分析处理    # 必须完全一致
```

### 规则2：步骤数量一致

- WORKFLOW.md 有 N 个步骤 → _index.yaml 必须有 N 个节点
- 不允许一个节点对应多个步骤

### 规则3：步骤顺序一致

- WORKFLOW.md 步骤1 → _index.yaml nodes[0]
- WORKFLOW.md 步骤2 → _index.yaml nodes[1]
- 顺序必须一一对应

## 验证方法

```bash
cd ~/.hermes/skills/openclaw-imports/workflow-manager
python actions/validate.py {工作流名称} --check-consistency
```

## 不一致时的处理

由 AI 修改文档文件，使其符合规范。

优先修改 _index.yaml，保持 WORKFLOW.md 不变（因为 WORKFLOW.md 包含执行指令，修改风险更大）。
