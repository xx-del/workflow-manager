# findings.md 问题记录机制实现文档

> 实施日期：2026-05-14
> 状态：已部署，4/4 测试通过

---

## 1. 机制概述

为 workflow-manager 增加持久化问题记录文件 `findings.md`，不被 `execute.py --init` 清理，支持自动问题记录与动态统计更新。

## 2. 修改清单

| 文件 | 修改内容 |
|------|----------|
| `templates/findings.md` | 完全替换为问题记录模板（原为资产发现模板） |
| `actions/execute.py` | 增加 `update_findings_md()` 函数、`--reset-findings` 参数、函数调用 |
| `hooks/workflow-progress/handler.sh` | 增加 `auto_record_issue()` 函数、失败检测逻辑、提醒内容 |
| `SKILL.md` | 新增"九、问题记录机制"章节 |

## 3. execute.py 修改细节

### 新增参数
```
--reset-findings    重置 findings.md（删除并重建）
```

### 新增函数：update_findings_md()
- 位置：`init_workflow()` 函数之前
- 参数：`workflow_dir`, `template_path`, `reset=False`
- 行为：
  - `reset=True` 且文件存在 → 删除文件
  - 文件不存在 → 从模板创建，替换 `{created_at}` 和 `{updated_at}`
  - 文件已存在 → 仅更新"最后更新"时间戳（正则替换）
- 调用位置：清理 status.md 之后、生成 status.json 之前

### 函数签名变更
```python
# 旧
def init_workflow(workflow_name: str, workflow_path: str = None) -> dict:
# 新
def init_workflow(workflow_name: str, workflow_path: str = None, reset_findings: bool = False) -> dict:
```

### main() 调用更新
```python
result = init_workflow(args.workflow, args.path, args.reset_findings)
```

## 4. handler.sh 修改细节

### 环境变量约定（关键）

handler.sh 的自动记录依赖以下环境变量，需由调用方（executor.py 或主 AI）设置：

| 变量 | 必需 | 说明 | 默认值 |
|------|------|------|--------|
| `STEP_EXIT_CODE` | 否 | 上一步骤退出码 | `0`（不触发记录） |
| `CURRENT_STEP_NAME` | 否 | 当前步骤名称 | `未知步骤` |
| `STEP_ERROR_MSG` | 否 | 错误信息 | `未提供错误信息` |

**重要**：当前 executor.py 未设置这些环境变量。需在后续版本中由 executor 在步骤执行后设置，否则自动记录不会触发。

### auto_record_issue() 函数

```
位置：handler.sh 会话标记检查之后、原有提醒逻辑之前
并发安全：flock -x 200（排他锁）
锁文件：$WORKFLOW_INSTANCE_DIR/.findings.lock
```

**插入位置**：使用 `sed -i "/<!-- STATS_BLOCK_START/i $issue_line"` 在统计块之前插入新行

**统计更新**：内联 python3 脚本解析 STATS_BLOCK JSON，递增 total_issues 和 pending，更新 last_issue_time

### 提醒内容增强

在原有提醒末尾增加：
- findings.md 自动记录提示
- 手动补充格式说明
- --reset-findings 重置说明

## 5. 模板格式：动态统计块

```markdown
<!-- STATS_BLOCK_START
{"total_issues":0,"resolved":0,"pending":0,"last_issue_time":""}
STATS_BLOCK_END -->
```

- 位于 Issues Encountered 表格之后
- handler.sh 的 python3 内联脚本负责解析和更新
- 字段：total_issues, resolved, pending, last_issue_time

## 6. 问题类型分类

| 类型 | 说明 | 示例 |
|------|------|------|
| API 错误 | 外部 API 调用失败 | HTTP 503, 超时 |
| 网络错误 | 连接问题 | SSH 超时, DNS 失败 |
| 权限错误 | 认证失败 | 401, 密钥过期 |
| 数据错误 | 数据格式问题 | JSON 错误, 字段缺失 |
| 逻辑错误 | 工作流逻辑 | 依赖错误, 条件判断 |

## 7. 测试记录

| 测试 | 内容 | 结果 |
|------|------|------|
| 测试 1 | 初始化创建 findings.md + 时间戳 | ✅ 通过 |
| 测试 2 | 再次初始化保留内容 + 更新时间戳 | ✅ 通过 |
| 测试 3 | 模拟步骤失败自动记录 + 统计更新 | ✅ 通过 |
| 测试 4 | --reset-findings 重置 | ✅ 通过 |

**测试 3 遇坑**：第一次测试时工作流目录不在 `~/.hermes/workflows/` 下，导致 flock 创建 `.findings.lock` 失败（父目录不存在）。解决：确保工作流目录在 `~/.hermes/workflows/` 下。

## 8. 备份位置

```
~/.hermes/skills/openclaw-imports/workflow-manager/.backup/findings-mechanism-20260514_165257/
├── findings.md      (旧模板)
├── execute.py       (修改前)
├── handler.sh       (修改前)
└── SKILL.md         (修改前)
```

## 9. 待改进

- [ ] executor.py 需在步骤执行后设置 STEP_EXIT_CODE 等环境变量
- [ ] 问题类型目前硬编码为"未知错误"，可根据退出码或错误信息智能分类
- [ ] 统计块中的 resolved 计数目前无自动机制（需手动更新状态后触发）
