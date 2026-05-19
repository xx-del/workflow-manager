# status.md 完整生成机制

**版本**: v1.0  
**更新时间**: 2026-05-15  
**来源**: 会话审计与架构纠正

---

## 核心理解

### status.md 的正确定位

**类似 planning-with-files 的 task_plan.md**：
- ✅ 执行过程文档（AI 会更新、会执行、会记录）
- ✅ 包含完整约束（256 行）
- ✅ 包含完整 WORKFLOW.md 内容（非概要，非前30行）
- ✅ 一次性生成，自包含

**不是概要**：
- ❌ 不是步骤列表
- ❌ 不是简单说明
- ❌ 不是前30行摘要

---

## 架构设计原则

### 单一生成入口

**原则**：status.md 的生成必须是**一次性的、自包含的**

**实现方式**：
- ✅ 在 `generate_status_md` 函数内部完成所有生成
- ✅ Python 读取 WORKFLOW.md 并注入完整内容
- ✅ handler.sh 只负责调用函数，不追加内容

**禁止方式**：
- ❌ 不在 handler.sh 中追加 shell 逻辑
- ❌ 不在 shell 层操作文件
- ❌ 不分多次生成或追加

---

## 完整约束内容

### handler.sh 已注入的约束（256 行）

| 章节 | 行数 | 内容 |
|------|------|------|
| 一、执行行为约束 | 14 行 | 绝对禁止 + 必须遵守 |
| 二、主AI职责边界约束 | 13 行 | 禁止行为 + 允许行为 |
| 二之一、文件操作约束 | 19 行 | 禁止删除 + 清理方法 |
| 三、Agent-Pool 使用约束 | 50 行 | 使用方法 + 返回值 |
| 四、异常处理约束 | 19 行 | 处理流程 + 禁止行为 |
| 五、进度记录约束 | 21 行 | 记录要求 + 更新格式 |
| 六、完成判定约束 | 12 行 | 完成标准 + 完成命令 |
| 错误日志 | 6 行 | 执行时填写 |
| 七、类型特殊约束 | 98 行 | branch/heartbeat 约束 |

---

## generate_status_md 完整实现

### 函数结构

```python
def generate_status_md(workflow_name, workflow_type):
    """
    生成完整 status.md 内容（一次性、自包含）
    
    内容结构：
    1. 完整约束（256 行）
    2. 执行步骤（读取完整 WORKFLOW.md）
    3. 错误日志
    4. 类型特殊约束
    """
    
    # 第一部分：完整约束
    md_lines = generate_complete_constraints()
    
    # 第二部分：执行步骤（读取完整 WORKFLOW.md）
    md_lines.extend(generate_detailed_steps(workflow_name, workflow_type))
    
    # 第三部分：错误日志
    md_lines.extend(generate_error_log_section())
    
    # 第四部分：类型特殊约束
    md_lines.extend(generate_type_constraints(workflow_type))
    
    return '\n'.join(md_lines)
```

### 关键辅助函数

```python
def extract_step_from_workflow_md(wf_md_path, step_name):
    """从 WORKFLOW.md 提取指定步骤的完整内容"""
    # 使用正则匹配步骤标题到下一个步骤标题
    # 返回完整内容，不是前30行

def extract_steps_section_from_workflow_md(wf_md_path):
    """从 WORKFLOW.md 提取执行步骤章节"""
    # 提取 ## 执行步骤 到下一个 ## 之间的内容
```

---

## 拼接工作流处理

### branch 类型

**逻辑**：
1. 从 status.json 获取所有步骤信息
2. 对每个步骤，读取源工作流的 WORKFLOW.md
3. 提取对应步骤的**完整内容**
4. 注入到 status.md

**关键**：读取完整 WORKFLOW.md，不是概要

---

## 架构冲突陷阱

### 错误方案

**在 handler.sh 中追加 shell 逻辑**：
```bash
# ❌ 错误示例
cat >> "$STATUS_MD" << 'EOF'
## 执行步骤
EOF

# 读取 WORKFLOW.md 并追加
python3 -c "..." >> "$STATUS_MD"
```

**问题**：
1. generate_status_md 生成的 status.md 缺少执行步骤
2. handler.sh 追加的内容会导致结构混乱
3. 步骤会出现在"错误日志"和"类型约束"之后
4. 可能出现重复或错位

### 正确方案

**在 generate_status_md 函数内部实现**：
```python
# ✅ 正确示例
def generate_status_md(workflow_name, workflow_type):
    # 一次性生成所有内容
    md_lines = []
    md_lines.extend(generate_complete_constraints())
    md_lines.extend(generate_detailed_steps())  # 读取完整 WORKFLOW.md
    md_lines.extend(generate_error_log())
    md_lines.extend(generate_type_constraints())
    return '\n'.join(md_lines)
```

---

## 验证清单

### 生成验证

- [ ] status.md 总行数 > 500 行
- [ ] 包含完整约束（7个章节）
- [ ] 每个步骤包含完整内容（不是概要）
- [ ] 步骤包含执行指令、输入输出、验证清单
- [ ] 章节顺序正确（约束 → 步骤 → 错误日志 → 类型约束）

### Hook 可用性验证

- [ ] PreToolUse 阻断正常（status.md 不存在时）
- [ ] PreToolUse 注入前 30 行正常
- [ ] PostToolUse 提醒更新正常
- [ ] Stop 清理标记正常

---

## 预期结果示例

```markdown
# 资产收集流程 - 执行计划

**生成时间**: 2026-05-15 19:00:00
**工作流类型**: branch
**执行模式**: serial

---

## 一、执行行为约束
（14 行完整约束）

---

## 二、主AI职责边界约束
（13 行完整约束）

---

## 执行步骤（详细）

### 步骤 1: 解析日期范围
**做什么**: 解析用户输入的日期，确定要处理的日期列表

**输入示例**:
- `20260320` → `[20260320]`
- `20260320-20260322` → `[20260320, 20260321, 20260322]`

**输出**: 日期列表

---

### 步骤 2: 备份旧文件
**做什么**: 备份前一天的数据

**执行指令**:
\`\`\`bash
cp /x/rank/hwxinxisouji/liuliang/start/dianli.txt \
   /x/rank/hwxinxisouji/liuliang/start/bk/dianli_{昨天日期}.txt
\`\`\`

---

（每个步骤的完整内容）

## 错误日志
（6 行）

---

## 七、拼接工作流约束
（98 行完整约束）
```

---

## 核心改进总结

| 改进项 | 修改前 | 修改后 |
|--------|--------|--------|
| **生成机制** | 可能多次追加 | 一次性生成 |
| **约束完整性** | 简化版（约 100 行） | 完整版（256 行） |
| **步骤详细度** | 只有概要 | 完整 WORKFLOW.md 内容 |
| **章节顺序** | 可能混乱 | 严格正确 |
| **Shell 注入风险** | 存在 | 消除 |

---

## 参考资料

- planning-with-files-integration.md（融合机制对比）
- hook-constraint-injection-complete-design-20260514.md（Hook 注入设计）
