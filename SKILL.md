---
name: workflow-manager
description: AI-Native 工作流管理系统 - 执行、监控、守护
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
---

# workflow-manager 使用指南

## 前置条件

工作流名称从用户指令提取，若无法确定则列出所有工作流：

**叶子工作流**（有 WORKFLOW.md）：
```bash
find ~/.hermes/workflows -maxdepth 2 -name WORKFLOW.md -exec dirname {} \; | xargs -n1 basename
```

---

## Hook 配置格式要求

**SKILL.md 中的 Hook 配置必须是列表格式**：

```yaml
# ✅ 正确格式（列表格式）
hooks:
  UserPromptSubmit:
    - hooks: [{type: command, command: bash hooks/workflow-context/handler.sh}]
  PreToolUse:
    - matcher: "terminal|delegate_task|write_file|patch"
      hooks: [{type: command, command: bash hooks/workflow-step-check/handler.sh}]

# ❌ 错误格式（字符串格式，translator.py 不支持）
hooks:
  UserPromptSubmit: workflow-context/handler.sh
  PreToolUse: workflow-step-check/handler.sh
```

**原因**：skill-hook-bridge 的 translator.py 只解析列表/字典格式，字符串格式会导致 commands 为空，Hook 无法触发。

---

## status.md 定位

| 文件 | 定位 | 更新机制 |
|------|------|----------|
| status.md | 执行计划 + 状态追踪 | AI 生成并更新 |
| status.json | 状态持久化 | AI 按指令更新 |

**关键理解**：
- status.md 前 30 行：执行指令（Goal、Current Phase、Phases）
- status.md 第 31+ 行：执行后操作 + 所有禁止事项和约束
- AI 直接更新 status.md 的状态（⏳ → 🔄 → ✅）
- AI 执行完步骤后按指令更新 status.json

**执行流程**：
```
execute.py --init → status.md 模板（前 30 行框架）
    ↓
AI 读取 WORKFLOW.md → 填充 status.md（Goal、Current Phase、Phases）
    ↓
AI 执行步骤 → 更新 status.md 状态 → 按"执行后操作"章节更新 status.json
```

**执行后操作章节**（status.md 第 31+ 行）：
- 包含更新 status.json 的 Python 代码
- 主 AI 执行完步骤后复制执行

详见：
- `references/status-md-first-30-lines-design-20260518.md` - 前 30 行设计问题分析
- `references/status-md-generation-mechanism-clarification-20260518.md` - 生成机制澄清
- `references/status-json-sync-update-20260518.md` - status.json 同步更新机制

**拼接工作流**（只有 _index.yaml）：
```bash
find ~/.hermes/workflows -maxdepth 2 -name _index.yaml -exec dirname {} \; | xargs -n1 basename
```

**完整列表**：
```bash
find ~/.hermes/workflows -maxdepth 2 \( -name WORKFLOW.md -o -name _index.yaml \) -exec dirname {} \; | xargs -n1 basename | grep -v "^workflows$" | sort -u
```

## 执行流程

```
初始化 → 循环{ 读步骤ID+命令 → 执行步骤（⚠️禁止时间参数） → 更新状态 } → 全部完成
```

---

## 第0步：初始化

当 Hook 返回"无活跃工作流"阻断时执行（首次强制）：

```bash
python actions/execute.py <工作流名> --init
```

---

## 第1步：读取待执行步骤（获取ID和命令）

```bash
python3 -c "
import json, os
path = os.path.expanduser('~/.hermes/workflows/<工作流名>/status.json')
with open(path) as f:
    d = json.load(f)
for k, v in d['steps'].items():
    if v.get('status') != 'completed':
        cmd = v.get('command', '未指定命令，请查阅 WORKFLOW.md')
        print(f'STEP_ID={k}')
        print(f'COMMAND={cmd}')
        print(f'NAME={v.get(\"name\", \"\")}')
        break
"
```

若无输出，说明所有步骤已完成，跳至"完成"部分。

---

## 第2步：执行步骤

使用上一步输出的 STEP_ID 和 COMMAND：

```python
delegate_task(
    goal=f"执行工作流步骤 {step_id}: {step_name}",
    context={
        "workflow_name": "<工作流名>",
        "step_id": step_id,
        "command": command
    },
    toolsets=["terminal"]
)
```

**⚠️ 断点步骤特殊处理**：

执行前检查步骤类型：
```python
step = status['steps'][step_id]
if step.get('type') == 'breakpoint':
    # 断点步骤：执行后返回控制权
    执行步骤()
    标记当前子工作流完成
    继续执行父工作流的下一个子工作流
    return  # 不再循环当前子工作流
```

