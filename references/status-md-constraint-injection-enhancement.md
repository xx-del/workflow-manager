# status.md 约束注入完整优化方案

**版本**: v1.0.0  
**创建时间**: 2026-05-13  
**设计目标**: 融合 planning-with-files 后，status.md 成为 AI 唯一约束来源，需整合所有执行约束

---

## 一、现状分析

### 1.1 当前 status.md 注入内容

**代码位置**: `src/core/executor.py` 第 101-225 行

**当前注入内容**:
```
1. 工作流元信息（名称、生成时间、执行模式、总步骤）
2. 目标（从 WORKFLOW.md 提取）
3. 执行步骤详情（名称、描述、命令、输入、输出、状态）
4. 步骤级约束（通过 _identify_step_constraints 识别）
5. 约束清单（硬编码，6条通用约束）
6. 错误日志表格
7. 执行记录
```

**当前约束清单（硬编码）**:
```markdown
## 约束清单 ⚠️（必须严格遵守）
- [ ] 严格按步骤顺序执行
- [ ] 禁止修改上述命令
- [ ] 禁止添加 WORKFLOW.md 没有的步骤
- [ ] 禁止添加 timeout 参数
- [ ] 每步执行后验证输出
- [ ] 遇到问题立即停止，不推断原因
```

### 1.2 问题分析

| 问题 | 影响 | 根因 |
|------|------|------|
| 约束清单是通用的 | 缺少拼接工作流特殊约束 | 代码硬编码，未根据工作流类型动态生成 |
| AI 只读 status.md | SKILL.md 中的约束不可见 | planning-with-files 融合后，注意力操控机制 |
| 拼接工作流断点 | AI 询问用户是否继续 | status.md 未注入"自动继续执行"约束 |
| 子工作流状态不可见 | AI 无法判断执行进度 | status.md 未包含子工作流状态追踪表 |
| 职责边界不明确 | AI 可能越权执行 | status.md 未注入"禁止自行诊断/修复"约束 |

---

## 二、约束来源全面盘点

### 2.1 SKILL.md 约束章节

| 章节 | 约束类型 | 必须注入 |
|------|---------|---------|
| 第四章 执行约束 | 主AI禁止行为 | ✅ |
| 第四章 执行约束 | 执行前强制检查 | ✅ |
| 第五章 守护机制 | 遇到问题时处理流程 | ✅ |
| 第六章 并发控制 | 最大并发数 | ✅ |
| 第九章 拼接工作流串行执行约束 | 串行执行、禁止询问 | ✅ |
| 第十章 常见错误模式 | 错误行为清单 | ✅ |

### 2.2 references 约束文档

| 文档 | 约束类型 | 必须注入 |
|------|---------|---------|
| executor-constraints.md | subagent 绝对禁止 | ✅ |
| serial-execution-constraints.md | 拼接工作流串行约束 | ✅ |
| terminal-execution-constraints.md | timeout 禁止约束 | ✅ |
| execution-constraint-rationale.md | 越权行为示例 | ✅ |
| execution-best-practices.md | 结果验证、归档标准 | ✅ |
| execution-pitfalls.md | 依赖配置、超时陷阱 | ✅ |
| status-update-responsibility.md | 状态更新职责 | ✅ |
| long-running-step-execution.md | 后台模式约束 | ✅ |
| guardian.md | 守护机制 | ⚠️ 参考 |
| breakpoint-workflow-handling.md | 断点处理 | ⚠️ 参考 |

---

## 三、约束分类与注入策略

### 3.1 约束分类矩阵

| 约束类别 | 注入范围 | 注入位置 |
|---------|---------|---------|
| **A. 工作流元信息约束** | 所有工作流 | status.md 头部 |
| **B. 执行行为约束** | 所有工作流 | 约束清单章节 |
| **C. 主AI职责边界约束** | 所有工作流 | 约束清单章节 |
| **D. 异常处理约束** | 所有工作流 | 约束清单章节 |
| **E. 进度记录约束** | 所有工作流 | 约束清单章节 |
| **F. 完成判定约束** | 所有工作流 | 约束清单章节 |
| **G. 拼接工作流特殊约束** | type: branch | 专项章节 |
| **H. 串行工作流约束** | mode: serial | 专项章节 |
| **I. 并行工作流约束** | mode: parallel | 专项章节 |
| **J. 心跳驱动工作流约束** | type: heartbeat | 专项章节 |
| **K. 步骤级约束** | 每个步骤 | 步骤详情中 |

