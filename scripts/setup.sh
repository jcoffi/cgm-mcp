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

# Create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi
}

# Activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Dependencies installed"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
    
    # Install development dependencies
    pip install pytest pytest-asyncio pytest-cov black isort mypy
    print_success "Development dependencies installed"
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
    print_status "Running tests..."
    
    if command -v pytest &> /dev/null; then
        pytest tests/ -v
        print_success "Tests completed"
    else
        print_error "pytest not found"
        exit 1
    fi
}

# Format code
format_code() {
    print_status "Formatting code..."
    
    # Format with black
    if command -v black &> /dev/null; then
        black src/ tests/ examples/ --line-length 88
        print_success "Code formatted with black"
    else
        print_warning "black not found, skipping formatting"
    fi
    
    # Sort imports with isort
    if command -v isort &> /dev/null; then
        isort src/ tests/ examples/ --profile black
        print_success "Imports sorted with isort"
    else
        print_warning "isort not found, skipping import sorting"
    fi
}

# Type checking
type_check() {
    print_status "Running type checks..."

    if command -v mypy &> /dev/null; then
        # Only check our code, exclude external libraries
        mypy src/cgm_mcp --ignore-missing-imports --exclude venv/ || {
            print_warning "Type checking found some issues, but continuing..."
        }
        print_success "Type checking completed"
    else
        print_warning "mypy not found, skipping type checking"
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
    echo "2. Activate virtual environment:"
    echo "   source venv/bin/activate"
    echo ""
    echo "3. Start the server:"
    echo "   python main.py"
    echo ""
    echo "4. Run tests:"
    echo "   pytest tests/"
    echo ""
    echo "5. Run examples:"
    echo "   python examples/example_usage.py"
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
