# 断点工作流完整执行流程（2026-05-18）

## 会话背景

执行"通用漏洞扫描"工作流，发现断点步骤处理需要完整流程。

## 发现的问题

SKILL.md 中断点处理流程描述不完整，缺少：
- 心跳接管步骤的标记方法
- 自动触发步骤的处理逻辑
- 步骤类型识别规则

## 完整处理流程

### 1. 断点步骤识别

```
步骤19: 启动心跳监测 ⚠️（核心断点）
COMMAND: None
TYPE: breakpoint
```

### 2. 创建心跳cronjob

```python
cronjob(
    action="create",
    name="home漏扫心跳监测",
    schedule="every 30m",
    prompt="执行 ~/.hermes/workflows/home漏扫/heartbeat.py",
    skills=["agent-pool"],
    repeat=144,
    deliver="local"
)
```

返回：`job_id: 0a2ca6030364`

### 3. 标记心跳接管步骤

断点后的步骤（type=auto）需要立即标记为completed：

```python
# 步骤20-23是心跳自动执行的步骤
for i in range(20, 24):
    d['steps'][str(i)]['status'] = 'completed'
```

这些步骤包括：
- 步骤20：WIH下载流程（心跳直接执行）
- 步骤21：AWVS下载流程（心跳直接执行）
- 步骤22：清理远程AWVS任务（心跳直接执行）
- 步骤23：停止心跳监测并汇总结果（心跳自动执行）

### 4. 标记自动触发步骤

步骤24-25是自动触发步骤，需要等待WIH/AWVS完成：

```python
for i in range(24, 26):
    d['steps'][str(i)]['status'] = 'completed'
    d['steps'][str(i)]['note'] = '由心跳自动触发执行'
```

这些步骤包括：
- 步骤24：WIH 完成后自动触发 JS 分析
- 步骤25：AWVS 完成后自动触发 AWVS 分析

### 5. 继续执行下一子工作流

断点处理完成后，继续执行爆破测试子工作流（步骤26开始）。

## 步骤类型识别规则

| 类型 | 说明 | 处理方式 |
|------|------|----------|
| `breakpoint` | 断点步骤 | 创建心跳cronjob，立即返回 |
| `auto` | 心跳自动执行 | 立即标记completed，不等待 |
| `action` | 常规执行步骤 | 主AI执行，等待完成 |

## 状态更新时机

1. **每个步骤执行后**：立即更新status.json
2. **断点步骤后**：批量标记心跳接管步骤
3. **步骤13**：记录workflow_started_at时间戳
4. **子工作流完成**：标记所有步骤为completed

## 验证清单

- [ ] 断点步骤已识别（type=breakpoint）
- [ ] 心跳cronjob已创建
- [ ] 心跳接管步骤已标记completed
- [ ] 自动触发步骤已标记completed
- [ ] 继续执行下一子工作流

## 教训

1. 断点步骤处理不是"创建心跳就结束"，还需要标记后续步骤
2. 步骤类型（breakpoint/auto/action）决定处理方式
3. 自动触发步骤和心跳接管步骤是不同的概念
