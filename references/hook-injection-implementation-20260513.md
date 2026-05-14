# Hook 注入机制实现文档

## 背景

v6.4 架构重构后，约束注入从 executor.py 迁移到 Hook 机制。

## 实现原理

**触发条件**：
- `execute.py --init` 生成 status.json
- Hook 检测到 status.json 且 status.md 不存在
- Hook 自动创建 status.md 并注入约束

**注入内容**：
1. 核心禁止事项（5个章节）
2. 工作流类型识别结果
3. 类型特殊约束（拼接/断点）

## 工作流类型识别

**识别逻辑**（从 executor.py 提取）：

```python
# 1. branch
if wf.get('type') == 'branch':
    return 'branch'
if all(n.get('calls') == 'workflow-manager' for n in nodes):
    return 'branch'

# 2. heartbeat
config = wf.get('config', {})
if config.get('heartbeat', {}).get('enabled'):
    return 'heartbeat'
if any(n.get('type') in ['breakpoint', 'auto'] for n in nodes):
    return 'heartbeat'
if any(n.get('trigger') == 'heartbeat' for n in nodes):
    return 'heartbeat'

# 3. normal
return 'normal'
```

## Hook 文件

**位置**：`hooks/workflow-ai-remind/handler.sh`

**关键功能**：
- 查找活动工作流（当前目录/workflows/）
- 解析 _index.yaml（使用 Python YAML 解析）
- 识别工作流类型
- 收集断点步骤
- 收集子工作流列表
- 创建 status.md 并注入约束

## 禁止事项章节

**完整内容**（从 executor.py 提取）：

1. **执行行为约束**
   - 绝对禁止：修改命令、添加 timeout、跳过步骤
   - 必须遵守：严格按指令执行、验证输出、更新状态

2. **主AI职责边界约束**
   - 禁止自己读取 _index.yaml
   - 禁止自己判断步骤顺序
   - 禁止直接调用 delegate_task

3. **异常处理约束**
   - 立即停止工作流
   - 上报异常现象
   - 等待用户指示

4. **进度记录约束**
   - 更新 status.json
   - 记录执行日志

5. **完成判定约束**
   - 所有步骤状态 = completed
   - 所有预期输出文件存在

## 测试验证

**测试工作流**：
- `/tmp/wf-test-suite/normal-workflow/` - 普通工作流
- `/tmp/wf-test-suite/heartbeat-workflow/` - 断点工作流
- `/tmp/wf-test-suite/branch-workflow/` - 拼接工作流

**验证结果**：
- ✅ 普通工作流：类型识别正确，禁止事项完整
- ✅ 断点工作流：断点位置标注正确
- ✅ 拼接工作流：子工作流列表正确，展开指导完整

## 关键发现

**用户纠正**：
1. 叶节点展开后要识别断点工作流
2. 要覆盖到所有类型的工作流节点
3. 禁止事项要从代码中参考（完整提取）
4. 拼接工作流没有 WORKFLOW.md，需要读取叶节点文档

**架构变更**：
- 从 executor.py 注入 → 改为 Hook 直接注入
- AI 执行时只看 status.md，不看 SKILL.md
- SKILL.md 定位：创建和验证时的依据文档

## 文件路径

- Hook 脚本：`~/.hermes/skills/openclaw-imports/workflow-manager/hooks/workflow-ai-remind/handler.sh`
- 备份文件：`handler.sh.bak_20260513_220604`
- 测试目录：`/tmp/wf-test-suite/`

## 更新日期

2026-05-13
