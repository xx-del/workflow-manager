# 工作流智能守护 - 按需唤醒模式

> 本文档定义守护Agent的按需唤醒机制，替代原有的常驻模式。

## 核心定位

**守护Agent = 问题诊断专家**

不是常驻监控者，而是按需召唤的专家：
- 心跳正常时：静默，不占用资源
- 心跳异常时：被唤醒，诊断问题
- 完成任务后：退出，释放资源

## 设计背景

基于实际运维经验，守护 Agent 需避免以下错误：

| 错误类型 | 表现 | 后果 |
|----------|------|------|
| 缺少关联性分析 | 只看进程存在，没分析进程树、没看脚本依赖 | 诊断停留在表面 |
| 一刀切解决 | 杀死所有进程，而非先尝试最小干预 | 方案缺乏渐进性 |
| 脱离脚本执行 | 自己臆断步骤，没按实际脚本流程 | 缺少代码分析 |

因此，守护 Agent 采用 **三阶段诊断 + 渐进式修复** 模式。

## 架构对比

| 维度 | 旧架构（常驻守护） | 新架构（按需守护） |
|------|-------------------|-------------------|
| 守护Agent生命周期 | 常驻 | 按需唤醒，完成退出 |
| 监控机制 | 守护Agent自监控 | 轻量级脚本 |
| 单点故障 | 守护卡死无解 | 脚本轻量，可自动恢复 |
| 资源占用 | 持续占用 | 按需占用 |
| 问题发现延迟 | 0-30分钟 | 0-5分钟 |

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    工作流监控系统 v3                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐                                            │
│  │ 执行Agent    │───心跳──▶ status.json                      │
│  │ (每5分钟写入) │            │                              │
│  └─────────────┘            ▼                              │
│                      ┌─────────────┐                        │
│                      │ 心跳监控脚本 │ (heartbeat-monitor.py)  │
│                      │ (每5分钟)    │                        │
│                      └──────┬──────┘                        │
│                             │                               │
│                    ┌────────┴────────┐                      │
│                    │ 心跳超时?        │                      │
│                    └────────┬────────┘                      │
│                        否   │   是                          │
│                        ▼   │   ▼                            │
│                    [无操作] │ [唤醒守护Agent]                │
│                            │   │                            │
│                            │   ▼                            │
│                            │ ┌─────────────┐                │
│                            │ │ 守护Agent    │                │
│                            │ │ - 诊断问题   │                │
│                            │ │ - 尝试修复   │                │
│                            │ │ - 报告用户   │                │
│                            │ │ - 完成退出   │                │
│                            │ └─────────────┘                │
│                            │                                │
└─────────────────────────────────────────────────────────────┘
```

## 生命周期

```
[待机] → 被心跳监控脚本唤醒 → [诊断中] → [修复中] → [完成] → [退出]
                                          ↓
                                    [无法修复] → [报告用户] → [退出]
```

## 触发条件

由 `heartbeat-monitor.py` 检测并触发：

| 触发条件 | 说明 |
|----------|------|
| workflow.heartbeat 超时 | 工作流心跳超过阈值（默认30分钟） |
| status=running 但无心跳 | 状态显示运行但没有心跳记录 |

## status.json 数据结构

```json
{
  "status": "running",
  "workflow": {
    "heartbeat": "2026-04-11T02:30:00+08:00",
    "current_step": "step-2",
    "step_progress": "2/5",
    "pid": 12345
  },
  "guardian": {
    "status": "idle",
    "invocation_count": 0,
    "last_invoked": null,
    "trigger_reason": null,
    "last_result": null
  },
  "heartbeat_monitor": {
    "last_check": "2026-04-11T02:35:00+08:00",
    "check_count": 42,
    "alerts": []
  }
}
```

## 守护Agent执行流程

### 阶段 1：关联性诊断（必须线性完成）

触发守护后，依次执行以下分析链：

#### 1.1 进程关联分析
- 进程树结构：`pstree -p <主进程PID>`
- 父子进程关系：识别主进程 → 子进程 → 孙进程
- 孤儿进程检测：`ps -eo pid,ppid,stat,cmd | grep "PPID=1"`
- 进程状态分布：统计 R/S/D/Z 状态数量

#### 1.2 产出关联分析
- 最后产出时间：`ls -lt <输出目录> | head -5`
- 产出速率变化：对比历史产出数量
- 停产时间计算：当前时间 - 最后产出时间

#### 1.3 代码关联分析（核心）
- 读取执行脚本：`cat <脚本路径>`
- 分析当前执行阶段：对比脚本行号与日志
- 识别依赖关系：
  - 脚本依赖什么工具
  - 工具依赖什么资源
  - 资源依赖什么状态
- 定位卡住的具体步骤

#### 1.4 资源关联分析
- 网络连接状态：`lsof -p <PID> | grep TCP`
- 文件句柄：`lsof -p <PID> | wc -l`
- 锁文件检测：`find <工作目录> -name "*.lock"`
- 磁盘 IO 状态：`iostat -x 1 3`

#### 诊断报告格式

```markdown
## 关联诊断报告

