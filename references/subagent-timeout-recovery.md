# Subagent Timeout 部分结果恢复模式

## 问题场景

`delegate_task` 超时（600s），但任务可能已经完成了部分工作。

## 症状

```
{"results": [{"task_index": 0, "status": "timeout", ...}]}
```

## 恢复检查清单

**立即检查**：
1. 检查输出文件是否已生成
2. 检查文件是否非空
3. 统计已完成数量

```bash
# 示例：检查 URL 分析结果
ls -lh *.txt 2>/dev/null
wc -l dianli.txt excluded.txt guojiadianwang.txt
```

## 判断逻辑

| 情况 | 处理 |
|------|------|
| 文件已生成且完整 | ✅ 继续下一步，无需重试 |
| 文件已生成但不完整 | ⚠️ 评估是否需要补充 |
| 文件未生成 | ❌ 需要重新执行 |

## 实际案例

### 电力数据 AI 分析步骤

```
状态: timeout (600s 超时)
检查结果:
  - dianli.txt: 127 URLs ✓
  - excluded.txt: 133 URLs ✓
  - guojiadianwang.txt: 0 URLs ✓
  - report.txt: 已生成 ✓

结论: 任务实际完成，超时是因为 API 调用过多
处理: 继续下一步，跳过重试
```

## 原因分析

Subagent 超时通常因为：
1. **API 调用过多** - 最常见原因
2. **网络延迟** - 远程服务器响应慢
3. **实际任务失败** - 较少见

## 最佳实践

1. 超时后**先检查输出**，不要立即重试
2. 验证输出文件的完整性（行数、大小、格式）
3. 只有确认失败才重试

## 相关技能

- `workflow-guardian-pattern` - 断点工作流守护机制

## 发现时间

2026-05-06
