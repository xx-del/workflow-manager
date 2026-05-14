# 工作流创建指南

## 一、工作流类型

| 类型 | type 值 | 说明 | 必需文件 |
|------|---------|------|----------|
| **叶子节点** | `leaf` | 有具体执行步骤 | `_index.yaml` + `WORKFLOW.md` |
| **分支节点** | `branch` | 拼接多个子工作流 | 仅 `_index.yaml` |

**重要**：创建工作流时必须在 `_index.yaml` 顶层设置 `type` 字段。

---

## 二、叶子节点创建

### 2.1 目录结构

```
~/.hermes/workflows/工作流名称/
├── _index.yaml       # 可选，如果步骤定义在 WORKFLOW.md 中
└── WORKFLOW.md       # 必需，包含执行步骤
```

### 2.2 _index.yaml 格式

```yaml
name: {工作流名称}
type: leaf  # 叶子节点
description: {工作流描述}
version: 1.0.0
mode: serial

# 可选：定义输入参数
inputs:
  date_start:
    description: 开始日期
    format: YYYYMMDD
    required: true
  date_end:
    description: 结束日期
    format: YYYYMMDD
    required: false

nodes:
  - id: 1
    name: {步骤1名称}  # 必须与 WORKFLOW.md 步骤名称一致
    calls: agent-pool
    capabilities:
      - {能力1}
    depends_on: []
```

**参数说明：**
- `inputs` 字段定义工作流接收的参数
- 执行时通过 `--date-start/--date-end` 传入
- Agent 可从 `context` 中读取参数值

### 2.3 WORKFLOW.md 格式

```markdown
# 工作流名称

## 目标
[一句话描述]

## 输入
- 来源: [数据源]
- 参数: [参数说明]

## 输出
- 文件: [输出文件列表]

## 执行步骤

### 步骤 1: [步骤名称]
**做什么**: [说明]
**命令**: 
\`\`\`bash
[具体命令]
\`\`\`
**输出**: [本步输出]

### 步骤 2: ...
```

---

## 三、分支节点创建（拼接工作流）

### 3.1 核心原则

> **分支节点只引用，不定义**
> - 子工作流独立维护
> - 分支节点零维护
> - 修改子工作流无需同步

### 3.2 目录结构

```
~/.hermes/workflows/拼接工作流名称/
└── _index.yaml       # 唯一必需文件
```

**禁止事项**：
- ❌ 不要创建 `nodes/` 目录
- ❌ 不要复制子工作流的定义
- ❌ 不需要 `WORKFLOW.md`（SKILL.md 会自动引导）

### 3.3 _index.yaml 格式

```yaml
name: 拼接工作流名称
type: branch  # 分支节点
description: 简要描述
version: 1.0.0
mode: serial  # serial（串行）或 parallel（并行）

# 工作目录配置（可选）
work_dir: /path/to/work/
output_dir: /path/to/output/

# 子工作流引用
nodes:
  - id: 1
    name: 子工作流1名称          # 必须与子工作流目录名一致
    calls: workflow-manager       # 固定值，表示调用子工作流
    description: 子工作流说明
    depends_on: []                # 依赖的前置节点 ID
    
  - id: 2
    name: 子工作流2名称
    calls: workflow-manager
    description: 子工作流说明
    depends_on: [1]               # 依赖节点1

# 执行配置（可选）
config:
  strict_mode: true
  max_parallel: 1

# 约束规则（可选）
strict_rules:
  - 禁止跳过当前步骤
  - 禁止使用历史数据代替执行
```

### 3.4 关键字段说明

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | ✅ | 必须与 `~/.hermes/workflows/{name}/` 目录名一致 |
| `calls` | ✅ | 固定为 `workflow-manager`，表示这是子工作流引用 |
| `depends_on` | ✅ | 定义执行顺序，空数组 `[]` 表示第一步 |

### 3.5 完整示例

```yaml
name: 资产收集流程
type: branch  # 分支节点
description: 串联5个阶段的完整资产收集流程
version: 2.1.0
mode: serial

work_dir: /x/rank/hwxinxisouji/liuliang/
output_dir: /x/rank/hwxinxisouji/liuliang/start/

nodes:
  - id: 1
    name: 电力数据
    calls: workflow-manager
    description: 下载JSON数据，AI分析URL
    depends_on: []
    
  - id: 2
    name: 域名处理
    calls: workflow-manager
    description: DNS解析域名
    depends_on: [1]
    
  - id: 3
    name: 端口扫描
    calls: workflow-manager
    description: masscan扫描开放端口
    depends_on: [2]
    
  - id: 4
    name: URL生成
    calls: workflow-manager
    description: 组合IP端口生成URL
    depends_on: [3]
    
  - id: 5
    name: URL分析
    calls: workflow-manager
    description: 检测URL有效性
    depends_on: [4]

config:
  strict_mode: true
  max_parallel: 1

strict_rules:
  - 禁止跳过当前步骤
  - 禁止使用历史数据代替执行
```

