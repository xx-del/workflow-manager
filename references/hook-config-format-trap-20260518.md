# Hook 配置格式陷阱

**发现日期**: 2026-05-18
**问题类型**: SKILL.md 配置格式与 translator.py 解析逻辑不匹配

## 问题现象

- workflow-manager 的 Hook 不触发（trigger_count = 0）
- hooks_manifest.json 中 commands 字段为空
- status.md 未更新

## 根因分析

### 问题链

```
SKILL.md Hook 配置为字符串格式
    ↓
translator.py 的 translate_hook() 不处理字符串格式
    ↓
commands 保持为空
    ↓
handle_post_tool_call 循环不执行（for command in commands）
    ↓
Hook 未触发
```

### translator.py 原始逻辑

```python
def translate_hook(claude_event: str, hook_config: dict) -> Optional[dict]:
    commands = []
    if isinstance(hook_config, list):      # 只处理列表
        ...
    elif isinstance(hook_config, dict):   # 或字典
        ...
    # 字符串格式不处理，commands 保持为空！
```

## 格式对比

| 格式 | SKILL.md 写法 | 解析结果 |
|------|---------------|----------|
| 字符串（错误） | `PostToolUse: workflow-progress/handler.sh` | `commands: []` |
| 列表（正确） | `PostToolUse: [{hooks: [{type: command, command: bash ...}]}]` | `commands: ['bash ...']` |
| 字典（正确） | `PostToolUse: {hooks: [{type: command, command: bash ...}]}` | `commands: ['bash ...']` |

## 修复方案

### 方案 A：修复 SKILL.md 格式

将字符串格式改为列表格式：

```yaml
# 修改前
hooks:
  PostToolUse: workflow-progress/handler.sh

# 修改后
hooks:
  PostToolUse:
    - hooks: [{type: command, command: bash hooks/workflow-progress/handler.sh}]
```

### 方案 B：增强 translator.py（推荐）

修改 translator.py 支持字符串格式（向后兼容）：

```python
def translate_hook(claude_event: str, hook_config: dict) -> Optional[dict]:
    commands = []
    
    # 新增：支持字符串格式
    if isinstance(hook_config, str):
        cmd = hook_config if hook_config.startswith('bash ') else f'bash {hook_config}'
        commands.append(cmd)
    elif isinstance(hook_config, list):
        ...
    elif isinstance(hook_config, dict):
        ...
```

## 验证方法

```bash
# 检查 hooks_manifest.json
cat ~/.hermes/plugins/skill-hook-bridge/hooks_manifest.json | \
  python3 -c "
import json,sys
d=json.load(sys.stdin)
skill=[s for s in d['skills'] if s['name']=='workflow-manager'][0]
print('Hook 配置状态:')
for h in skill['hooks']:
    status = '✅' if h['commands'] else '❌'
    print(f\"  {status} {h['claude_event']}: {h['commands'][:1] if h['commands'] else '空'}\")
"
```

## 影响范围

- 所有使用 skill-hook-bridge 的技能
- Hook 配置格式错误的技能都会导致 Hook 不触发
- 影响功能：status.md 更新、约束注入、进度追踪

## 相关文件

- `~/.hermes/skills/openclaw-imports/workflow-manager/SKILL.md`
- `~/.hermes/plugins/skill-hook-bridge/translator.py`
- `~/.hermes/plugins/skill-hook-bridge/hooks_manifest.json`

## 执行记录

1. 发现 workflow-manager 的 Hook 未触发
2. 分析 hooks_manifest.json，发现 commands 为空
3. 检查 SKILL.md 格式，发现是字符串格式
4. 检查 translator.py，发现不处理字符串格式
5. 手动触发 Hook 扫描
6. 增强 translator.py 支持字符串格式
7. 验证 Hook 正常触发（PreToolUse: 3 次，PostToolUse: 3 次）
