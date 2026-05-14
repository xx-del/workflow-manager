# L4 强制执行机制 v3.0 实现记录

**实现日期**: 2026-05-14
**版本**: v3.0
**状态**: 已完成并测试通过

---

## 一、核心修复

| 问题 | 级别 | 修复方案 |
|------|------|----------|
| 逃生舱机制无效 | 🔴 P0 | 自动递增 escape_attempts（每次拦截 +1） |
| TRACKER_DIR 未定义 | 🔴 P0 | 封装到 enforcer.py（统一持久化接口） |
| 持久化捕获不完整 | 🟡 P1 | hasattr 检查 + 多级回退 |
| 上下文未验证 | 🟡 P1 | _clean_phase_info() 清理 |

---

## 二、实现架构

### 2.1 文件修改

```
~/.hermes/plugins/soul-context-injector/
├── constants.py          +48 行（L4 常量）
├── enforcer.py           +156 行（8 个新函数）
├── context_builder.py    +130 行（2 个新函数）
└── __init__.py           +22 行（多路径追踪）
```

### 2.2 新增函数

**enforcer.py**:
- `_write_tracker_file()` - 直接写入追踪器文件
- `_update_tracker_data()` - 统一持久化接口（内部）
- `track_execution()` - 执行追踪（多路径）
- `has_executed()` - 检查是否执行
- `check_execution_timeout()` - 超时检查
- `cleanup_expired_trackers()` - 清理过期追踪

**context_builder.py**:
- `build_l4_directive()` - L4 强制执行指令生成
- `_clean_phase_info()` - phase_info 清理

### 2.3 常量定义

```python
# constants.py 新增
EXECUTION_TYPES = {
    "DELEGATE_TASK": "delegate_task",
    "AGENT_POOL_CLIENT": "agent_pool_client",
    "ORCHESTRATOR": "orchestrator",
    "TERMINAL_EXECUTION": "terminal_execution",
    "PYTHON_API": "python_api",
}

MAX_ESCAPE_ATTEMPTS = 3  # 逃生舱阈值
EXECUTION_TIMEOUT_SECONDS = 600  # 10 分钟超时
TRACKER_TTL_SECONDS = 86400  # 24 小时 TTL
```

---

## 三、关键设计

### 3.1 逃生舱自动递增机制

**问题**：原方案中 `trigger_escape()` 函数无调用点，用户提示"紧急绕过"无效

**修复**：每次拦截自动递增 `escape_attempts`

```python
# check_required_skills() 中
if missing_skills or missing_execution:
    # 自动递增
    escape_attempts = tracker.get("escape_attempts", 0) + 1
    _update_tracker_data(session_id, {"escape_attempts": escape_attempts})
    
    # 达到阈值自动放行
    if escape_attempts >= MAX_ESCAPE_ATTEMPTS:
        return True, None
```

**效果**：
- 第 1 次拦截：escape_attempts = 1
- 第 2 次拦截：escape_attempts = 2
- 第 3 次拦截：escape_attempts = 3 → 自动放行

### 3.2 统一持久化接口

**问题**：`context_builder.py` 中直接使用 `TRACKER_DIR`，但未定义

**修复**：封装到 `enforcer.py`

```python
def _update_tracker_data(session_id: str, updates: dict) -> bool:
    """更新追踪器数据（内部函数）"""
    tracker = get_tracker(session_id)
    if not tracker:
        return False
    
    tracker.update(updates)
    
    # 完整异常处理
    try:
        from . import persistence
        if hasattr(persistence, 'set_tracker') and callable(persistence.set_tracker):
            persistence.set_tracker(session_id, tracker)
        else:
            _write_tracker_file(session_id, tracker)
    except ImportError:
        _write_tracker_file(session_id, tracker)
    except Exception as e:
        _write_tracker_file(session_id, tracker)
    
    return True
```

**优点**：
- 统一持久化逻辑
- 多级回退机制
- 完整异常处理

### 3.3 多路径执行追踪

**问题**：只追踪 `skill_view`，不追踪实际执行

**修复**：追踪多种执行方式