**断点执行流程**：
```
拼接工作流（如通用漏洞扫描）：
├─ 子工作流1: 凭证检测 ✅
├─ 子工作流2: home漏扫
│   ├─ 步骤13-17: 启动扫描 ✅
│   └─ 步骤18: 断点返回 ✅ → 标记home漏扫完成
│       └─ 启动心跳（后台运行步骤19-22）
├─ 子工作流3: 爆破测试 ← 立即执行
└─ 子工作流4: nuclei扫描
```

**关键规则**：
- 断点步骤执行完成后，**整个子工作流标记为完成**
- **继续执行父工作流的下一个子工作流**
- 断点后的心跳步骤（`trigger: heartbeat`）由心跳在后台执行

---

## 第3步：更新步骤状态

**⚠️ 关键发现：status.json 不会自动更新**

Hook（PostToolUse）只负责**提醒**，不执行更新。主 AI 必须手动执行：

```bash
python3 -c "
import json, os
path = os.path.expanduser('~/.hermes/workflows/<工作流名>/status.json')
with open(path, 'r+') as f:
    d = json.load(f)
    d['steps']['<STEP_ID>']['status'] = 'completed'
    d['steps']['<STEP_ID>']['completed_at'] = '$(date -Iseconds)'
    d['current_step'] = <NEXT_STEP_ID>
    d['updated_at'] = '$(date -Iseconds)'
    f.seek(0)
    json.dump(d, f, indent=2, ensure_ascii=False)
    f.truncate()
"
```

**验证更新**：
```bash
cat ~/.hermes/workflows/<工作流名>/status.json | jq '.steps["<STEP_ID>"].status'
```

更新完成后，返回第1步继续执行下一未完成步骤。

**⚠️ status.json 更新说明**：
- 步骤执行完成后，status.json **不会自动更新**
- 必须**手动执行更新命令**（见 status.md 第31+行的"执行后操作"章节）
- 参考：`references/status-json-sync-update-20260518.md`

---

## 异常处理

- delegate_task 失败 → 停止执行，报告用户失败原因
- Hook 阻断（如"前序步骤未完成"）→ 检查并修正 status.json 后重试
- Hook 阻断（如"禁止时间参数"）→ 移除 timeout/time/-t/-m 等参数后重试
- 禁止自行修改命令、跳过步骤、手动清理标记文件

---

## 查看心跳管理工作流状态

当用户问"XX工作流是否执行完毕"且该工作流由心跳监测代管时：

**⚠️ 禁止直接数文件数量作为结论**（如"30个报告"是累积下载，不是当前任务产出）

**正确流程**：
1. 先读心跳脚本（heartbeat.py），理解执行逻辑和触发条件
2. 读心跳日志最新状态（tail heartbeat.log）
3. 读 status.json 获取步骤状态
4. 对照心跳脚本的 should_stop 逻辑判断是否完成
5. 区分"累积产出"和"当前轮次产出"

**常见陷阱**：
- 心跳每30分钟检测一次，AWVS 100%后每次都下载报告，导致报告文件名含时间戳累积（report_..._{HHMMSS}.html），这不是问题，是设计行为
- WIH 时间戳对比陷阱：`workflow_started_at` 每次心跳重置，导致压缩包被误判为历史文件。详见：`references/heartbeat-wih-timestamp-comparison-trap-20260518.md`

---

## 断点工作流处理

**识别断点步骤**：
- 步骤名称包含"断点返回"或"启动心跳监测"
- `_index.yaml` 中 `type: breakpoint`
- 断点步骤启动心跳后立即返回，不等待后续步骤

**断点执行流程**：
```
执行到断点步骤 → 启动心跳cronjob → 标记当前子工作流完成 → 返回父工作流 → 继续执行下一子工作流
```

**⚠️ 断点步骤完整处理流程**：

1. **执行断点步骤**：
   - 断点步骤通常无具体命令（COMMAND=None）
   - 主要任务是创建心跳cronjob

2. **创建心跳cronjob**：
```python
cronjob(
    action="create",
    name="工作流名心跳监测",
    schedule="every 30m",
    prompt="执行 ~/.hermes/workflows/<工作流名>/heartbeat.py",
    skills=["agent-pool"],
    repeat=144,
    deliver="local"
)
```

3. **标记心跳接管步骤**：
   - 断点后的步骤（type=auto）需要立即标记为completed
   - 这些步骤由心跳自动执行，主AI不等待

