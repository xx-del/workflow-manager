# 工作流类型识别与展开策略实现

**修复日期**: 2026-05-12
**修复类型**: 架构级（影响所有工作流类型）

---

## 核心问题

**缺少"展开策略"抽象层**

当前代码直接跳过了"判断如何展开"这一步：
- loader 不知道应该用 nodes 还是 parsed_steps
- expander 不知道应该如何展开不同类型的工作流
- executor 拿到混乱数据，生成错误的指令

---

## 解决方案：三阶段处理流程

```
阶段1：识别工作流类型
    ↓
阶段2：选择展开策略
    ↓
阶段3：生成执行计划
```

---

## 阶段1：类型识别

**方法**: `_identify_workflow_type()`

**识别规则**:

| 类型 | 判定条件 |
|------|----------|
| branch | `type: branch` 或所有节点 `calls: workflow-manager` |
| heartbeat | 有 `heartbeat.enabled` 或 `breakpoint/auto` 节点 |
| normal | 其他 |

**代码位置**: `src/tools/loader.py` 第 159-197 行

---

## 阶段2：展开策略选择

**策略矩阵**:

| 类型 | nodes 来源 | parsed_steps 处理 | 合并策略 |
|------|-----------|------------------|---------|
| branch | _index.yaml | 不解析 | 不合并，递归展开 |
| heartbeat | _index.yaml | 记录为 execution_steps | 保留双层结构 |
| normal（1对1） | _index.yaml | 补充命令 | 名称匹配合并 |
| normal（1对多） | WORKFLOW.md | 作为 nodes | 完全替换 |

**代码位置**: `src/tools/loader.py` 第 350-395 行

---

## 阶段3：执行计划生成

**心跳驱动工作流特殊处理**:
- 保留双层结构：nodes（逻辑层）+ execution_steps（执行层）
- breakpoint 节点：生成心跳启动指令
- auto 节点：标记为"心跳自动执行"

---

## 代码修改摘要

### loader.py

**新增方法**:
- `_identify_workflow_type()` - 类型识别（第 159-197 行）
- `_rebuild_depends_on()` - 依赖重建（第 253-281 行）

**修改方法**:
- `_build_workflow()` - 根据类型选择策略（第 350-395 行）
- `validate_dependencies()` - 支持名称和ID引用（第 33-55 行）

### expander.py

**修改方法**:
- `_apply_id_mapping()` - 支持名称映射（第 113-155 行）

**新增映射**:
- `{工作流名}_{节点名}` → 展开后ID
- `{节点名}` → 展开后ID（兼容无前缀查找）

---

## 修复效果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 总步骤数（通用漏洞扫描） | 25 | 43 |
| 跨工作流依赖警告 | 18个 | 0个 |
| 有命令步骤 | ~18 | 36 |
| 心跳驱动工作流 | 结构丢失 | 双层结构保留 |

---

## 测试结果

| 工作流 | 类型 | nodes | execution_steps | 状态 |
|--------|------|-------|-----------------|------|
| 通用漏洞扫描 | branch | 4 | - | ✅ |
| home漏扫 | heartbeat | 7 | 12 | ✅ |
| 凭证检测 | normal | 12 | - | ✅ |
| 爆破测试 | normal | 12 | - | ✅ |
| nuclei扫描 | normal | 12 | - | ✅ |

---

## 心跳驱动工作流验证

**home漏扫** 保留完整心跳机制:

- 启动扫描 → type=action, trigger=manual
- 断点返回 → type=**breakpoint**, trigger=manual
- WIH下载 → type=**auto**, trigger=**heartbeat**
- AWVS下载 → type=**auto**, trigger=**heartbeat**
- JS分析 → type=**auto**, trigger=**heartbeat**
- AWVS分析 → type=**auto**, trigger=**heartbeat**
- 清理任务 → type=**auto**, trigger=**heartbeat**

---

## 关键发现

### 1. 节点-步骤对应关系

| 工作流 | _index.yaml 节点 | WORKFLOW.md 步骤 | 对应模式 |
|--------|------------------|------------------|----------|
| 通用漏洞扫描 | 4 | 无 | 无步骤（引用子工作流） |
| home漏扫 | 7 | 12 | 多对多 |
| 凭证检测 | 3 | 12 | 1对多 |
| 爆破测试 | 3 | 12 | 1对多 |
| nuclei扫描 | 12 | 12 | 1对1 |

### 2. 依赖引用格式

**问题**: 验证器检查 `depends_on` 是否在 `node_names` 中，但:
- `node_names` 收集的是名称（如"启动扫描"）
- `depends_on` 可能是ID（如"step_1"）

**解决**: 验证时同时检查名称和ID

```python
valid_refs = node_names | node_ids  # 名称和ID都可作为引用
```

### 3. 名称映射必要性

**问题**: expander 的 `_resolve_cross_workflow_dependency` 无法匹配名称引用

**原因**:
- `id_mapping` 存储的是 `{工作流名}_{原始ID}` → 展开后ID
- 但 `depends_on` 可能引用名称（如"启动扫描"）

**解决**: 在 `_apply_id_mapping` 中增加名称映射

```python
name_mapping_key = f"{workflow_name}_{node_name}"
self.id_mapping[name_mapping_key] = expanded_id
```

---

## 用户偏好记录

**用户纠正**: "通盘考虑全面分析，一次性解决所有问题，不要修一个问题产生另一个问题"

**设计原则**:
- ✅ 分析问题时要全盘考虑架构
- ✅ 制定方案时要一次性解决所有相关问题
- ❌ 禁止"修一个问题产生另一个问题"
- ❌ 禁止头痛医头、脚痛医脚
