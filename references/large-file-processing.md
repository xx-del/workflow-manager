# 大型文件处理策略

## 问题背景

在工作流执行中，delegate_task 创建的子 Agent 工具集有限制：
- 子 Agent 工具集可能不包含 Python/Shell 执行能力
- 子 Agent 无法执行编程脚本
- 大型压缩 JSON 文件（单行）难以解析

## 失败案例

**场景**：分析 1982 个 URL 的 JSON 文件（3.2MB）

**问题**：
1. JSON 文件是压缩单行格式
2. 子 Agent 的 read_file 工具被截断
3. 子 Agent 创建了 Python 脚本但无法执行

**错误输出**：
```
无法执行 Python 脚本：工具集不包含脚本执行能力
文件内容截断：read_file 返回的内容被截断，无法获取完整信息
```

## 解决方案

### 方案 1：主 AI 编写脚本 + terminal 执行（推荐）

当子 Agent 无法执行时，主 AI 应：

1. **编写分类脚本**：
```python
# /x/rank/dispatch-system/classify_urls.py
# 完整的分类逻辑，基于 CLAUDE.md 规则
```

2. **使用 terminal 执行**：
```bash
cd /x/rank/dispatch-system/
python3 classify_urls.py
```

3. **验证输出**：
```bash
ls -lh *.txt
cat report.txt
```

### 方案 2：jq 分批处理 + 多个 delegate_task

适用于可分割的 JSON 文件：

1. **分割文件**：
```bash
total=$(jq 'length' url_info.json)
batches=$(( (total + 29) / 30 ))
mkdir -p batches

for i in $(seq 0 $((batches-1))); do
  start=$((i * 30))
  end=$((start + 30))
  jq -c ".[$start:$end]" url_info.json > "batches/batch_$((i+1)).json"
done
```

2. **并行处理**：
```json
{
  "tool": "delegate_task",
  "params": {
    "tasks": [
      {"goal": "分析 batch_1.json...", "toolsets": ["file"]},
      {"goal": "分析 batch_2.json...", "toolsets": ["file"]},
      {"goal": "分析 batch_3.json...", "toolsets": ["file"]}
    ]
  }
}
```

### 方案 3：简化 JSON 格式

如果可能，提前处理 JSON 文件：

```bash
# 使用 jq 美化输出
jq '.' url_info.json > url_info_formatted.json
```

## 决策流程

```
发现大文件（>30KB）
    ↓
检查是否可分割
    ├─ 可分割 → jq 分批 + delegate_task 并行
    └─ 不可分割 → 主 AI 编写脚本 + terminal 执行
```

## 注意事项

1. **工具集限制**：
   - `toolsets: ["file"]` 仅包含文件操作工具
   - 不包含 Python/Shell 执行能力
   - 无法运行脚本

2. **文件格式**：
   - 压缩 JSON（单行）难以解析
   - 建议使用 jq 预处理
   - 或使用 Python 脚本直接读取

3. **性能考虑**：
   - jq 分批适合大量小任务
   - Python 脚本适合复杂逻辑
   - 选择基于任务复杂度

## 相关文档

- CLAUDE.md：智能分析规则
- WORKFLOW.md：工作流定义
- jq 文档：https://stedolan.github.io/jq/manual/
