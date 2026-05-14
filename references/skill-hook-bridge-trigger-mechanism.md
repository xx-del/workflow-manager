# skill-hook-bridge Hook 触发机制

## 架构

```
skill-hook-bridge 插件
    ↓ 扫描技能目录
    ↓ 读取 SKILL.md 中的 hooks 定义
    ↓ 生成 hooks_manifest.json
    ↓ 注册到 Hermes (ctx.register_hook)
    ↓
Hermes 触发事件 (pre_llm_call, pre_tool_call, ...)
    ↓ skill-hook-bridge 拦截
    ↓ 查找 manifest 中匹配的 hook
    ↓ 执行 shell 命令
    ↓ 返回结果注入上下文
```

## 关键文件

| 文件 | 位置 | 作用 |
|------|------|------|
| hooks_manifest.json | ~/.hermes/plugins/skill-hook-bridge/ | 已注册的 hook 清单 |
| agent-hooks/ | ~/.hermes/agent-hooks/ | 符号链接目录 |
| handler.sh | 技能目录/hooks/xxx/handler.sh | 实际执行的脚本 |

## 触发条件

1. **自动触发**：技能被 skill-hook-bridge 扫描到
2. **扫描时机**：Hermes 启动时、手动执行 `cli.py scan`
3. **执行时机**：对应事件发生时（pre_llm_call, pre_tool_call 等）

## 验证方法

```bash
# 1. 检查 manifest
cat ~/.hermes/plugins/skill-hook-bridge/hooks_manifest.json | jq '.skills[] | select(.name == "workflow-manager")'

# 2. 检查符号链接
ls -la ~/.hermes/agent-hooks/ | grep workflow

# 3. 检查触发统计
cat ~/.hermes/plugins/skill-hook-bridge/hooks_manifest.json | jq '.skills[].hooks[] | {event: .hermes_event, count: .trigger_count}'
```

## 常见问题

### Q: Hook 未触发？

**检查清单**：
1. hooks_manifest.json 中是否有该技能？
2. 符号链接是否存在？
3. handler.sh 是否有执行权限？
4. skill-hook-bridge 插件是否启用？

### Q: 如何手动注册？

```bash
# 方法1：重新扫描
python ~/.hermes/plugins/skill-hook-bridge/cli.py scan

# 方法2：手动执行 handler.sh（调试用）
bash ~/.hermes/skills/openclaw-imports/workflow-manager/hooks/workflow-ai-remind/handler.sh "/工作流路径"
```

## 与 config.yaml hooks 的区别

| 方式 | config.yaml hooks | skill-hook-bridge |
|------|------------------|-------------------|
| 配置位置 | config.yaml | 技能目录/hooks/ |
| 注册方式 | 手动配置 | 自动扫描 |
| 执行内容 | Python函数 | Shell命令 |
| 适用场景 | 核心插件 | 技能扩展 |

## 更新日期

2026-05-14
