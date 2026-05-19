# 拼接工作流编排机制缺失分析

**发现时间**：2026-05-14
**分析场景**：资产收集流程（type: branch）执行分析

---

## 核心发现

拼接工作流（type: branch）缺少自动编排机制，依赖主AI手动执行子工作流。

---

## 一、Hook不会合并子工作流WORKFLOW.md

**验证路径**：
- loader.py 393-395行：`if wf_type == 'branch': pass`
- 拼接工作流目录下没有WORKFLOW.md（如资产收集流程）
- status.md只显示子工作流名称，无执行命令

**结论**：Hook只生成一个status.md（拼接工作流层面），不合并子工作流文档。

---

## 二、计划文档逐个创建

**执行流程**：
```
execute.py 资产收集流程 --init
→ 创建 status.json（空节点）
→ 创建 status.md（显示5个子工作流）
→ 主AI读取 → 检测到"电力数据"
→ execute.py 电力数据 --init
→ 电力数据/status.md 独立生成
```

**分布**：
- 父工作流/status.md（目录索引）
- 子工作流1/status.md（独立计划）
- 子工作流2/status.md（独立计划）
- ...

---

## 三、缺少自动编排器

**缺失内容**：

| 功能 | 当前状态 | 应有状态 |
|------|---------|---------|
| 自动执行子工作流 | 无，依赖主AI | 自动检测并逐个调用 |
| 进度追踪 | 分散在多个status.md | 统一视图 |
| 完成验证 | 主AI判断 | 自动验证所有叶节点=completed |
| 失败处理 | 停止上报 | 自动重试/跳过（可配置） |

**约束现状**：
- status.md 127-129行明确主AI职责："主 AI 在执行子工作流前更新状态为 running"
- 但没有代码强制执行
- 如果主AI只执行第一个子工作流就停止，其他不会执行

---

## 四、根本原因

1. workflow-manager设计假设主AI按步骤执行
2. "串行执行"约束写在status.md，无代码强制
3. Hook只负责约束注入，不负责执行调度

---

## 五、推荐方案

**方案A：创建拼接工作流执行器（Orchestrator）**
```python
class BranchWorkflowOrchestrator:
    def execute_branch_workflow(self, workflow_name):
        # 加载拼接工作流
        # 逐个执行子工作流
        # 验证完成状态
        # 返回统一进度视图
```

**方案B：增强Hook**
- 检测拼接工作流
- 注入"自动执行下个步骤"逻辑
- 自动追踪所有子工作流状态

**方案C：统一进度视图**
- 创建 `progress.json` 聚合所有子工作流状态
- 提供单一查询接口

---

## 六、相关文件

- loader.py:393-395（branch类型处理）
- expander.py:306-384（嵌套节点展开，但拼接工作流不触发）
- status.md生成逻辑（execute.py + Hook）