4. **标记自动触发步骤**：
   - 步骤24-25等自动触发步骤标记为completed
   - 添加note说明"由心跳自动触发执行"

5. **继续执行下一子工作流**：
   - 断点处理完成后，继续执行父工作流的下一个子工作流

**步骤类型识别**：
- `type=breakpoint`：断点步骤，启动心跳后返回
- `type=auto`：心跳自动执行步骤，立即标记completed
- `type=action`：常规执行步骤，需要主AI执行

**⚠️ executor.py 已知问题**：
- expander.py 展开拼接工作流时，步骤顺序与子工作流 WORKFLOW.md 不符
- 影响：步骤在依赖项之前执行，导致工作流失败
- 检测：执行前检查 status.json 步骤顺序是否与 WORKFLOW.md 一致
- 详见：`references/expander-step-order-bug-20260518.md`

**⚠️ executor.py 已知问题**：
- expander.py 展开拼接工作流时，断点节点的 `type: breakpoint` 属性丢失
- 导致断点步骤被展开为普通步骤
- 临时方案：通过步骤名称识别断点（"断点返回"、"启动心跳监测"）
- 详见：`references/breakpoint-type-loss-bug-20260518.md`

**⚠️ execute.py --init 生成空模板**：
- `--init` 创建的 status.json 的 nodes 为空（`{}`）
- 需要根据 WORKFLOW.md 手动构建步骤节点
- 包含字段：name, description, status(pending), type, depends_on
- 详见：`references/status-json-init-gap-20260518.md`

## 复用现有工作流

**场景**：当任务与现有工作流功能相似，只是输入输出路径不同时。

**正确做法**：
1. ✅ 完全复用现有工作流逻辑
2. ✅ 只修改输入输出路径和文件名
3. ✅ 使用独立文件名避免冲突（如 `*_key_analysis.txt`）
4. ✅ 保持工作目录在同一位置

**错误做法**：
- ❌ 创建全新的临时工作流
- ❌ 修改工作流的核心逻辑
- ❌ 复制工作流文件到新目录

**示例**：复用"电力数据"工作流处理 key.txt 关键词搜索结果
- 输入：`/home/kali/zixun/konggu/9.txt`（FOFA搜索结果）
- 输出：`/home/kali/zixun/konggu/xxsj/dianli_key_analysis.txt`（独立命名）
- 工作目录：`/home/kali/zixun/konggu/xxsj/`（key.txt 同目录）

---

## 大批量 FOFA 搜索超时问题

**问题**：大量关键词搜索时，terminal 执行超时（600秒限制）。

**原因分析**：
- FOFA API 查询速度：约 5 秒/次
- 关键词数量 × 5 秒 = 总耗时
- 146 个关键词 × 5 秒 = 730 秒 > 600 秒限制

**解决方案**：

**方案 A：分批执行（推荐）**
```bash
# 第1批：1-50个关键词（约250秒）
# 第2批：51-100个关键词（约250秒）
# 第3批：101-146个关键词（约230秒）
```

**方案 B：筛选高价值关键词**
- 根据历史数据，只搜索高价值关键词
- 储能、风电、光伏发电、逆变器
- EMS、SCADA、调度中心
- 继电保护、PMU

**预防措施**：
- 执行前预估总耗时：关键词数 × 5 秒
- 超过 500 秒 → 分批执行或筛选关键词
- 提前告知用户预估时间

---

## 长时间运行任务处理

**问题**：terminal 工具默认 60 秒超时，长时间任务会被中断。

**解决方案**：
```python
# 使用 background=True 执行长时间任务
terminal(
    command="python3 main.py",
    background=True,
    notify_on_complete=True
)
```

**监控进程**：
```python
# 检查进程状态
process(action='poll', session_id='proc_xxx')

# 查看进程日志
process(action='log', session_id='proc_xxx', limit=100)
```

**适用场景**：
- FOFA 大批量搜索（100+ 关键词）
- 长时间网络扫描
- 大文件处理
- 任何超过 60 秒的任务

---

## ⚠️ delegate_task 陷阱

**陷阱1：后台进程等待**（2026-05-18 实测）
- delegate_task 执行启动后台进程的任务时，子 agent 会轮询等待（`process(action="poll")`）
- 轮询消耗 API 调用次数，达到 max_iterations（50次）后失败
- 实际案例：DB 更新脚本，子 agent 卡住 1689 秒后因 max_iterations 失败

