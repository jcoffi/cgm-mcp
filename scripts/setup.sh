#!/bin/bash

# CGM MCP Server Setup Script
# This script sets up the development environment for CGM MCP Server

set -e  # Exit on any error

echo "🚀 Setting up CGM MCP Server..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check Python version
check_python() {
    print_status "Checking Python version..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            print_success "Python $PYTHON_VERSION found"
        else
            print_error "Python 3.8+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.8+"
        exit 1
    fi
}

# Environment setup (uvx-based)
create_venv() {
    print_status "No local virtual environment will be created; using uv-based execution"
}

# Activate environment (uvx-based)
activate_venv() {
    print_status "No environment activation required; tools run via uv/uvx"
}

# Install dependencies (uv-based; no persistent install)
install_dependencies() {
    print_status "Skipping persistent dependency installation; use uv/uvx to run commands with resolved deps as needed"
}

# Setup environment file
setup_env() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Environment file created from template"
            print_warning "Please edit .env file with your API keys and configuration"
        else
            print_error ".env.example not found"
            exit 1
        fi
    else
        print_warning ".env file already exists"
    fi
}

# Run tests
run_tests() {
    print_status "Running tests via uvx..."
    if command -v uvx >/dev/null 2>&1; then
        uvx -q --from pytest pytest tests/ -v || {
            print_error "Tests failed"
            exit 1
        }
        print_success "Tests completed"
    else
        print_warning "uvx not found; skipping tests"
    fi
}

# Format code
format_code() {
    print_status "Formatting code via uvx..."
    if command -v uvx >/dev/null 2>&1; then
        uvx -q --from black black src/ tests/ examples/ --line-length 88
        BLACK_STATUS=$?
        uvx -q --from isort isort src/ tests/ examples/ --profile black
        ISORT_STATUS=$?
        if [ $BLACK_STATUS -eq 0 ] && [ $ISORT_STATUS -eq 0 ]; then
            print_success "Formatting completed"
        else
            if [ $BLACK_STATUS -ne 0 ] && [ $ISORT_STATUS -ne 0 ]; then
                print_warning "Both black and isort encountered issues"
            elif [ $BLACK_STATUS -ne 0 ]; then
                print_warning "black encountered issues"
            elif [ $ISORT_STATUS -ne 0 ]; then
                print_warning "isort encountered issues"
            fi
        fi
    else
        print_warning "uvx not found; skipping formatting"
    fi
}

# Type checking
type_check() {
    print_status "Running type checks via uvx..."
    if command -v uvx >/dev/null 2>&1; then
        if uvx -q --from mypy mypy src/cgm_mcp --ignore-missing-imports; then
            print_success "Type checking completed successfully"
        else
            print_warning "Type checking found some issues, but continuing..."
        fi
    else
        print_warning "uvx not found; skipping type checking"
    fi
}

# Create directories
create_directories() {
    print_status "Creating project directories..."
    
    mkdir -p logs
    mkdir -p data
    mkdir -p cache
    
    print_success "Project directories created"
}

# Display usage information
show_usage() {
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your API keys:"
    echo "   nano .env"
    echo ""
    echo "2. Start the server (modelless):"
    echo "   uvx -q --from . cgm-mcp-modelless"
    echo ""
    echo "3. Start the server (with LLM provider):"
    echo "   uvx -q --from . cgm-mcp"
    echo ""
    echo "4. Run tests:"
    echo "   uvx -q --from pytest pytest tests/"
    echo ""
    echo "5. Run examples:"
    echo "   uv run python examples/example_usage.py"
    echo ""
    echo "For more information, see README.md"
}

# Main setup function
main() {
    echo "CGM MCP Server Setup"
    echo "===================="
    echo ""
    
    # Parse command line arguments
    SKIP_TESTS=false
    SKIP_FORMAT=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --skip-format)
                SKIP_FORMAT=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --skip-tests    Skip running tests"
                echo "  --skip-format   Skip code formatting"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Run setup steps
    check_python
    create_venv
    activate_venv
    install_dependencies
    setup_env
    create_directories
    
    if [ "$SKIP_FORMAT" = false ]; then
        format_code
        type_check
    fi
    
    if [ "$SKIP_TESTS" = false ]; then
        run_tests
    fi
    
    show_usage
}

# Run main function
main "$@"
