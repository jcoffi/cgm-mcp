#EDIT: Add a single-command setup-and-run script for MCP server with optional GPU acceleration
#!/usr/bin/env bash

# One-shot setup and launch for CGM MCP (stdio) server.
# - Creates venv if missing
# - Installs dependencies (Torch GPU where available via requirements.txt)
# - Optionally installs CuPy for NVIDIA if CGM_INSTALL_CUPY=true
# - Loads .env if present, otherwise honors current environment
# - Starts the MCP stdio server (intended to be spawned by an MCP client)
#
# Usage examples:
#   ./scripts/run_mcp.sh                         # Use existing env/.env
#   CGM_LLM_PROVIDER=openai CGM_LLM_API_KEY=... ./scripts/run_mcp.sh
#   CGM_INSTALL_CUPY=true ./scripts/run_mcp.sh   # Attempt CuPy install for NVIDIA
#
# In Claude Desktop config, set command to bash and args to:
#   ["-lc", "/absolute/path/to/scripts/run_mcp.sh"]

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

blue()  { printf "\033[0;34m[INFO]\033[0m %s\n" "$*"; }
green() { printf "\033[0;32m[SUCCESS]\033[0m %s\n" "$*"; }
yellow(){ printf "\033[1;33m[WARNING]\033[0m %s\n" "$*"; }
red()   { printf "\033[0;31m[ERROR]\033[0m %s\n" "$*"; }

# # 1) Safety: avoid racing pip installs in ephemeral envs
# if pgrep -fa "(pip|python(3)? -m pip)" >/dev/null 2>&1; then
#   yellow "Detected background pip process. Waiting for it to finish..."
#   while pgrep -fa "(pip|python(3)? -m pip)" >/dev/null 2>&1; do sleep 2; done
#   green "Background pip finished. Proceeding."
# fi

# 2) Python check
if ! command -v python3 >/dev/null 2>&1; then
  red "python3 not found. Please install Python 3.8+"
  exit 1
fi

# 3) Create venv if needed
if [ ! -d venv ]; then
  blue "Creating virtual environment..."
  python3 -m venv venv
  green "Virtual environment created."
fi

# 4) Activate venv
# shellcheck disable=SC1091
source venv/bin/activate

# 5) Upgrade pip minimally (fast)
python -m pip install --upgrade --quiet pip

# 6) Install core deps (Torch wheel in requirements already selects GPU build when available)
blue "Installing dependencies..."
pip install -r requirements.txt

echo
# 7) Optional: NVIDIA CuPy for extra GPU acceleration
if [[ "${CGM_INSTALL_CUPY:-false}" == "true" ]]; then
  if command -v nvidia-smi >/dev/null 2>&1; then
    blue "Detected NVIDIA environment. Installing CuPy (CUDA 12.x)..."
    pip install cupy-cuda12x || yellow "CuPy install failed or unavailable; continuing without it."
  else
    yellow "CGM_INSTALL_CUPY=true but NVIDIA not detected (nvidia-smi not found). Skipping CuPy."
  fi
fi

echo
# 8) Load .env if present (does not override already-exported vars)
if [ -f .env ]; then
  blue "Loading .env (without overriding existing environment)..."
  # export only variables that are not already set in environment
  # shellcheck disable=SC2046
  set -a
  while IFS= read -r line; do
    # skip comments/empty
    [[ -z "$line" || "$line" == \#* ]] && continue
    key="${line%%=*}"
    if [ -z "${!key:-}" ]; then
      export "$line"
    fi
  done < .env
  set +a
  green ".env loaded (existing env vars preserved)."
else
  yellow ".env not found; relying on current environment."
fi

# # 9) Provider sanity: default to openai if API key provided; else keep existing or fallback to mock
# if [[ -n "${CGM_LLM_API_KEY:-}" ]]; then
#   export CGM_LLM_PROVIDER="${CGM_LLM_PROVIDER:-openai}"
# else
#   export CGM_LLM_PROVIDER="${CGM_LLM_PROVIDER:-mock}"
# fi
# export CGM_LOG_LEVEL="${CGM_LOG_LEVEL:-INFO}"

blue "Starting CGM MCP Server (log=$CGM_LOG_LEVEL)..."

# 10) Exec stdio MCP server. This process should be started by an MCP client (e.g., Claude Desktop),
# which will communicate over stdio. Running it standalone without a client will typically exit early.
exec python main.py --log-level "$CGM_LOG_LEVEL"
