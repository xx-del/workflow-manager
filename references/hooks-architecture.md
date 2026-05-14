# 钩子架构说明

**版本**: v6.1.0  
**更新时间**: 2026-05-12  
**变更原因**: 职责分离优化 - 脚本外置，frontmatter 简洁声明

---

## 架构设计

### 文件职责分离

| 文件 | 职责 | 更新频率 |
|------|------|----------|
| SKILL.md | 技能使用指南 + 钩子声明 | 功能变更时 |
| hooks/*.sh | 钩子执行脚本 | 逻辑调整时 |
| references/hooks-implementation.md | 钩子机制文档 | 文档更新时 |

### 目录结构

```
workflow-manager/
├── SKILL.md                    # 使用指南 + 简洁钩子声明
├── hooks/                      # 钩子脚本目录（v6.1.0 新增）
│   ├── user_prompt_submit.sh   # UserPromptSubmit 钩子
│   └── pre_tool_use.sh         # PreToolUse 钩子
├── actions/                    # 代码工具
├── references/                 # 参考文档
└── scripts/                    # 辅助脚本
```

---

## 钩子配置

### UserPromptSubmit 钩子

**触发时机**：用户发送消息时（会话开始）

**作用**：检测未完成工作流，提示继续执行

**配置**：
```yaml
hooks:
  UserPromptSubmit:
    - type: command
      command: bash $SKILL_DIR/hooks/user_prompt_submit.sh
```

**脚本路径**：`hooks/user_prompt_submit.sh`

**执行逻辑**：
1. 查找运行中的工作流（status.json）
2. 检测 status.md 是否存在
3. 不存在则自动生成
4. 显示执行计划前 60 行

---

### PreToolUse 钩子

**触发时机**：AI 调用 terminal 或 delegate_task 工具前

**作用**：注入当前步骤和约束清单

**配置**：
```yaml
hooks:
  PreToolUse:
    - matcher: "terminal|delegate_task"
      type: command
      command: bash $SKILL_DIR/hooks/pre_tool_use.sh
```

**脚本路径**：`hooks/pre_tool_use.sh`

**执行逻辑**：
1. 查找运行中的工作流（status.json）
2. 检测 status.md 是否存在
3. 读取当前步骤
4. 提取约束清单
5. 注入到工具调用前

---

## 环境变量

Hermes 自动注入以下环境变量：

- `$SKILL_DIR`：技能目录绝对路径
- 示例：`/home/kali/.hermes/skills/openclaw-imports/workflow-manager`

---

## 修改历史

### v6.1.0 (2026-05-12)

**变更**：
- 将 80+ 行内联脚本外置到 hooks/ 目录
- SKILL.md frontmatter 简化为 8 行声明
- 减少 49 行文档代码

**原因**：
- 职责分离：SKILL.md 专注于使用指南
- 可维护性：钩子逻辑独立维护
- 可读性：AI 读取技能时更简洁

**影响**：
- 功能无变化
- 性能无影响
- 维护更便捷

### v6.0.0 (2026-05-11)

**变更**：
- 融合 planning-with-files 钩子机制
- 新增 UserPromptSubmit 和 PreToolUse 钩子
- 实现"注意力操控"机制

---

## 测试验证

### 脚本测试

```bash
# 测试 UserPromptSubmit 钩子
bash ~/.hermes/skills/openclaw-imports/workflow-manager/hooks/user_prompt_submit.sh

# 测试 PreToolUse 钩子
bash ~/.hermes/skills/openclaw-imports/workflow-manager/hooks/pre_tool_use.sh
```

### 预期结果

- 无运行中工作流时：无输出
- 有运行中工作流时：
  - UserPromptSubmit：显示工作流名称和执行计划
  - PreToolUse：显示当前步骤和约束清单

---

## 故障排查

### 钩子不触发

**可能原因**：
1. 脚本权限不足 → `chmod +x hooks/*.sh`
2. $SKILL_DIR 未注入 → 使用绝对路径
3. status.json 不存在 → 检查工作流状态

### 脚本执行失败

**排查步骤**：
```bash
# 检查脚本权限
ls -la hooks/

# 手动执行脚本
bash hooks/user_prompt_submit.sh

# 检查路径变量
echo $SKILL_DIR
```

---

## 相关文档

- `references/hooks-implementation.md` - 钩子机制实现详解
- `SKILL.md` - 技能使用指南
- `references/planning-with-files-integration-analysis.md` - planning-with-files 融合分析
