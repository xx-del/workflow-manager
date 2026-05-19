# 拼接工作流执行陷阱（2026-05-15）

本文档记录了拼接工作流执行过程中的常见陷阱和解决方案。

---

## 陷阱1：execute.py初始化失败

**现象**：
```
错误: WORKFLOW.md 不存在: /home/kali/.hermes/workflows/资产收集流程
```

**根因**：execute.py未正确处理拼接工作流类型

**正确判断逻辑**（已修复漏洞）：
```python
# ❌ 错误：all([])返回True，导致误判
is_branch = (workflow_type == 'branch' or all(...))

# ✅ 正确：增加nodes非空检查
is_branch = (
    workflow_type == 'branch' and 
    nodes and  # 关键：防止空列表误判
    all(node.get('calls') == 'workflow-manager' for node in nodes)
)
```

---

## 陷阱2：expander未集成到执行流程

**现象**：status.json生成但steps为空，agent-pool无法执行

**根因**：expander.py不存在或未在init_branch_workflow中调用

**正确流程**：
```python
def init_branch_workflow(workflow_name, sub_workflows):
    # 创建会话标记
    session_marker = workflows_dir / f'.active_session_{workflow_name}'
    session_marker.write_text(f"{workflow_name}\n{os.getpid()}")
    
    # ✅ 关键：调用expander展开步骤
    from expander import expand_branch_workflow
    expanded_steps = expand_branch_workflow(workflow_name, sub_workflows)
    
    # 生成status.json（包含完整步骤）
    status = {
        'workflow': workflow_name,
        'type': 'branch',
        'steps': {str(i+1): step for i, step in enumerate(expanded_steps)}
    }
```

---

## 陷阱3：generate_status_md.py无效代码陷阱 ⚠️ 最常见

**现象**：主AI提议创建generate_status_md.py脚本，但实际不需要

**根因**：未检查现有Hook实现，误以为需要新代码

**关键发现**（2026-05-15）：
- handler.sh第16行**已使用JSON解析**标记文件
- handler.sh第158行**已实现**status.md注入（从status.json生成）
- **generate_status_md.py是无效代码**，Hook机制已完整实现

**正确做法**：
1. ✅ 先检查handler.sh现有实现
2. ✅ 验证JSON解析是否已支持
3. ❌ 禁止未检查就提议创建新脚本

---

## 陷阱4：步骤解析简陋

**现象**：status.json中steps仅包含标题，无执行指令

**根因**：步骤解析只提取标题，忽略完整内容

---

## 陷阱5：并发会话标记冲突

**现象**：同时运行多个工作流，后启动的覆盖先启动的标记

**根因**：标记文件共用`.active_session`

**解决方案**：按工作流命名标记文件

---

## 陷阱6：普通工作流功能丢失

**现象**：修改execute.py后，普通工作流初始化失败

**根因**：用简化版本替换整个init_normal_workflow函数

**正确修改方式**：在现有函数内部开头插入代码，不替换整个函数

---

## 陷阱7：方案生成未验证现有机制 ⚠️ 高频错误

**现象**：修复方案提议创建新脚本/新代码，但功能已被现有Hook实现

**根因**：未检查现有Hook实现就假设功能缺失

**正确做法**：
1. 修改前先grep验证现有实现
2. 关注机制层面，不读代码细节
3. 机制已存在 → 只需创建触发条件

---

## 参考文档

- `references/hook-already-implements-status-md-20260515.md` - Hook 已实现 status.md 生成
- `references/branch-workflow-execution-example-20260514.md` - 拼接工作流执行示例