### 执行链路分析
脚本: <脚本名称>
当前阶段: <阶段名称> (第N行)
↓
依赖: <工具链>
↓
卡点: <具体问题>
  ├─ 证据: <证据列表>
  └─ 影响: <影响范围>

### 问题定位
- 根因: <根本原因>
- 影响范围: <受影响的进程/数据>
- 主进程状态: <正常/异常>
- 数据完整性: <已产出数据状态>
```

### 阶段 2：渐进式修复（从最小干预开始）

修复方案按影响从小到大排序，**必须从方案 A 开始**：

#### 方案分级原则

| 级别 | 原则 | 说明 |
|------|------|------|
| 方案 A | 最小干预 | 只处理问题点，保留主进程和数据 |
| 方案 B | 中等干预 | 重启部分进程，从断点继续 |
| 方案 C | 完全重启 | 最后手段，从头执行 |

#### 方案模板

每个方案必须包含：
- 具体执行命令
- 预期恢复时间
- 数据影响评估
- 回滚方案

```markdown
## 修复方案评估

### 方案 A: <最小干预>（优先）
```bash
# 只杀死问题进程，保留主进程
<具体命令>
```
- 预期效果: <效果描述>
- 恢复时间: <时间>
- 数据影响: <影响>
- 回滚方案: 如无效再执行方案 B

### 方案 B: <中等干预>
...

### 方案 C: <完全重启>（最后手段）
...
```

### 阶段 3：执行验证（每步确认）

执行方案前必须确认：
1. 用户选择哪个方案
2. 方案执行步骤明细
3. 每一步的预期结果
4. 异常时的回滚操作

#### 执行模式

```
方案 A → 执行 → 等待验证 → 有效则结束
                      ↓ 无效
        方案 B → 执行 → 等待验证 → 有效则结束
                                ↓ 无效
              方案 C → 执行 → 最终修复
```

#### 验证检查清单

执行后必须验证：
- [ ] 进程是否恢复正常？
- [ ] 产出是否恢复？
- [ ] 日志是否有新输出？
- [ ] 数据是否完整？

如验证失败，记录失败原因，进入下一方案。

## 与心跳监控的协作

```
心跳监控脚本 (每5分钟)
    │
    ├─ 心跳正常 → 无操作
    │
    └─ 心跳超时 → 唤醒守护Agent
                      │
                      ├─ 诊断问题
                      ├─ 尝试修复
                      ├─ 更新状态
                      └─ 退出
                           │
                           ▼
                    下个周期心跳监控继续检测
```

## 配置示例

```yaml
# config.yaml
heartbeat:
  enabled: true
  interval: 300        # 5分钟
  timeout: 1800        # 30分钟超时
  script: ~/.hermes/skills/openclaw-imports/workflow-manager/actions/heartbeat-monitor.py

guardian:
  enabled: true
  mode: on_demand      # 按需唤醒
  max_invocations: 3   # 单次工作流最多唤醒3次
  timeout: 3600        # 守护Agent超时（1小时）
```

## Cronjob 持久化机制

**核心架构**：

```
┌─────────────────────────────────────────────────────────────┐
│                    Hermes Cronjob 架构                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   jobs.json (持久化)                                        │
│   ~/.hermes/cron/jobs.json                                  │
│        │                                                    │
│        ▼                                                    │
│   Gateway 进程 (运行时)                                      │
│   - 加载 jobs.json                                          │
│   - 内存中维护调度状态                                        │
│   - 定时执行 cronjob 任务                                    │
│        │                                                    │
│        ▼                                                    │
│   执行脚本 (如 heartbeat.py)                                 │
│   - 检测工作流进度                                           │
│   - 更新 status.json                                        │
│   - 写入 heartbeat.log                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**生命周期绑定关系**：

