# 心跳清理逻辑最佳实践

**创建日期**: 2026-05-09
**问题来源**: home漏扫工作流心跳清理误删后续触发器

---

## 问题场景

工作流心跳启动时需要清理旧的心跳cronjob，但清理逻辑可能误删其他重要cronjob。

---

## 典型案例

**工作流名称**: home漏扫

**创建的cronjob**:
1. `home漏扫心跳监测`（主心跳，应清理）
2. `home漏扫-WIH完成检测`（后续工作流触发器，不应清理）
3. `home漏扫-AWVS完成检测`（后续工作流触发器，不应清理）

---

## 错误清理逻辑

```python
# ❌ 错误：匹配所有包含"home漏扫"的cronjob
if 'home漏扫' in lines[j]:
    old_job_ids.append(job_id)

# 结果：删除所有3个cronjob（误删触发器）
```

---

## 正确清理逻辑

```python
# ✅ 正确：精确匹配主心跳名称
if 'home漏扫心跳监测' in lines[j]:
    old_job_ids.append(job_id)

# 结果：只删除主心跳，保留触发器
```

---

## 核心原则

1. **精确匹配主心跳名称**，不使用模糊匹配
2. **保留后续工作流触发器**，它们有独立的触发条件
3. **测试验证清理逻辑**，确保不会误删重要cronjob

---

## Hermes Cronjob输出格式

```
  af88ec61fb75 [active]
    Name:      home漏扫心跳监测
    Schedule:  every 30m
    Repeat:    126/144
    Next run:  2026-05-09T11:46:27.006947+08:00
    Deliver:   local
    Skills:    agent-pool
```

---

## 解析方法

```python
import re

lines = result.stdout.strip().split('\n')
for i, line in enumerate(lines):
    # 匹配job_id行：2个空格 + 12位十六进制 + [状态]
    job_match = re.match(r'^\s+([a-f0-9]{12})\s+\[', line)
    if job_match:
        job_id = job_match.group(1)
        # 检查后续行（Name字段在后面）
        for j in range(i+1, min(i+8, len(lines))):
            if '精确的心跳名称' in lines[j]:
                old_job_ids.append(job_id)
                break
```

---

## Pitfall清单

- ❌ 使用模糊匹配（如 `'home漏扫' in line`）会误删所有相关cronjob
- ❌ 不测试清理逻辑直接在生产环境执行
- ❌ 忽略cronjob名称的完整格式（Name字段在后续行）

---

## 后续工作流触发器架构

**主工作流** → **主心跳** → **更新status.json** → **触发器检测** → **执行后续工作流**

```
主工作流（步骤1-5）
    ↓
步骤5.5：创建主心跳cronjob
    Name: "home漏扫心跳监测"
    Schedule: every 30m
    ↓
主心跳检测：
    ├─ WIH完成 → 执行步骤6 → heartbeat.wih.complete = true
    ├─ AWVS完成 → 执行步骤7 → heartbeat.awvs.is_complete = true
    └─ 全部完成 → 执行步骤8/9 → 停止主心跳

独立触发器（并行运行）：
├─ "home漏扫-WIH完成检测"（每5分钟）
│   └─ 检测 heartbeat.wih.complete == true
│       └─ 触发步骤10（JS敏感信息分析）
│
└─ "home漏扫-AWVS完成检测"（每5分钟）
    └─ 检测 heartbeat.awvs.is_complete == true
        └─ 触发步骤11（AWVS报告分析）
```

---

## 验证清单

- [ ] 清理逻辑是否精确匹配主心跳名称？
- [ ] 是否测试过清理逻辑不会误删触发器？
- [ ] 触发器cronjob是否已创建？
- [ ] 触发器检测脚本是否正确读取status.json？
- [ ] 触发器执行后是否更新status.json避免重复触发？
