# Hook 配置格式与 Manifest 同步问题

**发现时间**: 2026-05-18
**问题类型**: 配置格式 + 缓存同步

---

## 问题描述

### 现象
- workflow-manager 的 Hook 未触发
- hooks_manifest.json 中 commands 为空
- status.md 在步骤执行后未更新

### 根因分析

**问题链**：
```
SKILL.md Hook 配置格式（疑似）
    ↓
translator.py 解析失败
    ↓
commands 为空
    ↓
handle_post_tool_call 循环不执行
    ↓
Hook 未触发
```

**实际情况**：
1. SKILL.md 的 Hook 配置**已经是正确格式**（列表格式）
2. 问题在于 **hooks_manifest.json 未更新**（缓存问题）
3. 需要手动触发 Hook 重新扫描

---

## Hook 配置格式规范

### 正确格式（列表格式）

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

### 错误格式（字符串格式）

```yaml
hooks:
  UserPromptSubmit: workflow-context/handler.sh  # ❌ 不推荐
  PreToolUse: workflow-step-check/handler.sh     # ❌ 不推荐
```

**注意**：translator.py 已增强，现在支持字符串格式（向后兼容），但推荐使用列表格式。

---

## 备份版本问题

### 问题
- 备份版本被禁用后（mv → .disabled 后缀）
- scanner 仍然扫描到该目录
- 但备份版本缺少 `hooks/` 目录
- 导致 Hook 执行失败：`No such file or directory`

### 解决方案
1. 彻底删除备份版本，而非仅重命名
2. 或修改 scanner 过滤 `.disabled` 后缀的目录

---

## 修复步骤

### 步骤 1：手动触发 Hook 扫描

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

manifest = {
    "version": "1.0",
    "generated_at": datetime.now().isoformat(),
    "skills": [...]
}

manifest_file = Path("/home/kali/.hermes/plugins/skill-hook-bridge/hooks_manifest.json")
manifest_file.write_text(json.dumps(manifest, indent=4))
```

### 步骤 2：验证 Hook 配置

```bash
cat ~/.hermes/plugins/skill-hook-bridge/hooks_manifest.json | \
  python3 -c "
import json,sys
d=json.load(sys.stdin)
skill=[s for s in d['skills'] if s['name']=='workflow-manager'][0]
for h in skill['hooks']:
    status = '✅' if h['commands'] else '❌'
    print(f'{status} {h[\"claude_event\"]}: commands={h[\"commands\"][:1] if h[\"commands\"] else \"空\"}')
"
```

### 步骤 3：删除备份版本

```bash
rm -rf ~/.hermes/skills/openclaw-imports/workflow-manager/.backup/findings-mechanism-*
```

---

## 验证方法

### 验证 Hook 触发

```bash
# 检查 trigger_count
cat ~/.hermes/plugins/skill-hook-bridge/hooks_manifest.json | \
  python3 -c "
import json,sys
d=json.load(sys.stdin)
skill=[s for s in d['skills'] if s['name']=='workflow-manager'][0]
for h in skill['hooks']:
    print(f'{h[\"claude_event\"]}: trigger_count={h[\"trigger_count\"]}')
"
```

### 验证 status.md 更新

```bash
# 执行步骤前后对比
stat ~/.hermes/workflows/<工作流名>/status.md | grep Modify
```

---

## 长期优化

### translator.py 增强（已实施）

```python
def translate_hook(claude_event: str, hook_config: dict) -> Optional[dict]:
    commands = []
    
    # 新增：支持字符串格式（向后兼容）
    if isinstance(hook_config, str):
        cmd = hook_config if hook_config.startswith('bash ') else f'bash {hook_config}'
        commands.append(cmd)
    elif isinstance(hook_config, list):
        # 原有逻辑
        ...
```

### scanner 过滤优化（建议）

修改 scanner.py 过滤 `.disabled` 后缀的目录：

```python
def scan_skill_hooks(skills_dirs: list[str]) -> list[dict]:
    results = []
    for skills_dir in skills_dirs:
        for skill_file in skills_path.rglob("SKILL.md"):
            skill_path = skill_file.parent
            
            # 新增：过滤 .disabled 后缀
            if skill_path.name.endswith('.disabled'):
                continue
                
            # 原有逻辑
            ...
```

---

## 教训

1. **不要只检查配置格式**：问题可能在缓存/同步层面
2. **备份版本要彻底删除**：重命名后缀仍会被扫描
3. **Hook 不触发时检查 commands**：commands 为空是最常见原因
4. **验证要完整**：不只检查文件存在，还要检查触发次数和更新时间

---

## 相关文件

- `~/.hermes/skills/openclaw-imports/workflow-manager/SKILL.md`
- `~/.hermes/plugins/skill-hook-bridge/hooks_manifest.json`
- `~/.hermes/plugins/skill-hook-bridge/translator.py`
- `~/.hermes/plugins/skill-hook-bridge/scanner.py`
