#!/usr/bin/env python3
from __future__ import annotations

"""
Install CuPy and PyTorch matching the locally installed CUDA version (detected via nvidia-smi).

Behavior:
- Detect CUDA version with `nvidia-smi`.
- Choose package variants:
  - CuPy: cupy-cuda12x for CUDA 12.x, cupy-cuda11x for CUDA 11.x
  - PyTorch: use official wheel index URLs:
      CUDA 12.4+ -> cu124
      CUDA 12.0–12.3 -> cu121 (closest supported)
      CUDA 11.x -> cu118
- Use the current Python interpreter (sys.executable), not the system default.
- Optionally supports --dry-run to print commands without executing.

Notes:
- Requires `nvidia-smi` to be present and visible on PATH.
- If you run this inside a virtual environment, packages will install there.
"""

import argparse
import os
import re
import shlex
import subprocess
import sys
from typing import Optional, Tuple


def run(cmd: list[str], dry_run: bool = False) -> int:
    print("=>", " ".join(shlex.quote(c) for c in cmd))
    if dry_run:
        return 0
    proc = subprocess.run(cmd)
    return proc.returncode


def get_cuda_version() -> Tuple[int, int]:
    """Parse CUDA version (major, minor) from `nvidia-smi` output.

    Returns:
        (major, minor)
    Raises:
        RuntimeError if CUDA version cannot be determined.
    """
    try:
        out = subprocess.check_output(["nvidia-smi"], stderr=subprocess.STDOUT, text=True)
    except FileNotFoundError as e:
        raise RuntimeError("nvidia-smi not found on PATH. Is the NVIDIA driver installed?") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to run nvidia-smi: {e.output}") from e

    # Example line: "| NVIDIA-SMI 555.42.02    Driver Version: 555.42.02    CUDA Version: 12.4 |"
    m = re.search(r"CUDA\s+Version:\s*([0-9]+)\.([0-9]+)", out)
    if not m:
        raise RuntimeError("Unable to detect CUDA version from nvidia-smi output")
    major, minor = int(m.group(1)), int(m.group(2))
    return major, minor


def choose_cupy_package(cuda_major: int, cuda_minor: int) -> str:
    if cuda_major >= 12:
        return "cupy-cuda12x"
    if cuda_major == 11:
        return "cupy-cuda11x"
    # Fallback (may build from source; not recommended). Better to install CUDA 11/12.
    return "cupy"


def choose_torch_index(cuda_major: int, cuda_minor: int) -> str:
    # Mapping aligned with official PyTorch wheels
    # https://pytorch.org/get-started/locally/
    if cuda_major >= 12:
        if cuda_minor >= 4:
            return "https://download.pytorch.org/whl/cu124"
        else:
            # Covers 12.0–12.3
            return "https://download.pytorch.org/whl/cu121"
    elif cuda_major == 11:
        return "https://download.pytorch.org/whl/cu118"
    else:
        # CPU-only fallback
        return "https://download.pytorch.org/whl/cpu"


def install_system_packages(dry_run: bool) -> None:
    """Install system packages using apt."""
    print("Installing system packages...")
    run(["apt", "update"], dry_run)
    run(["apt", "install", "-y", "graphviz", "libgraphviz-dev"], dry_run)


def install_packages(cupy_pkg: str, torch_index: str, dry_run: bool) -> None:
    py = sys.executable
    print(f"Using Python interpreter: {py}")

    # Install system packages first
    install_system_packages(dry_run)

    # Upgrade pip first
    run([py, "-m", "pip", "install", "-U", "pip"], dry_run)

    # Install CuPy (latest compatible wheel for that CUDA line)
    run([py, "-m", "pip", "install", "-U", cupy_pkg], dry_run)

    # Install PyTorch and extras from the correct index
    run([py, "-m", "pip", "install", "-U", "torch", "torchvision", "torchaudio", "--index-url", torch_index], dry_run)


def verify_install() -> None:
    print("\nVerifying CuPy...")
    try:
        import cupy as cp  # type: ignore
        from cupy import cuda as cpcuda  # type: ignore
        print("CuPy:", cp.__version__)
        print("CuPy CUDA runtime version:", cpcuda.runtime.runtimeGetVersion())
        print("CUDA devices:", cpcuda.runtime.getDeviceCount())
    except Exception as e:
        print("CuPy verification failed:", e)

    print("\nVerifying PyTorch...")
    try:
        import torch  # type: ignore
        print("Torch:", torch.__version__)
        print("Torch CUDA:", torch.version.cuda)
        print("CUDA available:", torch.cuda.is_available())
        if torch.cuda.is_available():
            print("Device:", torch.cuda.get_device_name(0))
    except Exception as e:
        print("PyTorch verification failed:", e)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="Print actions without installing")
    args = p.parse_args(argv)

    try:
        major, minor = get_cuda_version()
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    print(f"Detected CUDA version: {major}.{minor}")

    cupy_pkg = choose_cupy_package(major, minor)
    torch_index = choose_torch_index(major, minor)

    print(f"Selected CuPy package: {cupy_pkg}")
    print(f"Selected PyTorch index: {torch_index}")

    install_packages(cupy_pkg, torch_index, args.dry_run)

    if not args.dry_run:
        verify_install()

    print("\nDone.")
    return 0


def main():
    """Entry point for the install_cuda_stack script"""
    import sys
    raise SystemExit(_main(sys.argv[1:]))


def _main(argv=None):
    """Internal main function"""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="Print actions without installing")
    args = p.parse_args(argv)

    try:
        major, minor = get_cuda_version()
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    print(f"Detected CUDA version: {major}.{minor}")

    cupy_pkg = choose_cupy_package(major, minor)
    torch_index = choose_torch_index(major, minor)

    print(f"Selected CuPy package: {cupy_pkg}")
    print(f"Selected PyTorch index: {torch_index}")

    install_packages(cupy_pkg, torch_index, args.dry_run)

    if not args.dry_run:
        verify_install()

    print("\nDone.")
    return 0


if __name__ == "__main__":
    main()
