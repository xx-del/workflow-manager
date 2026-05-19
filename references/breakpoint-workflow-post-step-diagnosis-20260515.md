# 断点工作流后续步骤未执行诊断

**日期**: 2026-05-15
**工作流**: home漏扫
**问题**: 心跳完成后，步骤 10/11（JS 分析 + AWVS 分析）未执行

---

## 问题现象

| 项目 | 预期 | 实际 | 状态 |
|------|------|------|------|
| 步骤 10 (JS分析) | WIH 完成后自动触发 | cronjob 不存在 | ❌ |
| 步骤 11 (AWVS分析) | AWVS 完成后自动触发 | cronjob 不存在 | ❌ |
| status.json | 包含步骤 10/11 状态 | 无相关字段 | ❌ |
| heartbeat 标记 | 已设置但无人消费 | wih.complete=true, awvs.is_complete=true | ⚠️ |

---

## 根因分析

### 架构设计

WORKFLOW.md 设计了独立 cronjob 触发机制：

```
主心跳（步骤 5.5）
  ↓
检测 WIH/AWVS 完成
  ↓
执行步骤 6/7/8/9
  ↓
设置 heartbeat 标记
  ↓
独立 cronjob 检测标记 → 触发步骤 10/11
```

### 实际状态

```
主心跳 → 执行步骤 6/7/8/9 → 设置标记 ✅
独立 cronjob → 不存在 ❌ → 步骤 10/11 未执行
```

**根因**：用户未按 WORKFLOW.md 设计创建独立 cronjob。

---

## 诊断方法

### 1. 检查 cronjob 是否存在

```bash
hermes cronjob list | grep -E "漏扫|wih|awvs"
```

**预期输出**：应显示类似 `home漏扫-WIH完成检测`、`home漏扫-AWVS完成检测` 的 cronjob

**实际输出**：无相关 cronjob

### 2. 检查 status.json 标记

```bash
cat ~/.hermes/workflows/home漏扫/status.json | jq '.heartbeat'
```

**输出**：
```json
{
  "wih": {
    "complete": true
  },
  "awvs": {
    "is_complete": true
  }
}
```

**分析**：标记已设置，但无人消费。

### 3. 检查步骤状态

```bash
cat ~/.hermes/workflows/home漏扫/status.json | jq '.steps | keys'
```

**输出**：`["0", "1", "2", "3", "4", "5", "5.5", "6", "7", "8", "9"]`

**分析**：缺少步骤 10/11。

---

## 修复方案

### 方案 1：立即手动触发（推荐）

**步骤 10**：
```python
delegate_task(
  goal="执行 WIH JS 敏感信息分析",
  toolsets=["skills"],
  context={
    "技能": "awvs-report-extractor",
    "输入目录": "/x/rank/hwxinxisouji/liuliang/results/20260515/wih",
    "输出目录": "/x/rank/hwxinxisouji/liuliang/results/20260515/js_analysis"
  }
)
```

**步骤 11**：
```python
delegate_task(
  goal="执行 AWVS 报告分析",
  toolsets=["skills"],
  context={
    "技能": "awvs-report-extractor",
    "输入目录": "/x/rank/hwxinxisouji/liuliang/results/20260515/awvs",
    "输出目录": "/x/rank/hwxinxisouji/liuliang/results/20260515/awvs_analysis"
  }
)
```

### 方案 2：创建独立 cronjob（长期）

**WIH 完成 cronjob**：
```bash
hermes cronjob create "every 5m" \
  "检测 WIH 完成并执行 JS 分析" \
  --name "home漏扫-WIH完成检测" \
  --script ~/.hermes/workflows/home漏扫/wih_monitor.py \
  --repeat 2016 \
  --deliver local
```

**AWVS 完成 cronjob**：
```bash
hermes cronjob create "every 5m" \
  "检测 AWVS 完成并执行报告分析" \
  --name "home漏扫-AWVS完成检测" \
  --script ~/.hermes/workflows/home漏扫/awvs_monitor.py \
  --repeat 2016 \
  --deliver local
```

---

## 验证清单

- [ ] 步骤 10 已执行（js_analysis/report.md 存在）
- [ ] 步骤 11 已执行（awvs_analysis/report.md 存在）
- [ ] status.json 已更新（包含步骤 10/11 状态）
- [ ] heartbeat.analyzed 标记已设置

---

## 经验总结

1. **设计验证**：WORKFLOW.md 设计了独立 cronjob，但实际未创建，导致功能缺失
2. **标记消费**：heartbeat 标记是信号机制，需要消费者（cronjob）才能触发后续动作
3. **诊断优先级**：先检查 cronjob 是否存在，再检查标记是否设置，最后检查步骤状态

---

## 相关文档

- WORKFLOW.md 步骤 10/11 设计
- `wih_monitor.py` - WIH 完成检测脚本
- `awvs_monitor.py` - AWVS 完成检测脚本
- `post_workflows/wih_complete_monitor.json` - cronjob 配置模板
- `post_workflows/awvs_complete_monitor.json` - cronjob 配置模板
