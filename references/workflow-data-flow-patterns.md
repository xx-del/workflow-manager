# 工作流间数据流向设计模式

**版本**: v1.0.0  
**创建时间**: 2026-05-13  
**来源**: 资产收集流程执行问题分析

---

## 问题背景

### 实际案例

**工作流**: 资产收集流程（电力数据 → 域名处理 → 端口扫描 → URL生成 → URL分析）

**问题现象**：
- 电力数据工作流生成 dianli.txt (32个URL)
- URL分析工作流执行后，dianli.txt只剩6个URL
- 数据丢失率：81.25%

**根本原因**：
- URL分析工作流步骤2删除了dianli.txt
- URL分析工作流分析的是url.txt（端口扫描结果，20个URL）
- url.txt ≠ dianli.txt，数据集不重叠

---

## 设计原则

### 核心原则：增强而非覆盖

**错误设计** ❌：
```bash
# URL分析工作流步骤2
rm -f dianli.txt  # 删除上游结果
# 分析新数据
# 生成新 dianli.txt
```

**正确设计** ✅：
```bash
# URL分析工作流步骤2
if [ -f dianli.txt ]; then
    mv dianli.txt dianli_from_upstream.txt
fi
# 分析新数据
# 合并结果
cat dianli_from_upstream.txt dianli.txt | sort -u > dianli_merged.txt
mv dianli_merged.txt dianli.txt
```

### 三大原则

#### 1. 不删除上游工作流结果

**理由**：
- 上游工作流的结果可能包含下游没有的数据
- 删除导致数据永久丢失
- 无法追溯完整数据流

**替代方案**：
- 备份而非删除
- 重命名保留历史
- 合并新旧结果

#### 2. 明确输入输出边界

**每个工作流应明确定义**：

```yaml
输入:
  - 文件: dianli.txt
  - 来源: 电力数据工作流
  - 格式: 纯URL列表

输出:
  - 文件: dianli_verified.txt
  - 说明: 验证后的电力行业URL
  - 关系: 增强dianli.txt
```

#### 3. 使用增量命名

**避免同名覆盖**：

| 工作流 | 输入 | 输出 | 说明 |
|--------|------|------|------|
| 电力数据 | JSON数据 | dianli_initial.txt | 初步筛选 |
| URL分析 | dianli_initial.txt | dianli_verified.txt | 验证确认 |
| 最终合并 | dianli_initial.txt + dianli_verified.txt | dianli.txt | 最终结果 |

---

## 常见陷阱

### 陷阱1: 同名文件覆盖

**场景**：多个工作流输出同名文件

**示例**：
```yaml
工作流A:
  输出: result.txt (100条数据)

工作流B:
  输入: 其他数据源
  输出: result.txt (50条数据)  # ❌ 覆盖了工作流A的结果
```

**后果**：
- 数据丢失
- 无法追溯数据来源
- 影响下游工作流

**解决**：
```yaml
工作流A:
  输出: result_from_A.txt

工作流B:
  输出: result_from_B.txt

最终步骤:
  合并: result_from_A.txt + result_from_B.txt → result.txt
```

### 陷阱2: 隐式依赖

**场景**：工作流B假设工作流A的输出存在

**示例**：
```yaml
工作流B:
  步骤1: 读取 dianli.txt
  步骤2: 删除 dianli.txt  # ❌ 假设后续不需要
  步骤3: 生成新结果
```

**后果**：
- 如果单独执行工作流B，步骤1失败
- 如果工作流A未执行，无法工作
- 破坏了工作流独立性

**解决**：
```yaml
工作流B:
  步骤0: 检查输入
    if [ ! -f dianli.txt ]; then
        echo "需要先执行工作流A"
        exit 1
    fi
  
  步骤1: 备份输入
    cp dianli.txt dianli_backup.txt
  
  步骤2: 处理数据
  
  步骤3: 合并结果
    cat dianli_backup.txt new_result.txt | sort -u > dianli.txt
```

### 陷阱3: 数据流向不清

**场景**：工作流间数据流向没有明确定义

