# 心跳步骤编号一致性检查与修复方法论

**创建时间**：2026-05-09
**触发场景**：心跳无法停止、持续发送告警、工作流状态混乱

---

## 问题特征

当出现以下症状时，应检查步骤编号一致性：

1. 心跳无法自动停止（超过预期时间）
2. 持续发送重复告警
3. `status.json` 中步骤编号与工作流定义不一致
4. 停止条件检查的步骤不存在

---

## 根本原因

**三层编号不一致**：

| 层级 | 文件 | 常见问题 |
|------|------|----------|
| 工作流定义 | `_index.yaml` | 定义 step_1/2/3，但心跳执行更多步骤 |
| 心跳脚本 | `heartbeat.py` | 执行 step_6/7/8，检查 step_6/7/8 |
| 状态文件 | `status.json` | 记录 step_10/11（由其他脚本写入） |

**结果**：停止条件永远无法满足，心跳持续运行。

---

## 诊断方法

### 步骤 1：检查工作流定义

```bash
cat ~/.hermes/workflows/<工作流名>/_index.yaml | grep "id: step"
```

记录定义的步骤编号。

### 步骤 2：检查心跳脚本停止条件

```bash
grep -n "required_steps" ~/.hermes/workflows/<工作流名>/heartbeat.py
```

记录心跳检查的步骤编号。

### 步骤 3：检查状态文件

```bash
cat ~/.hermes/workflows/<工作流名>/status.json | jq '.step_status | keys'
```

记录实际记录的步骤编号。

### 步骤 4：对比三层编号

如果三层编号不一致 → 确认问题。

---

## 修复方案

### 方案 A：统一步骤编号（推荐）

**原则**：重新规划步骤编号，确保语义清晰、连续。

**步骤**：

1. 定义完整的步骤列表（包括心跳自动执行的步骤）
2. 更新工作流定义 `_index.yaml`
3. 更新心跳脚本停止条件
4. 添加状态迁移逻辑（自动转换旧编号）

**示例**：

```yaml
# _index.yaml
nodes:
  - id: step_1  # 启动扫描
  - id: step_2  # 断点返回
  - id: step_3  # WIH下载（心跳执行）
  - id: step_4  # AWVS下载（心跳执行）
  - id: step_5  # JS分析（心跳触发）
  - id: step_6  # AWVS报告分析（心跳触发）
  - id: step_7  # 清理任务（心跳执行）
```

```python
# heartbeat.py
required_steps = ["step_5", "step_6", "step_7"]
```

### 方案 B：状态迁移机制

**在 `read_status()` 函数中添加自动迁移**：

```python
def read_status() -> dict:
    """读取工作流状态，自动迁移旧步骤编号"""
    with open(STATUS_FILE) as f:
        status = json.load(f)
    
    # 迁移映射
    step_mapping = {
        "step_10": "step_5",  # JS分析
        "step_11": "step_6",  # AWVS报告分析
    }
    
    step_status = status.get("step_status", {})
    migrated = []
    
    for old_id, new_id in step_mapping.items():
        if old_id in step_status:
            step_status[new_id] = step_status.pop(old_id)
            migrated.append(f"{old_id}→{new_id}")
    
    if migrated:
        status["step_status"] = step_status
        status["migration_info"] = {
            "migrated_at": datetime.now().isoformat(),
            "migrated_steps": migrated
        }
        write_status(status)
        log(f"✅ 自动迁移步骤编号: {migrated}")
    
    return status
```

---

## 告警去重机制

**问题**：告警消息文件未更新，导致用户看到旧告警。

**解决方案**：检查 `alert_status` 状态

```python
def should_send_awvs_alert(status: dict) -> tuple:
    """检查是否应该发送 AWVS 告警（去重机制）"""
    alert_status = status.get("heartbeat", {}).get("awvs", {}).get("alert_status")
    
    if alert_status == "sent":
        return False, "告警已发送"
    
    if alert_status == "message_prepared":
        return False, "告警消息已准备，等待人工发送"
    
    return True, "需要发送告警"
```

---

## 测试验证流程

**用户偏好**：先模拟测试验证方案可行性，再实施。

### 测试步骤

1. **创建测试环境**
   ```bash
   mkdir -p /tmp/<工作流名>-test/{workflow,scripts,results}
   ```

2. **模拟当前问题状态**
   - 复制当前工作流定义
   - 复制当前状态文件
   - 模拟心跳停止条件检查

3. **验证修复逻辑**
   - 测试状态迁移机制
   - 测试停止条件修正
   - 测试告警去重机制

4. **真实数据验证**
   - 使用真实 `status.json` 测试
   - 验证迁移逻辑正确性

5. **输出测试报告**
   - 记录测试结果
   - 确认方案可行

---

## 实施流程

**阶段 1：紧急处理**
- 停止当前心跳（如无法自动停止）
- 补充执行缺失步骤
- 更新状态文件

**阶段 2：方案实施**
- 更新工作流定义
- 更新心跳脚本
- 添加状态迁移逻辑
- 添加告警去重机制

**阶段 3：验证测试**
- 验证停止条件
- 验证告警去重
- 验证状态迁移

---

## 检查清单

修复完成后验证：

- [ ] 工作流定义步骤编号连续
- [ ] 心跳停止条件检查正确的步骤
- [ ] 状态迁移逻辑已添加
- [ ] 告警去重机制已添加
- [ ] 测试验证通过

---

## 长期稳定性保障

1. **步骤编号规范**
   - 工作流定义、心跳脚本、状态文件使用统一编号
   - 编号连续、语义清晰
   - 避免跳跃式编号

2. **停止条件验证**
   - 停止前检查所有步骤是否真的完成
   - 记录验证结果到 `status.json`

3. **告警去重机制**
   - 告警发送后标记 `alert_status: "sent"`
   - 心跳检测时检查告警状态

4. **状态迁移机制**
   - 心跳启动时自动检测旧编号
   - 自动转换为新编号

5. **文档同步规范**
   - 修改任一处时，同步更新其他相关处
   - 使用代码注释标注关联关系

---

**案例**：Home 漏扫心跳优化（2026-05-09）

**问题**：
- 工作流定义：step_1/2/3
- 心跳执行：step_6/7/8
- 状态记录：step_10/11
- 结果：心跳无法停止

**修复**：
- 统一为 step_1 ~ step_7
- 添加状态迁移逻辑
- 添加告警去重机制
- 测试验证通过
