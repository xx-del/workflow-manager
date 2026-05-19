# status.json 同步更新机制

## 问题背景

工作流执行时，status.json 不会自动同步更新，导致步骤状态丢失。

## 解决方案

**最小改动方案**：在 execute.py 的 generate_status_md() 函数中添加"执行后操作"章节。

## 实现位置

**文件**：`actions/execute.py`
**位置**：L136（约束章节之前）

## 修改内容

```python
# 在 md_lines.extend([...]) 之前添加：

post_instruction_lines = [
    "",
    "---",
    "",
    "## 执行后操作（必须）",
    "",
    "**步骤执行完成后，必须更新 status.json**：",
    "",
    "```bash",
    "python3 -c \"",
    "import json",
    "from datetime import datetime",
    f"path = '{workflow_dir}/status.json'",
    "with open(path, 'r+') as f:",
    "    d = json.load(f)",
    "    # 替换 STEP_ID 为实际步骤ID",
    "    d['steps']['STEP_ID']['status'] = 'completed'",
    "    d['steps']['STEP_ID']['completed_at'] = datetime.now().isoformat()",
    "    d['updated_at'] = datetime.now().isoformat()",
    "    f.seek(0)",
    "    json.dump(d, f, indent=2, ensure_ascii=False)",
    "    f.truncate()",
    "\"",
    "```",
    "",
    "---",
]

md_lines.extend(post_instruction_lines)
```

## 验证

- status.md 第 31+ 行包含"执行后操作"章节
- 主 AI 执行步骤后复制命令更新 status.json
- 其他文件零改动（Hook、SKILL.md 不变）

## 设计原则

**planning-with-files 哲学**：
- 前 30 行：告诉 AI 做什么
- 第 31+ 行：告诉 AI 怎么做（含更新指令）

## 测试案例

工作流：status-json-test
- 步骤 1-4 执行后，手动运行更新命令
- 验证 status.json 步骤状态变为 completed
