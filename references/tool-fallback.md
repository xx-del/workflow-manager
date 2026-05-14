# 工具不可用时的替代方法

## 问题描述

`workflow-tools.js` 可能不存在或无法执行，导致以下命令失败：

```bash
node ~/.hermes/skills/openclaw-imports/workflow-manager/src/workflow-tools.js list
# Error: Cannot find module '.../workflow-tools.js'
```

## 替代方法

| 工具用途 | 替代方法 |
|----------|----------|
| 列出工作流 | `search_files(path="~/.hermes/workflows", pattern="_index.yaml")` |
| 读取工作流定义 | `read_file(path="{workflow_path}/_index.yaml")` + `read_file(path="{workflow_path}/WORKFLOW.md")` |
| 查询状态 | `read_file(path="{workflow_path}/status.json")` |
| 更新状态 | `read_file` + 修改 JSON + `write_file` |

## 示例

### 列出所有工作流

```python
search_files(path="/home/kali/.hermes/workflows", pattern="_index.yaml")
```

### 读取工作流定义

```python
read_file(path="/home/kali/.hermes/workflows/URL分析/_index.yaml")
read_file(path="/home/kali/.hermes/workflows/URL分析/WORKFLOW.md")
```

### 查询工作流状态

```python
read_file(path="/x/rank/hwxinxisouji/liuliang/start/status.json")
```

### 更新工作流状态

```python
# 1. 读取现有状态
status = read_file(path="{workflow_path}/status.json")
status_json = json.loads(status)

# 2. 更新内容
status_json["updated"] = datetime.now().isoformat()
status_json["progress"]["current_step"] = step_id

# 3. 写回文件
write_file(path="{workflow_path}/status.json", content=json.dumps(status_json, indent=2))
```

## 发现时间

2026-05-11：执行 URL 分析工作流时发现 workflow-tools.js 不存在，使用 search_files + read_file 替代成功。
