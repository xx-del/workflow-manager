# Hook 会话标记机制实施记录

**实施日期**: 2026-05-14
**方案**: 方案 B（会话标记文件机制）
**状态**: ✅ 已实施并验证

---

## 背景

### 问题

workflow-manager 的 Hook 在非工作流会话中也会触发，导致：
- 用户进行普通对话时注入工作流上下文
- 污染上下文，影响正常交互

### 需求

Hook 只在工作流会话中触发，其他时候不触发。

---

## 方案分析

### 方案 C：技能加载检测

**原理**：检测 workflow-manager 技能是否在当前会话加载。

**可行性分析结果**：❌ 无法实施

**原因**：
1. Hermes 不追踪会话级技能加载状态（无 `self.loaded_skills`）
2. Plugin Hook 回调不传递技能信息
3. skill-hook-bridge TemplateResolver 不支持 `{{loaded_skills}}` 变量

**需要的 Hermes 核心修改**：
- `run_agent.py`: 添加 `self.loaded_skills = []` 属性
- `hermes_cli/plugins.py`: PluginContext 添加 `get_loaded_skills()` 方法
- `gateway/run.py`: Gateway 会话同样需要追踪

**工作量评估**：~100-150 行代码，需要 PR 和 code review

### 方案 B：会话标记文件（已实施）

**原理**：工作流初始化时创建标记文件，Hook 检测标记决定是否触发。

**优势**：
- 零侵入（不修改 Hermes 核心）
- 只修改技能目录内的文件
- 立即可用

---

## 实施内容

### 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `actions/execute.py` | 修改 | 添加 `import os`，创建标记文件 |
| `actions/complete.py` | 修改 | 清理标记文件 |
| `hooks/workflow-context/handler.sh` | 修改 | 添加 MARKER_FILE 检测 |
| `hooks/workflow-step-check/handler.sh` | 修改 | 添加 MARKER_FILE 检测 |
| `hooks/workflow-progress/handler.sh` | 修改 | 添加 MARKER_FILE 检测 |
| `scripts/cleanup_marker.py` | 新增 | 异常清理脚本 |

### 标记文件格式

**路径**: `~/.hermes/workflows/.active_session`

**内容**:
```json
{
    "workflow_name": "工作流名称",
    "session_id": "20260514_122904",
    "started_at": "2026-05-14T12:29:04.156628",
    "pid": 2576366
}
```

### Hook 检测逻辑

```bash
MARKER_FILE="$HOME/.hermes/workflows/.active_session"

if [[ ! -f "$MARKER_FILE" ]]; then
    exit 0  # 非工作流会话，静默退出
fi

# 有标记 → 读取 workflow_name → 注入上下文
WORKFLOW_NAME=$(python3 -c "import json; print(json.load(open('$MARKER_FILE'))['workflow_name'])")
```

### 异常清理机制

**cleanup_marker.py 功能**：
- PID 存活检测（`os.kill(pid, 0)`）
- 强制清理选项（`--force`）
- JSON 输出支持（`--json`）

**使用场景**：
1. Gateway 启动时调用
2. 会话异常中断后
3. 定期清理任务

---

## 验证结果

### 测试 1：标记文件创建

```
✅ execute.py --init 成功创建 .active_session
✅ 包含 workflow_name, session_id, started_at, pid
```

### 测试 2：Hook 读取标记

```
✅ workflow-context 正确注入上下文
✅ workflow-step-check 正确注入约束
```

### 测试 3：无标记静默退出

```
✅ 3 个 Handler 均静默退出（退出码 0，无输出）
```

### 测试 4：清理脚本功能

```
✅ PID 不存在检测 → 清理残留标记
✅ --force 参数 → 强制清理
✅ --json 参数 → JSON 输出
```

### 测试 5：工作流完成清理

```
✅ complete.py 清理标记
✅ 标记文件被删除
```

### 测试 6：清理后静默

```
✅ 标记删除后 Hook 不再触发
```

---

## 工作流执行验证

**测试工作流**: 凭证检测
**结果**: 
- 检测 19 URL
- Hook 触发统计：UserPromptSubmit 1次, PreToolUse 1次, PostToolUse 4次
- 工作流完成后标记正确清理
- 清理后 Hook 静默退出

---

## 改进建议

1. **Gateway 启动清理**: 在 Gateway 启动脚本添加 `cleanup_marker.py` 调用
2. **定期清理**: 添加 cronjob 每小时清理残留标记
3. **多工作流并发**: 当前设计已支持（标记记录 workflow_name）

---

## 参考文档

- `scripts/cleanup_marker.py` - 异常清理脚本
- `actions/execute.py` - 标记创建逻辑（第 86-109 行）
- `actions/complete.py` - 标记清理逻辑（第 181-188 行）
- `hooks/*/handler.sh` - 标记检测逻辑
