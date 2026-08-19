"""
Source file loading utility for CGM MCP Server.

Loads bounded source content from repository files with path confinement,
symlink protection, file-count limits, and aggregate byte limits.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

# Limits
DEFAULT_MAX_FILES = 20
DEFAULT_MAX_FILE_BYTES = 100_000  # 100 KB per file
DEFAULT_MAX_TOTAL_BYTES = 500_000  # 500 KB aggregate


def load_file_contents(
    repo_path: str,
    file_paths: List[str],
    *,
    max_files: int = DEFAULT_MAX_FILES,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> Dict[str, str]:
    """
    Load source content for a list of repository-relative file paths.

    Enforces:
    - Canonical path confinement within repo_path
    - Symlink rejection (file must not be a symlink)
    - Per-file byte limit (truncates)
    - Aggregate byte limit (stops loading more files)
    - File count limit

    Returns a dict mapping relative_path -> file content (possibly truncated).
    """
    if not repo_path or not os.path.isdir(repo_path):
        logger.warning(f"Repository path not found or not a directory: {repo_path}")
        return {}

    repo_real = os.path.realpath(repo_path)
    contents: Dict[str, str] = {}
    total_bytes = 0

    for rel_path in file_paths[:max_files]:
        if total_bytes >= max_total_bytes:
            logger.info(
                f"Aggregate byte limit reached ({total_bytes}/{max_total_bytes}), "
                f"stopping file loading"
            )
            break

        try:
            candidate = os.path.join(repo_real, rel_path)
            real_candidate = os.path.realpath(candidate)

            # Path confinement check
            if not real_candidate.startswith(repo_real + os.sep) and real_candidate != repo_real:
                logger.warning(f"Path traversal rejected: {rel_path}")
                continue

            # Symlink rejection
            if os.path.islink(candidate):
                logger.warning(f"Symlink rejected: {rel_path}")
                continue

            if not os.path.isfile(real_candidate):
                logger.debug(f"File not found: {rel_path}")
                continue

            with open(real_candidate, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(max_file_bytes)

            contents[rel_path] = content
            total_bytes += len(content.encode("utf-8", errors="ignore"))

        except Exception as e:
            logger.warning(f"Failed to load file {rel_path}: {e}")
            continue

    return contents


def load_function_excerpt(
    file_content: str,
    line_start: int,
    line_end: int,
    context_lines: int = 5,
) -> str:
    """
    Extract a function excerpt from file content given line range.

    Adds context_lines before and after the function body.
    """
    lines = file_content.splitlines()
    start = max(0, line_start - 1 - context_lines)
    end = min(len(lines), line_end + context_lines)
    return "\n".join(lines[start:end])
