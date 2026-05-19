# 技能一致性审计方法论

**日期**: 2026-05-15
**触发场景**: 技能文档/代码积累过多，需要清理过期内容

---

## 审计流程

### 1. 全盘扫描

```bash
# 扫描所有文件
find ~/.hermes/skills/<skill-name> -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.yaml" \)

# 统计文件数量
ls -la references/ | wc -l
```

### 2. 分类识别

| 分类 | 检测方法 | 处理方式 |
|------|----------|----------|
| 重复文档 | 同一主题多个日期版本 | 保留最新，备份其他 |
| 过期文档 | 已完成任务、旧方案、迁移报告 | 备份到 .backup/ |
| 过期代码 | 未被引用的函数/脚本 | 备份后可删除 |
| 有效内容 | 当前使用中 | 保留 |

### 3. 重复文档检测

按主题分组，识别演进版本：
```
hook-constraint-injection-mechanism.md
hook-constraint-injection-mechanism-v6.6-20260514.md
hook-constraint-injection-complete-design-20260514.md
→ 同一主题3个版本，保留最新（complete-design）
```

### 4. 过期文档检测

| 类型 | 特征 | 示例 |
|------|------|------|
| 迁移报告 | "迁移完成"、"已执行" | HOOK_MIGRATION_REPORT.md |
| 优化报告 | "优化分析"、"优化计划" | OPTIMIZATION_ANALYSIS.md |
| 任务产物 | 根目录的 progress.md, task_plan.md | 不应在根目录 |
| 过时指南 | Hook名称与实际不符 | HOOKS_GUIDE.md |

---

## 备份原则

**禁止直接删除**，必须备份：

```
references/.backup/
├── duplicate-docs/      # 重复文档
│   └── README.md        # 说明备份原因
├── archived-reports/    # 过期报告
└── deprecated-code/     # 废弃代码
```

---

## 验证清单

- [ ] SKILL.md 引用的 references/ 文件仍然存在
- [ ] 备份目录有 README.md 说明内容
- [ ] 移动后文件数量符合预期
- [ ] 技能功能不受影响

---

## 本次审计结果（workflow-manager）

| 项目 | 数量 |
|------|------|
| references/ 总文件 | 159 |
| 重复文档 | ~12 |
| 过期根目录文档 | 8 |
| 备份后保留 | ~139 |
