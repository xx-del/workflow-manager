# 故障排查

> ⚠️ **通过 agent 排查问题，禁止直接执行命令**

## 常见问题

### 1. 工作流执行失败

**症状**: status.json 显示 failed

**排查步骤**:
1. 读取历史记录文件
2. 检查输出目录
3. 分析错误原因

**解决方案**:
- 权限问题: 通过 agent 修复权限
- 依赖缺失: 通过 agent 安装依赖
- 配置错误: 修改 WORKFLOW.md

---

### 2. 定时任务不执行

**症状**: 设置了定时但未执行

**排查步骤**:
1. 使用 cron skill 检查定时状态
2. 检查 cron 服务状态
3. 查看定时日志

**解决方案**:
- 服务问题: 通过 cron skill 启动服务
- 路径错误: 修改工作流配置

---

### 3. 重试不生效

**症状**: 配置了重试但失败后未重试

**排查步骤**:
1. 检查 status.json 中的 retry 配置
2. 分析失败原因

**解决方案**:
- 确认 retry.enabled: true
- 确认 max_attempts > 0

---

### 4. 通知未发送

**症状**: 工作流完成/失败未收到通知

**排查步骤**:
1. 检查 status.json 中的 notify 配置
2. 测试通知渠道

**解决方案**:
- 确认 channel 正确
- 确认 on_complete / on_fail 为 true

---

### 5. 守护 Agent 不工作

**症状**: 工作流卡住但无守护 Agent 响应

**排查步骤**:
1. 检查 guardian 配置
2. 检查守护 agent 状态

**解决方案**:
- 确认 guardian.enabled: true
- 确认 interval 和 stuck_threshold 合理

---

### 6. 工作流未找到（Workflow not found）

**症状**: 执行工作流时报错 `Workflow not found`

**原因**: workflow-manager 使用两个目录结构：
- `~/.hermes/workflows/` - 工作流注册表（全局索引）
- `~/.hermes/workspace/workflows/` - 工作流执行目录（实际执行）

**排查步骤**:
1. 检查工作流是否在全局注册表中：
   ```bash
   cat ~/.hermes/workflows/_index.yaml | grep "工作流名称"
   ```

2. 检查工作流目录是否有 `_index.yaml`：
   ```bash
   ls -la ~/.hermes/workflows/工作流名称/_index.yaml
   ```

3. 检查工作流是否在 workspace 目录：
   ```bash
   ls -la ~/.hermes/workspace/workflows/工作流名称/_index.yaml
   ```

**解决方案**（按顺序尝试）:

**方案 A：从全局索引重建目录**（推荐）
```bash
# 1. 提取工作流定义（使用 Python/脚本）
cd ~/.hermes/workflows/工作流名称/
# 手动创建 _index.yaml 或从全局索引提取

# 2. 复制到 workspace
cp -r ~/.hermes/workflows/工作流名称 ~/.hermes/workspace/workflows/

# 3. 重新执行
~/.hermes/skills/openclaw-imports/workflow-manager/actions/execute.sh "工作流名称"
```

**方案 B：快速修复**（临时）
```bash
# 直接复制整个目录
cp -r ~/.hermes/workflows/工作流名称 ~/.hermes/workspace/workflows/
```

**注意事项**:
- workspace 目录下的 `_index.yaml` 必须包含 `nodes` 和 `connections` 字段
- 全局索引和工作流目录的版本应保持一致
- 修改 workspace 目录后，原工作流目录不会同步更新

**永久修复建议**:
修改 `workflow-executor.js` 的 `loadWorkflow()` 方法，支持从全局索引自动同步到 workspace。

---

### 7. 状态字段覆盖导致误判

**症状**: status.json 显示已完成但实际未执行（如 `heartbeat.wih.complete = true` 但 WIH 从未运行）

**根本原因**: 多个脚本并发更新 status.json 时，使用简化版结构覆盖了完整字段

**案例**: wih_monitor.py vs heartbeat.py
- heartbeat.py 维护详细状态：`screenshot_count`, `process_count`, `latest_file`, `stagnant_checks`
- wih_monitor.py 使用 `setdefault()` 创建简化结构：只保留 `complete`, `analyzed`
- 结果：详细字段丢失，状态判断失效

**诊断步骤**:
1. 检查 status.json 中的字段完整性：
   ```bash
   jq '.heartbeat.wih' ~/.hermes/workflows/工作流名称/status.json
   ```
   - 完整结构应包含：`complete`, `stagnant`, `latest_file`, `screenshot_count`, `stagnant_checks`, `process_count`
   - 简化结构只有：`complete`, `analyzed`（错误）

2. 对比心跳快照：
   ```bash
   ls ~/.hermes/workflows/工作流名称/status_*.json | tail -1 | xargs cat | jq '.heartbeat.wih'
   ```
   - 心跳快照保存了完整的检测状态

3. 检查时间戳一致性：
   - 压缩包时间戳 vs 工作流启动时间
   - 如果压缩包早于启动时间 → 历史文件，非本次扫描结果

**修复方法**:
```python
# 恢复完整状态结构
status["heartbeat"]["wih"] = {
    "complete": False,  # 实际状态
    "analyzed": False,
    "stagnant": False,
    "latest_file": "/path/to/file.tar.gz",
    "screenshot_count": 0,
    "stagnant_checks": 0,
    "process_count": 0,
    "note": "详细诊断信息"
}
```

**预防措施**:
- 更新 status.json 时，使用**部分更新**而非整体替换
- 保留其他脚本维护的字段：
  ```python
  # ❌ 错误：覆盖整个对象
  status["heartbeat"]["wih"] = {"complete": True}
  
  # ✅ 正确：只更新需要的字段
  status.setdefault("heartbeat", {}).setdefault("wih", {})
  status["heartbeat"]["wih"]["complete"] = True
  # 保留其他字段不变
  ```
- 监控脚本应检查字段完整性，发现缺失时报警

---

## 诊断步骤

| 步骤 | 用途 |
|------|------|
| 列出工作流 | 读取 _index.yaml |
| 查看状态 | 读取 status.json |
| 查看历史 | 列出 history/ 目录 |
| 查看定时 | 使用 cron skill |
| 检查字段完整性 | `jq '.heartbeat.*' status.json` |
