# 工作流数据流向设计模式

## 问题来源

2026-05-13 资产收集流程执行发现：URL分析工作流删除并覆盖了电力数据工作流的dianli.txt，导致32个URL丢失为6个。

## 问题复现

### 数据流向

```
电力数据工作流
  ↓ 输出: dianli.txt (32个URL)
  ↓
域名处理 → 端口扫描 → URL生成
  ↓ 输出: url.txt (20个URL，基于端口扫描)
  ↓
URL分析工作流
  ↓ 步骤2: rm -f dianli.txt  ← 删除上游结果
  ↓ 步骤4: 分析url.txt → 输出新的dianli.txt (6个URL)
  ↓
最终结果: dianli.txt = 6个 ❌ (应该是32+6=38个)
```

### 根本原因

1. **数据集不同**：url.txt是端口扫描后的新URL列表，不包含dianli.txt中的所有原始URL
2. **设计假设错误**：URL分析假设url.txt包含了dianli.txt中的所有URL
3. **输出文件同名**：两个工作流都输出dianli.txt，后者覆盖前者

### 交集分析

| 数据集 | URL数量 | 来源 |
|--------|---------|------|
| dianli.txt（电力数据） | 32 | JSON元数据AI分析 |
| url.txt（URL生成） | 20 | 端口扫描后的新URL |
| 交集 | ~1 | http://116.62.144.158:3000 |

## 设计模式

### 模式1：差异化命名（推荐用于筛选型工作流）

```yaml
电力数据工作流:
  输出: 
    - dianli_initial.txt  # 初始分类结果

URL分析工作流:
  输入: url.txt
  输出:
    - dianli_verified.txt  # 验证后的结果

最终步骤:
  命令: cat dianli_initial.txt dianli_verified.txt | sort -u > dianli.txt
```

### 模式2：合并增强（推荐用于增强型工作流）

```yaml
URL分析工作流:
  步骤2（准备文件）:
    # 不删除dianli.txt，而是备份
    command: |
      mv dianli.txt dianli_from_upstream.txt
      cp url.txt url_info_input.txt

  步骤4（智能分析后）:
    # 合并上游结果
    command: |
      cat dianli_from_upstream.txt dianli.txt | sort -u > dianli_merged.txt
      mv dianli_merged.txt dianli.txt
```

### 模式3：统一输出目录（推荐用于多阶段流程）

```yaml
资产收集流程:
  output_dir: /x/rank/.../start/20260512/

  电力数据工作流:
    输出: 20260512/dianli_initial.txt

  URL分析工作流:
    输出: 20260512/dianli_verified.txt

  汇总步骤:
    命令: 合并所有dianli_*.txt → dianli.txt
```

## 设计检查清单

### 拼接工作流设计时

1. **同名文件检测**
   ```bash
   # 检查所有工作流的输出文件是否有重名
   grep -r "输出:" ~/.hermes/workflows/资产收集流程/*/WORKFLOW.md
   ```

2. **删除操作检测**
   ```bash
   # 检查是否有工作流删除上游结果
   grep -r "rm -f" ~/.hermes/workflows/*/WORKFLOW.md | grep -E "(dianli|guojiadianwang)"
   ```

3. **输入输出边界确认**
   - 每个工作流的输入来自哪里？
   - 每个工作流的输出会覆盖谁？
   - 两个数据集是否完全重叠？

## 修复方案

### 资产收集流程的修复

**文件**：`~/.hermes/workflows/URL分析/WORKFLOW.md`

**步骤2修改**：
```bash
# 原始（有问题）：
rm -f /x/rank/hwxinxisouji/liuliang/start/dianli.txt

# 修复后：
if [ -f dianli.txt ]; then
  mv dianli.txt dianli_from_powerdata.txt
fi
```

**步骤4修改（智能分析后）**：
```bash
# 合并上游结果
if [ -f dianli_from_powerdata.txt ]; then
  cat dianli_from_powerdata.txt dianli.txt | sort -u > dianli_merged.txt
  mv dianli_merged.txt dianli.txt
  rm -f dianli_from_powerdata.txt
fi
```

## 教训总结

1. **永远不要删除上游工作流的结果文件** — 备份而非删除
2. **不同数据集不应输出同名文件** — 差异化命名
3. **拼接工作流必须验证数据流向** — 检查覆盖和丢失
4. **增强而非覆盖** — 合并上游结果，而非替代
