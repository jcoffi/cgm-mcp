#!/usr/bin/env bash
set -euo pipefail

# Default: install CUDA toolkit components via pip + CuPy + PyTorch
# Options:
#   MINIMAL=1   → CuPy-only (skip toolkit + torch)
#   NVCC=1      → add CUDA compiler
#   CUDNN=1     → add cuDNN

MINIMAL="${MINIMAL:-0}"
NVCC="${NVCC:-0}"
CUDNN="${CUDNN:-0}"

log(){ printf "[install] %s\n" "$*"; }
fail(){ printf "[error] %s\n" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || fail "Run as root."
command -v nvidia-smi >/dev/null || fail "nvidia-smi not visible; pass --gpus all."

SMI=$(nvidia-smi) || fail "nvidia-smi failed."
[[ "$SMI" =~ CUDA[[:space:]]Version:[[:space:]]*([0-9]+\.[0-9]+) ]] || fail "Cannot parse CUDA version."
CUDA_VER="${BASH_REMATCH[1]}"
CUDA_MAJOR="${CUDA_VER%%.*}"
CUDA_MINOR="${CUDA_VER#*.}"
log "Detected CUDA: ${CUDA_VER} (major=${CUDA_MAJOR}, minor=${CUDA_MINOR})"

command -v python3 >/dev/null || fail "python3 not found."
log "Upgrading pip tooling…"
python3 -m pip install -U --no-cache-dir pip setuptools wheel

# Select CuPy & Torch wheels
case "$CUDA_MAJOR" in
  12)
    CUPY_PKG="cupy-cuda12x"
    TORCH_PKG="torch==2.4.1+cu124"
    TORCH_INDEX="--extra-index-url https://download.pytorch.org/whl/cu124"
    ;;
  11)
    CUPY_PKG="cupy-cuda11x"
    TORCH_PKG="torch==2.4.1+cu118"
    TORCH_INDEX="--extra-index-url https://download.pytorch.org/whl/cu118"
    ;;
  *)
    fail "Unsupported CUDA major: ${CUDA_MAJOR}"
    ;;
esac

CUDA_PKGS=()
if [ "$MINIMAL" != "1" ]; then
  if [ "$CUDA_MAJOR" = "12" ]; then
    CUDA_PKGS=(
      nvidia-cuda-runtime-cu12
      nvidia-cuda-nvrtc-cu12
      nvidia-cuda-cupti-cu12
      nvidia-cublas-cu12
      nvidia-cufft-cu12
      nvidia-curand-cu12
      nvidia-cusolver-cu12
      nvidia-cusparse-cu12
      nvidia-nvjitlink-cu12
    )
    [ "$CUDNN" = "1" ] && CUDA_PKGS+=(nvidia-cudnn-cu12)
    [ "$NVCC" = "1" ] && CUDA_PKGS+=(nvidia-cuda-nvcc-cu12)
  else
    CUDA_PKGS=(
      nvidia-cuda-runtime-cu11
      nvidia-cuda-nvrtc-cu11
      nvidia-cuda-cupti-cu11
      nvidia-cublas-cu11
      nvidia-cufft-cu11
      nvidia-curand-cu11
      nvidia-cusolver-cu11
      nvidia-cusparse-cu11
    )
    [ "$CUDNN" = "1" ] && CUDA_PKGS+=(nvidia-cudnn-cu11)
    [ "$NVCC" = "1" ] && CUDA_PKGS+=(nvidia-cuda-nvcc-cu11)
  fi
  log "Installing CUDA components via pip: ${CUDA_PKGS[*]}"
  python3 -m pip install -U --no-cache-dir "${CUDA_PKGS[@]}"
else
  log "MINIMAL=1 → skipping toolkit + torch."
fi

log "Installing NumPy + CuPy: ${CUPY_PKG}"
python3 -m pip install -U --no-cache-dir numpy "${CUPY_PKG}"

if [ "$MINIMAL" != "1" ]; then
  log "Installing PyTorch: ${TORCH_PKG}"
  python3 -m pip install -U --no-cache-dir "${TORCH_PKG}" ${TORCH_INDEX}
fi

# Expose libs + nvcc if present
PY_SITE="$(python3 - <<'PY'
import site, sysconfig
paths=[]
try: paths+=site.getsitepackages()
except Exception: pass
paths+=[site.getusersitepackages()]
paths=[p for p in paths if p] or [sysconfig.get_paths()["purelib"]]
print(paths[0])
PY
)"
NVIDIA_DIR="${PY_SITE}/nvidia"
export LD_LIBRARY_PATH="${NVIDIA_DIR}:${NVIDIA_DIR}/cuda_runtime/lib:${LD_LIBRARY_PATH:-}"
[ -x "${NVIDIA_DIR}/cuda_nvcc/bin/nvcc" ] && export PATH="${NVIDIA_DIR}/cuda_nvcc/bin:${PATH}"

# CuPy smoke test
log "Verifying CuPy + CUDA…"
python3 - <<'PY'
import cupy as cp, cupy.cuda.runtime as rt
print("CuPy:", cp.__version__)
print("CUDA runtime:", rt.runtimeGetVersion(), "driver:", rt.driverGetVersion(), "devices:", rt.getDeviceCount())
assert rt.getDeviceCount()>0, "No CUDA device visible"
print("GPU sum:", float(cp.arange(10, dtype=cp.float32).sum()))
PY

if [ "$MINIMAL" != "1" ]; then
  log "Verifying PyTorch…"
  python3 - <<'PY'
import torch
print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("Torch device:", torch.cuda.get_device_name(0))
PY
fi

log "Done."
