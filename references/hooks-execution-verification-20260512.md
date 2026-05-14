# 钩子机制实际运行验证报告

**日期**: 2026-05-12  
**工作流**: 资产收集流程  
**验证人**: AI Agent  

---

## 一、验证背景

workflow-manager v6.2 配置了钩子机制，但缺少实际运行验证记录。本次执行资产收集工作流时，重点监控钩子触发情况。

## 二、钩子配置验证

### 钩子文件位置
```
~/.hermes/skills/openclaw-imports/workflow-manager/hooks/
├── user_prompt_submit.sh  ✅ 存在且可执行
├── pre_tool_use.sh        ✅ 存在且可执行
├── post_tool_use.sh       ✅ 存在且可执行
└── stop.sh                ✅ 存在且可执行
```

### SKILL.md 钩子声明
```yaml
hooks:
  UserPromptSubmit:
    - type: command
      command: bash $SKILL_DIR/hooks/user_prompt_submit.sh
  PreToolUse:
    - matcher: "terminal|delegate_task"
      hooks:
        - type: command
          command: bash $SKILL_DIR/hooks/pre_tool_use.sh
```

---

## 三、实际运行验证

### UserPromptSubmit 钩子

**触发时机**: 用户发送消息时  
**触发次数**: 1次  
**触发时间**: 18:18:10  

**执行内容**:
1. 检测到未完成工作流: 资产收集流程
2. 自动生成 status.md: `/home/kali/.hermes/workflows/资产收集流程/status.md`
3. 显示执行计划前60行

**验证结果**: ✅ 正常运行，成功生成执行计划

---

### PreToolUse 钩子

**触发时机**: AI调用 terminal 或 delegate_task 前  
**触发次数**: 15次（每个工作流步骤执行前）  
**匹配规则**: `terminal|delegate_task`

**执行内容**:
1. 检查 status.md 是否存在
2. 显示当前步骤名称
3. 显示约束清单
4. 如果 status.md 不存在，exit 1 阻断执行

**验证结果**: ✅ 正常运行，约束注入成功

**触发记录**:
- 步骤1（解析日期范围）: ✅ 触发
- 步骤2（备份旧文件）: ✅ 触发
- 步骤3（删除旧输出）: ✅ 触发
- 步骤4（批量下载数据）: ✅ 触发
- 步骤5（AI分析数据）: ✅ 触发（delegate_task）
- 步骤6（记录日志）: ✅ 触发
- 步骤7（生成报告）: ✅ 触发
- 步骤8（域名处理）: ✅ 触发
- 步骤9（端口扫描）: ✅ 触发
- 步骤10（URL生成）: ✅ 触发
- 步骤11（备份旧文件）: ✅ 触发
- 步骤12（准备文件）: ✅ 触发
- 步骤13（抓取页面信息）: ✅ 触发
- 步骤14（智能分析）: ✅ 触发（delegate_task）
- 步骤15（随机打乱URL）: ✅ 触发

---

### PostToolUse 钩子

**状态**: 已配置，文件存在  
**验证**: 未详细监控（非本次重点）

---

## 四、钩子注入效果验证

### 约束注入成功

✅ **每次工具调用前都看到约束提醒**  
- PreToolUse 钩子成功显示当前步骤和约束清单
- 类似"注意力操控"机制，确保AI遵守执行规则

✅ **防止AI偏离执行流程**
- 未添加 timeout 参数
- 未修改 WORKFLOW.md 定义的命令
- 未添加 WORKFLOW.md 中没有的验证步骤
- 严格按 pending_instructions 执行

✅ **遇到问题停止并上报**
- 端口扫描等待期间，未擅自跳过
- 等待远程扫描完成后继续执行

---

## 五、关键发现

### 1. 钩子触发统计方法

**UserPromptSubmit**: 1次/会话（用户发送消息时）  
**PreToolUse**: N次/工作流（N = 工作流步骤数）  
**PostToolUse**: N次/工作流（N = 工具调用次数）

### 2. 钩子文件权限

所有钩子脚本必须可执行：
```bash
-rwxrwxr-x  user_prompt_submit.sh
-rwxrwxr-x  pre_tool_use.sh
-rwxrwxr-x  post_tool_use.sh
-rwxrwxr-x  stop.sh
```

### 3. exit 1 阻断机制

PreToolUse 钩子中，如果 status.md 不存在：
```bash
if [ ! -f "$WORKFLOW_DIR/status.md" ]; then
    echo "❌ 错误：必须先生成执行计划"
    exit 1  # 阻断执行
fi
```

**效果**: 强制AI先调用 execute.py --plan-only，防止绕过代码工具直接执行。

### 4. matcher 匹配规则

PreToolUse 钩子只匹配 `terminal|delegate_task`：
- ✅ terminal 调用前触发
- ✅ delegate_task 调用前触发
- ❌ 其他工具调用前不触发

---

## 六、验证结论

✅ **钩子机制运行正常**  
✅ **约束注入有效**  
✅ **防止AI违规操作成功**  
✅ **工作流标准化执行达成**

---

## 七、建议

1. **保持现有配置**: 钩子机制设计合理，运行稳定
2. **增加触发点**: 可考虑增加 PostToolUse 验证（工具调用后检查）
3. **监控日志**: 建议记录钩子触发日志，便于问题排查
4. **文档更新**: 将本次验证结果添加到技能文档

---

## 八、附录

### 钩子脚本内容示例

**user_prompt_submit.sh**:
```bash
#!/bin/bash
STATUS_FILE=$(find ~/.hermes/workflows -name "status.json" -exec grep -l '"status": "running"' {} \; 2>/dev/null | grep -v ".backup" | head -1)

if [ -n "$STATUS_FILE" ]; then
  WORKFLOW_DIR=$(dirname "$STATUS_FILE")
  WORKFLOW_NAME=$(basename "$WORKFLOW_DIR")
  
  if [ ! -f "$WORKFLOW_DIR/status.md" ]; then
    echo "⚠️  status.md 不存在，正在自动生成..."
    python3 ~/.hermes/skills/openclaw-imports/workflow-manager/actions/execute.py "$WORKFLOW_NAME" --plan-only 2>/dev/null
  fi
  
  echo "🔔 检测到未完成工作流: $WORKFLOW_NAME"
  head -60 "$WORKFLOW_DIR/status.md"
fi
```

**pre_tool_use.sh**:
```bash
#!/bin/bash
STATUS_FILE=$(find ~/.hermes/workflows -name "status.json" -exec grep -l '"status": "running"' {} \; 2>/dev/null | grep -v ".backup" | head -1)

if [ -n "$STATUS_FILE" ]; then
  WORKFLOW_DIR=$(dirname "$STATUS_FILE")
  
  # 强制检查：status.md 必须存在
  if [ ! -f "$WORKFLOW_DIR/status.md" ]; then
    echo "❌ 错误：必须先生成执行计划"
    exit 1
  fi
  
  # 显示当前步骤和约束
  # ...
fi
```

---

**验证完成时间**: 2026-05-12 18:32  
**验证状态**: ✅ 通过
