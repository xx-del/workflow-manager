# Hook 类型识别一致性问题与修复方案

**日期**：2026-05-15
**状态**：已验证，待实施

---

## 一、问题描述

### 问题 A：类型识别不一致

**现象**：`generate_status_md` 直接读取 `_index.yaml` 的 `type` 字段，而实际类型由 `loader.py` 的 5 个条件推断。

**验证结果**：

| 工作流 | _index.yaml type字段 | loader 推断类型 | 不一致 |
|--------|---------------------|----------------|--------|
| 资产收集流程 | (未设置) | branch | ⚠️ 是 |
| home漏扫 | (未设置) | heartbeat | ⚠️ 是 |

**影响**：
- status.md 包含错误类型
- 主 AI 看到的约束与实际执行不一致
- 可能执行错误策略

### 问题 B：函数定义顺序

**现象**：`generate_status_md` 定义在文件末尾，调用在定义之前。

**风险**：虽然 Python 运行时不会报错，但影响可读性和维护性。

---

## 二、修复方案

### 修复 A：generate_status_md 接收外部传入的类型

**核心原则**：generate_status_md 不自行判断类型，使用外部已识别的准确类型。

**修改函数签名**：
```python
def generate_status_md(workflow_name: str, workflow_type: str = None) -> str:
    """
    Args:
        workflow_name: 工作流名称
        workflow_type: 工作流类型（可选，若传入则直接使用，保证一致性）
    """
    if workflow_type is None:
        # 回退方案：从 _index.yaml 读取（不推荐）
        workflow_type = workflow_config.get('type', 'normal')
        type_warning = True  # 添加警告注释
    # else: 使用传入的准确类型（推荐）
```

**Hook 调用修改**：
```bash
# handler.sh 传入已识别的准确类型
python3 -c "
from execute import generate_status_md
content = generate_status_md('$workflow_name', '$workflow_type')
"
```

### 修复 B：函数定义前置

将 `generate_status_md` 移至文件头部（imports 之后，其他函数之前）。

---

## 三、类型识别统一来源模式

```
┌──────────────────────────────────────────────┐
│            identify_type.py                   │
│  （使用 loader._identify_workflow_type()）    │
└──────────────────────────────────────────────┘
                    ↓ 准确类型
┌──────────────────────────────────────────────┐
│              Hook handler.sh                  │
│  获取 workflow_type 变量                      │
└──────────────────────────────────────────────┘
                    ↓ 传入类型参数
┌──────────────────────────────────────────────┐
│         generate_status_md(workflow_name,     │
│                         workflow_type)        │
└──────────────────────────────────────────────┘
                    ↓ 正确类型的 status.md
┌──────────────────────────────────────────────┐
│           主 AI 读取执行                       │
│  （约束与实际一致）                            │
└──────────────────────────────────────────────┘
```

---

## 四、向后兼容

**未传入类型时**：
- 回退到从 `_index.yaml` 读取 `type` 字段
- 在 status.md 中添加警告注释：
  ```markdown
  <!-- ⚠️ 类型来自 _index.yaml 的 type 字段，可能与实际识别不一致 -->
  <!-- 建议调用 generate_status_md 时传入通过 identify_type.py 识别的准确类型 -->
  ```

---

## 五、验证方法

```bash
# 1. 运行 identify_type.py 获取类型
python3 ~/.hermes/skills/openclaw-imports/workflow-manager/actions/identify_type.py ~/.hermes/workflows/资产收集流程

# 2. 检查 status.md 中的类型是否一致
cat ~/.hermes/workflows/资产收集流程/status.md | grep "工作流类型"
```

---

## 六、实施文件

| 文件 | 修改内容 |
|------|----------|
| `actions/execute.py` | 新增 generate_status_md 函数（前置定义 + 接收类型参数） |
| `actions/identify_type.py` | 新增 CLI 包装器 |
| `hooks/workflow-step-check/handler.sh` | 调用 identify_type.py + 传入类型参数 |
| `scripts/verify_type_consistency.py` | 新增验证脚本 |

---

## 七、相关参考

- `references/workflow-type-identification.md` - 类型识别机制
- `references/branch-workflow-hook-enhancement-20260514.md` - Hook 增强方案
- `references/hook-already-implements-status-md-20260515.md` - Hook 已实现 status.md 注入