---

## 四、完整约束注入模板

### 4.1 工作流元信息约束（A类）

```markdown
## 工作流元信息

**工作流名称**: {workflow_name}
**工作流类型**: {type: branch/serial/parallel/heartbeat/normal}
**执行模式**: {mode: serial/parallel/hybrid}
**生成时间**: {timestamp}
**总步骤**: {total_steps}

**工作流类型说明**:
- `branch`: 拼接工作流（编排多个子工作流）
- `serial`: 串行工作流（步骤按顺序执行）
- `parallel`: 并行工作流（步骤可并行执行）
- `heartbeat`: 心跳驱动工作流（断点+心跳接管）
- `normal`: 普通工作流
```

### 4.2 执行行为约束（B类）

```markdown
### 执行行为约束

**绝对禁止**:
- ❌ **禁止修改命令**（工作流命令经过验证，修改可能导致失败）
- ❌ **禁止添加 timeout 参数**（工作流设计无 timeout 概念，添加会导致中断）
- ❌ **禁止跳过步骤**（串行工作流存在依赖关系，跳过会导致后续失败）
- ❌ **禁止添加未定义步骤**（只执行 WORKFLOW.md 定义的步骤）
- ❌ **禁止使用替代方案**（严格按指令执行）
- ❌ **禁止自行决定**（遇到问题上报，不自作主张）
- ❌ **禁止凭记忆执行**（有文档必须读原文）
- ❌ **禁止将"命令返回"等同于"工作流完成"**（需验证实际输出）

**必须遵守**:
- ✅ **严格按指令执行**
- ✅ **验证每个输出**（文件存在性、内容正确性）
- ✅ **每步执行后更新状态**（更新 status.json）
- ✅ **记录执行日志**（调用 update_plan.py --log-step）
```

### 4.3 主AI职责边界约束（C类）

```markdown
### 主AI职责边界约束

**代码已实现，禁止主AI重复执行**:
- ❌ **禁止自己读取 _index.yaml**（代码实现：loader.load()）
- ❌ **禁止自己判断步骤顺序**（代码实现：analyzer.analyze()）
- ❌ **禁止自己检测依赖关系**（代码实现：analyzer._calculate_levels()）
- ❌ **禁止自己检测循环依赖**（代码实现：analyzer.detect_circular_dependency()）
- ❌ **禁止自己识别并行组**（代码实现：analyzer._find_parallel_groups()）
- ❌ **禁止直接调用 delegate_task 未通过 execute.py**（代码实现：agent_pool_client.execute_full()）
- ❌ **禁止自己处理 Handoff**（代码实现：agent_pool_client._build_instructions()）
- ❌ **禁止自己处理 Feedback**（代码实现：agent_pool_client._build_instructions()）

**执行前强制检查**:
- [ ] 是否已调用 execute.py --plan-only？（必须：是）
- [ ] 是否收到了 pending_instructions？（必须：是）
- [ ] 是否直接读取了 _index.yaml？（必须：否）
- [ ] 是否直接调用了 delegate_task 而未通过 execute.py？（必须：否）

**任何一项不符合 → 禁止执行**
```

### 4.4 异常处理约束（D类）

```markdown
### 异常处理约束

**遇到问题时的处理流程**:
```
步骤执行失败
     ↓
立即停止工作流（不诊断、不修复、不跳过）
     ↓
上报异常现象：
- 步骤名称: XXX
- 执行命令: XXX
- 错误信息: XXX
- 输出内容: XXX
     ↓
