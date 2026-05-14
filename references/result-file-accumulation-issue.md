# 结果文件累积问题

**发现日期**：2026-05-13
**影响范围**：所有使用临时文件汇总的工作流

---

## 问题描述

使用临时文件汇总分类结果时，分类文件会累积之前工作流的残留数据。

---

## 案例：电力调度系统识别工作流

### 第一次执行（源文件：4.txt）

```
power_dispatch.txt = [
  http://bfzuowen.com,
  http://m.bfzuowen.com,
  ...
]
```

### 第二次执行（源文件：5.txt）

```
power_dispatch.txt = [
  http://bfzuowen.com,      ← 第一次残留
  http://m.bfzuowen.com,    ← 第一次残留
  https://www.friendcom.cn  ← 本次新增
]
```

### 第三次执行（源文件：6.txt）

```
power_dispatch.txt = [
  http://bfzuowen.com,           ← 第一次残留
  http://m.bfzuowen.com,         ← 第一次残留
  https://www.friendcom.cn,      ← 第二次残留
  http://111.230.149.193:8091,   ← 本次新增
  ...
]
```

**验证结果**：
- 源文件：68个URL
- 汇总结果：124个URL（包含56个残留）

---

## 根本原因

### 汇总命令的问题

```bash
# 错误的汇总方式
for category in sgcc_dispatch power_dispatch ...; do
  > ${category}.txt
  for file in $(find . -name "*${category}*.txt"); do
    cat "$file" >> ${category}.txt  # ← 会包含所有临时文件
  done
done
```

**问题**：
1. `find . -name "*${category}*.txt"` 会匹配所有历史临时文件
2. 历史临时文件可能未被清理
3. 即使清理了临时文件，备份目录中的文件也会被匹配

---

## 解决方案

### 方案1：清理非源文件URL（推荐）

```bash
# 只保留在源文件中存在的URL
grep -Fxf url.txt ${category}.txt > ${category}_clean.txt
mv ${category}_clean.txt ${category}.txt
```

**优点**：
- 简单直接
- 不影响工作流执行
- 自动过滤所有残留

**缺点**：
- 需要在汇总后执行
- 依赖源文件格式正确

### 方案2：使用唯一临时文件名

```bash
# 使用时间戳或会话ID
session_id=$(date +%Y%m%d_%H%M%S)
for category in ...; do
  cat result_*_${session_id}_${category}.txt >> ${category}.txt
done
```

**优点**：
- 从源头避免混淆
- 支持并行执行

**缺点**：
- 需要修改所有子 agent 的输出逻辑

### 方案3：清理所有临时文件

```bash
# 执行前清理
rm -f result_*.txt batch_*.json temp/*.txt tmp/*.txt
```

**优点**：
- 预防性清理

**缺点**：
- 可能误删其他工作流的临时文件
- 不解决备份目录问题

---

## 验证方法

### 检查分类文件中的URL是否都在源文件中

```bash
cd /x/rank/dispatch-system/

# 方法1：逐行检查
while read url; do
  if ! grep -q "$url" url.txt; then
    echo "❌ $url (不在源文件中)"
  fi
done < power_dispatch.txt

# 方法2：统计差异
total=$(wc -l < url.txt)
classified=$(cat sgcc_dispatch.txt power_dispatch.txt sgcc_assets.txt power_related.txt excluded.txt | sort -u | wc -l)
echo "源文件: ${total} 个URL"
echo "已分类: ${classified} 个URL"
if [ $classified -gt $total ]; then
  echo "⚠️  存在残留数据: $((classified - total)) 个"
fi
```

---

## 最佳实践

### 工作流设计

1. **步骤2（准备文件）**：清理所有临时文件
   ```bash
   rm -f result_*.txt batch_*.json temp/*.txt tmp/*.txt
   ```

2. **步骤4（智能分析）**：使用唯一临时文件名
   ```bash
   session_id=$(date +%Y%m%d_%H%M%S)
   # 输出到 result_${batch_num}_${session_id}_${category}.txt
   ```

3. **步骤5（生成报告）**：验证并清理残留
   ```bash
   # 汇总后清理
   grep -Fxf url.txt ${category}.txt > ${category}_clean.txt
   mv ${category}_clean.txt ${category}.txt
   ```

### 执行前检查

```bash
# 检查是否存在历史临时文件
temp_files=$(find . -name "result_*.txt" -o -name "batch_*.json" | wc -l)
if [ $temp_files -gt 0 ]; then
  echo "⚠️  发现 ${temp_files} 个历史临时文件，建议清理"
fi
```

---

## 影响的工作流

| 工作流 | 是否受影响 | 解决方案 |
|--------|-----------|----------|
| 电力调度系统识别 | ✅ 是 | 已实施清理方案 |
| URL分析 | ⚠️ 可能 | 建议检查 |
| 凭证检测 | ⚠️ 可能 | 建议检查 |
| 通用漏洞扫描 | ❌ 否 | 不使用临时文件汇总 |

---

## 相关文档

- [data-flow-design-patterns.md](./data-flow-design-patterns.md) - 数据流向设计模式
- [execution-pitfalls.md](./execution-pitfalls.md) - 执行陷阱
