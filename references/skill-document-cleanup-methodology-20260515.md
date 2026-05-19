# 技能文档清理方法论

**日期**: 2026-05-15
**触发场景**: 技能文档存在重复、过期、矛盾内容

---

## 一、问题识别

### 重复文档特征

| 特征 | 说明 |
|------|------|
| 同主题多版本 | `hook-mechanism.md` vs `hook-mechanism-v6.6-20260514.md` |
| 无日期 vs 有日期 | `loader-fix.md` vs `loader-fix-20260512.md` |
| 演进未清理 | 旧版本未归档，新版本已替代 |

### 过期文档特征

| 特征 | 说明 |
|------|------|
| 任务已完成 | 迁移报告、优化报告等一次性任务 |
| 配置已过时 | Hook名称、路径等已变更 |
| 根目录冗余 | progress.md、findings.md 不应在技能根目录 |

---

## 二、清理流程

### Step 1: 创建备份目录

```bash
mkdir -p references/.backup/duplicate-docs/
mkdir -p references/.backup/archived-reports/
mkdir -p .backup/root-docs/
```

### Step 2: 移动重复文档

保留最新版本，移动旧版本到备份目录：

```bash
mv references/hook-mechanism.md references/.backup/duplicate-docs/
mv references/hook-mechanism-v6.6-20260514.md references/.backup/duplicate-docs/
# 保留 hook-mechanism-complete-design-20260514.md
```

### Step 3: 移动过期根目录文档

```bash
mv HOOKS_GUIDE.md .backup/root-docs/
mv HOOK_MIGRATION_REPORT.md .backup/root-docs/
mv OPTIMIZATION_*.md .backup/root-docs/
```

### Step 4: 创建 README 说明

在备份目录创建 README.md，说明：
- 备份时间
- 备份原因
- 保留版本
- 恢复方法

### Step 5: 整合旧备份

将分散的备份目录整合到统一的 `.backup/` 目录：

```bash
mv .backup_from_inner .backup/
mv .backup_refactor_20260513 .backup/
```

### Step 6: 验证 SKILL.md 引用

确保 SKILL.md 中引用的文档仍然存在：

```bash
grep "references/" SKILL.md | 验证文件存在
```

---

## 三、备份 README 模板

```markdown
# 重复文档备份

**备份时间**: YYYY-MM-DD
**备份原因**: 这些文档是演进过程中的重复版本，保留最新版本在 references/ 目录

## 备份文件清单

| 文件 | 保留版本 | 说明 |
|------|----------|------|
| xxx.md | xxx-latest.md | 旧版本 |

## 恢复方法

cp .backup/duplicate-docs/<文件名> ../
```

---

## 四、验证清单

- [ ] 重复文档已备份
- [ ] 过期文档已备份
- [ ] README 说明已创建
- [ ] SKILL.md 引用验证通过
- [ ] 旧备份已整合

---

## 五、案例

**workflow-manager 技能清理（2026-05-15）**：

| 操作 | 数量 |
|------|------|
| 移动重复文档 | 11个 |
| 移动过期根目录文档 | 8个 |
| references/ 减少 | 12个（159→147） |
