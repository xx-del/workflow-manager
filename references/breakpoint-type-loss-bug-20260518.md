# executor.py 断点类型丢失 Bug

**发现日期**：2026-05-18
**影响范围**：所有包含断点节点的拼接工作流

## 问题现象

拼接工作流展开后，断点节点的 `type: breakpoint` 属性丢失，导致：
- 断点步骤被当作普通步骤执行
- 主AI在断点后询问用户，而非自动返回父工作流
- 父工作流未继续执行后续子工作流

## 实例分析

**通用漏洞扫描工作流**：

| 配置定义 | status.json实际 | 问题 |
|---------|----------------|------|
| step_2（断点返回，type=breakpoint） | 步骤18-22（普通步骤） | ❌ 断点类型丢失 |
| heartbeat.enabled: true | 未识别 | ❌ 心跳配置未生效 |

**正确流程**：
```
步骤13-17: home漏扫启动扫描
步骤18: 断点返回 → 启动心跳 → 标记home漏扫完成 → 继续父工作流
步骤19-22: (心跳后台执行，不阻塞父工作流)
步骤31-48: 爆破测试 + nuclei扫描 (应该立即执行)
```

**实际流程**：
```
步骤13-17: 执行完成
步骤18: 停止，询问用户
后续步骤未执行
```

## 根本原因

`expander.py` 在展开拼接工作流时：
1. 读取子工作流的 `_index.yaml`
2. 识别 `type: breakpoint` 节点
3. **但展开后未保留 type 属性**
4. 导致 `executor.py` 无法识别断点

## 临时方案

通过步骤名称识别断点：
- 名称包含"断点返回"
- 名称包含"启动心跳监测"
- 名称包含"心跳直接执行"（后续步骤）

## 修复方向

1. **expander.py**：展开节点时保留 `type` 属性
2. **executor.py**：识别 `type: breakpoint` 后：
   - 执行断点步骤（启动心跳）
   - 标记当前子工作流完成
   - 返回父工作流继续执行
3. **status.json**：添加 `is_breakpoint` 字段标记断点步骤

## 相关文件

- `~/.hermes/skills/openclaw-imports/workflow-manager/actions/expander.py`
- `~/.hermes/skills/openclaw-imports/workflow-manager/actions/executor.py`
- `~/.hermes/workflows/home漏扫/_index.yaml`（断点配置示例）
