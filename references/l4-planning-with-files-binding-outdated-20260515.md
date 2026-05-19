# L4 任务等级绑定 planning-with-files 过时问题

**发现日期**: 2026-05-15
**问题类型**: 配置过时 / 架构残留
**影响范围**: soul-context-injector 插件

---

## 问题描述

L4 任务等级（方案执行）仍绑定 `planning-with-files` 技能，而非 `workflow-manager`。

这是旧架构设计的残留，当时 L4 = planning-with-files + agent-pool。

现在已融合 Hook 机制，应直接根据 status.md 执行，不再需要 planning-with-files。

---

## 问题位置

| 文件 | 行号 | 问题内容 |
|------|------|----------|
| `context_builder.py` | 127-135 | L4 软提醒模式建议 `skill_view("planning-with-files")` |
| `context_builder.py` | 173-175 | L4 强制步骤要求 `skill_view("planning-with-files")` |
| `context_builder.py` | 186-188 | 验证清单要求已创建 `task_plan.md` |
| `context_builder.py` | 196 | 绑定技能声明为 `planning-with-files, agent-pool` |
| `enforcer.py` | 35 | `SKILL_BINDINGS["L4"] = ["planning-with-files", "agent-pool"]` |
| `enforcer.py` | 45 | `REQUIRED_SKILLS_L4 = ["planning-with-files", "agent-pool"]` |

---

## 正确配置

L4 任务应绑定 `workflow-manager` 而非 `planning-with-files`：

```python
# enforcer.py
SKILL_BINDINGS = {
    "W": ["workflow-manager"],
    "L2": ["deep-thinking"],
    "L3": ["deep-thinking", "openclaw-behavior-plan"],
    "L4": ["workflow-manager", "agent-pool"],  # ← 应改为 workflow-manager
}

REQUIRED_SKILLS_L4 = ["workflow-manager", "agent-pool"]  # ← 应改为 workflow-manager
```

验证清单应改为：
- `status.md`（workflow-manager 产物）而非 `task_plan.md`（planning-with-files 产物）

---

## 根本原因

1. **历史遗留**：旧架构中 L4 = planning-with-files + agent-pool
2. **未同步更新**：workflow-manager 融合 Hook 机制后，L4 绑定未更新
3. **职责混淆**：L4（方案执行）与 W（工作流）职责重叠

---

## 修复方案

### 方案 A：修改 L4 绑定（推荐）

将 L4 绑定改为 `workflow-manager`：

```python
SKILL_BINDINGS["L4"] = ["workflow-manager", "agent-pool"]
REQUIRED_SKILLS_L4 = ["workflow-manager", "agent-pool"]
```

同时更新 `context_builder.py` 中的指令文本。

### 方案 B：合并 L4 和 W

将 L4 任务统一为 W 任务，删除 L4 绑定。

---

## 文件路径

- `/home/kali/.hermes/plugins/soul-context-injector/context_builder.py`
- `/home/kali/.hermes/plugins/soul-context-injector/enforcer.py`

---

## 相关文档

- `references/w-task-system-implementation.md` - W 任务体系实现
- `references/planning-with-files-integration.md` - planning-with-files 融合文档
