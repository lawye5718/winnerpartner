#!/bin/bash

# Winner Partner 启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

# 检查是否已经创建了虚拟环境
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv "$PROJECT_DIR/venv"
    
    # 激活虚拟环境
    source "$PROJECT_DIR/venv/bin/activate"
    
    # 升级pip
    echo "升级pip..."
    pip install --upgrade pip
    
    # 安装依赖
    echo "安装依赖..."
    pip install -r "$PROJECT_DIR/requirements.txt"
else
    # 激活虚拟环境
    source "$PROJECT_DIR/venv/bin/activate"
fi

# 运行主程序
echo "启动 Winner Partner 主程序..."
cd "$PROJECT_DIR"
PYTHONPATH="$PROJECT_DIR/src" python src/main.py

echo "程序已退出"