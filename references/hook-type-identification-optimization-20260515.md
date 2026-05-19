# Hook 工作流类型识别优化分析

**日期**：2026-05-15
**状态**：已分析，待执行

---

## 一、问题发现

### 1.1 Hook 与 loader 识别逻辑对比

| 判断条件 | Hook (handler.sh) | Code (loader.py) | 一致性 |
|---------|-------------------|------------------|--------|
| `type: branch` | ✅ 第 66 行 | ✅ 第 182 行 | 一致 |
| 所有节点 `calls: workflow-manager` | ✅ 第 70-72 行 | ✅ 第 184 行 | 一致 |
| `config.heartbeat.enabled: true` | ✅ 第 75-77 行 | ✅ 第 189 行 | 一致 |
| 节点 `type: breakpoint` 或 `auto` | ✅ 第 79-81 行 | ✅ 第 191 行 | 一致 |
| 节点 `trigger: heartbeat` | ⚠️ 第 87 行（位置错误） | ✅ 第 193 行 | **Hook位置错误** |
| 节点 `heartbeat.enabled: true` | ❌ 未检测 | ✅ 第 195 行 | **Hook缺失** |

### 1.2 核心问题

**问题 1**：Hook 缺少节点级 `heartbeat.enabled: true` 检测
**问题 2**：Hook 的 `trigger: heartbeat` 检测在 else 分支中，逻辑位置错误
**影响**：某些断点工作流可能被误判为 normal 类型，导致 Hook 不注入断点约束

---

## 二、方案对比

### 2.1 注入提示词 vs 代码实现

| 维度 | 注入提示词 | 代码实现 |
|------|-----------|---------|
| **准确性** | ❌ AI 识别不可控 | ✅ 代码 100% 准确 |
| **一致性** | ❌ 可能与代码冲突 | ✅ 复用 loader 逻辑 |
| **可维护性** | ⚠️ prompt 篇幅大 | ✅ 单点维护 |
| **token 消耗** | ❌ 大量 prompt | ✅ 无额外 prompt |
| **已有教训** | ❌ SKILL.md 可能矛盾 | ✅ 无此风险 |

### 2.2 已有明确结论

| 证据 | 来源 | 结论 |
|------|------|------|
| "禁止自己读取 _index.yaml" | handler.sh 第 160 行 | ❌ 不应该让 AI 自己识别 |
| "禁止自己判断步骤顺序" | handler.sh 第 161 行 | ❌ AI 不应该判断 |
| "禁止优先考虑写代码" | branch-workflow-hook-enhancement 第 14 行 | ⚠️ 机制优先 |
| "路径信息由 Hook 注入，不是 AI 自己识别" | branch-workflow-hook-enhancement 第 188 行 | ✅ Hook 注入，不是 AI 识别 |

---

## 三、推荐方案

**方案 B1**：Hook 调用 loader 识别 + Hook 根据模板生成 status.md

**架构**：
```
Hook (handler.sh)
  ↓ 调用
identify_type.py (CLI 包装器)
  ↓ 调用
loader._identify_workflow_type()
  ↓ 返回
JSON: {type, mode, breakpoints, sub_workflows}
  ↓
Hook 根据 JSON 生成 status.md（使用模板）
```

**优势**：
1. 复用 loader 识别逻辑（确定性、可验证）
2. Hook 控制注入时机（灵活性）
3. 职责分离（loader 识别、Hook 注入、executor 执行）
4. 避免 AI 自己识别的不确定性

---

## 四、实现步骤

### 步骤 1：创建 identify_type.py CLI 包装器

路径：`actions/identify_type.py`

功能：
- 调用 `WorkflowLoader.load()`
- 输出 JSON：`{type, mode, breakpoints, sub_workflows, workflow_name}`

### 步骤 2：修改 Hook handler.sh

替换第 50-123 行的自己识别逻辑：
```bash
# 调用 CLI 获取类型信息
IDENTIFY_CLI="$HOME/.hermes/skills/openclaw-imports/workflow-manager/actions/identify_type.py"
TYPE_INFO=$(python3 "$IDENTIFY_CLI" "$WORKFLOW_PATH" 2>/dev/null)

# 解析 JSON
workflow_type=$(echo "$TYPE_INFO" | python3 -c "import json,sys; print(json.load(sys.stdin).get('type', 'normal'))")
```

### 步骤 3：创建验证脚本

路径：`scripts/verify_type_consistency.py`

功能：验证 Hook 和 loader 识别结果一致

### 步骤 4：运行验证

验证所有工作流识别一致

---

## 五、执行方案位置

详细执行方案：`~/.hermes/plans/20260515-hook-type-identification/execution_plan.md`

---

## 六、核心教训

**不应该让 AI 自己识别工作流类型**：
- AI 识别准确率不可控
- 与代码执行逻辑可能不一致
- 违反已明确禁止的行为（handler.sh 第 160-162 行）

**应该由代码识别**：
- 确定性：相同输入一定相同输出
- 可验证性：可直接运行验证
- 一致性：loader、executor、Hook 使用同一逻辑