---

## 四、验证清单

### 4.1 叶子节点验证

- [ ] `WORKFLOW.md` 存在
- [ ] 包含「执行步骤」章节
- [ ] 每个步骤有命令或指令

### 4.2 分支节点验证

- [ ] 仅 `_index.yaml` 存在
- [ ] 所有节点 `calls: workflow-manager`
- [ ] `name` 与子工作流目录名一致
- [ ] 子工作流目录存在：`~/.hermes/workflows/{name}/`
- [ ] 子工作流有 `WORKFLOW.md`

### 4.3 常见错误

| 错误 | 说明 | 修正 |
|------|------|------|
| 创建 `nodes/` 目录 | 重复定义 | 删除，直接引用子工作流 |
| 子工作流名称不一致 | AI 无法找到 | 确保 `name` 与目录名一致 |
| 缺少 `depends_on` | 执行顺序不明确 | 添加依赖关系 |

---

## 五、信息完整性要求

### 5.1 必需章节

WORKFLOW.md 必须包含以下章节：

| 章节 | 必需性 | 说明 |
|------|--------|------|
| ## 目标 | 必需 | 工作流目标描述 |
| ## 输入 | 必需 | 输入数据定义 |
| ## 输出 | 必需 | 输出数据定义（必须包含目录和文件名） |
| ## 执行步骤 | 必需 | 执行步骤定义 |
| ## 执行约束 | 必需 | 工作流特定约束 |

### 5.2 校验命令

```bash
python actions/validate.py {工作流名称} --check-info-completeness
```

### 5.3 缺失后果

缺失任何章节将导致：
- 子 agent 缺少上下文 → 执行偏离预期
- 输出位置不对 → 文件写入错误位置
- 约束缺失 → 违反工作流特定约束

---

## 六、AI 执行流程

### 6.1 创建分支节点时

1. 读取本指南
2. 创建目录：`~/.hermes/workflows/{工作流名称}/`
3. 创建 `_index.yaml`，格式见 3.3
4. 确认子工作流已存在
5. 不创建 `WORKFLOW.md`（零维护）

### 6.2 执行分支节点时

1. 读取 SKILL.md 的智能判断逻辑
2. 检测到 `calls: workflow-manager` → 分支节点
3. 依次加载子工作流的 `WORKFLOW.md`
4. 按 `depends_on` 顺序执行


---

## 工作流命名规范（v6.3 新增）

### 步骤名称格式

**推荐格式**: `步骤 N: 动作描述`

**示例**:
- ✅ 正确: `步骤 1: 端口扫描`
- ✅ 正确: `步骤 2: 服务识别`
- ❌ 错误: `1`
- ❌ 错误: `step_1`
- ❌ 错误: `端口扫描`（缺少序号）

### depends_on 引用格式

**必须与节点 name 字段完全一致**

**示例**:
```yaml
nodes:
  - name: 步骤 1: 端口扫描
    depends_on: []
  
  - name: 步骤 2: 服务识别
    depends_on:
      - 步骤 1: 端口扫描  # 必须完全一致
```

**常见错误**:
```yaml
# ❌ 错误示例
nodes:
  - name: 步骤 1: 端口扫描
    depends_on: []
  
  - name: 步骤 2: 服务识别
    depends_on:
      - 1              # 错误：引用不存在
      - step_1         # 错误：引用不存在
      - 端口扫描       # 错误：引用不存在
```

### 步骤定义完整性

每个步骤必须包含：
- **做什么**: 说明步骤目的
- **执行指令**: 具体的执行命令或操作
- **输入**: （可选）输入数据来源
- **输出**: （可选）输出数据位置

**示例**:
```markdown
### 步骤 1: 端口扫描

**做什么**: 扫描目标端口

**执行指令**:
```bash
nmap -sV $TARGET
```

**输入**: 目标 IP 列表
**输出**: 端口扫描结果
```

### 工作流结构完整性

WORKFLOW.md 必须包含以下章节：
- `## 目标`: 说明工作流目的
- `## 执行步骤`: 定义执行步骤

**示例**:
```markdown
# 工作流：端口扫描

## 目标

对目标进行端口扫描，识别开放端口和服务。

## 前置条件

- 目标 IP 列表已准备

## 执行步骤

### 步骤 1: 端口扫描
...

## 约束清单

- [ ] 严格按步骤顺序执行
```

---

## 验证机制（v6.3 新增）

### 自动验证

loader.py 在加载工作流时会自动验证：
1. depends_on 引用是否有效
2. 工作流结构是否完整
3. 步骤定义是否完整

### 验证失败处理

**严重错误**（阻止加载）:
- depends_on 引用不存在的步骤
- 缺少"目标"或"执行步骤"章节

**警告**（不阻止加载）:
- 步骤缺少"做什么"或"执行指令"

### 手动验证

使用验证脚本：
```bash
python actions/validate_workflow.py
```

验证所有工作流并生成报告。
