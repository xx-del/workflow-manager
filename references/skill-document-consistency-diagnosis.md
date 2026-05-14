# 技能文档一致性诊断方法论

## 问题背景

**发现时间**: 2026-05-11
**问题**: workflow-manager SKILL.md 被过度简化，导致代码与文档不一致

**表现**:
- 版本号倒退：v5.3.0 → v4.5.1
- 行数骤减：533行 → 79行（减少85%）
- 关键章节缺失：钩子机制、执行流程、强制要求、守护机制等

---

## 诊断方法

### 1. 版本对比

```bash
# 检查版本号
head -5 SKILL.md
# 预期：version: 5.x.x
# 异常：version: 4.x.x（倒退）

# 检查行数
wc -l SKILL.md
# 预期：500+ 行
# 异常：<100 行（过度简化）
```

### 2. 完整版备份检查

```bash
# 查找备份文件
ls -la SKILL.md.bak*

# 对比差异
diff SKILL.md SKILL.md.bak_YYYYMMDD_HHMMSS
```

### 3. 代码实现验证

**核心代码文件**：
- `src/core/executor.py` - 执行器（主逻辑）
- `src/core/agent_pool_client.py` - agent-pool客户端
- `actions/execute.py` - CLI入口

**验证方法**：
```bash
# 读取核心代码
wc -l src/core/executor.py  # 1113行
wc -l src/core/agent_pool_client.py  # 438行

# 搜索关键方法
grep -n "def generate_execution_plan_md" src/core/executor.py
grep -n "def execute_full" src/core/agent_pool_client.py
```

### 4. 章节映射检查

**核心章节清单**：

| 章节 | 代码实现 | SKILL.md | 一致性 |
|------|----------|----------|--------|
| 钩子机制 | executor.py: generate_execution_plan_md() | ? | 检查 |
| 执行流程 | executor.py: execute() | ? | 检查 |
| 强制要求 | executor.py: pending_instructions | ? | 检查 |
| 执行约束 | terminal-execution-constraints.md | ? | 检查 |
| 守护机制 | guardian.md | ? | 检查 |
| 并发控制 | max_agents=3 | ? | 检查 |
| 拼接工作流 | creation-guide.md | ? | 检查 |

---

## 修复方案

### 方案A：恢复完整版（推荐）

**步骤**：
1. 备份当前版本（如有必要）
2. 使用完整版备份替换当前SKILL.md
3. 精简references引用（保留核心文档）

**命令**：
```bash
# 恢复完整版
cp SKILL.md.bak_YYYYMMDD_HHMMSS SKILL.md

# 精简references引用（示例）
# 保留：creation-guide.md, guardian.md, terminal-execution-constraints.md, status-update-responsibility.md
# 删除：extraction.md, validation.md, optimization.md, examples.md, troubleshooting.md, migration-v4.md
```

**预期结果**：
- 版本号恢复：v4.5.1 → v5.3.0
- 行数恢复：79行 → 527行
- 关键章节恢复：7个章节
- 代码一致性：❌ → ✅

### 方案B：补充关键章节

**适用场景**：无完整版备份，或需要自定义内容

**步骤**：
1. 从代码实现提取章节内容
2. 从references文档提取规范内容
3. 补充缺失章节

**风险**：可能遗漏细节

---

## 预防措施

### 一致性检查清单

**创建/修改SKILL.md时**：
- [ ] 版本号是否递增？
- [ ] 行数是否合理？（对比代码行数）
- [ ] 核心章节是否完整？
- [ ] 代码实现是否有对应说明？
- [ ] references引用是否合理？

**定期检查**：
- [ ] 完整版备份是否存在？
- [ ] 版本号是否倒退？
- [ ] 关键章节是否缺失？

### 文档修改原则

**不要过度简化**：
- 代码是核心，SKILL.md是说明书
- 说明书应完整覆盖代码功能
- 精简references引用，而非精简核心章节

**保持一致性**：
- 每个代码功能都应有文档说明
- 每个文档章节都应映射到代码实现
- 版本号应反映实际变更

---

## 示例案例

### 案例：workflow-manager 2026-05-11

**问题**：
- 版本：v4.5.1（应为v5.3.0）
- 行数：79行（应为527行）
- 缺失：钩子机制、执行流程、强制要求、守护机制、并发控制、拼接工作流

**诊断**：
```bash
$ wc -l SKILL.md
79 SKILL.md  # 异常：过度简化

$ head -5 SKILL.md
version: 4.5.1  # 异常：版本倒退
```

**修复**：
```bash
$ cp SKILL.md.bak_20260511_162301 SKILL.md
$ wc -l SKILL.md
527 SKILL.md  # 恢复正常
```

**结果**：
- 版本：v5.3.0 ✅
- 行数：527行 ✅
- 章节：完整 ✅
- 一致性：代码与文档一致 ✅

---

## 相关文档

- [references/creation-guide.md](creation-guide.md) - 工作流创建指南
- [references/guardian.md](guardian.md) - 守护机制详细规范
- [references/terminal-execution-constraints.md](terminal-execution-constraints.md) - terminal执行约束
- [references/status-update-responsibility.md](status-update-responsibility.md) - 状态更新职责
