# 半自动化工作流模式

## 问题场景

当工作流包含需要人工参与的步骤时，如何正确管理状态标记？

### 案例：WIH 完成后触发 JS 敏感信息分析

**工作流定义**（`JS敏感信息分析/WORKFLOW.md`）：
- 步骤 1: 解压数据文件（自动化）
- 步骤 2: 提取URL并生成分析文件（自动化）
- 步骤 3: 数据清洗与敏感信息提取（需人工）
- 步骤 4: 批量JS处理与敏感信息验证（需人工）
- 步骤 5: 手动分析与数据清洗（需人工）

**问题**：
1. WIH 下载完成后，监控脚本触发 JS 分析
2. 自动化步骤 1-2 完成，生成 `final_merged.csv`
3. 步骤 3-5 需要人工参与
4. 如果标记 `analyzed=true`，下次监控会跳过执行
5. 但实际上工作流只完成了部分

## 解决方案

### 1. 状态标记语义

**区分三种状态**：

| 状态 | 含义 | 使用场景 |
|------|------|----------|
| `started` | 工作流已启动 | 开始执行第一个步骤 |
| `partial` | 部分完成 | 自动化步骤完成，人工步骤待执行 |
| `completed` | 全部完成 | 所有步骤（包括人工）已完成 |

**禁止语义混淆**：
- ❌ `analyzed`: 语义不清晰，不知道是"开始分析"还是"分析完成"
- ✅ `status`: 明确的执行进度状态

### 2. 详细进度记录

**status.json 结构**：

```json
{
  "heartbeat": {
    "wih": {
      "js_analysis": {
        "status": "partial",
        "completed_steps": [1, 2],
        "pending_steps": [3, 4, 5],
        "output_files": {
          "final_merged_csv": "/x/rank/hwxinxisouji/liuliang/jietu/final_merged.csv"
        },
        "started_at": "2026-05-11T18:55:00+08:00",
        "automated_completed_at": "2026-05-11T18:59:00+08:00",
        "note": "步骤1-2自动化完成，步骤3-5需人工参与"
      }
    }
  }
}
```

### 3. 监控脚本逻辑

**错误的检查逻辑**：
```python
# ❌ 错误：analyzed=true 可能只是"开始处理"
if status.get("heartbeat", {}).get("wih", {}).get("analyzed", False):
    log("✅ WIH已分析，跳过")
    return "ALREADY_ANALYZED"
```

**正确的检查逻辑**：
```python
# ✅ 正确：检查完成状态
js_analysis = status.get("heartbeat", {}).get("wih", {}).get("js_analysis", {})
if js_analysis.get("status") == "completed":
    log("✅ JS分析已完成，跳过")
    return "COMPLETED"

if js_analysis.get("status") == "partial":
    log(f"⏸️ JS分析部分完成: {js_analysis.get('completed_steps', [])}")
    return "PARTIAL"

if js_analysis.get("status") == "started":
    log("⚠️ JS分析已启动但未完成自动化步骤")
    return "IN_PROGRESS"
```

### 4. 状态更新时机

| 时机 | 操作 | 更新字段 |
|------|------|----------|
| 工作流启动 | 标记开始 | `status="started"`, `started_at=<时间>` |
| 自动化步骤完成 | 标记部分完成 | `status="partial"`, `completed_steps=[1,2]`, `automated_completed_at=<时间>` |
| 人工步骤完成 | 标记全部完成 | `status="completed"`, `completed_at=<时间>` |

### 5. 报告生成

**自动化步骤完成后应生成报告**：

```markdown
# JS 敏感信息分析进度报告

**状态**: partial（部分完成）

**已完成步骤**:
- ✅ 步骤 1: 解压数据文件
- ✅ 步骤 2: 提取URL并生成分析文件

**待人工步骤**:
- ⏸️ 步骤 3: 数据清洗与敏感信息提取
- ⏸️ 步骤 4: 批量JS处理与敏感信息验证
- ⏸️ 步骤 5: 手动分析与数据清洗

**输出文件**:
- `final_merged.csv`: 76 KB (691 行)
- 包含 690 个 URL
- 发现 38 个密码字段
- 发现 30 个邮箱字段

**下一步操作**:
```bash
cd /x/rank/hwxinxisouji/liuliang/jietu
# 执行步骤 3-5...
```
```

## 最佳实践

### 1. 工作流设计原则

**明确标注步骤类型**：

```yaml
nodes:
  - id: 1
    name: 解压数据文件
    type: automated  # 自动化
    automation: full
    
  - id: 2
    name: 提取URL
    type: automated  # 自动化
    automation: full
    
  - id: 3
    name: 数据清洗
    type: manual  # 人工
    automation: none
    requires_human: true
```

### 2. 状态标记命名规范

| 标记名 | 推荐用法 | 示例 |
|--------|----------|------|
| `status` | 执行进度状态 | `started`, `partial`, `completed` |
| `started_at` | 开始时间 | ISO 时间戳 |
| `completed_at` | 完成时间 | ISO 时间戳 |
| `completed_steps` | 已完成步骤列表 | `[1, 2]` |
| `pending_steps` | 待完成步骤列表 | `[3, 4, 5]` |
| `note` | 备注信息 | "步骤1-2自动化完成" |

**避免模糊标记**：
- ❌ `analyzed`: 是"已分析"还是"开始分析"？
- ❌ `processed`: 是"已处理"还是"开始处理"？
- ❌ `done`: 过于简略，不知道什么完成

### 3. 监控脚本设计

**检查逻辑优先级**：
1. 检查 `status == completed` → 跳过
2. 检查 `status == partial` → 报告进度
3. 检查 `status == started` → 检查是否超时
4. 检查 `status` 不存在 → 执行

**错误处理**：
- 目标工作流不存在 → 记录错误，不更新状态
- 自动化步骤失败 → 记录错误，标记 `status=failed`
- 人工步骤未完成 → 保持 `status=partial`

## 相关案例

### 案例 1: WIH 监控触发 JS 分析

**文件**：`~/.hermes/workflows/home漏扫/wih_monitor.py`

**问题**：
- `analyzed=true` 导致跳过执行
- 实际上只完成了自动化步骤 1-2

**解决**：
- 使用 `status` 字段替代 `analyzed`
- 记录 `completed_steps` 和 `pending_steps`
- 生成进度报告告知用户

### 案例 2: AWVS 分析工作流

**文件**：`~/.hermes/workflows/home漏扫/post_workflows/awvs_complete_monitor.json`

**触发条件**：`heartbeat.awvs.is_complete == true`

**建议改进**：
- 添加 `awvs.analysis.status` 字段
- 区分"扫描完成"和"分析完成"

## 参考

- workflow-manager 技能：状态管理参考章节
- WORKFLOW.md 定义格式：nodes[].type 字段
