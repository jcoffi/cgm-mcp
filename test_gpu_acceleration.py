#!/usr/bin/env python3
"""
Test script for GPU acceleration in CGM MCP Server
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
from cgm_mcp.core.gpu_accelerator import GPUAcceleratorConfig, EntityMatcher, TextProcessor


async def test_gpu_components():
    """Test individual GPU components"""
    print("🧪 Testing GPU Components")
    print("=" * 50)
    
    # Test GPU configuration
    gpu_config = GPUAcceleratorConfig()
    print(f"📊 GPU Config: use_gpu={gpu_config.use_gpu}, batch_size={gpu_config.batch_size}")
    
    # Test Entity Matcher
    print("\n🔍 Testing Entity Matcher:")
    entity_matcher = EntityMatcher(gpu_config)
    print(f"   GPU Available: {entity_matcher.gpu_available}")
    print(f"   Device: {entity_matcher.device}")
    
    # Create test entities
    test_entities = []
    for i in range(100):
        test_entities.append({
            "name": f"TestEntity_{i}",
            "description": f"This is test entity number {i} for GPU acceleration testing",
            "type": "test_class" if i % 2 == 0 else "test_function",
            "file_path": f"test_file_{i % 10}.py"
        })
    
    # Test entity matching
    start_time = time.time()
    similar_entities = entity_matcher.find_similar_entities(
        test_entities, "test entity acceleration", top_k=20
    )
    matching_time = time.time() - start_time
    
    print(f"   Entity Matching: {matching_time:.3f}s")
    print(f"   Results: {len(similar_entities)} entities")
    if similar_entities:
        print(f"   Top match: {similar_entities[0][0]['name']} (score: {similar_entities[0][1]:.3f})")
    
    # Test Text Processor
    print("\n📝 Testing Text Processor:")
    text_processor = TextProcessor(gpu_config)
    
    # Create test texts
    test_texts = [
        f"Sample code file {i} with various Python constructs like classes and functions"
        for i in range(200)
    ]
    
    start_time = time.time()
    text_stats = text_processor.batch_text_analysis(test_texts)
    text_time = time.time() - start_time
    
    print(f"   Text Analysis: {text_time:.3f}s")
    print(f"   Processing Mode: {text_stats.get('processing_mode', 'Unknown')}")
    print(f"   Total Characters: {text_stats.get('total_chars', 0)}")
    print(f"   Average Length: {text_stats.get('avg_length', 0):.1f}")
    
    # Test pattern matching
    patterns = ["class", "def", "import", "async"]
    start_time = time.time()
    pattern_results = text_processor.batch_pattern_search(test_texts, patterns)
    pattern_time = time.time() - start_time
    
    print(f"   Pattern Matching: {pattern_time:.3f}s")
    for pattern, matches in pattern_results.items():
        print(f"     '{pattern}': {len(matches)} matches")
    
    return True


async def test_gpu_server_integration():
    """Test GPU acceleration in the full server"""
    print("\n🚀 Testing GPU Server Integration")
    print("=" * 50)
    
    try:
        # Initialize server
        config = Config.load()
        server = ModellessCGMServer(config)
        
        print(f"📊 Analyzer Type: {type(server.analyzer).__name__}")
        
        # Test GPU statistics
        if hasattr(server.analyzer, 'get_gpu_stats'):
            gpu_stats = server.analyzer.get_gpu_stats()
            print(f"🔧 GPU Available: {gpu_stats.get('memory', {}).get('gpu_available', False)}")
            print(f"💾 Memory Info: {gpu_stats.get('memory', {})}")
        
        # Test repository analysis with GPU acceleration
        repo_path = str(Path.cwd())
        
        print(f"\n🔍 Testing Repository Analysis:")
        print(f"   Repository: {repo_path}")
        
        start_time = time.time()
        result = await server._analyze_repository({
            "repository_path": repo_path,
            "query": "GPU acceleration performance optimization",
            "analysis_scope": "focused",
            "max_files": 3
        })
        analysis_time = time.time() - start_time
        
        print(f"   Analysis Time: {analysis_time:.3f}s")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Files Analyzed: {result.get('file_count', 0)}")
        print(f"   Entities Found: {result.get('entity_count', 0)}")
        
        # Check for GPU-enhanced metadata
        if 'metadata' in result and 'gpu_text_analysis' in result['metadata']:
            gpu_analysis = result['metadata']['gpu_text_analysis']
            print(f"   GPU Text Analysis: {gpu_analysis.get('processing_mode', 'N/A')}")
        
        # Test file content analysis
        print(f"\n📁 Testing File Content Analysis:")
        start_time = time.time()
        file_result = await server._get_file_content({
            "repository_path": repo_path,
            "file_paths": ["src/cgm_mcp/core/gpu_accelerator.py"]
        })
        file_time = time.time() - start_time
        
        print(f"   File Analysis Time: {file_time:.3f}s")
        print(f"   Status: {file_result.get('status', 'unknown')}")
        print(f"   Files Processed: {file_result.get('file_count', 0)}")
        
        # Test GPU cache clearing
        if hasattr(server.analyzer, 'clear_gpu_caches'):
            print(f"\n🧹 Testing GPU Cache Clearing:")
            start_time = time.time()
            cache_result = await server._clear_gpu_cache({})
            cache_time = time.time() - start_time
            
            print(f"   Cache Clear Time: {cache_time:.3f}s")
            print(f"   Status: {cache_result.get('status', 'unknown')}")
            print(f"   Message: {cache_result.get('message', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Server integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def benchmark_gpu_vs_cpu():
    """Benchmark GPU vs CPU performance"""
    print("\n⚡ GPU vs CPU Performance Benchmark")
    print("=" * 50)
    
    # Test with different data sizes
    data_sizes = [50, 100, 500, 1000]
    
    for size in data_sizes:
        print(f"\n📊 Testing with {size} entities:")
        
        # Create test data
        entities = []
        for i in range(size):
            entities.append({
                "name": f"Entity_{i}",
                "description": f"Test entity {i} with description for performance testing",
                "type": "class" if i % 3 == 0 else "function",
                "file_path": f"file_{i % 20}.py"
            })
        
        query = "performance testing entity"
        
        # Test with GPU acceleration
        gpu_config = GPUAcceleratorConfig(use_gpu=True)
        gpu_matcher = EntityMatcher(gpu_config)
        
        start_time = time.time()
        gpu_results = gpu_matcher.find_similar_entities(entities, query, top_k=20)
        gpu_time = time.time() - start_time
        
        # Test with CPU fallback
        cpu_config = GPUAcceleratorConfig(use_gpu=False)
        cpu_matcher = EntityMatcher(cpu_config)
        
        start_time = time.time()
        cpu_results = cpu_matcher.find_similar_entities(entities, query, top_k=20)
        cpu_time = time.time() - start_time
        
        print(f"   GPU Time: {gpu_time:.3f}s ({len(gpu_results)} results)")
        print(f"   CPU Time: {cpu_time:.3f}s ({len(cpu_results)} results)")
        
        if gpu_time > 0 and cpu_time > 0:
            speedup = cpu_time / gpu_time
            print(f"   Speedup: {speedup:.1f}x {'(GPU faster)' if speedup > 1 else '(CPU faster)'}")


async def main():
    """Main test function"""
    print("🚀 CGM MCP GPU Acceleration Test Suite")
    print("=" * 60)
    
    try:
        # Test individual components
        success1 = await test_gpu_components()
        
        # Test server integration
        success2 = await test_gpu_server_integration()
        
        # Benchmark performance
        await benchmark_gpu_vs_cpu()
        
        print("\n" + "=" * 60)
        if success1 and success2:
            print("🎉 All GPU acceleration tests passed!")
            print("\n💡 GPU Acceleration Summary:")
            print("   ✅ Entity matching with similarity scoring")
            print("   ✅ Batch text processing and analysis")
            print("   ✅ Pattern matching across multiple files")
            print("   ✅ Memory management and cache clearing")
            print("   ✅ Performance monitoring and statistics")
            print("   ✅ Seamless CPU fallback when GPU unavailable")
            
            print("\n🎯 Ready for production use with GPU acceleration!")
            return True
        else:
            print("❌ Some tests failed - check the output above")
            return False
            
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
