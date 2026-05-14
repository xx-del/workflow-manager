# v6.2.0 验证发现的陷阱

**日期**: 2026-05-12
**上下文**: workflow-manager v6.1 → v6.2 强化 planning-with-files 融合后的代码验证

---

## Bug 1：Python f-string 字符串未终止

**文件**: `actions/update_plan.py` 第 45 行
**症状**: `SyntaxError: unterminated f-string literal`
**根因**: write_file 写入时 rf-string中的 `[^\n]` 被解释为换行，导致字符串在行尾终止
**修复**: 合并为单行 `rf"...[^\n]+"`
**教训**: Python 多行字符串中使用 `[^\n]` 时，确保不在行尾换行；或改用 `[\s\S]` 替代

## Bug 2：正则表达式重复匹配

**文件**: `actions/update_plan.py` update_step_status()
**症状**: `⚠️ 未找到步骤` — 正则匹配失败
**根因**: step_name 已包含"步骤 1:"前缀，但正则又加了 `步骤.*?:` 前缀，导致 `### 步骤.*?: 步骤 1: 端口扫描` 无法匹配实际文本 `### 步骤 1: 端口扫描`
**修复**: `rf"(### 步骤.*?: {re.escape(step_name)}..." → rf"(### {re.escape(step_name)}..."`
**教训**: 当变量已包含前缀文本时，正则中不要重复添加该前缀

## Bug 3：命令行参数索引偏移

**文件**: `actions/update_parallel_progress.py` main() 函数
**症状**: `ValueError: invalid literal for int() with base 10: '--completed'`
**根因**: argv 索引错误 — `--batch` 后参数位置应为 argv[3]/argv[5]/argv[7]，代码写成了 argv[4]/argv[6]/argv[8]
**修复**: `sys.argv[4] → sys.argv[3]`, `sys.argv[6] → sys.argv[5]`, `sys.argv[8] → sys.argv[7]`
**教训**: Python argparse 手动解析 argv 时，位置参数紧跟在选项后，索引 = 选项索引 + 1；建议使用 argparse 替代手动解析

---

## 通用教训

1. **代码创建后必须验证**：write_file 写入的代码可能因转义问题产生语法错误，py_compile / bash -n 是最低成本验证
2. **正则与变量内容冲突**：当变量值包含正则前缀文本时，检查正则是否重复匹配
3. **argv 手动解析易错**：参数索引计算容易偏移，优先使用 argparse