等待用户指示：
- 用户说"分析" → 进入诊断模式
- 用户说"重试" → 重试当前步骤
- 用户说"跳过" → 跳过当前步骤
- 用户说"终止" → 结束工作流
```

**禁止行为**:
- ❌ **禁止自主诊断问题**（不是守护Agent职责）
- ❌ **禁止自主修复问题**（不是守护Agent职责）
- ❌ **禁止跳过失败步骤**（等待用户指示）
```

### 4.5 进度记录约束（E类）

```markdown
### 进度记录约束

**主AI必须在执行步骤后记录进度**:

**1. 更新状态文件**:
```bash
# 每个步骤执行前后
jq '.status = "running" | .progress.current_step = N | .workflow.heartbeat = "'$(date -Iseconds)'"' \
   status.json > status.json.tmp && mv status.json.tmp status.json
```

**2. 记录执行日志**:
```bash
# 步骤执行后
python update_plan.py {workflow_name} \
  --log-step "步骤 N: XXX" \
  --command "执行命令" \
  --output "执行结果摘要" \
  --duration 耗时秒数
```

**3. 记录研究发现**:
```bash
# 发现新结果时
python update_plan.py {workflow_name} \
  --log-finding "发现描述" \
  --evidence "证据路径"
```
```

### 4.6 完成判定约束（F类）

```markdown
### 完成判定约束

**工作流完成标准**:
- 所有步骤状态 = `completed`
- 所有预期输出文件存在且有效
- 无未处理的错误

**步骤完成标准**:
- 命令执行完成（退出码 0）
- 输出文件存在
- 输出内容有效（非空、格式正确）

**验证方法**:
```bash
# 检查文件存在性和大小
ls -lh output_file.txt

# 检查行数
wc -l output_file.txt

# 预览内容
head -20 output_file.txt
```
```

### 4.7 拼接工作流特殊约束（G类，type: branch 专用）

```markdown
### 拼接工作流特殊约束（type: branch）

**核心规则**:
- ⚠️ **子工作流必须串行执行**（禁止并行启动）
- ⚠️ **当前子工作流完成后自动执行下一个**（禁止询问用户）
- ⚠️ **所有子工作流完成后工作流才算完成**
- ⚠️ **禁止在子工作流之间插入其他操作**

**禁止行为**:
- ❌ **禁止询问"是否继续执行下一个子工作流"**
- ❌ **禁止并行启动存在依赖关系的子工作流**
- ❌ **禁止跳过未完成的子工作流**
- ❌ **禁止在子工作流之间执行其他任务**

**执行流程**:
1. 识别拼接工作流（type: branch）
2. 获取子工作流列表（按 depends_on 顺序）
3. 串行执行每个子工作流
4. 等待当前子工作流完成（status = "completed"）
5. 自动执行下一个子工作流（不询问用户）
6. 所有子工作流完成 → 工作流完成

**子工作流执行状态追踪**:
| 序号 | 子工作流 | 依赖 | 状态 | 完成时间 |
|------|---------|------|------|---------|
| 1 | {name1} | 无 | ⏳ 待执行 | - |
| 2 | {name2} | {name1} | ⏳ 待执行 | - |
| 3 | {name3} | {name2} | ⏳ 待执行 | - |
| 4 | {name4} | {name3} | ⏳ 待执行 | - |

**状态更新规则**:
- 主 AI 在执行子工作流前更新状态为 `running`
- 主 AI 在子工作流完成后更新状态为 `completed`
- 所有子工作流状态 = `completed` → 工作流完成

**违规后果**:
| 违规行为 | 后果 |
|---------|------|
| 并行启动串行工作流 | 执行顺序错误，依赖关系破坏，结果无效 |
| 未等待依赖完成 | 越权执行，结果无效 |
| 跳过子工作流 | 结果不完整 |
```

### 4.8 串行工作流约束（H类，mode: serial 专用）

```markdown
### 串行工作流约束（mode: serial）

**核心规则**:
- 步骤必须按 depends_on 顺序执行
- 当前步骤完成后再执行下一步
- 遇到问题立即停止

**依赖检查规则**:
- 步骤有 `depends_on` → 必须等待依赖完成
- 依赖未完成 → 禁止执行当前步骤
```

