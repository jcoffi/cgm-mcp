#!/usr/bin/env python3
"""
Quick test to verify CGM MCP is working
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def quick_test():
    """Quick functionality test"""
    print("🚀 CGM MCP Quick Test")
    print("=" * 30)
    
    try:
        # Test imports
        from cgm_mcp.server_modelless import ModellessCGMServer
        from cgm_mcp.utils.config import Config
        print("✅ Imports successful")
        
        # Create server
        config = Config.load()
        server = ModellessCGMServer(config)
        print("✅ Server created")
        
        # Quick analysis test
        arguments = {
            "repository_path": ".",
            "query": "test",
            "analysis_scope": "minimal",
            "max_files": 1
        }
        
        print("🔍 Running quick analysis...")
        result = await server._analyze_repository(arguments)
        
        if result["status"] == "success":
            print(f"✅ Analysis successful!")
            print(f"   Files: {result['file_count']}")
            print(f"   Entities: {result['entity_count']}")
        else:
            print(f"❌ Analysis failed: {result['error']}")
            return False
            
        print("\n🎉 CGM MCP is working correctly!")
        print("\nReady to use:")
        print("• Start modelless server: python main_modelless.py")
        print("• Start with local model: ./scripts/start_local.sh")
        print("• Full demo: python examples/modelless_example.py --non-interactive")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    if not success:
        sys.exit(1)
