# Hermes 插件选择推荐分析

日期：2026-05-18

## 用户场景分析

**主要使用场景**：安全渗透、工作流编排、远程操作、飞书沟通、token 优化

## 推荐决策逻辑

### 1. 功能重叠检测

| 插件 | 与现有功能重叠 | 推荐 |
|------|----------------|------|
| Browser-Use | web-access 技能已覆盖 | ❌ |
| 飞书 MCP | Hermes 原生支持 | ⚠️ 已满足 |
| GitHub MCP | gh CLI + github 技能 | ❌ |
| ComfyUI | 与场景无关 | ❌ |
| Google Workspace | 不用 Google 全家桶 | ❌ |
| Spotify | 与工作无关 | ❌ |

### 2. 核心需求匹配

| 需求 | 插件 | 推荐 |
|------|------|------|
| 调试工作流执行黑盒 | Langfuse | ⭐ |
| 多 Agent 任务回收 | Multi-Agent Kanban | ⭐ |
| Token 节省 | RTK-Hermes | ⚠️ 需测试兼容性 |

### 3. 兼容性评估

**RTK-Hermes 风险**：
- 与 LCM 压缩功能重叠
- 需要测试是否冲突
- 建议：先安装测试，有问题则禁用

## 推荐清单

**必装**：
- 🥇 Langfuse（调试追踪）
- 🥈 Multi-Agent Kanban（任务回收）

**可选**：
- ⚠️ RTK-Hermes（需测试兼容性）

**已满足**：
- 飞书集成（Hermes 原生）
- GitHub（gh CLI）
- 知识管理（ByteRover）
- 浏览器（web-access）

## 安装命令

```bash
# 启用 Langfuse
hermes plugins enable observability/langfuse
hermes config set langfuse.public_key "你的Public Key"
hermes config set langfuse.secret_key "你的Secret Key"

# 安装 RTK-Hermes
cd ~/.hermes/plugins
git clone https://github.com/ogallotti/rtk-hermes.git
cd rtk-hermes
pip install -e .

# 初始化 Kanban
hermes kanban init
hermes kanban boards create "我的项目"
```

## 用户偏好记录

**决策风格**：
- 最小改动原则
- 功能重叠检测优先
- 向后兼容性重视
- 方案对比后选择

**分析偏好**：
- 先查数据再分析代码
- 用实际数据验证假设
- 不接受纯代码分析作为结论