### 4.9 并行工作流约束（I类，mode: parallel 专用）

```markdown
### 并行工作流约束（mode: parallel）

**核心规则**:
- 无依赖步骤可并行执行
- 最大并发数：3
- 有依赖步骤必须等待

**并发控制示例**:
```python
# 正确：批量执行（最多3个）
delegate_task(tasks=[
    {"goal": "任务1", ...},
    {"goal": "任务2", ...},
    {"goal": "任务3", ...}
])
```
```

### 4.10 心跳驱动工作流约束（J类，type: heartbeat 专用）

```markdown
### 心跳驱动工作流约束（type: heartbeat）

**识别特征**:
- 工作流包含断点步骤（type: breakpoint）
- 执行由心跳脚本自动接管

**执行模式**:
1. 主 AI 执行到断点步骤
2. 断点步骤返回，不等待完成
3. 心跳脚本自动接管后续步骤
4. 心跳脚本检测完成后退出

**长时间运行步骤处理**:
- 使用 `terminal(background=True)` 启动后台进程
- 设置 `notify_on_complete=True` 获取完成通知
- 通过 `process(action='poll')` 检查状态
```

---

## 五、代码实现方案

### 5.1 修改位置

**文件**: `src/core/executor.py`

### 5.2 新增方法

```python
def _generate_constraint_sections(self, workflow: Dict[str, Any]) -> List[str]:
    """
    生成约束清单章节
    
    根据工作流类型动态注入约束
    
    Args:
        workflow: 工作流定义字典
        
    Returns:
        约束章节字符串列表
    """
    sections = []
    
    # 获取工作流类型
    workflow_type = workflow.get('type', 'normal')
    workflow_mode = workflow.get('mode', 'serial')
    
    # B类：执行行为约束（始终注入）
    sections.append(self._generate_execution_behavior_constraints())
    
    # C类：主AI职责边界约束（始终注入）
    sections.append(self._generate_ai_responsibility_constraints())
    
    # D类：异常处理约束（始终注入）
    sections.append(self._generate_exception_handling_constraints())
    
    # E类：进度记录约束（始终注入）
    sections.append(self._generate_progress_tracking_constraints())
    
    # F类：完成判定约束（始终注入）
    sections.append(self._generate_completion_criteria_constraints())
    
    # G类：拼接工作流特殊约束（type: branch）
    if workflow_type == 'branch':
        sections.append(self._generate_composite_workflow_constraints(workflow))
    
    # H类：串行工作流约束
    elif workflow_mode == 'serial':
        sections.append(self._generate_serial_workflow_constraints())
    
    # I类：并行工作流约束
    elif workflow_mode == 'parallel':
        sections.append(self._generate_parallel_workflow_constraints())
    
    # J类：心跳驱动工作流约束
    if workflow_type == 'heartbeat':
        sections.append(self._generate_heartbeat_workflow_constraints())
    
    return sections

def _generate_composite_workflow_constraints(self, workflow: Dict[str, Any]) -> str:
    """生成拼接工作流特殊约束"""
    # 获取子工作流列表
    nodes = workflow.get('nodes', [])
    sub_workflows = []
    for node in nodes:
        if node.get('calls') == 'workflow-manager':
            sub_wf = {
                'name': node.get('name'),
                'depends_on': node.get('depends_on', []),
                'status': 'pending'
            }
            sub_workflows.append(sub_wf)
    
    # 生成约束文本（包含子工作流状态追踪表）
    # ... 详细实现见附录

def _generate_execution_behavior_constraints(self) -> str:
    """生成执行行为约束"""
    # 返回 B 类约束模板

def _generate_ai_responsibility_constraints(self) -> str:
    """生成主AI职责边界约束"""
    # 返回 C 类约束模板

# ... 其他约束生成方法
```

### 5.3 修改 generate_execution_plan_md 方法

**修改位置**: 第 190-202 行

