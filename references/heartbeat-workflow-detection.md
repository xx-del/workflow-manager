# 心跳驱动工作流识别与处理机制

**日期**: 2026-05-12
**用途**: 区分心跳驱动工作流与普通工作流，采用不同的处理策略

---

## 心跳驱动工作流特征

### 识别条件（满足任一即可）

| 条件 | 位置 | 示例 |
|------|------|------|
| `trigger: heartbeat` | 节点级别 | `trigger: heartbeat` |
| `type: breakpoint` | 节点级别 | `type: breakpoint` |
| `type: auto` | 节点级别 | `type: auto` |
| `heartbeat.enabled: true` | 节点级别 | `heartbeat: {enabled: true}` |

### 检测方法

```python
def _is_heartbeat_workflow(self, nodes: List[Dict]) -> bool:
    for node in nodes:
        if node.get('trigger') == 'heartbeat':
            return True
        if node.get('type') in ['breakpoint', 'auto']:
            return True
        if node.get('heartbeat', {}).get('enabled'):
            return True
    return False
```

---

## 处理策略差异

| 操作 | 普通工作流 | 心跳驱动工作流 |
|------|-----------|---------------|
| 步骤定义验证 | 检查"做什么"+"执行指令" | 跳过验证 |
| WORKFLOW.md 解析 | 展开详细步骤 | 保留 _index.yaml 结构 |
| 命令合并 | 补充到节点 | 不合并（心跳脚本执行） |
| 执行方式 | 主 Agent 串行执行 | 心跳脚本后台执行 |

---

## 设计原理

### 为什么心跳驱动工作流需要特殊处理？

**1. 结构定义在 _index.yaml**

心跳驱动工作流的节点是高层抽象：
```yaml
nodes:
- name: 启动扫描           # 包含多个 WORKFLOW.md 步骤
  type: action
- name: 断点返回（启动心跳监测）
  type: breakpoint         # 断点类型
- name: WIH下载（心跳自动执行）
  type: auto              # 自动类型
  trigger: heartbeat      # 心跳触发
```

**2. 详细步骤在 WORKFLOW.md**

WORKFLOW.md 定义了详细的执行逻辑，但由心跳脚本执行，不是主 Agent。

**3. 验证器冲突**

如果用普通工作流的验证逻辑检查心跳驱动工作流：
- 检查"执行指令"字段 → WORKFLOW.md 使用"命令"字段 → 警告
- 检查步骤完整性 → _index.yaml 节点是合并后的 → 不匹配

---

## 典型案例：home漏扫

### _index.yaml 结构（7个节点）

```
启动扫描 → 断点返回 → WIH下载 → AWVS下载 → JS分析 → AWVS分析 → 清理任务
```

### WORKFLOW.md 结构（12个步骤）

```
步骤0: 记录启动时间
步骤1: 复制url.txt
步骤2: 检查yellowsocks
步骤3: 执行scan.sh
步骤4: 查看docker IP
步骤5: 查看AWVS进度
步骤5.5: 启动心跳监测（断点）
步骤6: WIH下载流程（心跳执行）
步骤7: AWVS下载流程（心跳执行）
步骤8: 清理远程任务（心跳执行）
步骤9: 停止心跳监测（心跳执行）
步骤10: JS分析（独立cronjob触发）
步骤11: AWVS分析（独立cronjob触发）
```

### 映射关系

| _index.yaml 节点 | WORKFLOW.md 步骤 |
|------------------|------------------|
| 启动扫描 | 步骤 0-5 |
| 断点返回 | 步骤 5.5 |
| WIH下载 | 步骤 6 |
| AWVS下载 | 步骤 7 |
| JS分析 | 步骤 10 |
| AWVS分析 | 步骤 11 |
| 清理任务 | 步骤 8-9 |

---

## 实现位置

- `src/tools/loader.py` 第 131-157 行：`_is_heartbeat_workflow()` 方法
- `src/tools/loader.py` 第 316-330 行：验证逻辑跳过处理
