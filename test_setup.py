#!/usr/bin/env python3
"""
Quick setup test for CGM MCP
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test basic imports"""
    try:
        from cgm_mcp.models import CodeEntity, CodeAnalysisRequest
        print("✅ Models imported successfully")
        
        from cgm_mcp.core.analyzer import CGMAnalyzer
        print("✅ Analyzer imported successfully")
        
        from cgm_mcp.utils.config import Config
        print("✅ Config imported successfully")
        
        from cgm_mcp.utils.llm_client import LLMClient
        print("✅ LLM Client imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality"""
    try:
        from cgm_mcp.models import CodeEntity
        
        # Test model creation
        entity = CodeEntity(
            id="test:function:main",
            type="function",
            name="main",
            file_path="main.py"
        )
        print(f"✅ Created entity: {entity.name} ({entity.type})")
        
        # Test config
        from cgm_mcp.utils.config import Config
        config = Config()
        print(f"✅ Config loaded: {config.server_config.log_level}")
        
        return True
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False

async def test_analyzer():
    """Test analyzer functionality"""
    try:
        from cgm_mcp.core.analyzer import CGMAnalyzer
        from cgm_mcp.models import CodeAnalysisRequest
        
        analyzer = CGMAnalyzer()
        print("✅ Analyzer created")
        
        # Test with minimal scope on current directory
        request = CodeAnalysisRequest(
            repository_path=".",
            query="python files",
            analysis_scope="minimal",
            max_files=1
        )
        
        response = await analyzer.analyze_repository(request)
        print(f"✅ Analysis completed: {len(response.code_graph.files)} files found")
        print(f"   Entities: {len(response.relevant_entities)}")
        
        return True
    except Exception as e:
        print(f"❌ Analyzer test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🧪 CGM MCP Setup Test")
    print("=" * 40)
    
    # Test imports
    if not test_imports():
        return False
        
    print()
    
    # Test basic functionality
    if not test_basic_functionality():
        return False
        
    print()
    
    # Test analyzer
    if not await test_analyzer():
        return False
        
    print()
    print("🎉 All tests passed! CGM MCP is ready to use.")
    print()
    print("Next steps:")
    print("1. Start modelless server: python main_modelless.py")
    print("2. Or start with local model: ./scripts/start_local.sh")
    print("3. Test with examples: python examples/modelless_example.py")
    
    return True

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
