# loader.py 拼接工作流验证修复

## 问题描述

**现象**：执行通用漏洞扫描工作流时报错：
```
步骤 '凭证检测' 缺少 '做什么' 定义
步骤 '凭证检测' 缺少 '执行指令' 定义
```

**根因**：`loader.py` 第 235-241 行对所有工作流验证步骤定义，未区分拼接节点。

---

## 拼接工作流特征

```yaml
type: branch  # 或
nodes:
  - calls: workflow-manager  # 关键标识
```

**正确行为**：拼接节点只调用子工作流，不应要求"做什么"和"执行指令"。

---

## 修复方案

### 1. 添加拼接节点识别方法

**位置**：`src/tools/loader.py` 第 106 行后

```python
def _is_branch_workflow(self, nodes: List[Dict]) -> bool:
    """
    判断是否为拼接工作流
    
    拼接工作流特征：
    1. 所有节点都有 calls: workflow-manager
    """
    if not nodes:
        return False
    
    for node in nodes:
        if node.get("calls") != "workflow-manager":
            return False
    
    return True
```

### 2. 修改步骤定义验证逻辑

**位置**：`src/tools/loader.py` 第 235 行

**修改前**：
```python
# 3. 验证步骤定义（仅警告）
if workflow.get('nodes'):
    steps = [...]
    step_warnings = self.validate_step_definitions(steps)
```

**修改后**：
```python
# 3. 验证步骤定义（仅警告，拼接工作流跳过）
if workflow.get('nodes'):
    if self._is_branch_workflow(workflow['nodes']):
        self.logger.info(f"拼接工作流 '{workflow['name']}' 跳过步骤定义验证")
    else:
        steps = [...]
        step_warnings = self.validate_step_definitions(steps)
```

---

## 验证方法

```bash
# 测试拼接工作流（应无警告）
python actions/execute.py 通用漏洞扫描 --plan-only --json

# 测试普通工作流（应正常验证）
python actions/execute.py 凭证检测 --plan-only --json
```

---

## 相关文件

- `src/tools/loader.py` - 需修改文件
- `src/expander.py` - 第 66 行已有拼接节点识别逻辑参考
- `SKILL.md` - 第七节明确规定拼接工作流不需要 WORKFLOW.md

---

## 修复记录

- **发现时间**：2026-05-12
- **修复方案**：execution_plan.md
- **状态**：待执行
