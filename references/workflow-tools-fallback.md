# workflow-tools.js 不存在时的替代方案

> **状态**: 已验证可用 (2026-05-09)

## 背景

`workflow-tools.js` 文件已从 workflow-manager 技能中移除。所有工作流操作应使用以下替代方案。

## 替代方案速查表

| 原方案 | 替代方案 |
|--------|----------|
| `node workflow-tools.js list` | `ls ~/.hermes/workflows/` |
| `node workflow-tools.js read "名称"` | `cat ~/.hermes/workflows/名称/_index.yaml` |
| `node workflow-tools.js status "名称"` | `cat ~/.hermes/workflows/名称/status.json` |
| `node workflow-tools.js update "名称" '{...}'` | Python 脚本（见下文） |

## 详细命令

### 列出所有工作流

```bash
# 方法 1: 列出目录
ls ~/.hermes/workflows/

# 方法 2: 查找所有定义文件
find ~/.hermes/workflows -name "_index.yaml" -o -name "WORKFLOW.md"

# 方法 3: 过滤备份目录
ls ~/.hermes/workflows/ | grep -v "^_" | grep -v "backup"
```

### 读取工作流定义

```bash
# 读取 YAML 定义
cat ~/.hermes/workflows/<工作流名称>/_index.yaml

# 读取 Markdown 定义（详细步骤）
cat ~/.hermes/workflows/<工作流名称>/WORKFLOW.md
```

### 查询工作流状态

```bash
# 读取状态文件
cat ~/.hermes/workflows/<工作流名称>/status.json

# 使用 jq 格式化输出
jq '.' ~/.hermes/workflows/<工作流名称>/status.json
```

### 更新工作流状态

```python
import json
from pathlib import Path

status_file = Path.home() / '.hermes' / 'workflows' / '<工作流名称>' / 'status.json'
status = json.loads(status_file.read_text())

# 更新字段
status['status'] = 'completed'
status['heartbeat']['wih']['complete'] = True

status_file.write_text(json.dumps(status, indent=2, ensure_ascii=False))
print('✅ 状态已更新')
```

### 大 JSON 文件处理

当 `url_info.json` 等文件较大（>30KB）时，使用 `jq` 分批处理：

```bash
# 查看总条目数
total=$(jq length url_info.json)

# 计算批次（每批30条）
batches=$(( (total + 29) / 30 ))

# 分割 JSON 文件
for i in $(seq 0 $((batches-1))); do
  start=$((i * 30))
  end=$((start + 30))
  jq -c ".[$start:$end]" url_info.json > "batch_$((i+1)).json"
done

# 提取特定字段
jq -r '.[] | select(.title != null) | "\(.url)|\(.title)"' url_info.json

# 过滤关键词
jq -r '.[] | select(.title | test("关键词"; "i")) | .url' url_info.json
```

## 最佳实践

1. **优先读取 _index.yaml**：包含结构化的工作流定义
2. **WORKFLOW.md 作为补充**：包含详细执行步骤和说明
3. **status.json 状态管理**：使用 Python 直接更新，避免 Node.js 依赖
4. **大文件用 jq**：避免读取完整 JSON 到内存

## 相关文件

- 工作流定义：`_index.yaml`
- 执行步骤：`WORKFLOW.md`
- 状态文件：`status.json`
- 历史记录：`history/<日期>.json`
