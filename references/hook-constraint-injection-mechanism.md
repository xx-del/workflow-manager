# Hook 约束注入机制

## 架构变更（2026-05-13）

### 变更原因

v6.4 架构重构后，AI 负责分解任务，可能绕过 executor.py 直接读 WORKFLOW.md，导致约束无法注入。

### 旧架构

```
executor.py → generate_execution_plan_md() → 生成 status.md → 注入约束章节
```

**问题**：
- AI 绕过 executor.py → status.md 未生成 → 约束无法注入

### 新架构

```
execute.py --init → 生成 status.json → Hook 检测 → 创建 status.md + 注入约束
```

**优势**：
- Hook 在 pre_llm_call 事件触发，AI 必定能看到
- 约束注入不依赖 executor.py
- 支持中文路径（通过 --path 参数）

---

## 实现细节

### Hook 文件

`hooks/workflow-ai-remind/handler.sh`

### 触发条件

1. 存在 status.json
2. status.json 中 status == "initialized"
3. status.md 不存在

### 注入内容

**基础约束**（所有工作流）：
1. 执行行为约束
2. 主AI职责边界约束
3. 异常处理约束
4. 进度记录约束
5. 完成判定约束

**类型特殊约束**：
- branch：拼接工作流展开指导
- heartbeat：断点位置标注

---

## 工作流类型识别

### 识别优先级

1. **branch（拼接）**：
   - `type: branch`
   - 或所有节点 `calls: workflow-manager`

2. **heartbeat（断点）**：
   - `config.heartbeat.enabled: true`
   - 或节点 `type: breakpoint` 或 `type: auto`
   - 或节点 `trigger: heartbeat`

3. **normal（普通）**：
   - 其他

### 识别代码

```python
# 使用 Python 解析 _index.yaml
import yaml
with open('_index.yaml') as f:
    data = yaml.safe_load(f)
nodes = data['workflows'][0]['nodes']

# 识别类型
if all(n.get('calls') == 'workflow-manager' for n in nodes):
    workflow_type = 'branch'
elif any(n.get('type') in ['breakpoint', 'auto'] for n in nodes):
    workflow_type = 'heartbeat'
else:
    workflow_type = 'normal'
```

---

## 拼接工作流展开

### 关键原则

**拼接工作流没有 WORKFLOW.md**，需要读取叶节点（子工作流）的文档。

### 展开流程

1. 读取 _index.yaml 获取子工作流列表
2. 对每个子工作流：
   - 定位目录：`/x/AI/openclaw/workflows/{子工作流名称}/`
   - 读取 _index.yaml 或 WORKFLOW.md
   - 识别类型：
     - branch：继续递归展开
     - heartbeat：标注断点位置
     - normal：直接解析步骤
3. 收集所有断点
4. 合并所有步骤到 status.md

### 断点标注格式

```
- ⛔ [子工作流名称] 步骤名称（断点）
```

### 递归处理

拼接工作流展开后可能包含：
- normal 子工作流
- heartbeat 子工作流（需要标注断点）
- branch 子工作流（需要继续展开）

---

## 中文路径支持

### execute.py 修改

增加 `--path` 参数：

```python
def find_workflow_dir(workflow_name: str, workflow_path: str = None) -> Path:
    # 0. 如果提供了完整路径，直接使用
    if workflow_path:
        path = Path(workflow_path)
        if path.exists() and (path / 'WORKFLOW.md').exists():
            return path
    # ... 其他逻辑
```

### handler.sh 修改

支持路径参数：

```bash
# 支持路径参数
WORKFLOW_PATH="$1"

if [ -n "$WORKFLOW_PATH" ]; then
    if [ -f "$WORKFLOW_PATH/status.json" ]; then
        WORKFLOW_DIR="$WORKFLOW_PATH"
    fi
fi
```

### 使用方法

```bash
# 初始化
python execute.py 工作流名称 --init --path "/完整/路径"

# 注入约束
bash handler.sh "/完整/路径"
```

---

## SKILL.md 定位

**创建和验证时**：SKILL.md 是依据文档
**执行时**：status.md 是计划文档

执行时 AI 看的是 status.md，不是 SKILL.md。所有约束和类型信息必须在 status.md 中。
