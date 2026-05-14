# Hook 集中化管理架构模式

**更新日期**：2026-05-13  
**适用场景**：技能包含 Hook 代码时的目录设计和维护方法

---

## 一、问题背景

### 1.1 传统方案的问题

**分散式管理**：
```
~/.hermes/hooks/workflow-status-check/HOOK.yaml      # Hook 配置
~/.hermes/agent-hooks/workflow-status-check.sh       # Hook 脚本
~/.hermes/skills/.../workflow-manager/SKILL.md       # 技能文档
```

**痛点**：
- ❌ Hook 代码与技能代码分离
- ❌ 更新 Hook 需要修改 2 个目录
- ❌ 版本控制不友好（不同 git 仓库）
- ❌ 技能更新后 Hook 可能未同步

---

## 二、解决方案：集中化管理

### 2.1 目录结构设计

```
~/.hermes/skills/<category>/<skill-name>/
├── hooks/                           # Hook 源代码目录
│   ├── workflow-status-check/
│   │   ├── HOOK.yaml               # Hook 配置
│   │   └── handler.sh              # Hook 脚本
│   └── workflow-step-check/
│       ├── HOOK.yaml
│       └── handler.sh
├── hooks-install.sh                # 安装脚本
└── SKILL.md                        # 技能文档
```

### 2.2 符号链接机制

```
源文件（技能目录）                目标链接（Hermes 标准路径）
─────────────────────────────────────────────────────────────────────
hooks/workflow-status-check/  →  ~/.hermes/hooks/workflow-status-check
hooks/.../handler.sh          →  ~/.hermes/agent-hooks/workflow-status-check.sh
```

**符号链接优势**：
- ✅ 单一真相来源
- ✅ 修改即时生效（无需重启 Gateway）
- ✅ 版本控制友好（Git 统一管理）
- ✅ 自动同步（修改一处即生效）

---

## 三、实施步骤

### 3.1 创建 hooks 目录

```bash
cd ~/.hermes/skills/<category>/<skill-name>
mkdir -p hooks/{hook1,hook2,hook3}
```

### 3.2 迁移现有 Hook

```bash
# 复制 Hook 配置和脚本
cp ~/.hermes/hooks/hook1/HOOK.yaml hooks/hook1/
cp ~/.hermes/agent-hooks/hook1.sh hooks/hook1/handler.sh
```

### 3.3 创建安装脚本

```bash
cat > hooks-install.sh << 'EOF'
#!/bin/bash
# Hook 安装脚本

SKILL_DIR="$HOME/.hermes/skills/<category>/<skill-name>"
HOOKS_SOURCE="$SKILL_DIR/hooks"

for hook_dir in "$HOOKS_SOURCE"/*/; do
    hook_name=$(basename "$hook_dir")
    
    # 创建符号链接到 ~/.hermes/hooks/
    ln -sf "$hook_dir" "$HOME/.hermes/hooks/$hook_name"
    
    # 创建符号链接到 ~/.hermes/agent-hooks/
    ln -sf "$hook_dir/handler.sh" "$HOME/.hermes/agent-hooks/$hook_name.sh"
    
    chmod +x "$hook_dir/handler.sh"
done
EOF

chmod +x hooks-install.sh
```

### 3.4 运行安装

```bash
bash hooks-install.sh
```

---

## 四、维护方法

### 4.1 更新 Hook 逻辑

```bash
# 编辑技能目录下的脚本
vim hooks/workflow-status-check/handler.sh

# 保存后立即生效（符号链接自动同步）
```

### 4.2 添加新 Hook

```bash
# 创建 Hook 目录和文件
mkdir hooks/my-new-hook
# ... 创建 HOOK.yaml 和 handler.sh

# 运行安装脚本
bash hooks-install.sh
```

### 4.3 删除 Hook

```bash
# 删除技能目录下的 hook
rm -rf hooks/my-old-hook/

# 运行安装脚本（会检测到链接失效）
bash hooks-install.sh

# 手动清理失效链接（可选）
rm ~/.hermes/hooks/my-old-hook
rm ~/.hermes/agent-hooks/my-old-hook.sh
```

---

## 五、验证方法

### 5.1 验证符号链接

