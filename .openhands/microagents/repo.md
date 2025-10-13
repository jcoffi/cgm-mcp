# CGM MCP Server - Agent Instructions

MCP server for CodeFuse-CGM: Graph-Integrated LLM for repository-level software engineering tasks via Model Context Protocol.

**Project Type:** Python package, AI/ML tool, MCP server  
**Languages:** Python 3.8+  
**Frameworks:** FastAPI, Transformers, PyTorch, NetworkX  
**Size:** Medium (~2K files, GPU acceleration support)

## Build Instructions

### Bootstrap
```bash
# Install Python 3.8+ first
./scripts/setup.sh                    # Full setup with venv
source venv/bin/activate              # Activate environment  
cp .env.example .env                  # Configure environment
```

**Required:** Python 3.8+, pip. Setup script creates venv, installs all dependencies from requirements.txt, creates directories (logs/, cache/, data/), copies .env template.

**Reference:** scripts/setup.sh:39-254, README.md:280-535

### Run
```bash
# Standard MCP server
python main.py                       # Start with default config
python main.py --config config.json  # Custom configuration

# Model-agnostic mode (no LLM required)
./scripts/start_modelless.sh         # Pure analysis tools
python main_modelless.py             # Direct modelless start
```

**Environment:** Set CGM_LLM_API_KEY, CGM_LLM_PROVIDER in .env. Mock provider available for testing.

**Reference:** main.py:1-112, scripts/start_modelless.sh:47-146

### Lint
```bash
black src/ tests/ examples/ --line-length 88     # Code formatting
isort src/ tests/ examples/ --profile black      # Import sorting
mypy src/cgm_mcp --ignore-missing-imports        # Type checking
```

**Config:** pyproject.toml:74-91. Black line length 88, isort profile black, mypy excludes venv/.

### Test
```bash
pytest tests/ -v                     # Run all tests
pytest tests/test_basic.py -v        # Basic functionality tests
python -m pytest --tb=short          # Short traceback format
```

**Requirements:** pytest, pytest-asyncio, pytest-cov. Installed by setup script.

**Reference:** tests/test_basic.py:1-30, scripts/setup.sh:108-254

### Validate
```bash
# Check dependencies and GPU support
python check_gpu_dependencies.py     # Platform-specific GPU analysis
python project_status_check.py       # Project health check

# Full validation sequence
./scripts/setup.sh                   # Runs format, type check, tests
```

**Failures:** Setup script continues on mypy warnings. GPU dependencies optional but recommended.

**Timeouts:** Setup ~2-3 minutes, tests <30 seconds

## Project Layout

### Entry Points
- `main.py` - Primary MCP server entry point
- `main_modelless.py` - Model-agnostic server (no LLM needed)
- `src/cgm_mcp/server.py` - Core MCP server implementation
- `src/cgm_mcp/server_modelless.py` - Modelless server implementation

### Source Structure
- `src/cgm_mcp/` - Main package directory
  - `components/` - Core analysis components (graph_builder, rewriter, reader)
  - `core/` - Central analyzer and orchestration logic
  - `utils/` - Configuration, LLM client, helpers
  - `models.py` - Pydantic data models for requests/responses

### Configuration
- `config.json` - Default server configuration
- `config.local.json`, `config.lmstudio.json` - Environment-specific configs
- `.env.example` - Environment variables template
- `pyproject.toml` - Python package configuration, tool settings

### Validation Files
- `scripts/setup.sh` - Complete environment setup
- `scripts/start_*.sh` - Server startup scripts for different modes
- `requirements.txt` - Core dependencies
- `tests/` - Test suite (basic functionality, components)

### Documentation
- `README.md` - Full usage documentation and setup
- `docs/ARCHITECTURE.md` - System architecture details
- `examples/` - Usage examples for different scenarios

### Root Files
pyproject.toml, requirements.txt, main.py, main_modelless.py, .env.example, .gitignore, README.md, LICENSE, config.json, config.local.json, config.lmstudio.json, check_gpu_dependencies.py

**Pre-check-in:** Run `./scripts/setup.sh` (includes black, isort, mypy, pytest). Use mock LLM provider for testing without API keys.

**Dependencies:** PyTorch (GPU acceleration), NetworkX (graph processing), MCP protocol, FastAPI, Transformers. Optional: CuPy (NVIDIA), DirectML (AMD Windows).

**Critical Files:**
- `src/cgm_mcp/models.py:1-50` - Core data structures
- `src/cgm_mcp/server.py` - MCP protocol implementation  
- `scripts/setup.sh:39-254` - Environment setup procedures
- `main.py:1-112` - Server initialization and argument parsing

**Non-obvious:** Modelless mode works without LLM API keys. GPU acceleration auto-detected (MPS on Apple Silicon). Virtual environment required. Delete temporary files in logs/, cache/, data/ when no longer needed.

Use this file as the primary source of truth. Do not search the repo unless an instruction is missing or leads to an error.