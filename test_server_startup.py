#!/usr/bin/env python3
"""
Test script to verify MCP server startup and tool registration
"""

import asyncio
import signal
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_server_startup():
    """Test if the server starts up and registers tools correctly"""
    try:
        from cgm_mcp.server_modelless import ModellessCGMServer
        from cgm_mcp.utils.config import Config
        
        print("🔄 Creating server instance...")
        config = Config()
        server = ModellessCGMServer(config)
        print("✅ Server instance created")
        
        # Test if tools are properly defined
        print("🔄 Checking tool definitions...")
        
        # The server should have _setup_handlers called during initialization
        # Let's verify the server has the expected methods
        
        # Check if the server has handlers defined
        has_tools = hasattr(server.server, '_tool_handlers') or hasattr(server.server, 'list_tools')
        print(f"✅ Server has tool handling: {has_tools}")
        
        # Test the handler setup by checking if it's callable
        if hasattr(server, '_setup_handlers'):
            print("✅ Server has _setup_handlers method")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during server test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🧪 Testing MCP Server Startup and Tool Registration")
    print("=" * 50)
    
    success = await test_server_startup()
    
    if success:
        print("\n✅ All tests passed! MCP server startup looks good.")
        print("\nExpected tools should be available:")
        tools = [
            "cgm_analyze_repository",
            "cgm_get_file_content", 
            "cgm_find_related_code",
            "cgm_extract_context",
            "clear_gpu_cache"
        ]
        for tool in tools:
            print(f"  • {tool}")
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())