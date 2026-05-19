#!/bin/bash
# 技能文档优化模板 - 基于内容匹配，避免行号依赖
# 用途：优化 SKILL.md，删除过期内容，迁移负面内容到 references/
# 使用方法：修改 SKILL_MD、REFERENCES_DIR、PATTERN 变量后执行

set -e

# ===== 配置区 =====
SKILL_MD="/path/to/skill/SKILL.md"           # 目标 SKILL.md 路径
REFERENCES_DIR="/path/to/skill/references"    # references 目录
TARGET_FILE="$REFERENCES_DIR/target.md"      # 迁移目标文件
BACKUP_FILE="/path/to/skill/SKILL.md.bak_$(date +%Y%m%d)"  # 备份文件
TEMP_DIR="/tmp/skill-optimization"            # 临时目录

# 内容匹配模式（正则表达式）
# 示例：提取特定章节
PATTERN='(### 某章节.*?)(?=\n---\n### 下个章节)'

# ===== 执行区 =====

mkdir -p "$TEMP_DIR"
mkdir -p "$REFERENCES_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "技能文档优化"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. 创建备份
cp "$SKILL_MD" "$BACKUP_FILE"
echo "✅ 备份创建：$BACKUP_FILE"

# 2. 提取内容（基于内容匹配）
python3 << PYEOF
import re

skill_md = "$SKILL_MD"
temp_dir = "$TEMP_DIR"
pattern = r"$PATTERN"

with open(skill_md, 'r') as f:
    content = f.read()

# 提取内容
match = re.search(pattern, content, re.DOTALL)

if match:
    extracted_content = match.group(1)
    
    # 创建完整文档
    full_doc = f"""# 提取内容

{extracted_content}

---
"""
    
    with open(f"{temp_dir}/extracted.md", 'w') as f:
        f.write(full_doc)
    
    print(f"✅ 提取成功：{len(extracted_content)} 字符")
else:
    print("❌ 未找到匹配内容")
    exit(1)
PYEOF

# 3. 删除内容并替换为链接引用
python3 << PYEOF
import re

skill_md = "$SKILL_MD"
temp_dir = "$TEMP_DIR"
pattern = r"$PATTERN"
target_file = "references/target.md"  # 相对路径

with open(skill_md, 'r') as f:
    content = f.read()

# 删除内容
content_new = re.sub(pattern, '', content, flags=re.DOTALL)

# 添加链接引用（根据实际情况调整位置）
# 示例：在某个章节后添加
# content_new = re.sub(
#     r'(## 某章节\n)',
#     r'\1\n**参考**: 见 [`target.md`](' + target_file + ')\n',
#     content_new
# )

with open(skill_md, 'w') as f:
    f.write(content_new)

char_count = len(content_new)
print(f"✅ 修改完成，当前字符数：{char_count}")
PYEOF

# 4. 移动提取文件到 references/
if [ -f "$TEMP_DIR/extracted.md" ]; then
    mv "$TEMP_DIR/extracted.md" "$TARGET_FILE"
    echo "✅ 内容已迁移：$TARGET_FILE"
fi

# 5. 验证字符数
CHAR_COUNT=$(wc -c < "$SKILL_MD")
echo ""
echo "优化结果："
echo "  字符数：$CHAR_COUNT"

if [ "$CHAR_COUNT" -le 3000 ]; then
    echo "  ✅ 篇幅达标（≤3000）"
else
    echo "  ⚠️  仍超标 $(($CHAR_COUNT - 3000)) 字符"
fi

# 6. 清理临时目录
rm -rf "$TEMP_DIR"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "优化完成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
