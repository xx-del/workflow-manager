# 工作流问题记录机制设计

## 背景

### 问题发现

| 问题 | 说明 |
|------|------|
| status.md 被清理 | `execute.py --init` 会删除旧的 status.md（第 98-101 行） |
| 问题无法持久化 | 工作流执行中的问题记录在 status.md，下次执行丢失 |
| 无法参考历史 | 下次执行相同工作流时，无法参考之前遇到的问题 |

### 需求

- 需要一个类似 planning-with-files findings.md 的文件
- 记录工作流执行中遇到的问题
- 不被 `execute.py --init` 清理
- 没遇到问题可以不记录

---

## 设计方案

### 方案 A：创建独立 issues.md（推荐）

**文件定位**：`~/.hermes/workflows/{workflow-name}/issues.md`

**文件内容**：
```markdown
# Issues Encountered

> 工作流执行中遇到的问题记录

## 问题列表

| 时间 | 步骤 | 问题类型 | 问题描述 | 原因分析 | 解决方案 | 状态 |
|------|------|---------|---------|---------|---------|------|
|       |      |          |         |         |         |      |

## 问题类型说明

- **API 错误**：外部 API 调用失败
- **网络错误**：连接超时、DNS 解析失败
- **权限错误**：权限不足、认证失败
- **数据错误**：数据格式错误、数据缺失
- **逻辑错误**：工作流逻辑问题

## 统计

- 总问题数：0
- 已解决：0
- 待解决：0

## 经验总结

<!-- 记录从问题中总结的经验，供下次执行参考 -->

---
*此文件不会被 execute.py --init 清理，问题记录会持久化保存*
```

**优点**：
- 职焦问题记录，不混杂其他内容
- 表格格式，易于阅读和统计
- 包含时间戳，可追溯

---

## 与 planning-with-files 对比

| 维度 | planning-with-files | workflow-manager |
|------|---------------------|------------------|
| **文件名** | findings.md | issues.md |
| **章节** | 6 个（Requirements, Research, Decisions, Issues, Resources, Visual） | 3 个（问题列表, 统计, 经验总结） |
| **清理策略** | 不清理 | 不清理 |
| **更新时机** | 发现新信息时 | 遇到问题时 |
| **主要用途** | 知识积累 | 问题追踪 |

---

## 实现要点

### execute.py 修改

**当前清理逻辑**（第 98-101 行）：
```python
status_md = workflow_dir / 'status.md'
if status_md.exists():
    status_md.unlink()
    print(f"    已清理旧 status.md")
```

**修改后**：
```python
# 清理旧状态文件（避免历史干扰）
status_md = workflow_dir / 'status.md'
if status_md.exists():
    status_md.unlink()
    print(f"    已清理旧 status.md")

# 创建 issues.md（如果不存在）
issues_md = workflow_dir / 'issues.md'
if not issues_md.exists():
    template_path = Path(__file__).parent.parent / 'templates' / 'issues.md'
    if template_path.exists():
        content = template_path.read_text()
        content = content.replace('{datetime}', datetime.now().strftime('%Y-%m-%d %H:%M'))
        issues_md.write_text(content)
        print(f"    已创建 issues.md")
```

### Hook 提醒修改

**workflow-progress/handler.sh 增加问题记录提醒**：
```bash
echo "⚠️  如果遇到问题，请记录到 issues.md："
echo "   | 时间 | 步骤 | 问题类型 | 问题描述 | 原因 | 解决方案 | 状态 |"
```

---

## 使用流程

```
execute.py --init
    ↓
创建 status.json + issues.md（如果不存在）
    ↓
AI 执行工作流
    ↓
遇到问题 → 记录到 issues.md
    ↓
execute.py --init（下次执行）
    ↓
清理 status.md，保留 issues.md
    ↓
AI 读取 issues.md → 参考历史问题
```

---

## 设计理念差异

| 技能 | 文件定位 | 设计哲学 |
|------|---------|---------|
| planning-with-files | 知识积累型 | 任务未知 → 探索 → 发现 → 记录到三个文件 |
| workflow-manager | 状态追踪型 | 工作流已知 → 执行 → 追踪 → 状态流转 + 问题记录 |

**核心结论**：workflow-manager 不需要 planning-with-files 的三文件结构，但需要独立的 issues.md 来持久化问题记录。
