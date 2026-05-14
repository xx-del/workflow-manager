# 工作流验证常见问题

**文档版本**: 2026-05-12
**来源**: 工作流有效性验证分析

---

## 一、依赖引用错误

### 问题概述

**发现数量**: 31 个
**严重程度**: 高（导致串行执行失败）
**影响工作流**: 6 个

---

### 根本原因

_index.yaml 和 WORKFLOW.md 步骤命名不一致：

| 文件 | 格式 | 示例 |
|------|------|------|
| _index.yaml | 简写格式 | `step_1`、`1` |
| WORKFLOW.md | 完整格式 | `步骤 1: 端口扫描` |

---

### 错误案例

**案例 1：月报生成**

_index.yaml:
```yaml
nodes:
  - name: step_2
    depends_on: step_1  # ❌ 错误：引用不存在的步骤
```

WORKFLOW.md:
```markdown
### 步骤 1: 参数解析
### 步骤 2: 数据库更新
```

**问题**: `depends_on: step_1` 引用的步骤名称不存在，实际名称是 "步骤 1: 参数解析"

---

**案例 2：nuclei扫描**

_index.yaml:
```yaml
nodes:
  - name: 2
    depends_on: 1  # ❌ 错误：数字格式
```

WORKFLOW.md:
```markdown
### 步骤 1: 准备URL列表
### 步骤 2: 执行nuclei扫描
```

**问题**: `depends_on: 1` 引用的步骤名称不存在

---

### 修复方案

**方案 A：修改 _index.yaml（推荐）**

使用完整步骤名称：
```yaml
nodes:
  - name: 步骤 2: 数据库更新
    depends_on: 步骤 1: 参数解析
```

**方案 B：修改 loader.py**

支持模糊匹配：
```python
def find_step_by_partial_name(nodes, partial_name):
    """通过部分名称查找步骤"""
    for node in nodes:
        if partial_name in node['name']:
            return node
    return None
```

---

## 二、步骤定义不完整

### 问题概述

**发现数量**: 51 个
**严重程度**: 中（影响AI理解）
**影响工作流**: 9 个

---

### 错误案例

**案例 1：缺少"做什么"说明**

```markdown
### 步骤 1: 端口扫描

**执行指令**:
```bash
nmap -sV target
```

❌ 问题：缺少"做什么"说明，AI无法理解步骤意图
```

---

**案例 2：缺少"执行指令"**

```markdown
### 步骤 2: 服务识别

**做什么**: 识别服务版本

❌ 问题：缺少"执行指令"，无法生成可执行命令
```

---

**案例 3：执行指令为空**

```markdown
### 步骤 3: 漏洞检测

**做什么**: 检测已知漏洞
**执行指令**:
```bash
# TODO: 待实现
```

❌ 问题：执行指令只有注释，实际为空
```

---

### 修复方案

补充完整的步骤定义：

```markdown
### 步骤 1: 端口扫描

**做什么**: 使用nmap扫描目标端口，识别开放端口和服务

**执行指令**:
```bash
nmap -sV -p- --min-rate 1000 target
```

**输入**: target（目标IP或域名）
**输出**: 开放端口列表、服务信息
**状态**: ⏳ 待执行
```

---

## 三、工作流定义不完整

### 问题概述

**发现数量**: 2 个
**严重程度**: 中
**影响工作流**: 机制测试v2、guardian-test

---

### 错误案例

WORKFLOW.md 缺少必要章节：

```markdown
# 工作流：机制测试v2

❌ 缺少"## 目标"章节
❌ 缺少"## 执行步骤"章节
```

---

### 修复方案

补充完整的工作流定义：

```markdown
# 工作流：机制测试v2

## 目标

测试工作流核心机制的完整功能

## 前置条件

- workflow-manager 已安装

## 执行步骤

### 步骤 1: ...

## 约束清单

- [ ] 严格按步骤顺序执行
```

---

## 四、验证方法论

### 静态验证（不执行）

1. **文件完整性验证**
   - WORKFLOW.md 存在
   - _index.yaml 存在
   - 包含必要章节

2. **步骤定义验证**
   - 每个步骤有名称
   - 每个步骤有"做什么"
   - 每个步骤有"执行指令"

3. **依赖关系验证**
   - depends_on 引用的步骤存在
   - 无循环依赖
   - 拓扑排序成功

---

### 动态验证（模拟执行）

1. **执行计划生成**
   ```bash
   python execute.py <workflow> --plan-only
   ```

2. **Agent 匹配验证**
   - 每个步骤能匹配到合适的 Agent
   - Agent 能力满足步骤需求

3. **钩子机制验证**
   - UserPromptSubmit 钩子正常
   - PreToolUse 钩子正常
   - PostToolUse 钩子正常

---

## 五、诊断工具

### 快速诊断脚本

```bash
# 检查工作流定义完整性
python -c "
import sys
sys.path.insert(0, '~/.hermes/skills/openclaw-imports/workflow-manager/src')
from tools.loader import loader

wf = loader.load('workflow-name')
print(f'步骤数: {len(wf[\"nodes\"])}')
"

# 检查执行计划生成
python execute.py workflow-name --plan-only --json

# 检查循环依赖
python execute.py workflow-name --dry-run
```

---

## 六、统计数据（2026-05-12）

| 指标 | 数量 |
|------|------|
| 总工作流数 | 18 |
| 完整工作流 | 7 |
| 部分完整 | 11 |
| 依赖引用错误 | 31 |
| 步骤定义不完整 | 51 |
| 工作流定义不完整 | 2 |

---

## 七、修复优先级

### 高优先级

1. **依赖引用验证**（loader.py）
   - 影响：串行执行失败
   - 工作量：中等
   - 收益：高

2. **统一步骤命名格式**
   - 影响：31 个错误
   - 工作量：低（修改 _index.yaml）
   - 收益：高

---

### 中优先级

3. **步骤定义完整性验证**（loader.py）
   - 影响：AI 理解偏差
   - 工作量：中等
   - 收益：中

4. **补充缺失的步骤定义**
   - 影响：51 个问题
   - 工作量：高
   - 收益：中

---

### 低优先级

5. **补充工作流定义**
   - 影响：2 个工作流
   - 工作量：低
   - 收益：低

---

## 八、参考资料

- workflow-manager SKILL.md
- references/creation-guide.md
- 工作流有效性验证分析报告（2026-05-12）