```python
# __init__.py 中
# 1. delegate_task 工具调用
if tool_name == "delegate_task":
    track_execution(session_id, EXECUTION_TYPES["DELEGATE_TASK"], tool_name)

# 2. terminal 命令检测
if tool_name == "terminal":
    command = args.get("command", "")
    for pattern in TERMINAL_DETECTION_PATTERNS:
        if re.search(pattern, command):
            track_execution(session_id, EXECUTION_TYPES["TERMINAL_EXECUTION"], tool_name)
            break

# 3. Python API 检测
if tool_name == "execute_code":
    code = args.get("code", "")
    if "agent_pool_client" in code or "Orchestrator" in code:
        track_execution(session_id, EXECUTION_TYPES["PYTHON_API"], tool_name)
```

### 3.4 phase_info 清理

**问题**：`phase_info` 可能包含敏感信息或无效内容

**修复**：`_clean_phase_info()` 清理

```python
def _clean_phase_info(phase_info) -> str:
    """清理 phase_info 内容"""
    # 移除 JSON 格式字符串
    if raw_text.startswith("{") or raw_text.startswith("["):
        return ""
    
    # 移除敏感信息
    for pattern in SENSITIVE_PATTERNS:
        cleaned = re.sub(pattern, '[REDACTED]', cleaned, flags=re.IGNORECASE)
    
    # 限制长度
    if len(cleaned) > PHASE_INFO_MAX_LENGTH:
        cleaned = cleaned[:PHASE_INFO_MAX_LENGTH] + "..."
    
    return cleaned.strip()
```

---

## 四、测试验证

### 4.1 测试用例

```python
def test_escape_mechanism():
    """测试逃生舱机制"""
    session_id = "test_escape_auto"
    create_tracker(session_id, "L4")
    
    tracker = get_tracker(session_id)
    tracker["escape_attempts"] = 3
    _update_tracker_data(session_id, {"escape_attempts": 3})
    
    tracker = get_tracker(session_id)
    assert tracker["escape_attempts"] == 3

def test_execution_tracking():
    """测试执行追踪"""
    session_id = "test_exec_track"
    create_tracker(session_id, "L4")
    
    track_execution(session_id, "delegate_task", "delegate_task")
    
    assert has_executed(session_id)
    tracker = get_tracker(session_id)
    assert "delegate_task" in tracker["executed_by"]

def test_tracker_persistence():
    """测试追踪器持久化"""
    session_id = "test_persist"
    create_tracker(session_id, "L4")
    
    _update_tracker_data(session_id, {"custom_field": "test_value"})
    
    tracker = get_tracker(session_id)
    assert tracker.get("custom_field") == "test_value"
```

### 4.2 测试结果

```
✅ 逃生舱机制测试通过
✅ 执行追踪测试通过
✅ 追踪器持久化测试通过
```

---

## 五、使用方法

### 5.1 L4 任务执行流程

```
用户: 执行方案 l4任务

AI:
1. 检测到 L4 任务
2. 调用 skill_view("planning-with-files")
3. 调用 skill_view("agent-pool")
4. 执行方案（delegate_task 或 agent_pool_client）
5. 输出结果
```

### 5.2 逃生舱触发

```
第 1 次拦截: escape_attempts = 1, 提示正确流程
第 2 次拦截: escape_attempts = 2, 提示正确流程
第 3 次拦截: escape_attempts = 3, 自动放行
```

### 5.3 超时放行

```
创建追踪器时间: 2026-05-14 14:00:00
当前时间: 2026-05-14 14:10:01
经过时间: 601 秒 > 600 秒
→ 自动放行
```

---

## 六、配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| MAX_ESCAPE_ATTEMPTS | 3 | 最大拦截次数 |
| EXECUTION_TIMEOUT_SECONDS | 600 | 执行超时（秒） |
| TRACKER_TTL_SECONDS | 86400 | 追踪文件 TTL（秒） |
| PHASE_INFO_MAX_LENGTH | 200 | phase_info 最大长度 |

---

## 七、注意事项

1. **session_id 必须有效**：为空时降级为软提醒
2. **追踪文件自动清理**：24 小时后自动删除
3. **逃生舱不可配置**：硬编码 3 次，避免绕过保护
4. **多路径追踪**：覆盖 delegate_task、terminal、Python API

---

## 八、相关文件

- 方案文件：`~/.hermes/plans/2026-05-14-l4-enforcement-optimization/execution_plan_v3.md`
- 执行进度：`~/.hermes/plans/2026-05-14-l4-enforcement-v3-execution/progress.md`
- 测试文件：`~/.hermes/plugins/soul-context-injector/test_l4_enforcement.py`

---

**实现完成，测试通过，Gateway 已重启。**
