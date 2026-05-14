#!/bin/bash
# Workflow Manager Hooks 安装脚本 (Python版本)
# 将技能目录下的 hooks 同步到 Hermes 标准路径

set -e

SKILL_DIR="$HOME/.hermes/skills/openclaw-imports/workflow-manager"
HOOKS_SOURCE="$SKILL_DIR/hooks"
HERMES_HOOKS_DIR="$HOME/.hermes/hooks"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Workflow Manager Hooks 安装 (Python)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 确保目标目录存在
mkdir -p "$HERMES_HOOKS_DIR"

# 遍历技能目录下的所有 hook
for hook_dir in "$HOOKS_SOURCE"/*/; do
    hook_name=$(basename "$hook_dir")
    
    # 检查必要文件是否存在
    if [[ ! -f "$hook_dir/HOOK.yaml" ]]; then
        echo "⚠️  跳过 $hook_name：缺少 HOOK.yaml"
        continue
    fi
    
    if [[ ! -f "$hook_dir/handler.py" ]]; then
        echo "⚠️  跳过 $hook_name：缺少 handler.py"
        continue
    fi
    
    echo "📦 安装 $hook_name"
    
    # 删除旧的目录/文件（如果存在）
    if [[ -d "$HERMES_HOOKS_DIR/$hook_name" ]]; then
        rm -rf "$HERMES_HOOKS_DIR/$hook_name"
    fi
    if [[ -L "$HERMES_HOOKS_DIR/$hook_name" ]]; then
        rm -f "$HERMES_HOOKS_DIR/$hook_name"
    fi
    
    # 创建符号链接到 ~/.hermes/hooks/
    ln -s "$hook_dir" "$HERMES_HOOKS_DIR/$hook_name"
    echo "   ✅ 配置链接: ~/.hermes/hooks/$hook_name"
    
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 安装完成"
echo ""
echo "📋 验证方法："
echo "   ls -la ~/.hermes/hooks/workflow-*"
echo ""
echo "🧪 测试执行："
echo "   python3 ~/.hermes/hooks/workflow-status-check/handler.py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
