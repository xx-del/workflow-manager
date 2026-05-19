# 工作流Timeout拦截模式

## 背景

主AI在执行工作流时添加 `timeout 600` 参数，导致爆破测试超时中断。根因：
- Hook只注入约束文本（"禁止添加 timeout 参数"）
- 缺少实际拦截代码
- 拦截范围不够全面

## 拦截规则（完整版）

### 命令级拦截

| 模式 | 示例 | 说明 |
|------|------|------|
| timeout | `timeout 600 cmd` | 设置整体超时 |
| time | `time python script.py` | 计时执行 |
| sleep | `sleep 10` | 延迟执行 |

### 参数级拦截

| 模式 | 示例 | 说明 |
|------|------|------|
| --timeout | `cmd --timeout=300` | 长参数 |
| -t N | `cmd -t 60` | 短参数+数字 |
| --max-time | `curl --max-time 30` | curl超时 |
| -m N | `curl -m 30` | curl短参数 |
| --connect-timeout | `wget --connect-timeout 10` | 连接超时 |
| --deadline | `cmd --deadline 60s` | 截止时间 |
| --time-limit | `cmd --time-limit 120` | 时间限制 |

### 不拦截的情况

| 情况 | 示例 | 说明 |
|------|------|------|
| 路径包含time | `/path/to/timeout/script.sh` | 路径一部分 |
| 字符串中的time | `echo 'timeout'` | 字符串字面量 |
| 文件名包含time | `cat timeline.txt` | 文件名 |
| URL包含time | `curl http://example.com/time` | URL一部分 |

## 正则表达式

```regex
\b(timeout|time|sleep)\s+|\s--(timeout|max-time|connect-timeout|deadline|time-limit)[=\s]|\s-[tm]\s+[0-9]
```

## Hook拦截代码

**文件**：`hooks/workflow-step-check/handler.sh`

**插入位置**：第90行后（删除文件拦截后，串行模式检查前）

```bash
# 规则 2: 禁止添加时间相关参数（timeout/time/sleep等）
if [[ "$TOOL_NAME" == "terminal" ]]; then
    if echo "$TOOL_INPUT" | grep -qiE '\b(timeout|time|sleep)\s+|\s--(timeout|max-time|connect-timeout|deadline|time-limit)[=\s]|\s-[tm]\s+[0-9]'; then
        # 提取违规参数用于提示
        VIOLATION=$(echo "$TOOL_INPUT" | grep -oiE '\b(timeout|time|sleep)\s+[0-9]*|\s--(timeout|max-time|connect-timeout|deadline|time-limit)[=\s]*[0-9]*|\s-[tm]\s+[0-9]+' | head -1)
        
        cat << BLOCKJSON
{
    "action": "block",
    "message": "⛔ 工作流执行禁止添加时间参数。\n\n违规参数: $VIOLATION\n\n原因：工作流步骤可能需要长时间运行，时间参数会导致意外中断。\n\n正确做法：直接执行命令，不添加任何时间参数。"
}
BLOCKJSON
        exit 0
    fi
fi
```

## 测试验证

测试用例（16个）：
- ✅ 10个拦截用例（timeout/time/sleep命令、各种时间参数）
- ✅ 6个放行用例（路径/字符串/URL包含time、普通命令）

## 实施记录

**日期**：2026-05-18
**问题**：爆破测试添加 `timeout 600` 导致超时
**根因**：Hook缺少实际拦截代码，拦截范围不全
**修复**：添加完整的时间参数拦截逻辑
