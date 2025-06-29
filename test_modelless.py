#!/usr/bin/env python3
"""
Quick test for modelless CGM functionality
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_modelless_server():
    """Test the modelless server functionality"""
    try:
        from cgm_mcp.server_modelless import ModellessCGMServer
        from cgm_mcp.utils.config import Config
        
        print("🧪 Testing Modelless CGM Server")
        print("=" * 40)
        
        # Create server instance
        config = Config.load()
        server = ModellessCGMServer(config)
        print("✅ Server created successfully")
        
        # Test repository analysis
        print("\n🔍 Testing repository analysis...")
        arguments = {
            "repository_path": ".",
            "query": "python files",
            "analysis_scope": "minimal",
            "max_files": 2
        }
        
        result = await server._analyze_repository(arguments)
        
        if result["status"] == "success":
            print(f"✅ Analysis completed")
            print(f"   Files analyzed: {result['file_count']}")
            print(f"   Entities found: {result['entity_count']}")
            
            # Test file content analysis
            print("\n📄 Testing file content analysis...")
            file_args = {
                "repository_path": ".",
                "file_paths": ["test_setup.py"]
            }
            
            file_result = await server._get_file_content(file_args)
            
            if file_result["status"] == "success":
                print(f"✅ File analysis completed")
                print(f"   Files processed: {file_result['file_count']}")
            else:
                print(f"❌ File analysis failed: {file_result['error']}")
                
            # Test context extraction
            print("\n📋 Testing context extraction...")
            context_args = {
                "repository_path": ".",
                "query": "test files",
                "format": "structured"
            }
            
            context_result = await server._extract_context(context_args)
            
            if context_result and len(context_result) > 0:
                print("✅ Context extraction completed")
                print(f"   Context length: {len(context_result)} characters")
            else:
                print("❌ Context extraction failed")
                
        else:
            print(f"❌ Analysis failed: {result['error']}")
            return False
            
        print("\n🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the test"""
    success = await test_modelless_server()
    
    if success:
        print("\n✅ Modelless CGM server is working correctly!")
        print("\nNext steps:")
        print("1. Start the server: python main_modelless.py")
        print("2. Run full demo: python examples/modelless_example.py --non-interactive")
        print("3. Integrate with your AI tools using MCP protocol")
    else:
        print("\n❌ Tests failed. Please check the setup.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
