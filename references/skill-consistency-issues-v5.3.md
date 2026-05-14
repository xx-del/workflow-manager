# SKILL.md v5.3.0 一致性问题清单

**分析日期**: 2026-05-11
**分析范围**: 主目录 `~/.hermes/skills/openclaw-imports/workflow-manager/`

---

## 问题1：主 AI 调用方式描述错误 🔴 高优先级

**位置**: SKILL.md 第167行

**错误描述**:
```markdown
| **更新状态** | 更新步骤执行状态 | `executor.update_step_status()` |
```

**问题**:
- executor.update_step_status() 是 Python 方法（executor.py:647）
- 没有命令行脚本暴露此方法
- 主 AI 无法导入 Python 模块，无法调用此方法

**正确做法**:
```markdown
| **更新状态** | 更新步骤执行状态 | `read_file` + `write_file` 直接操作 status.json |
```

**影响**: 主 AI 按描述执行会失败

---

## 问题2：状态更新流程缺失 🔴 高优先级

**位置**: SKILL.md 第157-169行

**问题**:
- 描述了"更新追踪状态"但没有说明具体方法
- 没有提供代码示例
- 主 AI 不知道如何操作 status.json

**应该补充**:
```markdown
### 主 AI 如何更新状态

**方法**: 使用 read_file + write_file 直接操作 status.json

**步骤**:
1. 读取: status_json = read_file("~/.hermes/workflows/{workflow}/status.json")
2. 解析: status = json.loads(status_json)
3. 更新: status['updated'] = datetime.now().isoformat()
4. 追加: status['steps'].append({...})
5. 写回: write_file(..., json.dumps(status, indent=2))
```

---

## 问题3：验证清单不完整 🟡 中优先级

**位置**: SKILL.md 第239行

**问题**:
- 缺少状态管理验证项
- 缺少 started/updated/steps 格式验证
- 导致近期工作流执行不规范

**应该补充**:
```markdown
状态管理验证清单:

初始化阶段:
- [ ] status 是否设置为 initialized？
- [ ] started 是否设置为 null？
- [ ] updated 是否设置为当前时间？

执行阶段:
- [ ] 每个步骤完成后，steps 数组是否已追加？
- [ ] 每个步骤完成后，updated 时间是否已更新？
- [ ] 步骤记录是否包含 step_id、step_name、status？
```

---

## 问题4：execute.py 作用未说明 🟢 低优先级

**位置**: SKILL.md 钩子部分（第62、88行）

**问题**:
- 钩子调用了 execute.py --plan-only
- 但没有说明这个脚本的作用
- 没有说明生成的 status.md 文件格式

**应该补充**:
```markdown
### execute.py 脚本说明

**作用**: 生成执行计划（status.md）

**用法**: python actions/execute.py <工作流名称> --plan-only

**输出**: status.md 文件（AI 可读的执行计划）
```

---

## 代码验证结果

### executor.py 关键方法

| 方法 | 行号 | 有CLI接口 | 主AI可调用 |
|------|------|-----------|------------|
| execute() | 217 | ❌ | ❌ |
| get_execution_plans() | 170 | ✅ execute.py --plan-only | ✅ |
| update_step_status() | 647 | ❌ | ❌ |
| _finalize_workflow() | 1070 | ✅ complete.py | ✅ |

### actions 目录脚本

| 脚本 | 存在 | SKILL.md说明 |
|------|------|--------------|
| execute.py | ✅ | ⚠️ 部分 |
| complete.py | ✅ | ✅ |
| status.py | ✅ | ❌ 未说明 |
| validate_status.py | ✅ | ❌ 未说明 |
| audit_workflow_execution.py | ✅ | ❌ 未说明 |

---

## 修复优先级

| 优先级 | 问题 | 修复方式 |
|--------|------|----------|
| 🔴 高 | 主AI调用方式错误 | 修改第167行描述 |
| 🔴 高 | 状态更新流程缺失 | 新增章节说明 |
| 🟡 中 | 验证清单不完整 | 补充状态管理验证 |
| 🟢 低 | execute.py未说明 | 补充脚本说明 |
