#!/bin/bash
# HoYoDeck 开发部署脚本
# 用法: ./scripts/deploy.sh
# 构建前端 + 同步到 Decky 插件目录，Decky debug 模式会自动热重载

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_DIR="$HOME/homebrew/plugins/hoyodeck"

# 复制函数：如果普通 cp 失败（权限不足），自动用 sudo
copy_file() {
    local src="$1" dst="$2"
    mkdir -p "$(dirname "$dst")"
    if ! cp "$src" "$dst" 2>/dev/null; then
        sudo cp "$src" "$dst"
    fi
}

echo "🔨 构建前端..."
cd "$PROJECT_DIR"
pnpm run build

echo "📦 同步到 Decky 插件目录..."
# 前端产物
copy_file dist/index.js "$PLUGIN_DIR/dist/index.js"

# Python 后端
copy_file main.py "$PLUGIN_DIR/main.py"
copy_file backend/__init__.py "$PLUGIN_DIR/backend/__init__.py"
copy_file backend/launcher.py "$PLUGIN_DIR/backend/launcher.py"
for f in backend/hoyodeck/*.py; do
    copy_file "$f" "$PLUGIN_DIR/$f"
done

# 配置文件（很少改动，通常不需要覆盖）
# copy_file plugin.json "$PLUGIN_DIR/plugin.json"
# copy_file package.json "$PLUGIN_DIR/package.json"

echo ""
echo "✅ 部署完成！Decky 将自动重载插件（debug 模式）"
echo "   查看日志: journalctl -u plugin_loader -b0 --no-pager | grep -i hoyodeck"
