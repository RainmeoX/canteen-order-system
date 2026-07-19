#!/bin/bash
# 智能食堂预订系统 - Linux/Mac 一键启动脚本
set -e

cd "$(dirname "$0")"

echo "=============================================="
echo "   智能食堂预订系统 - 一键启动"
echo "=============================================="

# 找 Python
PYTHON=""
for cmd in python3 python; do
    if command -v $cmd &> /dev/null; then
        PYTHON=$cmd
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[错误] 未找到 Python，请先安装 Python 3.8+"
    exit 1
fi

echo "[OK] 使用 Python: $($PYTHON --version)"

# 安装依赖
echo "[INFO] 安装依赖..."
$PYTHON -m pip install -q flask flask-cors

# 初始化数据库
echo "[INFO] 初始化数据库..."
$PYTHON database/init_db.py

# 启动服务
echo "[INFO] 启动服务..."
echo ""
echo "=============================================="
echo "  用户端: http://localhost:5000"
echo "  管理端: http://localhost:5000/admin"
echo "  管理员 ID: admin_ma"
echo "=============================================="
echo ""

$PYTHON server/app.py
