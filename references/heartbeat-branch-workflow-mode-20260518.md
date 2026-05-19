# 拼接工作流心跳接力机制

## 问题背景

拼接工作流初始化时，expander 生成的 status.json 会覆盖心跳关键字段（scan_date、parallel_signal、step_status），导致心跳状态丢失。

## 解决方案

**方案 A**：心跳检测拼接工作流模式，跳过父状态检查，保留关键字段。

## 修改位置

**文件**：`~/.hermes/workflows/home漏扫/heartbeat.py`

### 修改 1：should_stop_and_cleanup()

**位置**：L1033-1090

**逻辑**：
```python
workflow_type = status.get("type", "")
if workflow_type == "branch":
    log("🔄 拼接工作流模式，跳过父状态检查")
else:
    # 普通工作流模式：原有逻辑
```

### 修改 2：initialize_scan()

**位置**：L160-220

**逻辑**：
```python
if workflow_type == "branch":
    is_branch_mode = True
    # 保留父工作流字段
    saved_workflow = old_status.get("workflow", "")
    saved_type = old_status.get("type", "")
    saved_status = old_status.get("status", "initialized")
    saved_started_at = old_status.get("started_at", "")
    saved_sub_workflows = old_status.get("sub_workflows", [])
    saved_all_steps = old_status.get("steps", {})
```

### 修改 3：main()

**位置**：L1145

**逻辑**：
```python
if workflow_type != "branch" and scan_date != today:
    # 拼接工作流跳过日期重置
```

## 关键机制

```
心跳检测 type == "branch"?
├─ 是 → 拼接工作流模式
│   ├─ 跳过 status 字段检查
│   ├─ 跳过 scan_date 检查
│   ├─ 保留父工作流字段
│   └─ 只检测远程状态（WIH/AWVS）
│
└─ 否 → 普通工作流模式
    └─ 原有逻辑
```

## 向后兼容

- 缺少 `type` 字段 → 默认普通模式
- 旧心跳脚本 → 不受影响

## 测试验证

```bash
python3 ~/.hermes/workflows/home漏扫/test_branch_mode.py
```

## 设计原则

**拼接工作流**：
- 父工作流管理整体状态
- 心跳只检测远程进度
- 不干预父工作流状态字段

**普通工作流**：
- 心跳管理完整状态
- 日期隔离生效
- 状态检查生效
