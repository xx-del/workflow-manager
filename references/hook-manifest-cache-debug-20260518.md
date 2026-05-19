# Hook Manifest 缓存过期问题

**发现时间**: 2026-05-18
**问题**: SKILL.md 格式正确，但 hooks_manifest.json 的 commands 字段为空

## 问题链

```
SKILL.md 格式正确
    ↓
hooks_manifest.json 未更新（缓存过期）
    ↓
commands = []
    ↓
handle_post_tool_call 循环不执行（for command in []: 不迭代）
    ↓
Hook 未触发
```

## 诊断步骤

1. **检查 manifest**：
```bash
cat ~/.hermes/plugins/skill-hook-bridge/hooks_manifest.json | \
  python3 -c "
import json,sys
d=json.load(sys.stdin)
skill=[s for s in d['skills'] if s['name']=='workflow-manager'][0]
print('生成时间:', d.get('generated_at'))
for h in skill['hooks']:
    status = '✅' if h['commands'] else '❌'
    print(f\"{status} {h['claude_event']}: commands={h['commands']}\")
"
```

2. **预期结果**：
   - ✅ commands 有值 → manifest 正常
   - ❌ commands 为空 → manifest 缓存过期

## 手动触发扫描

当 manifest 缓存过期时，手动触发 Hook 重新扫描：

```python
import sys
sys.path.insert(0, '/home/kali/.hermes/plugins/skill-hook-bridge')

from scanner import scan_skill_hooks
from translator import translate_hook
import json
from pathlib import Path
from datetime import datetime

# 配置
skills_dirs = ["~/.hermes/skills", "~/.hermes/skills/openclaw-imports"]

# 扫描技能
skills_with_hooks = scan_skill_hooks(skills_dirs)

# 转换 Hook
for skill in skills_with_hooks:
    skill["translated_hooks"] = []
    for claude_event, hook_config in skill["hooks"].items():
        translated = translate_hook(claude_event, hook_config)
        if translated:
            skill["translated_hooks"].append(translated)

# 构建新的 manifest
manifest = {
    "version": "1.0",
    "generated_at": datetime.now().isoformat(),
    "skills": []
}

for skill in skills_with_hooks:
    skill_entry = {
        "name": skill["skill_name"],
        "path": skill["skill_path"],
        "enabled": True,
        "hooks": []
    }
    
    for translated in skill["translated_hooks"]:
        hook_entry = {
            "claude_event": translated["original_event"],
            "hermes_event": translated["hermes_event"],
            "commands": translated["commands"],
            "tool_matchers": translated["tool_matchers"],
            "enabled": True,
            "hook_id": None,
            "trigger_count": 0,
            "last_triggered": None
        }
        skill_entry["hooks"].append(hook_entry)
    
    manifest["skills"].append(skill_entry)

# 写入 manifest
manifest_file = Path("/home/kali/.hermes/plugins/skill-hook-bridge/hooks_manifest.json")
manifest_file.write_text(json.dumps(manifest, indent=4))

print(f"已重新扫描 {len(skills_with_hooks)} 个技能")
```

## translator.py 格式支持

**问题**: translator.py 原来不支持字符串格式的 Hook 配置

**修复**: 增强 translate_hook 函数支持三种格式

```python
def translate_hook(claude_event: str, hook_config: dict) -> Optional[dict]:
    hermes_event = HOOK_MAPPING.get(claude_event)
    if not hermes_event:
        return None
    commands = []
    
    # 新增：支持字符串格式（向后兼容）
    if isinstance(hook_config, str):
        cmd = hook_config if hook_config.startswith('bash ') else f'bash {hook_config}'
        commands.append(cmd)
    elif isinstance(hook_config, list):
        for item in hook_config:
            for h in item.get('hooks', []):
                if h.get('type') == 'command':
                    commands.append(h.get('command', ''))
    elif isinstance(hook_config, dict):
        for h in hook_config.get('hooks', []):
            if h.get('type') == 'command':
                commands.append(h.get('command', ''))
    ...
```

## 关键教训

1. **manifest 缓存优先**：Hook 不触发时，先检查 manifest，不是 SKILL.md
2. **on_session_start 触发**：skill-hook-bridge 在会话开始时扫描，会话中修改 SKILL.md 不会立即生效
3. **备份版本冲突**：多个技能同名或备份目录也会被扫描，需禁用（重命名为 .disabled）