**当前代码**（硬编码）:
```python
# 添加约束清单
md_lines.extend([
    "---",
    "",
    "## 约束清单 ⚠️（必须严格遵守）",
    "",
    "- [ ] 严格按步骤顺序执行",
    "- [ ] 禁止修改上述命令",
    "- [ ] 禁止添加 WORKFLOW.md 没有的步骤",
    "- [ ] 禁止添加 timeout 参数",
    "- [ ] 每步执行后验证输出",
    "- [ ] 遇到问题立即停止，不推断原因",
    "",
    # ...
])
```

**修改后**（动态注入）:
```python
# 添加约束章节（动态注入）
md_lines.extend([
    "---",
    "",
])

# 动态生成约束章节
constraint_sections = self._generate_constraint_sections(workflow)
for section in constraint_sections:
    md_lines.append(section)
    md_lines.append("")

# 添加错误日志章节
md_lines.extend([
    "---",
    "",
    "## 错误日志（执行时填写）",
    # ...
])
```

### 5.4 增强工作流元信息注入

**修改位置**: 第 136-152 行

**新增内容**:
```python
# 识别工作流类型
workflow_type = workflow.get('type', 'normal')
if workflow_type == 'normal':
    # 检查是否心跳驱动
    if self._is_heartbeat_workflow(workflow):
        workflow_type = 'heartbeat'

md_lines.extend([
    f"# 工作流执行计划：{workflow_name}",
    "",
    f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    f"**工作流类型**: {workflow_type}",
    f"**执行模式**: {workflow_mode}",
    f"**总步骤**: {len(nodes)}",
    "",
    "---",
    "",
    "## 工作流元信息",
    "",
    f"**工作流名称**: {workflow_name}",
    f"**工作流类型**: {workflow_type}",
    f"**执行模式**: {workflow_mode}",
    "",
    "**工作流类型说明**:",
    "- `branch`: 拼接工作流（编排多个子工作流）",
    "- `serial`: 串行工作流（步骤按顺序执行）",
    "- `parallel`: 并行工作流（步骤可并行执行）",
    "- `heartbeat`: 心跳驱动工作流（断点+心跳接管）",
    "- `normal`: 普通工作流",
    "",
    "---",
    "",
])
```

---

## 六、验证清单

**修改完成后验证**:

- [ ] 所有工作流类型都有对应的约束注入
- [ ] 拼接工作流包含子工作流状态追踪表
- [ ] 包含"禁止询问用户是否继续"约束
- [ ] 包含"自动执行下一个子工作流"约束
- [ ] 包含主AI职责边界约束
- [ ] 包含异常处理约束
- [ ] 包含进度记录约束
- [ ] 包含完成判定约束

**测试用例**:
```bash
# 测试拼接工作流
python execute.py 通用漏洞扫描 --plan-only
# 验证：status.md 包含 G 类约束 + 子工作流状态追踪表

# 测试串行工作流
python execute.py 爆破测试 --plan-only
# 验证：status.md 包含 H 类约束

# 测试心跳驱动工作流
python execute.py home漏扫 --plan-only
# 验证：status.md 包含 J 类约束
```

---

## 七、实施优先级

| 优先级 | 任务 | 预期效果 |
|--------|------|---------|
| P0 | 修改 executor.py，实现动态约束注入 | 拼接工作流断点问题解决 |
| P1 | 添加子工作流状态追踪表 | AI 可见执行进度 |
| P2 | 整合所有约束到模板 | status.md 成为唯一约束来源 |
| P3 | 添加工作流类型识别 | 约束注入更精准 |

---

## 八、总结

**核心改进**:
1. 从硬编码约束升级为**动态约束注入**
2. 根据工作流类型注入**专项约束**
3. 整合 SKILL.md + references 中**所有执行约束**
4. status.md 成为 AI **唯一约束来源**

**预期效果**:
- AI 明确知道拼接工作流串行执行
- AI 明确知道自动继续，不再询问用户
- AI 明确知道职责边界，不再越权执行
- AI 能够追踪子工作流状态
- 工作流不再断点

---

## 附录：完整约束模板文本

（详见第四章各约束模板）
