# status.md 生成功能增强记录

**日期**: 2026-05-15
**文件**: `actions/execute.py`
**函数**: `generate_status_md()` 及辅助函数

---

## 优化背景

### 问题诊断

原 `generate_status_md` 函数（第 25-203 行）存在以下问题：

1. **约束不完整** - 只生成了简化版约束（约 100 行）
2. **步骤概要化** - 只有步骤名称和一行说明，缺少完整 WORKFLOW.md 内容
3. **缺少错误日志章节** - 没有统一的错误记录区域

### 期望输出

完整的 status.md 应包含：
- 7 个完整约束章节（256 行）
- 每个步骤的详细执行指令（从 WORKFLOW.md 提取）
- 错误日志表格
- 类型特殊约束（拼接/断点工作流）

---

## 核心改进

### 1. 完整约束注入

新增 7 个约束章节：

```
## 一、执行行为约束
## 二、主AI职责边界约束
## 二之一、文件操作约束
## 三、Agent-Pool 使用约束
## 四、异常处理约束
## 五、进度记录约束
## 六、完成判定约束
```

**总行数**: 约 256 行（vs 原简化版约 100 行）

### 2. WORKFLOW.md 详细步骤提取

**新增两个辅助函数**：

#### `extract_step_from_workflow_md(wf_md_path, step_name)`

**用途**: 从子工作流 WORKFLOW.md 提取指定步骤的完整内容

**匹配模式**（支持多种格式）：
```python
patterns = [
    rf'### 步骤[^:]*:\s*{re.escape(step_name)}.*?(?=### 步骤|$)',
    rf'### {re.escape(step_name)}.*?(?=### |$)',
]
```

**返回**: 步骤内容（行列表），包含执行指令、输入输出、验证清单等

#### `extract_steps_section_from_workflow_md(wf_md_path)`

**用途**: 从普通工作流 WORKFLOW.md 提取整个执行步骤章节

**匹配模式**：
```python
pattern = r'## 执行步骤.*?(?=## |$)'
```

**返回**: 执行步骤章节内容（行列表）

### 3. 标题重复检测逻辑

**问题**: 提取的内容可能已包含步骤标题，导致重复

**修复**：
```python
if step_content and step_content[0].startswith('### '):
    md_lines.extend(step_content)  # 直接使用，不添加标题
else:
    md_lines.append(f"### 步骤 {step_id}: {step_name}")
    md_lines.append("")
    md_lines.extend(step_content)
```

### 4. 按类型生成步骤

**拼接工作流 (branch)**：
- 遍历 status.json 中的 steps
- 根据 `source_workflow` 字段定位源工作流
- 调用 `extract_step_from_workflow_md()` 提取每个步骤

**普通工作流 (normal)**：
- 读取当前工作流的 WORKFLOW.md
- 调用 `extract_steps_section_from_workflow_md()` 提取整个章节

**断点工作流 (heartbeat)**：
- 同普通工作流，读取完整章节

### 5. 错误日志章节

新增统一错误记录区域：
```markdown
## 错误日志

| 错误 | 步骤 | 尝试 | 解决方案 |
|------|------|------|----------|
| (执行时填写) | | | |
```

---

## 生成结构对比

| 改进项 | 修改前 | 修改后 |
|--------|--------|--------|
| **生成机制** | handler.sh 可能追加 | generate_status_md 一次性生成 |
| **约束完整性** | 简化版（约 100 行） | 完整版（256 行） |
| **步骤详细度** | 只有概要（一行说明） | 完整 WORKFLOW.md 内容 |
| **章节顺序** | 可能混乱 | 严格正确（4 部分顺序） |
| **Shell 注入风险** | 存在 | 消除 |

**生成顺序**：
1. 完整约束（第一部分）
2. 执行步骤详细（第二部分，读取 WORKFLOW.md）
3. 错误日志（第三部分）
4. 类型特殊约束（第四部分）

---

## 验证方法

### 语法检查
```bash
python3 -m py_compile ~/.hermes/skills/openclaw-imports/workflow-manager/actions/execute.py
```

### 生成验证
```bash
cd ~/.hermes/workflows/资产收集流程
rm -f status.md
python3 ~/.hermes/skills/openclaw-imports/workflow-manager/actions/execute.py 资产收集流程 --init
```

### 完整性检查
```bash
# 总行数（预期 > 500 行）
wc -l status.md

# 完整约束检查
grep -c "## 一、执行行为约束" status.md
grep -c "## 二、主AI职责边界约束" status.md
grep -c "## 三、Agent-Pool 使用约束" status.md

# 步骤详细内容检查（预期 > 10 个执行指令）
grep -c "执行指令" status.md
```

### 实测结果（资产收集流程）

```
✅ 总行数: 686 行
✅ 完整约束: 7 个章节全部存在
✅ 步骤详细内容: 11 个执行指令
✅ 错误日志章节: 已生成
✅ 类型特殊约束: 拼接工作流约束已注入
```

---

## 技术要点

### 正则匹配容错

**多模式匹配**：支持不同的步骤标题格式
```python
patterns = [
    rf'### 步骤[^:]*:\s*{re.escape(step_name)}.*?(?=### 步骤|$)',  # 标准格式
    rf'### {re.escape(step_name)}.*?(?=### |$)',                  # 简化格式
]
```

### re.DOTALL 标志

确保跨行匹配，捕获完整步骤内容（包括代码块、列表等）

### re.escape() 安全处理

对步骤名称进行转义，避免正则元字符干扰

---

## 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| 函数复杂度增加 | 低 | 模块化设计，提取辅助函数 |
| WORKFLOW.md 格式不一致 | 低 | 正则匹配容错处理 |
| status.md 篇幅过大 | 无 | 完整内容是需求，不是风险 |

---

## 与审计意见对比

| 审计意见 | 是否解决 | 说明 |
|----------|----------|------|
| **架构冲突** | ✅ 已解决 | 不在 handler.sh 中追加，改为 generate_status_md 内部实现 |
| **生成机制冲突** | ✅ 已解决 | 一次性生成，单一生成入口 |
| **结构混乱风险** | ✅ 已解决 | 在 Python 中严格按顺序拼接 |
| **重复或错位风险** | ✅ 已解决 | 无 shell 层操作，无追加逻辑 |

---

## 后续优化方向

1. **步骤缓存**：对已提取的步骤内容进行缓存，避免重复读取
2. **增量更新**：只更新变化的步骤，而非全量重新生成
3. **模板化**：将约束模板提取为独立文件，便于维护
4. **步骤依赖可视化**：在 status.md 中展示步骤依赖关系图

---

**备份位置**: `execute.py.bak`
**修改行数**: 第 25-358 行（函数替换 + 辅助函数添加）
**验证状态**: ✅ 通过（语法 + 生成效果）