| 组件 | 生命周期 | 说明 |
|------|----------|------|
| jobs.json | 永久 | 文件持久化，重启后自动加载 |
| Gateway 进程 | 服务运行期间 | 独立于会话，由 systemd/用户启动 |
| Cronjob 调度 | Gateway 运行期间 | 内存中维护，从 jobs.json 加载 |
| 执行脚本 | 单次执行 | 每次调度启动新进程 |

**关键结论**：

| 问题 | 答案 |
|------|------|
| 会话关闭后 cronjob 是否继续运行？ | ✅ 是（独立于会话） |
| Gateway 重启后 cronjob 是否恢复？ | ✅ 是（从 jobs.json 重新加载） |
| 心跳是否依赖会话存在？ | ❌ 否（由 Gateway 调度） |

**状态检查命令**：

```bash
# 查看 cronjob 配置
cat ~/.hermes/cron/jobs.json | jq '.jobs[] | select(.name | contains("漏扫"))'

# 查看 cronjob 状态（通过 Hermes CLI）
hermes cronjob list

# 检查 Gateway 进程
ps aux | grep "hermes.*gateway"

# 检查心跳进程
ps aux | grep "heartbeat.py"
```

## 使用方法

### 1. 心跳监控（自动）

**推荐方式**：使用 Hermes cronjob 系统（会话关闭后继续运行）

```bash
# 通过 Hermes CLI 创建 cronjob
hermes cronjob create \
  --name "home漏扫心跳监测" \
  --schedule "every 30m" \
  --prompt "执行 ~/.hermes/workflows/home漏扫/heartbeat.py"
```

**备选方式**：系统 crontab（需要系统级配置）

```bash
# 每5分钟执行一次
*/5 * * * * python3 ~/.hermes/skills/openclaw-imports/workflow-manager/actions/heartbeat-monitor.py
```

### 2. 手动检查

```bash
# 检查所有工作流
python3 ~/.hermes/skills/openclaw-imports/workflow-manager/actions/heartbeat-monitor.py

# 检查特定工作流
python3 ~/.hermes/skills/openclaw-imports/workflow-manager/actions/heartbeat-monitor.py --workflow "资产收集流程"

# 只检查不触发守护
python3 ~/.hermes/skills/openclaw-imports/workflow-manager/actions/heartbeat-monitor.py --dry-run
```

### 3. 手动唤醒守护

```bash
# 唤醒守护Agent
~/.hermes/skills/openclaw-imports/workflow-manager/actions/spawn-guardian.sh ~/.hermes/workspace/workflows/资产收集流程 heartbeat_timeout
```

## 优势

| 能力 | 说明 |
|------|------|
| 关联性诊断 | 进程树 + 产出 + 代码 + 资源四维分析 |
| 代码分析 | 脚本解析 + 阶段定位 + 依赖识别 |
| 渐进式修复 | 方案分级 (A→B→C)，最小干预优先 |
| 逐步验证 | 每步确认，失败自动升级方案 |
| 无单点故障 | 监控脚本是轻量级的，几乎不会卡死 |
| 资源高效 | 守护Agent只在需要时运行 |
| 自动恢复 | 即使守护Agent卡死，下次心跳周期会重新唤醒 |
| 职责清晰 | 监控脚本负责检测，守护Agent负责诊断 |

## 故障排查

### 心跳监控脚本无响应

```bash
# 检查脚本权限
ls -la ~/.hermes/skills/openclaw-imports/workflow-manager/actions/heartbeat-monitor.py

# 手动执行测试
python3 ~/.hermes/skills/openclaw-imports/workflow-manager/actions/heartbeat-monitor.py --dry-run
```

### 守护Agent未被唤醒

```bash
# 检查守护脚本权限
ls -la ~/.hermes/skills/openclaw-imports/workflow-manager/actions/spawn-guardian.sh

# 检查 guardian.status
python3 -c "import json; print(json.load(open('status.json')).get('guardian', {}).get('status'))"

# 如果状态为 diagnosing 但守护未运行，手动重置
python3 -c "import json; s=json.load(open('status.json')); s['guardian']['status']='idle'; json.dump(s, open('status.json','w'), indent=2)"
```

### 工作流心跳不更新

```bash
# 检查执行Agent是否在运行
ps aux | grep workflow

# 检查 status.json
cat ~/.hermes/workspace/workflows/资产收集流程/status.json

# 检查 workflow.heartbeat 字段
python3 -c "import json; print(json.load(open('status.json')).get('workflow', {}).get('heartbeat'))"
```
