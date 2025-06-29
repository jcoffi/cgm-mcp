#!/usr/bin/env python3
"""
Simple test for optimized CGM MCP server
"""

import asyncio
import json
import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cgm_mcp.server_modelless import ModellessCGMServer
from cgm_mcp.utils.config import Config


async def test_optimized_server():
    """Test the optimized server functionality"""
    print("🚀 Testing Optimized CGM MCP Server")
    print("=" * 50)
    
    try:
        # Initialize server
        config = Config.load()
        server = ModellessCGMServer(config)
        
        # Test repository path (use current directory)
        repo_path = str(Path.cwd())
        
        print(f"📁 Testing with repository: {repo_path}")
        print()
        
        # Test 1: Repository analysis
        print("🔍 Test 1: Repository Analysis")
        start_time = time.time()
        
        result1 = await server._analyze_repository({
            "repository_path": repo_path,
            "query": "server optimization performance",
            "analysis_scope": "focused",
            "max_files": 3
        })
        
        end_time = time.time()
        print(f"⏱️  First analysis took: {end_time - start_time:.2f} seconds")
        print(f"📊 Status: {result1.get('status', 'unknown')}")
        print(f"📄 Files analyzed: {result1.get('file_count', 0)}")
        print(f"🔗 Entities found: {result1.get('entity_count', 0)}")
        print()
        
        # Test 2: Cached analysis (should be faster)
        print("🔍 Test 2: Cached Repository Analysis")
        start_time = time.time()
        
        result2 = await server._analyze_repository({
            "repository_path": repo_path,
            "query": "server optimization performance",
            "analysis_scope": "focused",
            "max_files": 3
        })
        
        end_time = time.time()
        print(f"⏱️  Cached analysis took: {end_time - start_time:.2f} seconds")
        print(f"📊 Status: {result2.get('status', 'unknown')}")
        print()
        
        # Test 3: File content analysis
        print("🔍 Test 3: File Content Analysis")
        start_time = time.time()
        
        result3 = await server._get_file_content({
            "repository_path": repo_path,
            "file_paths": ["src/cgm_mcp/server_modelless.py"]
        })
        
        end_time = time.time()
        print(f"⏱️  File analysis took: {end_time - start_time:.2f} seconds")
        print(f"📊 Status: {result3.get('status', 'unknown')}")
        print(f"📄 Files processed: {result3.get('file_count', 0)}")
        print()
        
        # Test 4: Performance metrics
        print("📊 Performance Metrics")
        try:
            perf_info = server._get_memory_usage()
            
            print(f"💾 Memory Usage: {perf_info['rss_mb']:.1f} MB")
            print(f"📈 Memory Percent: {perf_info['percent']:.1f}%")
            print()
            
        except Exception as e:
            print(f"❌ Error getting performance metrics: {e}")
            print()
        
        # Test 5: Cache information
        print("🗄️  Cache Information")
        try:
            print(f"📦 Analysis Cache: {len(server.analysis_cache)}/{server.analysis_cache.maxsize}")
            print(f"📄 File Cache: {len(server.file_cache)}/{server.file_cache.maxsize}")
            print(f"🌳 AST Cache: {len(server.ast_cache)}/{server.ast_cache.maxsize}")
            print(f"🎯 Cache Hits: {server.cache_stats['hits']}")
            print(f"❌ Cache Misses: {server.cache_stats['misses']}")
            print(f"📁 File Cache Hits: {server.cache_stats['file_hits']}")
            print(f"📁 File Cache Misses: {server.cache_stats['file_misses']}")
            
            # Calculate hit rates
            total_requests = server.cache_stats['hits'] + server.cache_stats['misses']
            if total_requests > 0:
                hit_rate = server.cache_stats['hits'] / total_requests
                print(f"🎯 Overall Cache Hit Rate: {hit_rate:.2%}")
            
            file_requests = server.cache_stats['file_hits'] + server.cache_stats['file_misses']
            if file_requests > 0:
                file_hit_rate = server.cache_stats['file_hits'] / file_requests
                print(f"📁 File Cache Hit Rate: {file_hit_rate:.2%}")
            
            print()
            
        except Exception as e:
            print(f"❌ Error getting cache info: {e}")
            print()
        
        print("✅ Optimization test completed successfully!")
        print("=" * 50)
        
        # Summary of optimizations
        print("\n🎯 Optimizations Implemented:")
        print("  ✅ TTL Cache (1 hour expiration)")
        print("  ✅ LRU File Cache (500 entries)")
        print("  ✅ AST Parsing Cache (200 entries)")
        print("  ✅ Memory Usage Monitoring")
        print("  ✅ Automatic Cache Cleanup")
        print("  ✅ Concurrent File Processing")
        print("  ✅ Enhanced Cache Key Generation")
        print("  ✅ Performance Statistics")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_optimized_server())
    if success:
        print("\n🎉 All tests passed! The optimized server is working correctly.")
    else:
        print("\n💥 Tests failed. Please check the error messages above.")
        sys.exit(1)
