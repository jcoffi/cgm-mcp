#!/usr/bin/env python3
"""
Example usage of CGM MCP Server

This example demonstrates how to use the CGM MCP server to process
repository issues and generate code patches.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cgm_mcp.models import CGMRequest, TaskType
from cgm_mcp.server import CGMServer
from cgm_mcp.utils.config import Config


async def example_issue_resolution():
    """Example: Process a repository issue"""

    # Load configuration
    config = Config.load()

    # Override with mock LLM for testing
    config.llm_config.provider = "mock"

    # Create server instance
    server = CGMServer(config)

    # Example issue
    request = CGMRequest(
        task_type=TaskType.ISSUE_RESOLUTION,
        repository_name="example-repo",
        issue_description="""
        Bug: Authentication fails when user tries to login with special characters in password
        
        Steps to reproduce:
        1. Go to login page
        2. Enter username: testuser
        3. Enter password with special characters: test@123!
        4. Click login button
        
        Expected: User should be logged in successfully
        Actual: Authentication fails with error "Invalid credentials"
        
        Error logs:
        File "auth/views.py", line 45, in authenticate_user
            if validate_password(password):
        ValidationError: Special characters not properly escaped
        """,
        repository_context={
            "name": "example-repo",
            "language": "Python",
            "framework": "Django",
            "path": "./example-repo",  # Path to repository
        },
    )

    print("🚀 Processing issue with CGM framework...")
    print(f"Repository: {request.repository_name}")
    print(f"Task Type: {request.task_type}")
    print(f"Issue: {request.issue_description[:100]}...")
    print()

    # Process the request
    try:
        response = await server._process_issue(request.dict())

        print("✅ Processing completed!")
        print(f"Task ID: {response.task_id}")
        print(f"Status: {response.status}")
        print(f"Processing Time: {response.processing_time:.2f}s")
        print()

        # Display results
        if response.rewriter_result:
            print("📝 Rewriter Results:")
            print(f"  Analysis: {response.rewriter_result.analysis[:200]}...")
            print(f"  Entities: {response.rewriter_result.related_entities}")
            print(f"  Keywords: {response.rewriter_result.keywords}")
            print()

        if response.retriever_result:
            print("🔍 Retriever Results:")
            print(f"  Anchor Nodes: {len(response.retriever_result.anchor_nodes)}")
            print(
                f"  Subgraph Nodes: {response.retriever_result.subgraph['metadata']['total_nodes']}"
            )
            print(f"  Relevant Files: {len(response.retriever_result.relevant_files)}")
            print()

        if response.reranker_result:
            print("📊 Reranker Results:")
            print(f"  Top Files: {response.reranker_result.top_files}")
            print("  File Scores:")
            for score in response.reranker_result.file_scores[:3]:
                print(f"    {score.file_path}: {score.score}/5")
            print()

        if response.reader_result:
            print("🔧 Reader Results:")
            print(f"  Generated Patches: {len(response.reader_result.patches)}")
            print(f"  Confidence: {response.reader_result.confidence:.2f}")
            print(f"  Summary: {response.reader_result.summary[:200]}...")
            print()

            if response.reader_result.patches:
                print("📋 Code Patches:")
                for i, patch in enumerate(response.reader_result.patches[:2], 1):
                    print(f"  Patch {i}: {patch.file_path}")
                    print(f"    Lines: {patch.line_start}-{patch.line_end}")
                    print(f"    Explanation: {patch.explanation[:100]}...")
                    print()

        if response.error_message:
            print(f"❌ Error: {response.error_message}")

    except Exception as e:
        print(f"❌ Error processing request: {e}")


async def example_code_analysis():
    """Example: Analyze code structure"""

    config = Config.load()
    config.llm_config.provider = "mock"

    server = CGMServer(config)

    request = CGMRequest(
        task_type=TaskType.CODE_ANALYSIS,
        repository_name="example-repo",
        issue_description="Analyze the authentication module for potential security vulnerabilities",
        repository_context={
            "name": "example-repo",
            "language": "Python",
            "framework": "Django",
        },
    )

    print("🔍 Analyzing code structure...")

    try:
        response = await server._process_issue(request.dict())
        print(f"✅ Analysis completed in {response.processing_time:.2f}s")
        print(f"Status: {response.status}")

    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Run examples"""
    print("CGM MCP Server Examples")
    print("=" * 50)
    print()

    # Example 1: Issue Resolution
    print("Example 1: Issue Resolution")
    print("-" * 30)
    await example_issue_resolution()

    print("\n" + "=" * 50 + "\n")

    # Example 2: Code Analysis
    print("Example 2: Code Analysis")
    print("-" * 30)
    await example_code_analysis()


if __name__ == "__main__":
    asyncio.run(main())
