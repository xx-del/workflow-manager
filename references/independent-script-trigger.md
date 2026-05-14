# 独立脚本触发工作流架构约束

## 问题场景

当独立 Python/Shell 脚本需要触发工作流时，存在**能力断层**：

```
独立脚本（代码）
    ↓
❌ 无法直接调用 workflow-manager 技能
    ↓
❌ 无法直接调用 delegate_task 工具
    ↓
结果：只能更新状态标记，无法真正执行工作流
```

## 实际案例

### 案例：wih_monitor.py

**背景**：
- 工作流：home漏扫
- 独立脚本：`~/.hermes/workflows/home漏扫/wih_monitor.py`
- 任务：检测 WIH 完成，触发 JS 敏感信息分析工作流

**问题代码**：
```python
# wih_monitor.py 第76-90行
# TODO: 这里需要调用workflow-manager执行JS敏感信息分析工作流
# 由于技能无法直接调用，这里先记录信号
log(f"📝 准备执行JS敏感信息分析")
log(f"   输入目录: {wih_result_dir}")
log(f"   输出目录: {output_dir}")

# 更新status
status.setdefault("heartbeat", {}).setdefault("wih", {})
status["heartbeat"]["wih"]["analyzed"] = True  # ❌ 只更新标记，未真正执行
status["heartbeat"]["wih"]["analyzed_at"] = datetime.now().isoformat()
write_status(status)
```

**后果**：
- 脚本标记了 `analyzed = True`，但实际未执行 JS 分析
- 后续 cronjob 检测到 `analyzed = True` 后跳过执行
- 工作流中断，JS 分析被静默跳过

## 正确架构

### 方案 1：信号标记 + Cronjob 监听（推荐）

```
独立脚本
    ↓
更新 status.json 标记（如 heartbeat.wih.complete = true）
    ↓
Hermes cronjob 定期检测标记
    ↓
检测到触发条件 → AI 执行工作流
```

**实现要点**：
1. 脚本只负责检测条件、更新标记
2. 不要在脚本中写 `analyzed = True`（这会阻止后续执行）
3. 配置 Hermes cronjob 来监听标记并执行工作流

**Cronjob 配置示例**：
```bash
hermes cronjob create \
  --name "WIH完成监听" \
  --schedule "every 5m" \
  --prompt "检测 ~/.hermes/workflows/home漏扫/status.json 中的 heartbeat.wih.complete 字段，如果为 true 且 analyzed 为 false，则执行 JS 敏感信息分析工作流"
```

### 方案 2：Hermes Cronjob 直接执行

```bash
# 不使用独立脚本，直接用 cronjob 执行监控逻辑
hermes cronjob create \
  --name "WIH监控" \
  --schedule "every 30m" \
  --prompt "执行 WIH 监控逻辑：
1. 读取 ~/.hermes/workflows/home漏扫/status.json
2. 检测 heartbeat.wih.complete 是否为 true
3. 如果是，调用 workflow-manager 执行 JS 敏感信息分析工作流
4. 输入目录：/x/rank/hwxinxisouji/liuliang/results/{scan_date}/wih
5. 输出目录：/x/rank/hwxinxisouji/liuliang/results/{scan_date}/js_analysis"
```

## 错误模式总结

| 错误模式 | 后果 | 正确做法 |
|----------|------|----------|
| 脚本中写 TODO 但不执行 | 工作流中断 | 使用 cronjob 触发 |
| 脚本中标记 `analyzed = True` | 后续执行被跳过 | 只标记 `complete`，不标记 `analyzed` |
| 脚本尝试调用技能 | 无法执行 | 脚本只更新状态，AI 执行工作流 |

## 验证清单

设计独立脚本触发工作流时，必须确认：

- [ ] 独立脚本是否只负责"检测条件 + 更新标记"？
- [ ] 脚本是否避免了设置"已完成"标记（如 `analyzed`）？
- [ ] 是否配置了对应的 Hermes cronjob 来监听标记？
- [ ] Cronjob 的 prompt 是否包含了完整的工作流触发指令？
- [ ] Cronjob 是否会在检测到标记后执行实际工作流？

## 版本历史

- v1.0.0 (2026-05-09): 初始版本 - 记录 wih_monitor.py 架构问题
