# Workflow-Manager 架构重构记录

**日期**：2026-05-13
**版本**：v6.4.0
**触发**：用户发现工作流执行完全绕过了 Hook/计划/agent-pool 机制

---

## 问题诊断

### 执行机制缺失（5项全未执行）

| 机制 | 状态 | 原因 |
|------|------|------|
| Hook 功能 | ❌ | 未通过 execute.py 注册活动工作流 |
| 计划文件生成 | ❌ | 直接读 WORKFLOW.md 手动执行 |
| 动态更新 | ❌ | 无 status.md |
| 节点状态更新 | ❌ | 无 status.json |
| Agent Pool 执行 | ❌ | 用 delegate_task 手动并行 |

### 根因

主 AI 将 workflow-manager 当"阅读文档手册"，而非"通过代码工具执行"。
execute.py 旧版包含任务分解逻辑，但 AI 直接绕过代码手动执行。

---

## 架构重构方案

**核心理念**：代码只做静态功能，AI 做动态决策

### 代码静态层

- 路径索引（工作流目录扫描）
- JSON 解析验证
- 文件存在性检查
- 初始 status.json 生成（空模板）

### AI 动态层

- 读取 WORKFLOW.md
- 分解任务（AI 智能分解）
- 生成 status.md（可动态编辑）
- 更新节点状态
- 调用 agent-pool 执行
- 动态添加子步骤

### Hook 注入层

- 注入 status.md 前30行
- 约束提醒
- 进度提醒
- agent-pool 使用提醒

---

## 实际修改

### 1. execute.py 简化

**删除**：任务分解逻辑、executor 调用
**新增**：--init 模式（生成空模板）、--status 模式（查询状态）
**保留**：路径索引功能

关键代码：
```python
def init_workflow(workflow_name):
    workflow_dir = find_workflow_dir(workflow_name)
    template = {
        "workflow": workflow_name,
        "status": "initialized",
        "workflow_dir": str(workflow_dir),
        "nodes": {},
        "created_at": datetime.now().isoformat()
    }
    with open(status_json, 'w') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
```

### 2. 新增 Hook：workflow-ai-remind

**位置**：`hooks/workflow-ai-remind/`
**事件**：pre_llm_call
**功能**：检测活动工作流，提醒 AI 使用 agent-pool 执行

handler.sh 逻辑：
1. 搜索当前目录、workflows/ 目录的活动工作流
2. 读取 status.json 的 status 字段
3. initialized → 提醒 AI 读取 WORKFLOW.md 并分解任务
4. in_progress → 注入 status.md 前30行

### 3. Hook 安装机制

**正确方式**：
- 源文件在技能目录：`hooks/workflow-*/`
- 映射通过 `hooks-install.sh` 创建符号链接
- `~/.hermes/hooks/workflow-*/` → 技能目录
- `~/.hermes/agent-hooks/workflow-*.sh` → 技能目录/handler.sh

**禁止**：直接在 agent-hooks 目录创建文件

---

## 验证结果

```
python actions/execute.py start --init
→ ✅ 生成 status.json
→ ✅ 输出 AI 执行步骤提醒

hooks-install.sh
→ ✅ 5个 Hook 全部符号链接安装
→ ✅ workflow-ai-remind 新增成功
```

---

## 教训

1. **不能绕过代码手动执行**：主 AI 必须通过 execute.py 启动工作流
2. **代码分解不可靠**：AI 智能分解比代码固定分解更灵活
3. **Hook 是保障机制**：没有 Hook 注入，主 AI 容易遗漏步骤
4. **安装脚本验证**：修改 Hook 后必须运行 hooks-install.sh 并验证符号链接

---

## 备份位置

`~/.hermes/skills/openclaw-imports/workflow-manager/.backup_refactor_20260513/`
