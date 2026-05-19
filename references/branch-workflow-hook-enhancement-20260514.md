# 拼接工作流与断点工作流Hook增强方案

日期：2026-05-14
状态：已同意，待执行

---

## 一、核心原则

**浩克机制优先**：
- 机制优先，代码次之
- 易用性、可用性优先
- 统筹考虑所有工作流类型
- 禁止优先考虑写代码

---

## 二、工作流类型识别

**类型判定规则**（loader.py已实现）：

| 类型 | 判定条件 |
|------|---------|
| `branch` | `type: branch` 或所有节点 `calls: workflow-manager` |
| `heartbeat` | `config.heartbeat.enabled=true` 或节点有 `type: breakpoint/auto` |
| `normal` | 其他 |

---

## 三、Hook统一处理逻辑

**workflow-context/handler.sh 增强**：

```bash
# 1. 读取 _index.yaml 识别类型
INDEX_YAML="$WORKFLOW_DIR/$WORKFLOW_NAME/_index.yaml"
if [[ -f "$INDEX_YAML" ]]; then
    WORKFLOW_TYPE=$(python3 -c "
import yaml
index = yaml.safe_load(open('$INDEX_YAML'))
nodes = index.get('nodes', [])
config = index.get('config', {})

# branch
if index.get('type') == 'branch' or all(n.get('calls') == 'workflow-manager' for n in nodes):
    print('branch')
# heartbeat
elif config.get('heartbeat', {}).get('enabled') or any(n.get('type') in ['breakpoint', 'auto'] for n in nodes):
    print('heartbeat')
# normal
else:
    print('normal')
")
fi

# 2. 根据类型注入不同内容
case "$WORKFLOW_TYPE" in
    branch)
        echo "🔄 拼接工作流检测"
        echo ""
        echo "子工作流路径："
        python3 -c "
import yaml
index = yaml.safe_load(open('$INDEX_YAML'))
for node in index['nodes']:
    if node.get('calls') == 'workflow-manager':
        print(f\"- {node['name']}: ~/.hermes/workflows/{node['name']}/WORKFLOW.md\")
"
        echo ""
        echo "📋 主AI任务：按顺序读取上述WORKFLOW.md，合并生成统一status.md"
        ;;
    heartbeat)
        echo "💓 断点工作流检测"
        echo ""
        echo "断点步骤："
        python3 -c "
import yaml
index = yaml.safe_load(open('$INDEX_YAML'))
for node in index['nodes']:
    if node.get('type') in ['breakpoint', 'auto']:
        print(f\"- 步骤{node['id']}: {node['name']} (type: {node['type']})\")
"
        echo ""
        echo "📋 主AI任务：执行到断点步骤后停止，等待心跳接管"
        ;;
    normal)
        # 普通工作流：无需额外提示
        ;;
esac

# 3. 正常注入前30行（所有类型都执行）
head -30 "$STATUS_FILE"
```

---

## 四、注入内容示例

### 普通工作流

```
（无额外提示，直接注入status.md前30行）
```

### 拼接工作流

```
🔄 拼接工作流检测

子工作流路径：
- 电力数据: ~/.hermes/workflows/电力数据/WORKFLOW.md
- 域名处理: ~/.hermes/workflows/域名处理/WORKFLOW.md
- 端口扫描: ~/.hermes/workflows/端口扫描/WORKFLOW.md
- URL生成: ~/.hermes/workflows/URL生成/WORKFLOW.md
- URL分析: ~/.hermes/workflows/URL分析/WORKFLOW.md

📋 主AI任务：按顺序读取上述WORKFLOW.md，合并生成统一status.md

（然后注入status.md前30行）
```

### 断点工作流

```
💓 断点工作流检测

断点步骤：
- 步骤3: 数据下载 (type: breakpoint)

📋 主AI任务：执行到断点步骤后停止，等待心跳接管

（然后注入status.md前30行）
```

---

## 五、主AI执行流程

### 普通工作流

```
读取注入的status.md前30行
→ 正常执行
```

### 拼接工作流

```
读取注入的子工作流路径
→ 按顺序读取每个WORKFLOW.md
→ 合并所有步骤：
   - 步骤编号连续（1,2,3...35）
   - 步骤名称加前缀（[电力数据] 解析日期范围）
→ 生成统一status.md
→ 正常执行
```

### 断点工作流

```
读取注入的断点步骤信息
→ 执行到断点步骤
→ 停止，等待心跳接管
```

---

## 六、方案优势

| 优势 | 说明 |
|------|------|
| ✅ 统一处理 | 一个Hook处理所有类型 |
| ✅ 现有机制不变 | 前30行+约束仍注入 |
| ✅ 类型自动识别 | 复用loader.py逻辑 |
| ✅ 零代码 | Hook只输出路径/断点信息 |
| ✅ 主AI根据提示自动处理 | 符合浩克机制 |

---

## 七、关键纠正记录

**用户纠正1**：status.md是主AI生成的，不是代码生成的
- 教训：查看SKILL.md理解机制，不要凭记忆推测

**用户纠正2**：浩克机制优先，不要优先考虑代码
- 教训：机制 > 代码，易用性 > 技术实现

**用户纠正3**：路径信息由Hook注入，不是AI自己识别
- 教训：Hook注入路径信息，主AI根据注入内容执行

**用户纠正4**：需要统筹考虑所有工作流类型
- 教训：不能只设计一种情况，要统一处理所有类型

**用户纠正5**：写那么多代码有毛线用
- 教训：零代码优先，Hook只输出信息，主AI自己处理
