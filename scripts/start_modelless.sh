#!/bin/bash

# CGM MCP Server - Model-agnostic Startup Script
# Starts the CGM server without any LLM dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
CONFIG_FILE=""
LOG_LEVEL="INFO"
CACHE_DIR=""
MAX_FILE_SIZE=""
PORT=8000

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --cache-dir)
            CACHE_DIR="$2"
            shift 2
            ;;
        --max-file-size)
            MAX_FILE_SIZE="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --config FILE         Configuration file path"
            echo "  --log-level LEVEL     Log level (DEBUG, INFO, WARNING, ERROR)"
            echo "  --cache-dir DIR       Cache directory path"
            echo "  --max-file-size SIZE  Maximum file size to analyze (bytes)"
            echo "  --port PORT           Server port [default: 8000]"
            echo "  --help                Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Start with defaults"
            echo "  $0 --log-level DEBUG                 # Enable debug logging"
            echo "  $0 --cache-dir /tmp/cgm_cache        # Use custom cache directory"
            echo "  $0 --max-file-size 2097152           # Limit files to 2MB"
            echo ""
            echo "Features:"
            echo "  • No LLM API keys required"
            echo "  • Pure code analysis tools"
            echo "  • Works with any external model"
            echo "  • High-performance caching"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_status "Starting CGM MCP Server (Model-agnostic)..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_error "Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Build command arguments
CMD_ARGS=()

if [ -n "$CONFIG_FILE" ]; then
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    CMD_ARGS+=(--config "$CONFIG_FILE")
fi

if [ -n "$LOG_LEVEL" ]; then
    CMD_ARGS+=(--log-level "$LOG_LEVEL")
fi

if [ -n "$CACHE_DIR" ]; then
    # Create cache directory if it doesn't exist
    mkdir -p "$CACHE_DIR"
    CMD_ARGS+=(--cache-dir "$CACHE_DIR")
fi

if [ -n "$MAX_FILE_SIZE" ]; then
    CMD_ARGS+=(--max-file-size "$MAX_FILE_SIZE")
fi

# Set environment variables
export CGM_SERVER_PORT="$PORT"

print_success "Configuration validated"
print_status "Mode: Model-agnostic (no LLM required)"
print_status "Log Level: $LOG_LEVEL"
print_status "Port: $PORT"

if [ -n "$CONFIG_FILE" ]; then
    print_status "Config: $CONFIG_FILE"
fi

if [ -n "$CACHE_DIR" ]; then
    print_status "Cache: $CACHE_DIR"
fi

if [ -n "$MAX_FILE_SIZE" ]; then
    print_status "Max File Size: $MAX_FILE_SIZE bytes"
fi

print_status "Available Tools:"
print_status "  • cgm_analyze_repository - Repository structure analysis"
print_status "  • cgm_get_file_content - Detailed file analysis"
print_status "  • cgm_find_related_code - Code relationship discovery"
print_status "  • cgm_extract_context - Context extraction for external models"

# Start the server
print_status "Starting server..."
python main_modelless.py "${CMD_ARGS[@]}"

print_success "CGM MCP Server (Model-agnostic) started successfully!"