```bash
# 检查配置链接
ls -la ~/.hermes/hooks/<hook-name>

# 检查脚本链接
ls -la ~/.hermes/agent-hooks/<hook-name>.sh
```

**预期输出**：
```
lrwxrwxrwx  ... <hook-name> -> /home/user/.hermes/skills/.../hooks/<hook-name>/
lrwxrwxrwx  ... <hook-name>.sh -> /home/user/.hermes/skills/.../hooks/<hook-name>/handler.sh
```

### 5.2 测试 Hook 执行

```bash
# 直接执行测试
bash ~/.hermes/agent-hooks/<hook-name>.sh

# 带环境变量测试
HERMES_TOOL_NAME=terminal bash ~/.hermes/agent-hooks/<hook-name>.sh
```

---

## 六、设计原则

### 6.1 单一真相来源

**原则**：Hook 源代码只存在于技能目录

**原因**：
- 避免版本不一致
- 简化维护流程
- Git 友好

### 6.2 符号链接优于复制

**原则**：使用符号链接而非复制文件

**原因**：
- 修改即时生效
- 无需同步机制
- 自动保持一致

### 6.3 安装脚本自动化

**原则**：提供自动化安装脚本

**原因**：
- 减少手动操作
- 降低出错概率
- 可重复执行

---

## 七、适用场景

### 7.1 适合集中化管理的场景

- ✅ 技能包含多个 Hook
- ✅ Hook 与技能功能强相关
- ✅ 需要频繁更新 Hook 逻辑
- ✅ 技能需要版本控制

### 7.2 不适合的场景

- ❌ Hook 与技能无关联
- ❌ Hook 被多个技能共享
- ❌ Hook 只使用一次且不维护

---

## 八、案例：workflow-manager 技能

### 8.1 迁移前

```
~/.hermes/hooks/workflow-status-check/HOOK.yaml
~/.hermes/hooks/workflow-step-check/HOOK.yaml
~/.hermes/hooks/workflow-progress-update/HOOK.yaml
~/.hermes/hooks/workflow-session-cleanup/HOOK.yaml
~/.hermes/agent-hooks/workflow-status-check.sh
~/.hermes/agent-hooks/workflow-step-check.sh
~/.hermes/agent-hooks/workflow-progress-update.sh
~/.hermes/agent-hooks/workflow-session-cleanup.sh
~/.hermes/skills/.../workflow-manager/SKILL.md
```

**问题**：8 个文件分散在 3 个目录

### 8.2 迁移后

```
~/.hermes/skills/.../workflow-manager/
├── hooks/
│   ├── workflow-status-check/
│   │   ├── HOOK.yaml
│   │   └── handler.sh
│   ├── workflow-step-check/
│   │   ├── HOOK.yaml
│   │   └── handler.sh
│   ├── workflow-progress-update/
│   │   ├── HOOK.yaml
│   │   └── handler.sh
│   └── workflow-session-cleanup/
│       ├── HOOK.yaml
│       └── handler.sh
├── hooks-install.sh
├── HOOKS_GUIDE.md
└── SKILL.md
```

**优势**：
- ✅ 所有文件集中在技能目录
- ✅ 符号链接自动同步
- ✅ Git 统一管理
- ✅ 维护只需修改一处

---

## 九、最佳实践

### 9.1 命名规范

- Hook 目录名：`<功能描述>-<事件类型>`
- 脚本文件名：统一为 `handler.sh`（或 `handler.py`）
- 配置文件名：统一为 `HOOK.yaml`

### 9.2 文档规范

- 每个技能包含 `HOOKS_GUIDE.md`：Hook 使用指南
- SKILL.md 中说明 Hook 维护方法
- HOOK.yaml 中写明 description

### 9.3 测试规范

- 安装后立即测试 Hook 执行
- 修改 Hook 后测试功能是否正常
- 定期验证符号链接是否有效

---

## 十、参考资料

- Hermes Hooks 机制：`references/hermes-hooks-system.md`
- Hook 架构说明：`references/hooks-architecture.md`
- Hook 使用指南：`HOOKS_GUIDE.md`

---

**维护者**：workflow-manager 技能  
**最后更新**：2026-05-13
