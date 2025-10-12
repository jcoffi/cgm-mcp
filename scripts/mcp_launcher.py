#!/usr/bin/env python3
"""
Lightweight MCP launcher for CGM-MCP in OpenHands or similar environments.
- Installs the project editable if not already installed (uses uv if available, else pip)
- Loads .env selectively (no overrides)
- Sets defaults for provider/log level
- Launches the stdio MCP server via module import (no subprocess for efficiency)

This is optimized for spawning as an MCP server (e.g., in OpenHands config: command=python3, args=[/path/to/mcp_launcher.py]).
It assumes the repo is already cloned; for one-shot bootstrap, use run_mcp.sh instead.

Usage:
  python3 scripts/mcp_launcher.py  # In the repo root
  CGM_LLM_PROVIDER=openai CGM_LLM_API_KEY=... python3 scripts/mcp_launcher.py

For uvx one-shot from git (no clone needed):
  uvx -q --from git+https://github.com/jcoffi/cgm-mcp.git scripts/mcp_launcher.py
  CGM_LLM_PROVIDER=openai CGM_LLM_API_KEY=... uvx -q --from git+https://github.com/jcoffi/cgm-mcp.git scripts/mcp_launcher.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional

# ANSI colors
ANSI_BLUE = "\033[0;34m"
ANSI_GREEN = "\033[0;32m"
ANSI_YELLOW = "\033[1;33m"
ANSI_RED = "\033[0;31m"
ANSI_RESET = "\033[0m"

def log(color: str, level: str, msg: str):
    print(f"{color}[{level}]{ANSI_RESET} {msg}", file=sys.stderr)

def blue(msg): log(ANSI_BLUE, "INFO", msg)
def green(msg): log(ANSI_GREEN, "SUCCESS", msg)
def yellow(msg): log(ANSI_YELLOW, "WARNING", msg)
def red(msg): log(ANSI_RED, "ERROR", msg)

def run_command(cmd: list[str], check: bool = True, cwd: Optional[Path] = None, quiet: bool = False):
    kwargs = {"check": check, "cwd": cwd}
    if quiet:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    try:
        subprocess.run(cmd, **kwargs)
    except subprocess.CalledProcessError as e:
        if not quiet and e.stderr:
            print(e.stderr, file=sys.stderr)
        red(f"Command failed: {' '.join(cmd)} (exit {e.returncode})")
        sys.exit(1)

# Detect repo root (handle uvx git+from by checking for pyproject.toml)
repo_root = Path.cwd()
pyproject = repo_root / "pyproject.toml"
if not pyproject.exists():
    # For uvx --from git+, the script runs in a temp dir with the repo checked out
    # Assume current dir is the repo root if pyproject.toml is missing (uvx handles it)
    blue("Assuming uvx git+ mode; skipping root check.")
else:
    # Standard run: Ensure in repo
    if Path(__file__).parent.parent != repo_root:
        os.chdir(repo_root)
    if not pyproject.exists():
        red("Not in CGM-MCP repo root. Please run from the repo directory or use uvx --from git+.")
        sys.exit(1)

# Check if installed (try import)
try:
    import cgm_mcp
    blue("CGM-MCP already installed; skipping install.")
except ImportError:
    blue("Installing CGM-MCP editable...")
    # Prefer uv for speed (common in OpenHands/modern envs)
    if shutil.which("uv"):
        run_command(["uv", "pip", "install", "-e", "."], cwd=repo_root, quiet=True)
    else:
        run_command([sys.executable, "-m", "pip", "install", "-e", "."], cwd=repo_root, quiet=True)
    green("Installation complete.")

# Load .env selectively (use dotenv if available, else manual)
env_path = repo_root / ".env"
if env_path.exists():
    blue("Loading .env (without overriding existing env)...")
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=str(env_path), override=False)
        green(".env loaded.")
    except ImportError:
        # Manual fallback
        yellow("dotenv not available; manual .env parse.")
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key not in os.environ:
                        os.environ[key] = value
else:
    yellow(".env not found; relying on current environment.")

# Set defaults
if os.getenv("CGM_LLM_API_KEY"):
    os.environ["CGM_LLM_PROVIDER"] = os.getenv("CGM_LLM_PROVIDER", "openai")
else:
    os.environ["CGM_LLM_PROVIDER"] = os.getenv("CGM_LLM_PROVIDER", "mock")
os.environ["CGM_LOG_LEVEL"] = os.getenv("CGM_LOG_LEVEL", "INFO")

blue(f"Starting CGM MCP Server (provider={os.environ['CGM_LLM_PROVIDER']}, log={os.environ['CGM_LOG_LEVEL']})...")

# Launch server via direct import (efficient for MCP stdio)
from cgm_mcp.server import main
main()
