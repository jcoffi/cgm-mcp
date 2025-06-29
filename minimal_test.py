#!/usr/bin/env python3
"""
Minimal test for optimized CGM MCP server components
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all optimized components can be imported"""
    print("🧪 Testing imports...")
    
    try:
        from cgm_mcp.server_modelless import ModellessCGMServer
        print("✅ ModellessCGMServer imported successfully")
        
        from cgm_mcp.core.analyzer_optimized import OptimizedCGMAnalyzer
        print("✅ OptimizedCGMAnalyzer imported successfully")
        
        from cgm_mcp.utils.config import Config
        print("✅ Config imported successfully")
        
        import cachetools
        print("✅ cachetools imported successfully")
        
        import psutil
        print("✅ psutil imported successfully")
        
        import aiofiles
        print("✅ aiofiles imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cache_creation():
    """Test cache creation"""
    print("\n🧪 Testing cache creation...")
    
    try:
        from cachetools import TTLCache, LRUCache
        
        # Test TTL cache
        ttl_cache = TTLCache(maxsize=100, ttl=3600)
        print("✅ TTL cache created successfully")
        
        # Test LRU cache
        lru_cache = LRUCache(maxsize=500)
        print("✅ LRU cache created successfully")
        
        # Test cache operations
        ttl_cache["test"] = "value"
        assert ttl_cache["test"] == "value"
        print("✅ Cache operations work correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        return False

def test_server_initialization():
    """Test server initialization"""
    print("\n🧪 Testing server initialization...")
    
    try:
        from cgm_mcp.server_modelless import ModellessCGMServer
        from cgm_mcp.utils.config import Config
        
        config = Config.load()
        server = ModellessCGMServer(config)
        
        # Check if caches are initialized
        assert hasattr(server, 'analysis_cache')
        assert hasattr(server, 'file_cache')
        assert hasattr(server, 'ast_cache')
        assert hasattr(server, 'cache_stats')
        
        print("✅ Server initialized with caches")
        
        # Check cache types
        from cachetools import TTLCache, LRUCache
        assert isinstance(server.analysis_cache, TTLCache)
        assert isinstance(server.file_cache, LRUCache)
        assert isinstance(server.ast_cache, LRUCache)
        
        print("✅ Cache types are correct")
        
        # Check cache stats
        assert 'hits' in server.cache_stats
        assert 'misses' in server.cache_stats
        assert 'file_hits' in server.cache_stats
        assert 'file_misses' in server.cache_stats
        
        print("✅ Cache statistics initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Server initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_monitoring():
    """Test memory monitoring functionality"""
    print("\n🧪 Testing memory monitoring...")
    
    try:
        from cgm_mcp.server_modelless import ModellessCGMServer
        from cgm_mcp.utils.config import Config
        
        config = Config.load()
        server = ModellessCGMServer(config)
        
        # Test memory usage function
        memory_info = server._get_memory_usage()
        
        assert 'rss_mb' in memory_info
        assert 'vms_mb' in memory_info
        assert 'percent' in memory_info
        
        print(f"✅ Memory monitoring works: {memory_info['rss_mb']:.1f}MB ({memory_info['percent']:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory monitoring failed: {e}")
        return False

def test_cache_key_generation():
    """Test cache key generation"""
    print("\n🧪 Testing cache key generation...")
    
    try:
        from cgm_mcp.server_modelless import ModellessCGMServer
        from cgm_mcp.utils.config import Config
        
        config = Config.load()
        server = ModellessCGMServer(config)
        
        # Test cache key generation
        key1 = server._generate_cache_key("path1", "query1", "scope1")
        key2 = server._generate_cache_key("path1", "query1", "scope1")
        key3 = server._generate_cache_key("path2", "query1", "scope1")
        
        assert key1 == key2  # Same inputs should generate same key
        assert key1 != key3  # Different inputs should generate different keys
        assert len(key1) == 32  # MD5 hash should be 32 characters
        
        print("✅ Cache key generation works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Cache key generation failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Minimal Test for CGM MCP Optimizations")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_cache_creation,
        test_server_initialization,
        test_memory_monitoring,
        test_cache_key_generation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print()
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Optimizations are working correctly.")
        print("\n💡 Key optimizations verified:")
        print("  ✅ TTL and LRU caching systems")
        print("  ✅ Memory usage monitoring")
        print("  ✅ Cache key generation")
        print("  ✅ Performance statistics tracking")
        print("  ✅ Enhanced server initialization")
        return True
    else:
        print(f"❌ {total - passed} tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
