# JSON 批量分析模式

## 适用场景

工作流步骤需要 AI 分析大量 JSON 数据（>30 条记录）

## 执行流程

### 1. 分割 JSON 文件

使用 jq 分割大 JSON 文件，避免子 agent 超时：

```bash
# 合并多个 JSON 文件
jq -s '.[0].assets + .[1].assets' file1.json file2.json > all_assets.json

# 分割成批次（每批 30 条）
total=$(jq 'length' all_assets.json)
batches=$(( (total + 29) / 30 ))
for i in $(seq 0 $((batches-1))); do
  start=$((i * 30))
  end=$((start + 30))
  jq -c ".[$start:$end]" all_assets.json > "batch_$((i+1)).json"
done
```

### 2. 并行启动子 Agent

使用 delegate_task 启动多个子 agent 并行分析：

```python
delegate_task(
  tasks=[
    {"goal": "分析 batch_1.json", "context": "判断标准...", "toolsets": ["terminal", "file"]},
    {"goal": "分析 batch_2.json", "context": "判断标准...", "toolsets": ["terminal", "file"]},
    {"goal": "分析 batch_N.json", "context": "判断标准...", "toolsets": ["terminal", "file"]}
  ]
)
```

**约束**：
- 最大并行 3 个 Task
- 每个 Task 处理 30 个 URL
- 超出需分批执行

### 3. 合并结果

```bash
jq -s 'add' batch_1_result.json batch_2_result.json > all_results.json
```

### 4. 按分类写入文件

```bash
# 国家电网资产
jq -r '.[] | select(.category | contains("国家电网")) | .url' all_results.json > guojiadianwang.txt

# 电力行业资产
jq -r '.[] | select(.category | contains("电力行业")) | .url' all_results.json > dianli.txt

# 排除资产
jq -r '.[] | select(.category == "排除") | .url' all_results.json > excluded.txt
```

## 输出格式要求

**纯 URL 格式**，不带任何前缀/后缀/注释：

```
http://example.com
http://another.example.com
```

**错误示例** ❌：
```
电力工程知识库管理系统|http://82.156.224.33:8099|10
国家电网资产: http://example.com
```

## 判断标准传递

子 agent 需要接收完整的判断标准：

- 三问判断法
- 评分标准
- 分类规则

通过 `context` 参数传递，或引用 CLAUDE.md 文件路径。

## 注意事项

1. **禁止使用 Python/Shell 脚本处理数据**，判断逻辑在 AI
2. **禁止使用 cat 读取大 JSON**，使用 jq 分批处理
3. **子 agent 返回结构化结果**：`[{url, score, category, reason}]`
4. **主 agent 汇总结果**，验证总数是否匹配

## 示例案例

**电力数据分析工作流**（2026-05-14）：
- 总 URL：63 个
- 分批：3 批次（30+30+3）
- 并行：3 个子 agent
- 耗时：约 3 分钟
- 输出：guojiadianwang.txt (3个)、dianli.txt (22个)、excluded.txt (10个)
