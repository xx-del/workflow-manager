# Hook 配置格式与 status 文件定位

**文档日期**: 2026-05-18
**来源会话**: workflow-manager Hook 失效修复

---

## 一、Hook 配置格式问题

### 问题描述

workflow-manager 的 Hook 未触发，status.md 未更新。

### 根因分析

SKILL.md 中的 Hook 配置使用了字符串格式：

```yaml
# 错误格式
hooks:
  UserPromptSubmit: workflow-context/handler.sh
```

skill-hook-bridge 的 translator.py 只解析列表/字典格式：

```python
def translate_hook(claude_event: str, hook_config: dict) -> Optional[dict]:
    commands = []
    if isinstance(hook_config, list):      # ✅ 解析列表
        ...
    elif isinstance(hook_config, dict):    # ✅ 解析字典
        ...
    # 字符串格式不处理，commands 保持为空
```

### 正确格式

```yaml
hooks:
  UserPromptSubmit:
    - hooks: [{type: command, command: bash hooks/workflow-context/handler.sh}]
  PreToolUse:
    - matcher: "terminal|delegate_task|write_file|patch"
      hooks: [{type: command, command: bash hooks/workflow-step-check/handler.sh}]
  PostToolUse:
    - hooks: [{type: command, command: bash hooks/workflow-progress/handler.sh}]
  Stop:
    - hooks: [{type: command, command: bash hooks/workflow-cleanup/handler.sh}]
```

### 验证方法

```bash
# 检查 hooks_manifest.json 中 commands 是否为空
cat ~/.hermes/plugins/skill-hook-bridge/hooks_manifest.json | \
  python3 -c "
import json,sys
d=json.load(sys.stdin)
skill=[s for s in d['skills'] if s['name']=='workflow-manager'][0]
for h in skill['hooks']:
    status = '✅' if h['commands'] else '❌'
    print(f\"{status} {h['claude_event']}: {h['commands'][:1] if h['commands'] else '空'}\")
"
```

---

## 二、hooks_manifest.json 缓存问题

### 现象

修改 SKILL.md 后，hooks_manifest.json 未更新，commands 仍为空。

### 解决方案

手动触发 Hook 扫描：

```python
import sys
sys.path.insert(0, '/home/kali/.hermes/plugins/skill-hook-bridge')

from scanner import scan_skill_hooks
from translator import translate_hook
import json
from pathlib import Path
from datetime import datetime

skills_dirs = ["~/.hermes/skills", "~/.hermes/skills/openclaw-imports"]
skills_with_hooks = scan_skill_hooks(skills_dirs)

for skill in skills_with_hooks:
    skill["translated_hooks"] = []
    for claude_event, hook_config in skill["hooks"].items():
        translated = translate_hook(claude_event, hook_config)
        if translated:
            skill["translated_hooks"].append(translated)

# ... 构建 manifest 并保存
```

---

## 三、status.md vs status.json 定位

### 关键发现

| 文件 | 生成时机 | 更新机制 | 定位 |
|------|----------|----------|------|
| status.md | 初始化时 | 不更新 | 静态执行计划 |
| status.json | 初始化时 | 主 AI 更新 | 动态状态文件 |

### 详细说明

**status.md**：
- 拼接工作流：execute.py 初始化时生成
- 叶子工作流：不生成（期望主 AI 生成，但有 bug）
- 内容：约束、步骤定义、验证清单
- 用途：告诉主 AI 应该做什么
- 更新：不更新（静态）

**status.json**：
- 所有工作流：execute.py 初始化时生成
- 内容：步骤执行状态、时间戳
- 用途：记录步骤执行状态
- 更新：主 AI 在步骤执行后更新（动态）

### 用户纠正记录

用户明确指出：
1. "status.md 这个玩意最后不是由hook让主ai生成了吗？"
2. "拼接工作流生成status.md之后 不是全部整合在一个status.md中了吗 只要执行这个不就可以了吗"

**正确理解**：
- 拼接工作流的 status.md 已包含所有子工作流步骤
- 主 AI 读取并执行统一的 status.md
- 状态记录在 status.json 中，不在 status.md 中

---

## 四、备份版本冲突问题

### 现象

备份版本（.backup 目录）被 scanner 扫描到，导致 Hook 重复执行或报错。

### 解决方案

彻底删除备份版本，不要只重命名为 .disabled：

```bash
# ❌ 错误做法
mv backup-dir backup-dir.disabled

# ✅ 正确做法
rm -rf backup-dir
```

**原因**：scanner.py 不过滤后缀，所有 SKILL.md 都会被扫描。

---

## 五、修复验证清单

- [ ] SKILL.md Hook 配置为列表格式
- [ ] hooks_manifest.json 中 commands 不为空
- [ ] 备份版本已彻底删除
- [ ] Hook trigger_count > 0（验证触发）
