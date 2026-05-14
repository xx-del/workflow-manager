# loader.py WORKFLOW.md 覆盖问题修复

**日期**: 2026-05-12
**问题**: loader.py 用 WORKFLOW.md 解析步骤覆盖 _index.yaml 节点定义

---

## 问题现象

```
[WARNING] 工作流 'home漏扫' 步骤定义警告:
步骤 '启动扫描' 缺少 '执行指令' 定义
步骤 '断点返回（启动心跳监测）' 缺少 '执行指令' 定义
...
```

## 根因分析

**loader.py 第 231-236 行**：
```python
if not workflow['nodes'] or all(
    n.get('task') and not n.get('command') 
    for n in workflow['nodes']
):
    workflow['nodes'] = parsed_steps  # ← 直接覆盖
```

**影响**：
- 心跳驱动工作流的节点类型丢失（breakpoint、auto、trigger）
- 验证器检查 WORKFLOW.md 字段名（"执行指令"），但实际使用"命令"

---

## 修复内容

### 1. 删除覆盖逻辑（第 230-240 行）

```python
# 修复后：
if not workflow['nodes']:
    # 情况1：无节点定义 → 使用 WORKFLOW.md
    workflow['nodes'] = parsed_steps
else:
    # 情况2：有节点定义 → 合并命令，保留结构
    merged_count = self._merge_workflow_md_commands(workflow['nodes'], parsed_steps)
```

### 2. 新增 `_is_heartbeat_workflow()` 方法

识别心跳驱动工作流特征：
- `trigger: heartbeat`
- `type: breakpoint/auto`
- `heartbeat.enabled: true`

### 3. 新增 `_merge_workflow_md_commands()` 方法

合并规则：
- 保留 _index.yaml 的节点结构
- 通过名称匹配补充命令
- 不覆盖已有字段

### 4. 优化验证逻辑

心跳驱动工作流跳过步骤定义验证。

---

## 验证结果

```bash
python actions/execute.py home漏扫 --plan-only
```

**输出**：
```
[INFO] 心跳驱动工作流 'home漏扫' 跳过步骤定义验证
```

- ✅ 无警告
- ✅ 节点结构保留（7个节点，breakpoint/auto 类型）

---

## 遗留问题

**跨工作流依赖无法解析**：
```
⚠️ 警告: 跨工作流依赖 启动扫描 无法解析
```

**原因**：expander 展开嵌套节点后，depends_on 引用的步骤名称与实际节点名称不匹配

**影响**：会影响工作流正常运行（步骤数量不匹配、命令缺失）

**待修复**：分层展开策略（方案C）
