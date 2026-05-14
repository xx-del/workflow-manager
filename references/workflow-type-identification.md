# 工作流类型识别机制

## 类型判定优先级

从 `loader.py` 第 162-199 行提取的识别逻辑：

### 1. branch（拼接工作流）

**识别条件**（满足任一）：
- `type: branch`（显式声明）
- 所有节点 `calls: workflow-manager`

**特征**：
- 多个子工作流串联
- 子工作流串行执行
- 所有子工作流完成才算完成

**示例**：
```yaml
# _index.yaml
workflows:
- id: zichan-shouji-liucheng
  name: 资产收集流程
  nodes:
  - calls: workflow-manager
    name: 电力数据
  - calls: workflow-manager
    name: 域名处理
  - calls: workflow-manager
    name: 端口扫描
```

---

### 2. heartbeat（断点工作流）

**识别条件**（满足任一）：
- `config.heartbeat.enabled: true`
- 节点 `type: breakpoint` 或 `type: auto`
- 节点 `trigger: heartbeat`
- 节点 `heartbeat.enabled: true`

**特征**：
- 包含断点步骤
- 执行断点后返回
- 等待心跳触发后续步骤

**示例**：
```yaml
# _index.yaml
workflows:
- id: home-loudou
  name: home漏扫
  config:
    heartbeat:
      enabled: true
  nodes:
  - type: breakpoint
    name: 执行扫描
```

---

### 3. normal（普通工作流）

**识别条件**：
- 不满足 branch 或 heartbeat 的任何条件

**特征**：
- 标准线性执行
- 无特殊约束

**示例**：
```yaml
# _index.yaml
workflows:
- id: dianli-shuju
  name: 电力数据
  mode: serial
  nodes:
  - calls: agent-pool
    name: 解析日期范围
  - calls: agent-pool
    name: 备份并清理
```

---

## Hook 自动识别实现

**文件**：`hooks/workflow-ai-remind/handler.sh`

**逻辑**：
```bash
# 方法1：读取 _index.yaml
workflow_type=$(python3 -c "
import yaml
with open('$WORKFLOW_DIR/_index.yaml') as f:
    data = yaml.safe_load(f)
workflows = data.get('workflows', [])
if workflows:
    wf = workflows[0]
    
    # 1. branch
    if wf.get('type') == 'branch':
        print('branch')
    nodes = wf.get('nodes', [])
    if all(n.get('calls') == 'workflow-manager' for n in nodes):
        print('branch')
    
    # 2. heartbeat
    config = wf.get('config', {})
    if config.get('heartbeat', {}).get('enabled'):
        print('heartbeat')
    if any(n.get('type') in ['breakpoint', 'auto'] for n in nodes):
        print('heartbeat')
    
    # 3. normal
    print('normal')
")

# 方法2：兼容旧格式（WORKFLOW.md 元信息）
if grep -q "^type:.*branch" WORKFLOW.md; then
    workflow_type="branch"
fi
```

---

## 约束注入

**注入时机**：
- `execute.py --init` 生成 status.json
- Hook 检测到 status.json 且 status.md 不存在
- Hook 自动创建 status.md 并注入约束

**注入内容**：
- 基础约束（所有工作流）
- 类型特殊约束（branch/heartbeat）

**AI执行时**：
- 只需阅读 status.md
- 所有约束和类型信息已包含
- 无需判断类型
