# 工作流timeout参数拦截机制

## 背景

2026-05-18爆破测试工作流执行时，主AI添加了 `timeout 600` 参数，导致工作流在10分钟后被强制中断，违反了workflow-manager技能"禁止添加timeout参数"的约束。

## 问题分析

### 根因

| 层级 | 问题 | 状态 |
|------|------|------|
| **主AI** | 添加了 `timeout 600` | ❌ 违规 |
| **技能约束** | 明确禁止添加timeout | ✅ 存在 |
| **Hook拦截** | 只注入文本，未实际拦截 | ❌ 缺失 |

### 约束来源

- SKILL.md禁止行为：❌ 修改命令或添加参数
- references/execution-constraint-rationale.md：禁止添加timeout
- references/hook-hard-constraint-mechanism-20260514.md：Hook应拦截timeout

## 修复方案

### Hook拦截机制

**文件**：`hooks/workflow-step-check/handler.sh`

**插入位置**：第84行（删除文件拦截后）

**正则表达式**（ERE兼容）：

```regex
(^|[|&;])[[:space:]]*(timeout|time)[[:space:]]+|
[[:space:]]--(timeout|max-time|connect-timeout|deadline|time-limit)([= ]|$)|
[[:space:]]-[tm][[:space:]]*[0-9]
```

### 拦截规则

| 类别 | 模式 | 示例 |
|------|------|------|
| **命令级** | 行首或管道后的timeout/time | `timeout 600 cmd`、`cmd | time ./script` |
| **参数级** | --timeout/--max-time等 | `curl --max-time 30` |
| **短参数** | -t N / -m N（支持粘连）| `curl -m30`、`uv run -t60` |

### 排除项

- **sleep命令**：工作流可能需要延迟等待，不拦截
- **路径中的time**：`/path/to/timeout/script.sh` 不拦截
- **参数值中的time**：`--name timeout other` 不拦截

### 测试验证

14个测试用例全部通过：

**拦截用例**（9个）：
- timeout命令
- time命令
- 管道后timeout
- --max-time参数
- -m粘连数字
- -m空格数字
- --timeout参数
- -t粘连数字
- -t空格数字

**放行用例**（5个）：
- 路径包含timeout
- 字符串timeout
- 文件名time
- timeout作为参数值
- sleep命令

## 兼容性说明

- **使用grep -E**：扩展正则，兼容Linux/BSD/macOS
- **使用[[:space:]]**：POSIX字符类，替代`\s`
- **不依赖grep -P**：避免Perl正则兼容性问题

## 修复时间

2026-05-18 01:30
