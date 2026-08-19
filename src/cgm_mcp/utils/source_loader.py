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


def validate_repo_path(repo_path: str, allowed_root: Optional[str] = None) -> Optional[str]:
    """
    Validate and resolve a repository path.

    If allowed_root is set, the repo_path must resolve to a location within it.
    Returns the resolved canonical path, or None if validation fails.
    """
    if not repo_path:
        return None

    resolved = os.path.realpath(os.path.expanduser(repo_path))

    if not os.path.isdir(resolved):
        logger.warning(f"Repository path is not a directory: {repo_path}")
        return None

    if allowed_root:
        root_real = os.path.realpath(os.path.expanduser(allowed_root))
        if not (resolved == root_real or resolved.startswith(root_real + os.sep)):
            logger.warning(
                f"Repository path {resolved} is outside allowed root {root_real}"
            )
            return None

    return resolved


def resolve_repo_path(
    repository_name: str,
    repository_context: Optional[Dict] = None,
    allowed_root: Optional[str] = None,
) -> Optional[str]:
    """
    Resolve repository path using the same logic as GraphBuilder.

    Checks repository_context['path'] first, then tries common locations.
    Validates against allowed_root if configured.
    """
    if repository_context and "path" in repository_context:
        return validate_repo_path(repository_context["path"], allowed_root)

    # Try common locations (same as GraphBuilder._get_repository_path)
    possible_paths = [
        f"./{repository_name}",
        f"../{repository_name}",
        f"/tmp/{repository_name}",
        f"~/repositories/{repository_name}",
    ]

    for path in possible_paths:
        expanded = os.path.expanduser(path)
        if os.path.exists(expanded):
            return validate_repo_path(expanded, allowed_root)

    return None


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
    - Per-file byte limit (hard, reads binary then decodes)
    - Aggregate byte limit (hard, never exceeds)
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

            # Read binary to enforce hard byte limits
            remaining = max_total_bytes - total_bytes
            read_limit = min(max_file_bytes, remaining)

            with open(real_candidate, "rb") as f:
                raw = f.read(read_limit)

            content = raw.decode("utf-8", errors="ignore")
            contents[rel_path] = content
            total_bytes += len(raw)

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
