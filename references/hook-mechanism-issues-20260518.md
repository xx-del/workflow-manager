# Hook 机制问题记录 (2026-05-18)

## 问题 1：translator.py 不支持字符串格式

**现象**：
- SKILL.md 中 Hook 配置为字符串格式：`PostToolUse: workflow-progress/handler.sh`
- translator.py 只处理列表和字典格式
- 导致 commands 为空，Hook 无法执行

**修复**：
增强 translator.py 支持字符串格式：
```python
if isinstance(hook_config, str):
    cmd = hook_config if hook_config.startswith('bash ') else f'bash {hook_config}'
    commands.append(cmd)
```

**影响**：向后兼容，支持三种格式（字符串、列表、字典）

---

## 问题 2：备份版本仍被扫描

**现象**：
- 备份目录重命名为 `.disabled` 后缀
- scanner 仍扫描到该目录
- hooks_manifest.json 包含备份版本
- Hook 执行时因缺少 hooks/ 目录而失败

**报错**：
```
Hook 命令执行失败: [Errno 2] No such file or directory: 
'/home/kali/.hermes/skills/.../findings-mechanism-20260514_165257'
```

**修复**：
彻底删除备份版本，而非仅重命名

**教训**：
- scanner 不过滤 .disabled 后缀
- 需彻底删除不需要的技能版本

---

## 问题 3：update_manifest 重置 trigger_count

**现象**：
- 每次 on_session_start 触发时，update_manifest 重新生成 manifest
- trigger_count 被重置为 0
- 无法统计 Hook 实际触发次数

**代码位置**：
`manager.py` 的 `update_manifest` 方法：
```python
hook_entry = {
    ...
    "trigger_count": 0,  # 每次重置
    "last_triggered": None
}
```

**影响**：统计不准确，但不影响 Hook 实际执行

**修复建议**：
保留已有的 trigger_count 和 last_triggered

---

## 问题 4：execute.py 不生成 status.md

**现象**：
- 叶子工作流初始化后，status.md 未生成
- execute.py 的 return 语句在生成 status.md 之前

**代码位置**：
`execute.py` 第 624 行的 return 在 generate_status_md 之前

**影响**：叶子工作流无 status.md 文件

**修复建议**：
调整 return 位置，确保 status.md 生成后再 return

---

## 验证结果

修复后 Hook 功能正常：
- ✅ commands 不为空
- ✅ Hook 正常触发
- ✅ 无报错
- ✅ 工作流上下文正确注入

---

**记录时间**：2026-05-18
**相关修复**：SKILL.md Hook 配置格式、translator.py 增强、备份版本删除
