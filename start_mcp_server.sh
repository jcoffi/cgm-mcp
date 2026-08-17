#!/bin/bash

# CGM MCP Server 启动脚本
# 用于启动 CGM Model Context Protocol 服务器

set -e  # 遇到错误时退出

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 设置项目根目录
PROJECT_ROOT="$SCRIPT_DIR"
CONFIG_FILE="${CONFIG_FILE:-$PROJECT_ROOT/config.ollama_cloud.json}"
PYTHON_BIN="${CGM_PYTHON:-python3}"

echo "CGM MCP Server 启动脚本" >&2
echo "项目根目录: $PROJECT_ROOT" >&2
echo "配置文件: $CONFIG_FILE" >&2
echo >&2

# Optionally activate an explicitly provided virtual environment.
if [ -n "${CGM_VENV_PATH:-}" ]; then
    if [ ! -f "$CGM_VENV_PATH/bin/activate" ]; then
        echo "错误: 指定的虚拟环境不存在。" >&2
        exit 1
    fi
    source "$CGM_VENV_PATH/bin/activate"
fi

# Set the source path without overriding configuration supplied by the caller.
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Main loads the configuration file, preserving its environment-variable precedence.
CONFIG_ARGS=()
if [ -f "$CONFIG_FILE" ]; then
    CONFIG_ARGS=(--config "$CONFIG_FILE")
else
    echo "警告: 配置文件不存在，使用环境变量。" >&2
    export CGM_LLM_PROVIDER="${CGM_LLM_PROVIDER:-ollama_cloud}"
    export CGM_LLM_MODEL="${CGM_LLM_MODEL:-gemma4:cloud}"
    export CGM_LLM_API_BASE="${CGM_LLM_API_BASE:-https://ollama.com}"
fi

# 检查必要的依赖
echo "检查依赖..." >&2
"$PYTHON_BIN" -c "import sys, cgm_mcp.server; print('依赖检查通过', file=sys.stderr)" || {
    echo "错误: 依赖检查失败，请确保已安装 requirements.txt 中的所有依赖。" >&2
    exit 1
}
echo >&2

# 启动 MCP 服务器
echo "正在启动 CGM MCP Server..." >&2

# 设置标准输入输出环境，适合 MCP 使用
exec "$PYTHON_BIN" "$PROJECT_ROOT/main.py" "${CONFIG_ARGS[@]}"
