# 工作流执行最佳实践

版本: 1.0.0
创建时间: 2026-05-06
来源会话: 资产收集 + 通用漏洞扫描工作流执行

---

## 核心发现

### 1. 工具路径问题

**问题**: 技能文档中的路径与实际路径不符

**文档路径**: `~/.hermes/skills/openclaw-imports/workflow-manager/src/workflow-tools.js`
**实际路径**: `~/.hermes/skills/openclaw-imports/bk/workflow-manager/src/workflow-tools.js`

**解决方案**: 使用 search_files 查找正确路径，而非依赖文档

```bash
# 查找 workflow-tools.js
search_files --path ~/.hermes/skills --pattern workflow-tools.js --target files
```

---

### 2. 子 Agent 超时处理

**现象**: delegate_task 经常超时（600秒），但结果文件已生成

**根本原因**: 长时间运行的任务会触发超时机制，但后台进程继续执行

**最佳实践**:

```bash
# 不要仅依赖 delegate_task 返回状态
# 超时后立即检查结果文件

# 检查最近生成的文件
ls -lht /path/to/output/ | head -10

# 验证文件内容
wc -l result_file.txt
head -5 result_file.txt
```

**决策树**:

```
delegate_task 超时
    ↓
检查预期输出目录
    ↓
文件存在？
    ├─ 是 → 验证内容 → 继续下一步
    └─ 否 → 重试（最多3次）→ 仍失败则报告用户
```

---

### 3. 工作流名称匹配

**问题**: 用户说"通用漏扫"，实际名称是"通用漏洞扫描"

**解决方案**:

```bash
# 先列出所有工作流
node workflow-tools.js list

# 模糊匹配工作流名称
# 使用 grep 或 jq 过滤
node workflow-tools.js list | grep -i "漏扫"
```

**建议**: 在执行前明确工作流完整名称

---

### 4. 并行 vs 串行执行模式

**并行工作流**: 使用 delegate_task 的 tasks 参数

```json
{
  "tool": "delegate_task",
  "params": {
    "tasks": [
      {"goal": "任务1", "context": "...", "toolsets": ["terminal"]},
      {"goal": "任务2", "context": "...", "toolsets": ["terminal"]}
    ]
  }
}
```

**串行工作流**: 逐个执行并等待完成

```json
// 步骤1
{
  "tool": "delegate_task",
  "params": {
    "goal": "步骤1",
    "context": "...",
    "toolsets": ["terminal"]
  }
}
// 等待完成后执行步骤2
```

**最大并发**: 3个 delegate_task

---

### 5. 工作流依赖关系

**两种依赖类型**:

| 类型 | 说明 | 处理方式 |
|------|------|----------|
| 数据依赖 | 步骤B需要步骤A的输出 | 严格串行执行 |
| 时间依赖 | 步骤B只需步骤A启动后即可执行 | 可并行执行 |

**示例**（通用漏洞扫描）:

```
并行组: [凭证检测, home漏扫]
    ↓
串行: 凭证检测 → 漏扫 → 爆破测试
```

- 凭证检测和home漏扫可并行
- 漏扫依赖凭证检测完成（时间依赖）
- 爆破测试依赖漏扫完成（时间依赖）

---

### 6. 结果验证清单

**每个步骤执行后必须验证**:

- [ ] 预期输出文件是否存在？
- [ ] 文件是否非空？
- [ ] 文件格式是否正确？
- [ ] 内容是否符合预期？

**验证命令**:

```bash
# 检查文件存在性和大小
ls -lh output_file.txt

# 检查行数
wc -l output_file.txt

# 检查格式
file output_file.txt

# 预览内容
head -20 output_file.txt
```

---

### 7. 长时间运行任务

**识别标志**:
- 包含"等待完成"的指令
- 涉及网络扫描、批量处理
- 预期执行时间 > 5分钟

**处理策略**:

1. **启动任务**: 使用 delegate_task 启动
2. **预期超时**: 知道会超时，不惊慌
3. **立即验证**: 超时后检查结果文件
4. **必要时归档**: 将结果移动到统一目录

---

### 8. 结果归档标准

**归档目录结构**:

```
/x/rank/hwxinxisouji/liuliang/results/$(date +%Y%m%d)/
├── 01-凭证检测/
│   └── credential_results.json
├── 02-爆破测试/
│   ├── result_cache.json
│   └── login_success.json
├── 03-nuclei扫描/
│   ├── scan_*.json
│   └── vulns_*.txt
└── 工作流执行报告.md
```

**归档命令模板**:

```bash
ARCHIVE_DIR="/x/rank/hwxinxisouji/liuliang/results/$(date +%Y%m%d)/XX-工作流名"
mkdir -p "$ARCHIVE_DIR"
cp result_file.json "$ARCHIVE_DIR/"
cp report.txt "$ARCHIVE_DIR/"
```

---

## 常见问题排查

### Q1: 找不到工作流

**症状**: `Workflow not found: XXX`

**排查**:
1. 使用 `list` 命令查看所有工作流
2. 检查名称拼写
3. 使用 grep 模糊匹配

### Q2: 步骤超时

**症状**: `Subagent timed out after 600.0s`

**排查**:
1. 检查输出目录是否有新文件
2. 验证文件内容
3. 如果文件有效，继续下一步

### Q3: 结果为空

**症状**: 输出文件存在但为空

**排查**:
1. 检查输入文件是否正确
2. 检查日志错误信息
3. 手动执行命令验证

---

## 执行效率优化

### 避免重复工作

- 超时后先验证结果，避免重试
- 使用已有结果文件，不重复执行
- 合并相似步骤（如步骤9-12合并执行）

### 资源利用

- 并行执行独立步骤（最大并发3）
- 长时间任务启动后立即执行其他步骤
- 使用心跳机制监控长时间任务

---

## 总结

**核心原则**:
1. 验证优先于信任（超时也要验证）
2. 文件存在即有效（检查内容确认）
3. 并行提升效率（最大并发3）
4. 归档保留历史（统一目录结构）
