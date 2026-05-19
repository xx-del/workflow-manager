# Hook 工作流类型识别完整解决方案

**日期**：2026-05-15
**状态**：已完成（部分）

---

## 一、执行摘要

### 已完成修改

| 文件 | 修改内容 | 状态 |
|------|----------|------|
| `actions/identify_type.py` | CLI 包装器，复用 loader 识别逻辑 | ✅ 已创建 |
| `actions/execute.py` | generate_status_md 函数（接收类型参数） | ✅ 已添加 |
| `hooks/workflow-step-check/handler.sh` | 调用 identify_type.py 获取类型 | ✅ 已修改 |

### 验证结果

| 工作流 | identify_type.py 识别 | status.md 生成 | 一致性 |
|--------|----------------------|----------------|--------|
| 资产收集流程 | branch ✅ | ✅ 已生成 | ✅ 一致 |
| home漏扫 | heartbeat ✅ | - | ✅ 正确 |
| 通用漏洞扫描 | branch ✅ | - | ✅ 正确 |

---

## 二、核心修改

### 2.1 identify_type.py 创建

**路径**：`actions/identify_type.py`

**核心逻辑**：
```python
loader = WorkflowLoader()
workflow = loader.load(workflow_path)

result = {
    'type': workflow.get('type', 'normal'),
    'mode': workflow.get('mode', 'serial'),
    'breakpoints': [...],
    'sub_workflows': [...],
    'workflow_name': workflow.get('name', workflow_path.name)
}
```

**关键特性**：
- 复用 loader._identify_workflow_type() 逻辑
- 路径校验（启动时检查 loader.py、_index.yaml）
- 错误处理（所有异常返回 JSON error 字段）

### 2.2 generate_status_md 函数

**位置**：`execute.py` imports 之后

**关键改进**：
1. **接收 workflow_type 参数**：保证与 Hook 识别一致
2. **读取主 _index.yaml**：而非子目录的 _index.yaml
3. **按 name 匹配工作流**：修复直接取 workflows[0] 的错误
4. **status_data 初始化**：统一初始化避免 NameError

### 2.3 handler.sh 修改

**修改位置**：第 50-123 行

**修改内容**：
```bash
# 调用 CLI 获取类型信息
IDENTIFY_CLI="$HOME/.hermes/skills/openclaw-imports/workflow-manager/actions/identify_type.py"
TYPE_INFO=$(python3 "$IDENTIFY_CLI" "$WORKFLOW_PATH" 2>/dev/null)

# 解析 JSON（带错误处理）
if [[ -z "$TYPE_INFO" ]] || echo "$TYPE_INFO" | grep -q '"error"'; then
    workflow_type="normal"
else
    workflow_type=$(echo "$TYPE_INFO" | python3 -c "import json,sys; print(json.load(sys.stdin).get('type', 'normal'))")
fi
```

---

## 三、关键发现

### 3.1 _index.yaml 结构差异

**问题**：子工作流目录的 `_index.yaml` workflows 字段为空

**原因**：工作流定义在主 `_index.yaml`（`~/.hermes/workflows/_index.yaml`）

**修复**：`generate_status_md` 读取主 `_index.yaml`

### 3.2 类型识别不一致问题

**问题**：部分工作流 `_index.yaml` 未设置 type 字段

**示例**：
- `资产收集流程`：type=(未设置)，loader 推断=branch
- `home漏扫`：type=(未设置)，loader 推断=heartbeat

**修复**：generate_status_md 接收外部传入的类型参数，不自行判断

---

## 四、审计问题修复清单

| 问题 | 等级 | 修复方案 |
|------|------|----------|
| 工作流匹配逻辑错误 | 阻断 | 按 name 字段匹配 |
| status_data 未定义 | 阻断 | 统一初始化 |
| 缺少依赖异常处理 | 阻断 | try-except 包裹 |
| 非原子写入 | 阻断 | 临时文件 + mv |
| 类型识别不一致 | 阻断 | 接收外部类型参数 |
| 函数定义顺序 | 风险 | 函数前置定义 |
| _index.yaml 路径错误 | 阻断 | 读取主 _index.yaml |
| 非 branch 类型缺少生成 | 功能 | is_branch 分支添加生成逻辑 |

---

## 五、待解决问题

### 5.1 status.md 完整版

**问题**：当前 status.md 只是概要，缺少：
- Hook 完整注入约束（约 285 行）
- 每个步骤详细执行指令（前 30 行）

**定位理解**：
- status.md 应类似 planning-with-files 的 task_plan.md
- 执行过程文档（AI 会更新、会执行、会记录）
- 不是概要，不是步骤列表

**解决方案**：见 `~/.hermes/plans/20260515-hook-type-identification/status_md_complete_solution.md`

### 5.2 Hook 与 generate_status_md 职责分工

**核心原则**：Hook 完全负责生成 status.md

**原因**：
- Hook 是核心机制，不应被绕过
- Hook 已包含完整约束（第 76-360 行）
- 与 planning-with-files 机制一致

---

## 六、验证方法

```bash
# 1. 验证 identify_type.py
python3 ~/.hermes/skills/openclaw-imports/workflow-manager/actions/identify_type.py ~/.hermes/workflows/资产收集流程

# 2. 验证 generate_status_md
python3 -c "from execute import generate_status_md; print(generate_status_md('资产收集流程', 'branch'))"

# 3. 验证 --init 生成 status.md
python3 actions/execute.py 资产收集流程 --init

# 4. 检查类型一致性
cat ~/.hermes/workflows/资产收集流程/status.md | grep "工作流类型"
```

---

## 七、核心教训

### 7.1 类型识别必须统一来源

**不应该让 AI 自己识别**：
- AI 识别准确率不可控
- 与代码执行逻辑可能不一致
- 违反已明确禁止的行为（handler.sh 第 160-162 行）

**应该由代码识别**：
- 确定性：相同输入一定相同输出
- 可验证性：可直接运行验证
- 一致性：loader、executor、Hook 使用同一逻辑

### 7.2 status.md 定位理解

**正确定位**：
- 类似 planning-with-files 的 task_plan.md
- 执行过程文档（AI 会更新、会执行、会记录）
- 包含完整约束 + 详细执行指令

**错误定位**：
- ❌ 不是概要
- ❌ 不是步骤列表
- ❌ 不是简单说明

### 7.3 Hook 可用性保障

**核心原则**：Hook 是核心机制，不应被绕过

**handler.sh 已包含**：
- 完整约束（第 76-260 行）
- 类型特殊约束（第 263-360 行）
- 执行步骤区域（第 248-251 行）

---

## 八、参考资料

- 完整方案：`~/.hermes/plans/20260515-hook-type-identification/`
- Hook 约束设计：`references/hook-constraint-injection-complete-design-20260514.md`
- planning-with-files 融合：`references/planning-with-files-integration.md`