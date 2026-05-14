# Gateway Hooks 触发机制

**日期**: 2026-05-14
**问题**: Hook已加载但未触发

## 触发机制真相

**Gateway Hooks只在Gateway主会话中触发**，不在以下场景触发：

❌ **不触发场景**：
- delegate_task创建的子agent
- 独立的Python脚本
- terminal命令直接执行

✅ **触发场景**：
- Gateway直接管理的会话
- 用户通过飞书/Telegram等平台发送消息
- Gateway接收到消息后启动的agent

## 事件名称规范

**Gateway事件名**（正确）：
- `agent:start` - Agent开始处理
- `agent:step` - Agent执行步骤
- `session:end` - 会话结束

**Plugin事件名**（错误，不适用于Gateway Hooks）：
- ~~`pre_llm_call`~~
- ~~`pre_tool_call`~~
- ~~`post_tool_call`~~

## 验证方法

**检查Hook是否加载**：
```bash
tail -30 ~/.hermes/logs/gateway.log | grep "hook"
# 输出: 6 hook(s) loaded
```

**检查Hook是否触发**：
- Hook输出不进日志
- Hook返回值注入到AI上下文
- 需要在Gateway主会话中测试

## 架构图

```
用户消息 → Gateway → 主Agent → 触发Hook ✅
                          ↓
                    delegate_task
                          ↓
                      子Agent → 不触发Hook ❌
```

## 结论

**Hook配置正确但仍未触发的原因**：
- 使用了delegate_task执行工作流
- 子agent不会触发Gateway的hook
- 需要在Gateway主会话中执行才能触发hook

**解决方案**：
1. 接受Hook只在主会话触发的限制
2. 或使用其他机制（如技能内部的规则注入）
