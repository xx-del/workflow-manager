# loader.py None 值陷阱修复（v6.3）

## 问题现象

执行资产收集流程时，工作流加载失败：

```
[ERROR] [WorkflowLoader] 加载失败: argument of type 'NoneType' is not iterable
错误: 工作流未找到: 资产收集流程
```

## 问题定位

### 调试过程

```python
# 直接调用 _build_workflow
wf = loader._build_workflow(index, idx_path.parent)

# 报错位置
File "src/tools/loader.py", line 238, in _build_workflow
    step_warnings = self.validate_step_definitions(steps)
File "src/tools/loader.py", line 100, in validate_step_definitions
    if field not in content:
TypeError: argument of type 'NoneType' is not iterable
```

### 根因分析

**触发条件**：拼接工作流（type: branch）没有 WORKFLOW.md

**数据流**：
```
1. _build_workflow() 初始化 workflow['workflow_md'] = None (第 191 行)
2. WORKFLOW.md 不存在 → workflow_md 保持 None
3. validate_step_definitions() 构建 steps:
   steps = [{'name': ..., 'content': workflow.get('workflow_md', '')} ...]
   → steps[i]['content'] = None
4. validate_step_definitions() 检查:
   content = step.get('content', '')  # ❌ 返回 None 而非 ''
   if field not in content:  # ❌ None 不可迭代
```

**Python 知识点**：
```python
d = {'key': None}
d.get('key', 'default')  # 返回 None，不是 'default'
d.get('key') or 'default'  # 返回 'default'
```

## 修复方案

**修改位置**：`src/tools/loader.py` 第 100 行

**修改前**：
```python
content = step.get('content', '')
```

**修改后**：
```python
content = step.get('content') or ''  # 修复: None 转空字符串
```

## 验证

修复后重新加载工作流：
```bash
python actions/execute.py 资产收集流程 --plan-only --json --date-start 20260512
```

结果：✅ 加载成功，生成 15 个 pending_instructions

## 教训

1. `dict.get('key', default)` 只在 key 不存在时返回 default
2. key 存在但值为 None 时，仍返回 None
3. 涉及字符串操作时，应使用 `value or ''` 确保 None 转空字符串
4. 拼接工作流（type: branch）不需要 WORKFLOW.md，代码应兼容此场景

## 相关文件

- `src/tools/loader.py` - 工作流加载器
- `src/core/executor.py` - 工作流执行器（占位符替换）
- `references/creation-guide.md` - 工作流创建指南（拼接工作流规范）
