#!/usr/bin/env python3
"""
GPU Dependencies Checker for CGM MCP Server
Provides platform-specific recommendations for optimal GPU performance
"""

import platform
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def detect_system_platform():
    """Detect system platform and hardware"""
    system = platform.system()
    machine = platform.machine()
    
    if system == "Darwin" and machine == "arm64":
        return "Apple Silicon"
    elif system == "Darwin" and machine == "x86_64":
        return "Intel Mac"
    elif system == "Windows":
        return "Windows"
    elif system == "Linux":
        return "Linux"
    else:
        return "Unknown"


def check_pytorch_installation():
    """Check PyTorch installation and GPU support"""
    try:
        import torch
        pytorch_version = torch.__version__
        
        # Check different GPU backends
        backends = {
            "CUDA": torch.cuda.is_available() if hasattr(torch, 'cuda') else False,
            "MPS": torch.backends.mps.is_available() if hasattr(torch.backends, 'mps') else False,
        }
        
        return True, pytorch_version, backends
    except ImportError:
        return False, None, {}


def check_optional_dependencies():
    """Check optional GPU dependencies"""
    dependencies = {}
    
    # Check CuPy
    try:
        import cupy
        dependencies["CuPy"] = cupy.__version__
    except ImportError:
        dependencies["CuPy"] = None
    
    # Check DirectML
    try:
        import torch_directml
        dependencies["DirectML"] = "Available"
    except ImportError:
        dependencies["DirectML"] = None
    
    return dependencies


def get_platform_recommendations(platform_type):
    """Get platform-specific recommendations"""
    recommendations = {
        "Apple Silicon": {
            "required": ["torch (with MPS support)"],
            "optional": [],
            "not_needed": ["cupy", "torch-directml"],
            "install_cmd": "pip install torch torchvision torchaudio",
            "notes": [
                "✅ MPS (Metal Performance Shaders) provides excellent GPU acceleration",
                "✅ Unified memory architecture for fast data transfer",
                "✅ No additional GPU libraries needed",
                "ℹ️  CuPy warnings can be safely ignored"
            ]
        },
        "Intel Mac": {
            "required": ["torch"],
            "optional": ["cupy (if NVIDIA eGPU)"],
            "not_needed": ["torch-directml"],
            "install_cmd": "pip install torch torchvision torchaudio",
            "notes": [
                "⚠️  Limited GPU acceleration on Intel Macs",
                "✅ NVIDIA eGPU supported with CUDA",
                "💡 Consider upgrading to Apple Silicon for better performance"
            ]
        },
        "Windows": {
            "required": ["torch"],
            "optional": ["cupy-cuda11x/cupy-cuda12x (NVIDIA)", "torch-directml (AMD)"],
            "not_needed": [],
            "install_cmd": {
                "NVIDIA": "pip install torch --index-url https://download.pytorch.org/whl/cu118",
                "AMD": "pip install torch-directml",
                "CPU": "pip install torch torchvision torchaudio"
            },
            "notes": [
                "🎯 Best platform for NVIDIA GPU acceleration",
                "✅ AMD GPU support via DirectML",
                "💡 Install GPU-specific PyTorch version for best performance"
            ]
        },
        "Linux": {
            "required": ["torch"],
            "optional": ["cupy-cuda11x/cupy-cuda12x (NVIDIA)", "torch with ROCm (AMD)"],
            "not_needed": ["torch-directml"],
            "install_cmd": {
                "NVIDIA": "pip install torch --index-url https://download.pytorch.org/whl/cu118",
                "AMD": "pip install torch --index-url https://download.pytorch.org/whl/rocm5.6",
                "CPU": "pip install torch torchvision torchaudio"
            },
            "notes": [
                "🚀 Excellent support for both NVIDIA and AMD GPUs",
                "✅ ROCm provides native AMD GPU acceleration",
                "💡 Best platform for AMD GPU performance"
            ]
        }
    }
    
    return recommendations.get(platform_type, {})


def main():
    """Main dependency checker"""
    print("🔍 CGM MCP GPU Dependencies Checker")
    print("=" * 50)
    
    # Detect platform
    platform_type = detect_system_platform()
    print(f"🖥️  Platform: {platform_type}")
    print(f"📊 System: {platform.system()} {platform.machine()}")
    print()
    
    # Check PyTorch
    pytorch_ok, pytorch_version, backends = check_pytorch_installation()
    
    print("📦 PyTorch Status:")
    if pytorch_ok:
        print(f"   ✅ PyTorch {pytorch_version} installed")
        for backend, available in backends.items():
            status = "✅ Available" if available else "❌ Not available"
            print(f"   {backend}: {status}")
    else:
        print("   ❌ PyTorch not installed")
    print()
    
    # Check optional dependencies
    optional_deps = check_optional_dependencies()
    print("🔧 Optional Dependencies:")
    for dep, version in optional_deps.items():
        if version:
            print(f"   ✅ {dep}: {version}")
        else:
            print(f"   ❌ {dep}: Not installed")
    print()
    
    # Get recommendations
    recommendations = get_platform_recommendations(platform_type)
    
    if recommendations:
        print("💡 Platform-Specific Recommendations:")
        print("=" * 50)
        
        print("📋 Required Dependencies:")
        for dep in recommendations.get("required", []):
            print(f"   • {dep}")
        
        if recommendations.get("optional"):
            print("\n🔧 Optional Dependencies (for enhanced performance):")
            for dep in recommendations.get("optional", []):
                print(f"   • {dep}")
        
        if recommendations.get("not_needed"):
            print("\n🚫 Not Needed on This Platform:")
            for dep in recommendations.get("not_needed", []):
                print(f"   • {dep}")
        
        print("\n📥 Installation Commands:")
        install_cmd = recommendations.get("install_cmd", "")
        if isinstance(install_cmd, dict):
            for gpu_type, cmd in install_cmd.items():
                print(f"   {gpu_type}: {cmd}")
        else:
            print(f"   {install_cmd}")
        
        print("\n📝 Notes:")
        for note in recommendations.get("notes", []):
            print(f"   {note}")
    
    # Current status summary
    print("\n" + "=" * 50)
    print("📊 CURRENT STATUS SUMMARY")
    print("=" * 50)
    
    if platform_type == "Apple Silicon":
        if backends.get("MPS", False):
            print("🎉 OPTIMAL: Apple Silicon GPU acceleration is active!")
            print("   • MPS backend enabled")
            print("   • No additional dependencies needed")
            print("   • CuPy warnings can be ignored")
        else:
            print("⚠️  SUBOPTIMAL: MPS not available")
            print("   • Update PyTorch to latest version")
            print("   • Ensure macOS 12.3+ for MPS support")
    
    elif platform_type in ["Windows", "Linux"]:
        if backends.get("CUDA", False):
            print("🎉 GOOD: CUDA GPU acceleration available!")
            if optional_deps.get("CuPy"):
                print("   • CuPy installed for enhanced performance")
            else:
                print("   • Consider installing CuPy for additional features")
        elif optional_deps.get("DirectML"):
            print("🎉 GOOD: DirectML GPU acceleration available!")
        else:
            print("⚠️  CPU ONLY: No GPU acceleration detected")
            print("   • Install GPU-specific PyTorch version")
            print("   • Check GPU drivers")
    
    print("\n🎯 For CGM MCP Server:")
    print("   • GPU acceleration will work automatically when available")
    print("   • CPU fallback ensures compatibility on all systems")
    print("   • Performance scales with available hardware")


if __name__ == "__main__":
    main()
