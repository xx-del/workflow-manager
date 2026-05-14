# 工作流架构重构 v6.4 - Hook注入机制

**日期**：2026-05-13
**版本**：v6.4
**核心改进**：代码静态 + AI动态 + Hook注入

---

## 一、架构原则

### 核心理念

**代码只做静态功能，AI做动态决策**

### 职责划分

**代码静态层**：
- 路径索引（扫描工作流目录）
- 文件验证（检查文件存在性）
- JSON 解析（验证格式正确性）
- 初始模板生成（生成空 status.json）

**AI动态层**：
- 读取 WORKFLOW.md
- 分解任务（AI智能分解）
- 生成 status.md
- 调用 agent-pool
- 执行 pending_instructions
- 更新 status.json

---

## 二、Hook注入机制

### 注入时机

```
execute.py --init → 生成 status.json → Hook 检测 → 创建 status.md + 注入约束
```

### 注入内容

**1. 完整禁止事项（5个约束章节）**：

- 执行行为约束
- 主AI职责边界约束
- 异常处理约束
- 进度记录约束
- 完成判定约束

**2. 工作流类型识别**：

- branch（拼接工作流）
- heartbeat（断点工作流）
- normal（普通工作流）

**3. 断点位置标注**：

- 收集断点步骤
- 标注格式：`⛔ [子工作流名称] 步骤名称（断点）`

**4. 拼接工作流展开指导**：

- 如何读取 _index.yaml
- 如何展开子工作流
- 如何处理嵌套拼接
- 如何收集断点

---

## 三、工作流类型识别

### 识别优先级

**1. branch（拼接工作流）**：
- `type: branch`
- 或所有节点 `calls: workflow-manager`

**2. heartbeat（断点工作流）**：
- `config.heartbeat.enabled: true`
- 或节点 `type: breakpoint` 或 `type: auto`
- 或节点 `trigger: heartbeat`

**3. normal（普通工作流）**：
- 其他情况

### AI执行时

- Hook 自动识别类型并注入约束到 status.md
- AI 只需阅读 status.md，无需判断类型
- status.md 已包含所有必要信息

---

## 四、拼接工作流展开

### 展开流程

**步骤1：读取 _index.yaml**
- 定位文件：`$WORKFLOW_DIR/_index.yaml`

**步骤2：解析子工作流列表**
- 对每个子工作流：
  - 定位目录：`/x/AI/openclaw/workflows/{子工作流名称}/`
  - 读取 `_index.yaml` 或 `WORKFLOW.md`

**步骤3：递归处理每个子工作流**
识别类型：
- branch：继续递归展开
- heartbeat：标注断点位置
- normal：直接解析步骤

**步骤4：收集所有断点**
- 对每个子工作流检查是否有断点步骤
- 标注格式：`⛔ [子工作流名称] 步骤名称（断点）`

**步骤5：生成完整计划**
- 合并所有子工作流步骤
- 标注断点位置
- 更新到本计划文档

---

## 五、用户纠正记录

### 纠正1：节点识别部分错误

**用户反馈**：
> "注入约束阶段正确，但是节点识别部分错误"

**问题**：
- 拼接工作流展开后可能包含断点
- 需要递归识别子工作流类型

**修复**：
- 增加"如何展开"完整步骤
- 增加递归处理断点的指导

### 纠正2：SKILL.md定位

**用户反馈**：
> "Skill文档失去指导意义，只有在创建和验证技能的时候才有指导意义"

**理解**：
- 执行时 AI 看的是 status.md
- SKILL.md 是创建和验证时的依据文档
- 不需要在 SKILL.md 中教 AI 如何识别类型

### 纠正3：覆盖所有工作流类型

**用户反馈**：
> "要覆盖到所有类型的工作流节点，能让我们的AI识别后生成计划文档"

**修复**：
- 增加拼接工作流展开指导
- 增加断点位置标注
- 增加递归断点识别

---

## 六、实施记录

**修改文件**：
- `hooks/workflow-ai-remind/handler.sh`：完整Hook注入逻辑

**备份位置**：
- `hooks/workflow-ai-remind/handler.sh.bak_20260513_220604`

**测试验证**：
- ✅ 普通工作流识别
- ✅ 禁止事项完整注入
- ⏳ 拼接工作流测试（中文路径问题）
- ⏳ 断点工作流测试

---

## 七、关键代码逻辑

### Hook注入代码结构

```bash
# 1. 工作流类型识别（Python解析YAML）
result=$(python3 -c "
import yaml
import json
# ... 识别逻辑 ...
print(json.dumps(output))
")

# 2. 创建 status.md 基础结构
cat > "$WORKFLOW_DIR/status.md" << EOF
# 工作流执行计划
... 5个约束章节 ...
EOF

# 3. 注入类型特殊约束
if [ "$workflow_type" == "branch" ]; then
    # 拼接工作流约束 + 展开指导
fi

if [ "$workflow_type" == "heartbeat" ]; then
    # 断点工作流约束 + 断点位置标注
fi
```

---

## 八、后续优化

- [ ] 测试拼接工作流展开
- [ ] 测试断点工作流断点识别
- [ ] 测试嵌套拼接工作流
- [ ] 验证 Hook 在所有场景下的触发
