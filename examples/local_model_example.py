#!/usr/bin/env python3
"""
Local Model Example for CGM MCP Server

This example demonstrates how to use CGM with local models (Ollama/LM Studio)
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cgm_mcp.models import CGMRequest, TaskType
from cgm_mcp.server import CGMServer
from cgm_mcp.utils.config import Config, LLMConfig


async def test_ollama_model():
    """Test with Ollama local model"""
    print("🦙 Testing with Ollama local model...")

    # Configure for Ollama
    config = Config()
    config.llm_config = LLMConfig(
        provider="ollama",
        model="deepseek-coder:6.7b",  # or deepseek-coder:1.3b for faster response
        api_base="http://localhost:11434",
        temperature=0.1,
        max_tokens=4000,
        timeout=120,
    )

    # Create server instance
    server = CGMServer(config)

    # Test health check first
    health_ok = await server.llm_client.health_check()
    if not health_ok:
        print("❌ Ollama service not available. Please ensure:")
        print("   1. Ollama is installed and running: ollama serve")
        print("   2. Model is downloaded: ollama pull deepseek-coder:6.7b")
        return

    print("✅ Ollama service is healthy")

    # Example issue
    request = CGMRequest(
        task_type=TaskType.BUG_FIXING,
        repository_name="auth-service",
        issue_description="""
        Bug: Password validation fails for special characters
        
        When users enter passwords with special characters like @, #, $, %, 
        the validation function throws an error and login fails.
        
        Error: ValidationError: Invalid character in password
        File: auth/validators.py, line 23
        
        Expected: Special characters should be allowed in passwords
        Actual: Validation fails and user cannot login
        """,
        repository_context={
            "name": "auth-service",
            "language": "Python",
            "framework": "FastAPI",
        },
    )

    print(f"🔍 Processing issue with Ollama model: {config.llm_config.model}")

    try:
        response = await server._process_issue(request.dict())

        print(f"✅ Processing completed!")
        print(f"   Task ID: {response.task_id}")
        print(f"   Status: {response.status}")
        print(f"   Processing Time: {response.processing_time:.2f}s")

        if response.rewriter_result:
            print(f"\n📝 Rewriter Analysis:")
            print(f"   Keywords: {response.rewriter_result.keywords}")
            print(f"   Entities: {response.rewriter_result.related_entities}")

        if response.reader_result and response.reader_result.patches:
            print(f"\n🔧 Generated {len(response.reader_result.patches)} patches:")
            for i, patch in enumerate(response.reader_result.patches[:2], 1):
                print(f"   Patch {i}: {patch.file_path}")
                print(f"   Explanation: {patch.explanation[:100]}...")

    except Exception as e:
        print(f"❌ Error: {e}")


async def test_lmstudio_model():
    """Test with LM Studio local model"""
    print("\n🏠 Testing with LM Studio local model...")

    # Configure for LM Studio
    config = Config()
    config.llm_config = LLMConfig(
        provider="lmstudio",
        model="deepseek-coder-6.7b-instruct",
        api_base="http://localhost:1234/v1",
        temperature=0.1,
        max_tokens=4000,
        timeout=120,
    )

    # Create server instance
    server = CGMServer(config)

    # Test health check
    health_ok = await server.llm_client.health_check()
    if not health_ok:
        print("❌ LM Studio service not available. Please ensure:")
        print("   1. LM Studio is installed and running")
        print("   2. A model is loaded and server is started")
        print("   3. Server is running on http://localhost:1234")
        return

    print("✅ LM Studio service is healthy")

    # Simple code analysis request
    request = CGMRequest(
        task_type=TaskType.CODE_ANALYSIS,
        repository_name="sample-project",
        issue_description="Analyze the authentication module for security vulnerabilities",
        repository_context={"name": "sample-project", "language": "Python"},
    )

    print(f"🔍 Processing analysis with LM Studio model: {config.llm_config.model}")

    try:
        response = await server._process_issue(request.dict())

        print(f"✅ Analysis completed!")
        print(f"   Status: {response.status}")
        print(f"   Processing Time: {response.processing_time:.2f}s")

    except Exception as e:
        print(f"❌ Error: {e}")


async def benchmark_models():
    """Benchmark different local models"""
    print("\n📊 Benchmarking local models...")

    models_to_test = [
        ("ollama", "deepseek-coder:1.3b", "http://localhost:11434"),
        ("ollama", "deepseek-coder:6.7b", "http://localhost:11434"),
        ("lmstudio", "deepseek-coder-6.7b-instruct", "http://localhost:1234/v1"),
    ]

    simple_request = CGMRequest(
        task_type=TaskType.CODE_ANALYSIS,
        repository_name="test-repo",
        issue_description="Quick analysis of main.py file",
        repository_context={"name": "test-repo"},
    )

    results = []

    for provider, model, api_base in models_to_test:
        print(f"\n🧪 Testing {provider}:{model}...")

        config = Config()
        config.llm_config = LLMConfig(
            provider=provider,
            model=model,
            api_base=api_base,
            temperature=0.1,
            max_tokens=1000,
            timeout=60,
        )

        server = CGMServer(config)

        # Check if service is available
        health_ok = await server.llm_client.health_check()
        if not health_ok:
            print(f"   ⏭️  Skipping {model} (service not available)")
            continue

        try:
            import time

            start_time = time.time()

            response = await server._process_issue(simple_request.dict())

            end_time = time.time()
            processing_time = end_time - start_time

            results.append(
                {
                    "model": f"{provider}:{model}",
                    "status": response.status,
                    "time": processing_time,
                    "success": response.status == "completed",
                }
            )

            print(f"   ✅ Completed in {processing_time:.2f}s")

        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results.append(
                {
                    "model": f"{provider}:{model}",
                    "status": "failed",
                    "time": 0,
                    "success": False,
                }
            )

    # Print benchmark results
    if results:
        print("\n📈 Benchmark Results:")
        print("=" * 50)
        for result in results:
            status_icon = "✅" if result["success"] else "❌"
            print(f"{status_icon} {result['model']:<30} {result['time']:.2f}s")


async def main():
    """Run local model examples"""
    print("CGM MCP Server - Local Model Examples")
    print("=" * 50)

    # Test Ollama
    await test_ollama_model()

    # Test LM Studio
    await test_lmstudio_model()

    # Benchmark models
    await benchmark_models()

    print("\n" + "=" * 50)
    print("💡 Tips for better performance:")
    print("   • Use deepseek-coder:6.7b for best balance of speed and quality")
    print("   • Use deepseek-coder:1.3b for fastest response times")
    print("   • Use deepseek-coder:33b for highest quality (requires 64GB+ RAM)")
    print("   • Enable caching for repeated requests")
    print("   • Adjust max_tokens based on your needs")


if __name__ == "__main__":
    asyncio.run(main())