**正确做法**：
- 后台进程 → 主 AI 直接 terminal 执行（background: true, notify_on_complete: true）
- 状态检查 → 主 AI 直接 terminal 命令（如 `ps aux | grep`、`sqlite3`）
- ❌ 不要用 delegate_task 等待后台进程

**陷阱2：长时间任务**（2026-05-18 实测）
- terminal 工具默认 60 秒超时，长时间任务会被中断
- 使用 `background=True` + `notify_on_complete=True` 启动
- 用 `process(action='poll')` 检查状态

---

## 禁止行为

- ❌ 跳过初始化
- ❌ 并行执行多个步骤
- ❌ 修改命令或添加参数
- ❌ 用 delegate_task 等待后台进程
  - ⚠️ 特别禁止：timeout、time、--max-time、-t N、-m N 等时间参数
  - 原因：工作流可能长时间运行，时间参数导致意外中断
  - Hook已拦截：handler.sh自动检测并阻止
- ❌ 手动删除 .active_session 标记（Stop Hook 自动清理）
- ❌ 断点步骤后询问用户（应自动返回父工作流）
- ❌ 对长时间任务使用默认 terminal（会超时）
- ❌ 创建临时工作流替代复用现有工作流（应直接修改输入输出路径）

---

## Hook 配置陷阱（重要）

**问题**：SKILL.md 中的 Hook 配置必须是**列表格式**，不能是字符串格式。

**错误格式**（导致 Hook 不触发）：
```yaml
hooks:
  PostToolUse: workflow-progress/handler.sh
```

**正确格式**：
```yaml
hooks:
  PostToolUse:
    - hooks: [{type: command, command: bash hooks/workflow-progress/handler.sh}]
```

**原因**：skill-hook-bridge 的 translator.py 只解析列表/字典格式，字符串格式会导致 commands 为空，Hook 无法触发。

**验证方法**：
```bash
cat ~/.hermes/plugins/skill-hook-bridge/hooks_manifest.json | \
  python3 -c "import json,sys; d=json.load(sys.stdin); \
  skill=[s for s in d['skills'] if s['name']=='workflow-manager'][0]; \
  [print(f'{h[\"claude_event\"]}: {h[\"commands\"]}') for h in skill['hooks']]"
```

**修复**：如果 commands 为空，检查 SKILL.md 格式并修正。

详见：`references/hook-config-format-trap-20260518.md`

---

## Hook 失效诊断

当 Hook 未触发（status.md 不更新、约束未注入）时，按此顺序排查：

1. **检查 manifest**：`cat ~/.hermes/plugins/skill-hook-bridge/hooks_manifest.json | python3 -c "import json,sys; d=json.load(sys.stdin); s=[x for x in d['skills'] if x['name']=='workflow-manager'][0]; [print(f\"{h['claude_event']}: commands={h['commands']}\") for h in s['hooks']]"`
2. **commands 为空** → manifest 缓存过期，需手动触发扫描（见下方）
3. **commands 有值但 trigger_count=0** → Hook 回调未注册，需重启 Gateway
4. **trigger_count>0 但 status.md 不更新** → handler.sh 逻辑问题或 .active_session 不匹配

**manifest 缓存过期修复**（commands 为空时）：
```bash
python3 << 'EOF'
import sys; sys.path.insert(0, '~/.hermes/plugins/skill-hook-bridge')
from scanner import scan_skill_hooks; from translator import translate_hook
import json; from pathlib import Path; from datetime import datetime
skills = scan_skill_hooks(["~/.hermes/skills", "~/.hermes/skills/openclaw-imports"])
for s in skills:
    s["translated_hooks"] = [translate_hook(e, c) for e, c in s["hooks"].items() if translate_hook(e, c)]
# 构建 manifest 并写入（完整代码见 references/hook-manifest-cache-debug.md）
EOF
```

详见：`references/hook-manifest-cache-debug-20260518.md`

---

## 完成

全部步骤状态均为 completed 后，向用户汇报结果。无需执行清理操作。

---

## Hook 备份版本清理

**正确方法**：彻底删除备份版本，不要只重命名 `.disabled` 后缀

**原因**：
- scanner.py 不过滤后缀，所有 SKILL.md 都会被扫描
- `.disabled` 后缀仍会被扫描 → hooks_manifest.json 包含 → 执行时找不到 hooks/ 目录 → 报错

**清理步骤**：
```bash
# 彻底删除备份版本
rm -rf ~/.hermes/skills/.../workflow-manager/.backup/findings-mechanism-*

# 重新触发 Hook 扫描
python3 << 'EOF'
import sys; sys.path.insert(0, '~/.hermes/plugins/skill-hook-bridge')
from scanner import scan_skill_hooks; from translator import translate_hook
import json; from pathlib import Path; from datetime import datetime
skills = scan_skill_hooks(["~/.hermes/skills", "~/.hermes/skills/openclaw-imports"])
# ... 构建 manifest 并写入
EOF
```

