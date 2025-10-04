#!/usr/bin/env python3
"""
Minimal dependency test for MCP tool exposure.
This test only requires the core MCP dependencies.
"""

import sys
import tempfile
import os
from pathlib import Path

# Add src to path  
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_minimal_import():
    """Test that we can import the essential components"""
    try:
        # Test basic MCP imports
        from mcp.server import Server
        from mcp.types import Tool
        print("✅ MCP imports successful")
        
        # Test that our server can be imported
        from cgm_mcp.server_modelless import ModellessCGMServer, cli, main
        print("✅ Server imports successful")
        
        # Test config
        from cgm_mcp.utils.config import Config
        config = Config()
        print("✅ Config creation successful")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_server_creation():
    """Test server creation with minimal config"""
    try:
        from cgm_mcp.server_modelless import ModellessCGMServer
        from cgm_mcp.utils.config import Config
        
        config = Config()
        server = ModellessCGMServer(config)
        
        print(f"✅ Server created: {server.server.name}")
        print(f"✅ Analyzer type: {type(server.analyzer).__name__}")
        
        return True
    except Exception as e:
        print(f"❌ Server creation error: {e}")
        return False

def test_entry_points():
    """Test that entry points are accessible"""
    try:
        from cgm_mcp.server_modelless import cli, main
        
        # Verify they are callable
        assert callable(cli), "cli should be callable"
        assert callable(main), "main should be callable"
        
        print("✅ Entry points are callable")
        print(f"  • cli: {cli}")
        print(f"  • main: {main}")
        
        return True
    except Exception as e:
        print(f"❌ Entry point error: {e}")
        return False

def main_test():
    """Run all minimal tests"""
    print("🧪 Minimal Dependency MCP Tool Test")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_minimal_import),
        ("Server Creation", test_server_creation), 
        ("Entry Points", test_entry_points)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔄 Running {test_name}...")
        try:
            result = test_func()
            results.append(result)
            if result:
                print(f"✅ {test_name} passed")
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} error: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 40)
    if all(results):
        print("🎉 ALL MINIMAL TESTS PASSED!")
        print("\nThis confirms that:")
        print("  • MCP server can be initialized")
        print("  • Tools should be available to agents")  
        print("  • Console scripts should work")
        print("  • uvx installation should work (with proper dependencies)")
    else:
        print("❌ Some tests failed")
        return False
        
    return True

if __name__ == "__main__":
    success = main_test()
    if not success:
        sys.exit(1)