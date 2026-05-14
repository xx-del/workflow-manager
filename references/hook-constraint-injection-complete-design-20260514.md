# Hook 约束注入完整设计（备份恢复）

**创建时间**: 2026-05-14  
**来源**: 备份文件 `hooks-backup-20260514.tar.gz`  
**原始文件**: `workflow-ai-remind/handler.sh.backup`（312 行）

---

## 核心机制

**Hook 自动创建 status.md 并注入所有约束**

```bash
# 第 46 行关键逻辑
if [ "$status" == "initialized" ] && [ ! -f "$WORKFLOW_DIR/status.md" ]; then
    # 创建 status.md 并注入所有约束
fi
```

**这意味着**：
- ❌ 不是主 AI 生成 status.md
- ✅ 是 Hook 检测到 status.md 不存在时自动创建
- ✅ Hook 在创建时注入所有约束

---

## 完整注入内容

### 1. 基础约束（所有工作流）

```markdown
## 一、执行行为约束

**绝对禁止**:
- ❌ 禁止修改命令
- ❌ 禁止添加 timeout 参数
- ❌ 禁止跳过步骤

**必须遵守**:
- ✅ 严格按指令执行
- ✅ 验证每个输出
- ✅ 每步执行后更新状态

---

## 二、主AI职责边界约束

**禁止行为**:
- ❌ 禁止自己读取 _index.yaml
- ❌ 禁止自己判断步骤顺序
- ❌ 禁止直接调用 delegate_task 未通过 execute.py

---

## 三、异常处理约束

**处理流程**:
- 立即停止工作流（不诊断、不修复、不跳过）
- 上报异常现象
- 等待用户指示

---

## 四、进度记录约束

**必须记录**:
- 更新 status.json
- 记录执行日志

---

## 五、完成判定约束

**完成标准**:
- 所有步骤状态 = completed
- 所有预期输出文件存在
```

### 2. 拼接工作流特殊约束（type == branch）

```markdown
## 拼接工作流约束

**识别依据**:
- `type: branch` 或所有节点 `calls: workflow-manager`

**执行要求**:
- ⚠️  必须展开所有子工作流
- ⚠️  子工作流串行执行（禁止并行）
- ⚠️  所有子工作流完成才算完成

**如何展开**:

**步骤1：读取 _index.yaml**
定位文件：`$WORKFLOW_DIR/_index.yaml`

**步骤2：解析子工作流列表**
对每个子工作流：
- 定位目录：`/x/AI/openclaw/workflows/{子工作流名称}/`
- 读取 `_index.yaml` 或 `WORKFLOW.md`

**步骤3：递归处理每个子工作流**
识别类型：
- branch：继续递归展开
- heartbeat：标注断点位置
- normal：直接解析步骤

**步骤4：收集所有断点**
对每个子工作流：
检查是否有断点步骤

**断点标注格式**:
```
- ⛔ [子工作流名称] 步骤名称（断点）
```

**状态更新规则**:
- 主 AI 在执行子工作流前更新状态为 running
- 主 AI 在子工作流完成后更新状态为 completed
- 所有子工作流状态 = completed → 工作流完成
```

### 3. 断点工作流特殊约束（type == heartbeat）

```markdown
## 断点工作流约束

**识别依据**:
- 存在 `type: breakpoint` 或 `trigger: heartbeat` 的节点

**断点位置**:
- ⛔ 步骤名称（断点步骤）

**执行要求**:
- ⚠️  执行断点步骤后返回，等待心跳触发
- ⚠️  禁止跳过断点检查
- ⚠️  禁止手动继续后续步骤

**心跳机制**:
- 断点步骤完成后写入状态文件
- 心跳 cronjob 检测状态文件
- 心跳自动触发后续步骤
```

---

## 工作流类型识别逻辑

**Hook 自动识别工作流类型**（第 48-124 行）：

```python
# 1. branch 类型
if wf.get('type') == 'branch':
    workflow_type = 'branch'
elif all(n.get('calls') == 'workflow-manager' for n in nodes):
    workflow_type = 'branch'

# 2. heartbeat 类型
if workflow_type == 'normal':
    config = wf.get('config', {})
    if config.get('heartbeat', {}).get('enabled'):
        workflow_type = 'heartbeat'
    elif any(n.get('type') in ['breakpoint', 'auto'] for n in nodes):
        workflow_type = 'heartbeat'
    elif any(n.get('trigger') == 'heartbeat' for n in nodes):
        workflow_type = 'heartbeat'
```

---

## 完整流程（正确理解）

```
1. execute.py --init
   → 生成 status.json（status: initialized）
   → 不生成 status.md

2. 主 AI 读取 WORKFLOW.md
   → 理解工作流定义
   → 准备执行

3. Hook（PreToolUse）检测
   → 发现 status.json 存在且 status: initialized
   → 发现 status.md 不存在
   → 自动创建 status.md
   → 注入所有约束（基础约束 + 类型特殊约束）
   → 输出: "✅ 已注入约束到 status.md"

4. 后续每次工具调用
   → Hook 注入 status.md 内容（或约束章节）
   → 主 AI 看到约束并遵守

5. 主 AI 执行步骤
   → 使用 terminal 执行命令
   → 更新 status.json
```

---

## 当前问题

**当前 `handler.sh` 是简化版**，丢失了：
1. ❌ 自动创建 status.md
2. ❌ 注入完整约束
3. ❌ 工作流类型识别
4. ❌ 拼接工作流约束注入
5. ❌ 断点工作流约束注入

**备份文件保留了完整设计**（312 行）。

---

## 恢复方案

**方案 A：恢复备份文件**
```bash
cd ~/.hermes/skills/openclaw-imports/workflow-manager/hooks
tar -xzf hooks-backup-20260514.tar.gz
cp hooks-backup/workflow-ai-remind/handler.sh.backup workflow-step-check/handler.sh
```

**方案 B：创建新的 handler.sh**
- 参考 `status-md-constraint-injection-enhancement.md`
- 实现完整的约束注入逻辑
- 添加会话标记机制支持

---

## 教训

**本次降智原因**：
1. 未查找备份文件
2. 未参考已有设计文档
3. 凭记忆推测而非查阅实际代码

**未来预防**：
1. 遇到"之前设计过"的提示，立即搜索备份文件
2. 查找 `*.bak*`, `.backup*`, `.bk` 等备份目录
3. 查找 `references/` 目录下的设计文档
4. 不要凭记忆推测已有设计