**示例**：
```
电力数据 → dianli.txt
域名处理 → output.txt
端口扫描 → scan_result.txt
URL生成 → url.txt
URL分析 → dianli.txt (覆盖)  # ❌ 数据流向冲突
```

**后果**：
- 不清楚哪个是最新结果
- 无法判断数据完整性
- 难以追溯问题

**解决**：
```
电力数据 → dianli_stage1.txt
域名处理 → dianli_stage2.txt
端口扫描 → dianli_stage3.txt
URL生成 → dianli_stage4.txt
URL分析 → dianli_final.txt
```

---

## 设计模式

### 模式1: 阶段式命名

**适用场景**：串行工作流，每个阶段增强数据

**模式**：
```
输入: source_data.txt
阶段1: stage1_processed.txt
阶段2: stage2_enhanced.txt
阶段3: stage3_validated.txt
最终: final_result.txt
```

**优点**：
- 每个阶段结果独立保存
- 可以回溯到任意阶段
- 数据流向清晰

**缺点**：
- 中间文件较多
- 需要定期清理

### 模式2: 合并式输出

**适用场景**：多个工作流贡献同一结果

**模式**：
```bash
# 工作流A
output_A.txt

# 工作流B
output_B.txt

# 最终合并步骤
cat output_A.txt output_B.txt | sort -u > final_result.txt
```

**优点**：
- 保留各工作流独立输出
- 可以单独验证每个工作流
- 合并逻辑明确

**缺点**：
- 需要额外的合并步骤
- 需要去重逻辑

### 模式3: 增量更新

**适用场景**：持续更新同一结果文件

**模式**：
```bash
# 工作流A
echo "new_data" >> result.txt

# 工作流B
echo "more_data" >> result.txt

# 最终去重
sort -u result.txt -o result.txt
```

**优点**：
- 不丢失历史数据
- 支持增量更新
- 简单直接

**缺点**：
- 需要定期去重
- 难以删除过期数据

---

## 最佳实践

### 1. 明确定义输入输出

**每个工作流WORKFLOW.md应包含**：

```markdown
## 输入
- 文件: dianli.txt
- 来源: 电力数据工作流
- 格式: 纯URL列表，每行一个URL
- 必需: 是

## 输出
- 文件: dianli_verified.txt
- 格式: 纯URL列表
- 关系: 验证后的dianli.txt
- 不覆盖: dianli.txt
```

### 2. 使用备份策略

**修改重要文件前**：

```bash
# 备份
timestamp=$(date +%Y%m%d_%H%M%S)
cp dianli.txt "bk/dianli_${timestamp}.txt"

# 修改
# ...

# 验证
if [ 验证失败 ]; then
    cp "bk/dianli_${timestamp}.txt" dianli.txt
fi
```

### 3. 添加数据来源标记

**在结果文件中记录来源**：

```bash
# 在文件开头添加元数据
cat > dianli.txt << 'EOF'
# 数据来源: 电力数据工作流 + URL分析工作流
# 生成时间: 2026-05-13 10:30:00
# URL数量: 38
# -- 数据开始 --
http://example1.com
http://example2.com
...
EOF
```

### 4. 实现数据完整性检查

**在工作流末尾验证**：

```bash
# 检查数据完整性
initial_count=$(wc -l < dianli_initial.txt)
final_count=$(wc -l < dianli_final.txt)

if [ $final_count -lt $((initial_count * 90 / 100)) ]; then
    echo "⚠️ 警告: 数据丢失超过10%"
    echo "初始: $initial_count, 最终: $final_count"
fi
```

---

## 验证清单

设计工作流时，检查以下项：

- [ ] 是否明确定义了输入输出文件？
- [ ] 输出文件名是否与上游工作流冲突？
- [ ] 是否避免了删除上游工作流结果？
- [ ] 数据流向是否清晰可追溯？
- [ ] 是否有备份/恢复机制？
- [ ] 是否有数据完整性检查？

---

## 相关文档

- `references/hooks-trigger-mechanism.md` - Hook触发机制
- `references/execution-architecture.md` - 执行架构
- `SKILL.md` - 工作流管理技能主文档