---

## status.md 前 30 行设计问题

**问题**：前 30 行只包含约束，不包含执行指令

**对比 planning-with-files**：

| 项目 | planning-with-files | workflow-manager |
|------|---------------------|------------------|
| 前 30 行内容 | Goal、Current Phase、Phases（执行指令） | 约束（禁止行为） |
| AI 看到后 | 知道要做什么 | 只知道不能做什么 |

**planning-with-files 设计思路**：
- 模板前 30 行包含 Goal、Current Phase、Phases
- AI 根据用户任务填充具体内容
- AI 在执行过程中更新 status

**workflow-manager 问题**：
- 前 30 行全是约束（禁止行为）
- 执行步骤在第 101 行之后
- AI 看不到执行指令，不知道要做什么

**解决方案**：调整 status.md 结构，让前 30 行包含执行指令

详见：`references/status-md-first-30-lines-design-20260518.md`

---

## 常见问题修复

- **status.json 不自动更新**：`references/status-json-no-auto-update-20260518.md`（⚠️ Hook 只提醒不执行，主 AI 必须手动更新）
- **僵尸工作流阻断**：`references/zombie-workflow-blockage-fix-20260518.md`（⚠️ initialized 状态的旧工作流会阻断新操作，需批量清理）
- **status.md 前 30 行设计问题**：`references/status-md-first-30-lines-design-20260518.md`（⚠️ 前 30 行只包含约束不包含执行指令，AI 不知道要做什么）
- **月报生成 MCP Word 模式**：`references/monthly-report-mcp-word-pattern-20260518.md`（使用 MCP word-document-server 填充 Word 模板）
- **status.md 前 30 行优化**：`references/status-md-first-30-lines-optimization-20260518.md`（⚠️ 前 30 行改为执行指令，约束后移，参考 planning-with-files）
- **status.md 生成机制**：`references/status-md-generation-mechanism-clarification-20260518.md`（⚠️ 拼接工作流由 execute.py 生成，子工作流不需要单独 status.md）
- **Hook 配置格式陷阱**：`references/hook-config-format-trap-20260518.md`（⚠️ 重要：SKILL.md 中 Hook 必须用列表格式，字符串格式导致 Hook 失效）
- **FOFA 批量搜索超时**：`references/fofa-batch-search-timeout-pattern-20260518.md`（⚠️ 大批量关键词搜索超时，分批执行或筛选关键词）
- **delegate_task 后台进程陷阱**：`references/delegate-task-background-process-pitfall-20260518.md`（⚠️ 等待后台进程会达到 max_iterations）
- **execute.py --init 空模板**：`references/status-json-init-gap-20260518.md`（--init 创建空 nodes，需手动构建）
- **分支工作流步骤冲突**：`references/branch-workflow-step-conflict-20260519.md`（⚠️ 子工作流共享目录时，删除步骤可能影响后续依赖步骤）
- **月报 MCP Word 填充**：`references/monthly-report-mcp-word-pattern-20260518.md`（完整执行模式）
- Hook 配置格式与 Manifest 同步：`references/hook-format-and-manifest-sync-20260518.md`
- **FOFA 批量搜索超时**：`references/fofa-batch-search-timeout-pattern-20260518.md`（⚠️ 大批量关键词搜索超时，分批执行或筛选关键词）
- 断点类型丢失：`references/breakpoint-type-injection-fix-20260518.md`
- status.json 依赖模式：`references/status-json-dependency-patterns-20260518.md`
- status.json 同步更新：`references/status-json-sync-update-20260518.md`（⚠️ 步骤执行后必须按指令更新 status.json）
- status.json 同步更新验证：`references/status-json-sync-update-verification-20260518.md`（实测验证流程）
- 步骤顺序错误：`references/expander-step-order-bug-20260518.md`
- WIH 路径检测错误：`references/heartbeat-wih-path-fix-20260517.md`
- 重复下载陷阱：`references/heartbeat-anti-duplicate-download-pattern.md`
- WIH 时间戳对比陷阱：`references/heartbeat-wih-timestamp-comparison-trap-20260518.md`
- Status文件同步机制：`references/heartbeat-status-file-sync-fix-20260517.md`
- Timeout拦截机制：`references/workflow-timeout-interception-pattern-20260518.md`
