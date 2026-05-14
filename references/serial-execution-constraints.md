# 拼接工作流串行执行约束

## ⚠️ 最高优先级

**拼接工作流中的子工作流必须串行执行**

这是强制约束，违反即失败。违反后本次执行无效。

---

## 用户纠正记录

**2026-05-13 用户明确要求**：
> "不要并行启动 N U C L IE扫描必须在爆破扫描执行后串行执行"

---

## 核心原则

**拼接工作流 ≠ 并行工作流**

| 工作流类型 | 执行方式 | 说明 |
|------------|----------|------|
| 拼接工作流（type: branch） | 串行执行 | 子工作流存在依赖关系 |
| 并行工作流（mode: parallel） | 并行执行 | 步骤无依赖关系 |
| 串行工作流（mode: serial） | 串行执行 | 步骤有依赖关系 |

---

## 绝对禁止

### ❌ 禁止并行启动存在依赖关系的子工作流

```python
# ❌ 错误：并行启动
execute_subworkflow("爆破测试", background=True)
execute_subworkflow("nuclei扫描")  # 错误！爆破测试未完成

# ✅ 正确：串行执行
execute_subworkflow("爆破测试")
wait_for_completion("爆破测试")
execute_subworkflow("nuclei扫描")
```

### ❌ 禁止跳过依赖检查

```python
# ❌ 错误：不检查依赖
if step.name == "nuclei扫描":
    execute(step)  # 错误！未检查爆破测试是否完成

# ✅ 正确：检查依赖
if step.name == "nuclei扫描":
    if get_status("爆破测试") != "completed":
        return "等待爆破测试完成"
    execute(step)
```

---

## 执行模式规范

### 拼接工作流执行流程

```
1. 识别拼接工作流（type: branch）
     ↓
2. 获取子工作流列表
     ↓
3. 按顺序执行子工作流
     ↓
4. 等待当前子工作流完成
     ↓
5. 执行下一个子工作流
     ↓
6. 所有子工作流完成 → 工作流完成
```

### 依赖检查代码

```python
def execute_composite_workflow(workflow_name):
    """执行拼接工作流（串行）"""
    
    # 获取子工作流列表
    sub_workflows = get_sub_workflows(workflow_name)
    
    # 串行执行
    for i, sub_wf in enumerate(sub_workflows):
        print(f"[{i+1}/{len(sub_workflows)}] 执行: {sub_wf.name}")
        
        # 执行子工作流
        result = execute_subworkflow(sub_wf.name)
        
        # 等待完成
        while get_status(sub_wf.name) != "completed":
            time.sleep(30)
            print(f"等待 {sub_wf.name} 完成...")
        
        print(f"✅ {sub_wf.name} 完成")
    
    print("✅ 拼接工作流完成")
```

---

## 验证清单

执行拼接工作流前必须确认：

- [ ] 是否识别为拼接工作流？（type: branch）
- [ ] 是否获取了子工作流列表？
- [ ] 是否按顺序串行执行？
- [ ] 是否等待当前子工作流完成后再执行下一个？
- [ ] 是否所有子工作流都完成？

---

## 违规后果

| 违规行为 | 后果 | 处理方式 |
|----------|------|----------|
| 并行启动串行工作流 | 执行顺序错误 | 停止工作流，重新执行 |
| 未等待依赖完成 | 结果无效 | 回滚执行，等待依赖 |
| 跳过子工作流 | 结果不完整 | 补充执行缺失步骤 |

---

## 相关文档

- `references/terminal-execution-constraints.md` - terminal 执行约束
- `references/guardian.md` - 守护机制
- SKILL.md 第九章 - 拼接工作流串行执行约束
