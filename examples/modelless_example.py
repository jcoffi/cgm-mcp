#!/usr/bin/env python3
"""
Model-agnostic CGM Example

This example demonstrates how to use the model-agnostic CGM server
that provides code analysis tools without requiring any LLM integration.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cgm_mcp.server_modelless import ModellessCGMServer
from cgm_mcp.utils.config import Config


async def demo_repository_analysis():
    """Demonstrate repository analysis capabilities"""
    print("🔍 Repository Analysis Demo")
    print("=" * 50)

    # Create server instance
    config = Config.load()
    server = ModellessCGMServer(config)

    # Example repository analysis
    arguments = {
        "repository_path": ".",  # Current directory
        "query": "authentication and security",
        "analysis_scope": "focused",
        "max_files": 5,
    }

    print(f"Analyzing repository: {arguments['repository_path']}")
    print(f"Query: {arguments['query']}")
    print()

    try:
        result = await server._analyze_repository(arguments)

        if result["status"] == "success":
            analysis = result["analysis"]

            print("✅ Analysis completed successfully!")
            print(f"📊 Summary: {result['summary']}")
            print(f"📁 Files analyzed: {result['file_count']}")
            print(f"🔗 Entities found: {result['entity_count']}")
            print()

            # Show relevant entities
            entities = analysis["relevant_entities"][:5]
            if entities:
                print("🎯 Top Relevant Entities:")
                for i, entity in enumerate(entities, 1):
                    print(
                        f"  {i}. {entity['type']}: {entity['name']} (in {entity['file_path']})"
                    )
                print()

            # Show file analyses
            files = analysis["file_analyses"][:3]
            if files:
                print("📄 Key Files:")
                for file_analysis in files:
                    print(f"  • {file_analysis['file_path']}")
                    print(
                        f"    Language: {file_analysis['metadata'].get('language', 'unknown')}"
                    )
                    print(f"    Lines: {file_analysis['metadata'].get('lines', 0)}")

                    # Show structure
                    structure = file_analysis["structure"]
                    if structure.get("classes"):
                        classes = [c["name"] for c in structure["classes"]]
                        print(f"    Classes: {', '.join(classes[:3])}")
                    if structure.get("functions"):
                        functions = [f["name"] for f in structure["functions"]]
                        print(f"    Functions: {', '.join(functions[:3])}")
                    print()
        else:
            print(f"❌ Analysis failed: {result['error']}")

    except Exception as e:
        print(f"❌ Error: {e}")


async def demo_file_content():
    """Demonstrate file content analysis"""
    print("📄 File Content Analysis Demo")
    print("=" * 50)

    config = Config.load()
    server = ModellessCGMServer(config)

    # Analyze specific files
    arguments = {
        "repository_path": ".",
        "file_paths": ["main_modelless.py", "src/cgm_mcp/models.py"],
    }

    print(f"Analyzing files: {arguments['file_paths']}")
    print()

    try:
        result = await server._get_file_content(arguments)

        if result["status"] == "success":
            print(f"✅ Analyzed {result['file_count']} files")

            for file_data in result["files"]:
                print(f"\n📁 File: {file_data['file_path']}")
                print(f"   Size: {len(file_data['content'])} characters")
                print(
                    f"   Language: {file_data['metadata'].get('language', 'unknown')}"
                )

                # Show dependencies
                if file_data["dependencies"]:
                    print(
                        f"   Dependencies: {', '.join(file_data['dependencies'][:5])}"
                    )

                # Show structure summary
                structure = file_data["structure"]
                if structure.get("functions"):
                    print(f"   Functions: {len(structure['functions'])}")
                if structure.get("classes"):
                    print(f"   Classes: {len(structure['classes'])}")
        else:
            print(f"❌ Analysis failed: {result['error']}")

    except Exception as e:
        print(f"❌ Error: {e}")


async def demo_context_extraction():
    """Demonstrate context extraction in different formats"""
    print("📋 Context Extraction Demo")
    print("=" * 50)

    config = Config.load()
    server = ModellessCGMServer(config)

    # Extract context in different formats
    base_arguments = {"repository_path": ".", "query": "MCP server implementation"}

    formats = ["structured", "markdown", "prompt"]

    for format_type in formats:
        print(f"\n🔧 Format: {format_type}")
        print("-" * 30)

        arguments = {**base_arguments, "format": format_type}

        try:
            result = await server._extract_context(arguments)

            if format_type == "structured":
                # Parse JSON and show summary
                data = json.loads(result)
                print(f"Repository: {data['repository_path']}")
                print(f"Entities: {len(data['relevant_entities'])}")
                print(f"Files: {len(data['file_analyses'])}")
            else:
                # Show first 500 characters
                print(result[:500])
                if len(result) > 500:
                    print("... (truncated)")

        except Exception as e:
            print(f"❌ Error: {e}")


async def demo_related_code():
    """Demonstrate finding related code"""
    print("🔗 Related Code Demo")
    print("=" * 50)

    config = Config.load()
    server = ModellessCGMServer(config)

    # Find code related to a specific entity
    arguments = {
        "repository_path": ".",
        "entity_name": "CGMServer",
        "relation_types": ["contains", "imports"],
    }

    print(f"Finding code related to: {arguments['entity_name']}")
    print()

    try:
        result = await server._find_related_code(arguments)

        if result["status"] == "success":
            target = result["target_entity"]
            if target:
                print(f"🎯 Target Entity: {target['name']} ({target['type']})")
                print(f"   File: {target['file_path']}")
                print()

            related = result["related_entities"]
            if related:
                print(f"🔗 Found {len(related)} related entities:")
                for item in related[:5]:
                    entity = item["entity"]
                    relation = item["relation"]
                    print(
                        f"  • {entity['name']} ({entity['type']}) - {relation['relation_type']}"
                    )
            else:
                print("No related entities found")
        else:
            print(f"❌ Search failed: {result['error']}")

    except Exception as e:
        print(f"❌ Error: {e}")


async def demo_as_external_tool():
    """Demonstrate how external models would use this as a tool"""
    print("🤖 External Model Integration Demo")
    print("=" * 50)

    print("This demonstrates how an external model (like Claude, GPT, etc.)")
    print("would use CGM as a tool to understand code structure.")
    print()

    config = Config.load()
    server = ModellessCGMServer(config)

    # Simulate external model workflow
    print("1. 🔍 External model asks: 'Analyze the authentication system'")

    # Step 1: Get repository overview
    analysis_args = {
        "repository_path": ".",
        "query": "authentication system",
        "analysis_scope": "focused",
    }

    analysis_result = await server._analyze_repository(analysis_args)

    if analysis_result["status"] == "success":
        print("   ✅ CGM provides repository structure and relevant entities")

        # Step 2: Get detailed context for the model
        context_args = {
            "repository_path": ".",
            "query": "authentication system",
            "format": "prompt",
        }

        context = await server._extract_context(context_args)

        print("\n2. 📋 CGM provides structured context:")
        print("   " + context[:200].replace("\n", "\n   ") + "...")

        print("\n3. 🤖 External model can now:")
        print("   • Understand code structure")
        print("   • Identify relevant files")
        print("   • See relationships between components")
        print("   • Generate informed responses about the codebase")

        print("\n4. 🔄 Model can request more specific information:")
        print("   • Get detailed file content")
        print("   • Find related code entities")
        print("   • Extract context for specific areas")

    else:
        print(f"   ❌ Analysis failed: {analysis_result['error']}")


async def main():
    """Run all demos"""
    import sys

    # Check if running interactively
    interactive = "--interactive" in sys.argv
    non_interactive = "--non-interactive" in sys.argv

    # Default to non-interactive mode if no arguments provided
    if not interactive and not non_interactive:
        non_interactive = True
        interactive = False

    print("CGM Model-agnostic MCP Server Demo")
    print("=" * 60)
    print("This demo shows how CGM can provide code analysis")
    print("capabilities without requiring any specific LLM integration.")

    if interactive:
        print("\n🔄 Running in interactive mode.")
        print("   Press Enter between demos to continue.")
    else:
        print("\n⚡ Running in non-interactive mode.")
        print("   All demos will run automatically.")
    print()

    demos = [
        ("Repository Analysis", demo_repository_analysis),
        ("File Content Analysis", demo_file_content),
        ("Context Extraction", demo_context_extraction),
        ("Related Code Discovery", demo_related_code),
        ("External Model Integration", demo_as_external_tool),
    ]

    for i, (demo_name, demo_func) in enumerate(demos, 1):
        print(f"\n{'='*60}")
        print(f"Demo {i}/{len(demos)}: {demo_name}")

        try:
            await demo_func()
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            continue

        if interactive and i < len(demos):
            print("\nPress Enter to continue to next demo...")
            input()
        elif not interactive and i < len(demos):
            print(f"\n✅ Demo {i} completed, continuing to next demo...")
            await asyncio.sleep(1)  # Brief pause for readability

    print("\n" + "=" * 60)
    print("🎉 Demo completed!")
    print("\n💡 Key Benefits of Model-agnostic CGM:")
    print("  • No API keys required")
    print("  • Works with any external model")
    print("  • Provides structured code understanding")
    print("  • Caches analysis results for performance")
    print("  • Supports multiple output formats")
    print("  • Can be integrated into any AI workflow")

    if not interactive:
        print("\n🚀 To run interactively: python examples/modelless_example.py --interactive")


if __name__ == "__main__":
    asyncio.run(main())
