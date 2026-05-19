# 月报生成 MCP Word 模式（2026-05-18）

## 适用场景

使用 MCP word-document-server 工具填充 Word 模板生成月报。

## 工作流步骤

### 步骤 1：准备数据

```bash
# 查询数据摘要
python cli.py --fill-template --year 2026 --month 4

# 导出完整 JSON 数据
python cli.py --export-data --year 2026 --month 4 --json-output reports/data_2026_04.json
```

### 步骤 2：复制模板

```python
mcp_word_document_server_copy_document(
    source_filename="/x/0ri/xiangmu/all/moban/国网河南电科院...-1月.docx",
    destination_filename="/x/0ri/xiangmu/reports/国网河南电科院...-4月.docx"
)
```

### 步骤 3：更新元数据

```python
# 替换月份
mcp_word_document_server_search_and_replace(
    filename="...-4月.docx",
    find_text="1月",
    replace_text="4月"
)
```

### 步骤 4：填充核心表格

**表格索引对照**：
| 索引 | 内容 | 类型 |
|------|------|------|
| 5 | 数据源统计 | 数据统计表 |
| 6 | 严重程度分布 | 数据统计表 |
| 8 | CRITICAL TOP10 | 大型数据表 |
| 9 | 产品排名 | 大型数据表 |

**填充示例**：
```python
# 填充单元格
mcp_word_document_server_format_table_cell_text(
    filename="...-4月.docx",
    table_index=5,
    row_index=1,  # 第2行（第1行是表头）
    column_index=0,
    text="NVD"
)
```

### 步骤 5：格式化文档

```bash
# 基础格式化（标题、段落、页边距）
python3 format_document.py input.docx output_formatted.docx

# 表格优化
python3 optimize_tables.py output_formatted.docx output_final.docx
```

### 步骤 6：生成 EXP 测试标记

```python
# 选择推荐测试的漏洞
python cli.py --select-cves --year 2026 --month 4 --top-n 3

# 或手动生成标记文件
# 参考 /x/0ri/xiangmu/docs/AI_EXP_GUIDE.md
```

## 核心表格填充要点

### 表格 5 - 数据源统计

```
表头：数据源 | 数量 | 占比
数据：NVD | 1489 | 100.0%
```

### 表格 6 - 严重程度分布

```
表头：严重程度 | 数量 | 占比 | 累计占比
数据：
- CRITICAL | 164 | 11.0% | 11.0%
- HIGH | 603 | 40.5% | 51.5%
- MEDIUM | 601 | 40.4% | 91.9%
- LOW | 60 | 4.0% | 95.9%
```

### 表格 8 - CRITICAL TOP10

```
表头：排名 | CVE编号 | CVSS评分 | 受影响产品 | 漏洞类型
数据：从 tables.critical_top10 获取
```

### 表格 9 - 产品排名

```
表头：排名 | 产品名称 | 漏洞数量 | 占比 | 累计占比
数据：从 tables.product_ranking 获取
```

## JSON 数据结构

```json
{
  "meta": {
    "year": 2026,
    "month": 4,
    "month_chinese": "四",
    "export_time": "2026-05-18 15:10:47",
    "date_range": ["2026-04-01", "2026-05-01"]
  },
  "statistics": {
    "total_count": 1489,
    "data_sources": [...],
    "severity_stats": [...]
  },
  "tables": {
    "critical_top10": [...],
    "product_ranking": [...]
  },
  "all_cves": [...]
}
```

## 常见问题

### Q1：严重程度统计格式异常

**原因**：JSON 中 severity_stats 是字符串列表而非字典

**解决**：从 all_cves 手动统计：
```python
from collections import Counter
severities = Counter(cve['severity'] for cve in data['all_cves'])
```

### Q2：产品名称过长

**原因**：一个 CVE 可能影响多个产品

**解决**：取第一个产品或简化名称：
```python
product = cve['products'][0] if cve['products'] else '未知'
```

### Q3：表格索引不匹配

**原因**：模板版本不同，表格顺序可能变化

**解决**：先用 get_document_outline 确认表格索引

## 输出文件

| 文件 | 说明 |
|------|------|
| `...-4月.docx` | 初始填充文档 |
| `...-4月_formatted.docx` | 格式化后文档 |
| `...-4月_final.docx` | 最终交付文档 |
| `cve_analysis_report_*.md` | 深度分析报告 |
| `exp_test_summary_*.md` | EXP 测试标记 |

## 参考文档

- `/x/0ri/xiangmu/docs/AI_REPORT_GUIDE.md` - CVE 报告编写指南
- `/x/0ri/xiangmu/docx/CLAUDE.md` - Word 格式标准
- `/x/0ri/xiangmu/docs/AI_EXP_GUIDE.md` - EXP 测试指南
