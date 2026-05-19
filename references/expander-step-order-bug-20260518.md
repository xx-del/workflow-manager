# Expander 步骤顺序错误 Bug

**发现日期**: 2026-05-18
**影响版本**: workflow-manager v6.5
**严重程度**: 高 - 导致工作流执行失败

---

## 问题现象

拼接工作流展开后，status.json 中的步骤顺序与子工作流 WORKFLOW.md 定义不符。

**案例：资产收集流程**

_index.yaml 定义：
```yaml
nodes:
- id: 1
  name: 电力数据
- id: 2
  name: 域名处理
- id: 3
  name: 端口扫描
- id: 4
  name: URL生成
- id: 5
  name: URL分析
```

电力数据 WORKFLOW.md 步骤顺序：
```
步骤1: 解析日期范围
步骤2: 备份旧文件
步骤3: 删除旧输出
步骤4: 批量下载数据
步骤5: AI 分析数据
步骤6: 记录日志
步骤7: 生成报告
```

**实际展开结果（错误）**：
```
全局步骤1: 解析日期范围 ✓
全局步骤2: 记录日志 ← 错误！应该在步骤7之后
全局步骤3: 生成报告 ← 错误！应该在AI分析之后
全局步骤4: 备份旧文件 ← 错误！应该在解析日期之后
全局步骤5: 删除旧输出
全局步骤6: 批量下载数据
全局步骤7: AI 分析数据
```

---

## 根本原因

expander.py 展开拼接工作流时：
1. 读取子工作流 WORKFLOW.md
2. 但未按子工作流的步骤顺序排列
3. 导致全局步骤编号与实际执行顺序不符

**推测原因**：
- 步骤合并时使用了字典或集合，丢失顺序
- 或排序逻辑使用了错误的字段（如 original_id 而非实际顺序）

---

## 影响

1. **执行顺序错误**：步骤在依赖项之前执行
2. **数据缺失**：生成报告时数据未下载
3. **工作流失败**：无法正常完成拼接工作流

---

## 临时方案

在 expander.py 修复前：
1. 执行前检查 status.json 步骤顺序
2. 对比子工作流 WORKFLOW.md 定义
3. 发现不一致时停止执行并报告

**检测命令**：
```bash
python3 -c "
import json
with open('status.json') as f:
    d = json.load(f)
for k in sorted(d['steps'].keys(), key=int):
    v = d['steps'][k]
    print(f'步骤{k}: {v.get(\"name\")} | source={v.get(\"source_workflow\")} | original_id={v.get(\"original_id\")}')
"
```

---

## 修复方向

1. 检查 expander.py 步骤合并逻辑
2. 确保使用有序数据结构（list 而非 dict/set）
3. 按子工作流 WORKFLOW.md 的实际步骤顺序排列
4. 添加步骤顺序验证测试

---

## 相关文件

- `workflow-manager/actions/expander.py` - 工作流展开器
- `workflow-manager/references/breakpoint-type-loss-bug-20260518.md` - 同一模块的另一个 Bug
