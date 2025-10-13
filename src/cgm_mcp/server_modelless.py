"""
Model-agnostic CGM MCP Server

This server provides CGM capabilities without depending on any specific LLM.
It serves as a tool and context provider for external models.
"""

import asyncio
import json
import uuid
import hashlib
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil
from cachetools import TTLCache, LRUCache
from loguru import logger
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server.lowlevel import NotificationOptions
from mcp.types import (
    EmbeddedResource,
    ImageContent,
    Resource,
    TextContent,
    Tool,
)
from pydantic import ValidationError

from .core.analyzer import CGMAnalyzer
from .core.analyzer_optimized import OptimizedCGMAnalyzer
from .core.gpu_enhanced_analyzer import GPUEnhancedAnalyzer
from .core.gpu_accelerator import GPUAcceleratorConfig
from .models import (
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    CodeEntity,
    CodeRelation,
    FileAnalysis,
)
from .utils.config import Config


class ModellessCGMServer:
    """
    Model-agnostic CGM MCP Server that provides code analysis tools
    and context without requiring any specific LLM integration.
    """

    def __init__(self, config: Config):
        self.config = config
        self.server = Server("cgm-modelless")

        # Initialize analyzer with GPU support if available
        gpu_config = GPUAcceleratorConfig(
            use_gpu=getattr(config, 'use_gpu', True),
            batch_size=getattr(config, 'gpu_batch_size', 1024),
            similarity_threshold=getattr(config, 'similarity_threshold', 0.1)
        )

        try:
            self.analyzer = GPUEnhancedAnalyzer(gpu_config)
            logger.info("GPU-enhanced analyzer initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize GPU analyzer, falling back to optimized: {e}")
            self.analyzer = OptimizedCGMAnalyzer()

        # Enhanced caching system
        self.analysis_cache = TTLCache(maxsize=100, ttl=3600)  # 1 hour TTL
        self.file_cache = LRUCache(maxsize=500)  # File-level cache
        self.ast_cache = LRUCache(maxsize=200)   # AST parsing cache

        # Performance monitoring
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "file_hits": 0,
            "file_misses": 0
        }

        self._setup_handlers()

    def _generate_cache_key(self, *args) -> str:
        """Generate a consistent cache key from arguments"""
        key_data = "|".join(str(arg) for arg in args)
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics"""
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent()
        }

    def _cleanup_caches_if_needed(self):
        """Clean up caches if memory usage is too high"""
        memory_usage = self._get_memory_usage()
        if memory_usage["percent"] > 80:  # If using more than 80% memory
            logger.warning(f"High memory usage ({memory_usage['percent']:.1f}%), clearing caches")
            self.file_cache.clear()
            self.ast_cache.clear()
            # Keep analysis cache but reduce size
            if len(self.analysis_cache) > 50:
                # Remove oldest entries
                keys_to_remove = list(self.analysis_cache.keys())[:len(self.analysis_cache)//2]
                for key in keys_to_remove:
                    self.analysis_cache.pop(key, None)

    def _setup_handlers(self):
        """Setup MCP server handlers"""

        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="cgm://health",
                    name="CGM Health Status",
                    description="CGM analyzer health and status information",
                    mimeType="application/json",
                ),
                Resource(
                    uri="cgm://cache",
                    name="Analysis Cache",
                    description="Cached analysis results and performance statistics",
                    mimeType="application/json",
                ),
                Resource(
                    uri="cgm://performance",
                    name="Performance Metrics",
                    description="Server performance and memory usage metrics",
                    mimeType="application/json",
                ),
                Resource(
                    uri="cgm://gpu",
                    name="GPU Statistics",
                    description="GPU acceleration performance and memory statistics",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read resource content"""
            if uri == "cgm://health":
                health = {
                    "status": "healthy",
                    "analyzer": "ready",
                    "cache_size": len(self.analysis_cache),
                    "timestamp": datetime.now().isoformat(),
                }
                return json.dumps(health, indent=2)
            elif uri == "cgm://cache":
                cache_info = {
                    "analysis_cache": {
                        "size": len(self.analysis_cache),
                        "maxsize": self.analysis_cache.maxsize,
                        "ttl": getattr(self.analysis_cache, 'ttl', None),
                        "keys": list(self.analysis_cache.keys())[:10]  # Show first 10 keys
                    },
                    "file_cache": {
                        "size": len(self.file_cache),
                        "maxsize": self.file_cache.maxsize,
                    },
                    "ast_cache": {
                        "size": len(self.ast_cache),
                        "maxsize": self.ast_cache.maxsize,
                    },
                    "stats": self.cache_stats
                }
                return json.dumps(cache_info, indent=2)
            elif uri == "cgm://performance":
                perf_info = {
                    "memory_usage": self._get_memory_usage(),
                    "cache_stats": self.cache_stats,
                    "cache_hit_rate": (
                        self.cache_stats["hits"] /
                        max(1, self.cache_stats["hits"] + self.cache_stats["misses"])
                    ),
                    "file_cache_hit_rate": (
                        self.cache_stats["file_hits"] /
                        max(1, self.cache_stats["file_hits"] + self.cache_stats["file_misses"])
                    ),
                    "timestamp": datetime.now().isoformat(),
                }
                return json.dumps(perf_info, indent=2)
            elif uri == "cgm://gpu":
                # GPU statistics (if available)
                if hasattr(self.analyzer, 'get_gpu_stats'):
                    gpu_info = self.analyzer.get_gpu_stats()
                    gpu_info["timestamp"] = datetime.now().isoformat()
                else:
                    gpu_info = {
                        "gpu_available": False,
                        "message": "GPU acceleration not available",
                        "timestamp": datetime.now().isoformat()
                    }
                return json.dumps(gpu_info, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="cgm_analyze_repository",
                    description="Analyze repository structure and extract code context",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repository_path": {
                                "type": "string",
                                "description": "Path to the repository to analyze",
                            },
                            "query": {
                                "type": "string",
                                "description": "Analysis query or focus area (e.g., 'authentication', 'user management')",
                            },
                            "analysis_scope": {
                                "type": "string",
                                "enum": ["minimal", "focused", "full"],
                                "description": "Scope of analysis",
                                "default": "focused",
                            },
                            "focus_files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific files to focus on (optional)",
                            },
                            "max_files": {
                                "type": "integer",
                                "description": "Maximum number of files to analyze in detail",
                                "default": 10,
                            },
                        },
                        "required": ["repository_path", "query"],
                    },
                ),
                Tool(
                    name="cgm_get_file_content",
                    description="Get detailed content and analysis of specific files",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repository_path": {
                                "type": "string",
                                "description": "Path to the repository",
                            },
                            "file_paths": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of file paths to analyze",
                            },
                        },
                        "required": ["repository_path", "file_paths"],
                    },
                ),
                Tool(
                    name="cgm_find_related_code",
                    description="Find code entities related to a specific entity or concept",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repository_path": {
                                "type": "string",
                                "description": "Path to the repository",
                            },
                            "entity_name": {
                                "type": "string",
                                "description": "Name of the entity to find relations for",
                            },
                            "relation_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Types of relations to include (optional)",
                            },
                        },
                        "required": ["repository_path", "entity_name"],
                    },
                ),
                Tool(
                    name="cgm_extract_context",
                    description="Extract structured context for external model consumption",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repository_path": {
                                "type": "string",
                                "description": "Path to the repository",
                            },
                            "query": {"type": "string", "description": "Context query"},
                            "format": {
                                "type": "string",
                                "enum": ["structured", "markdown", "prompt"],
                                "description": "Output format",
                                "default": "structured",
                            },
                        },
                        "required": ["repository_path", "query"],
                    },
                ),
                Tool(
                    name="clear_gpu_cache",
                    description="Clear GPU caches to free memory",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> List[TextContent]:
            """Handle tool calls"""
            try:
                if name == "cgm_analyze_repository":
                    result = await self._analyze_repository(arguments)
                    return [
                        TextContent(
                            type="text", text=json.dumps(result, indent=2, default=str)
                        )
                    ]

                elif name == "cgm_get_file_content":
                    result = await self._get_file_content(arguments)
                    return [
                        TextContent(
                            type="text", text=json.dumps(result, indent=2, default=str)
                        )
                    ]

                elif name == "cgm_find_related_code":
                    result = await self._find_related_code(arguments)
                    return [
                        TextContent(
                            type="text", text=json.dumps(result, indent=2, default=str)
                        )
                    ]

                elif name == "cgm_extract_context":
                    result = await self._extract_context(arguments)
                    return [TextContent(type="text", text=result)]

                elif name == "clear_gpu_cache":
                    result = await self._clear_gpu_cache(arguments)
                    return [
                        TextContent(
                            type="text", text=json.dumps(result, indent=2, default=str)
                        )
                    ]

                else:
                    raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                logger.error(f"Error handling tool call {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _analyze_repository(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze repository and return structured results"""
        try:
            request = CodeAnalysisRequest(**arguments)

            # Generate more precise cache key
            cache_key = self._generate_cache_key(
                request.repository_path,
                request.query,
                request.analysis_scope,
                str(sorted(request.focus_files or [])),
                request.max_files
            )

            # Check cache
            if cache_key in self.analysis_cache:
                logger.info(f"Cache hit for repository analysis: {cache_key[:16]}...")
                self.cache_stats["hits"] += 1
                response = self.analysis_cache[cache_key]
            else:
                logger.info(f"Cache miss - analyzing repository: {request.repository_path}")
                self.cache_stats["misses"] += 1

                # Clean up caches if needed before heavy operation
                self._cleanup_caches_if_needed()

                response = await self.analyzer.analyze_repository(request)

                # Cache the result
                self.analysis_cache[cache_key] = response

            return {
                "status": "success",
                "analysis": response.dict(),
                "summary": response.context_summary,
                "entity_count": len(response.relevant_entities),
                "file_count": len(response.file_analyses),
            }

        except Exception as e:
            logger.error(f"Error in repository analysis: {e}")
            return {"status": "error", "error": str(e)}

    async def _get_file_content(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed file content and analysis with caching and concurrency"""
        try:
            repo_path = arguments["repository_path"]
            file_paths = arguments["file_paths"]

            # Process files concurrently
            tasks = []
            for file_path in file_paths:
                full_path = f"{repo_path}/{file_path}"
                tasks.append(self._get_cached_file_analysis(full_path, file_path))

            # Wait for all file analyses to complete
            file_analyses = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions and None results
            valid_analyses = []
            for analysis in file_analyses:
                if isinstance(analysis, Exception):
                    logger.warning(f"File analysis failed: {analysis}")
                elif analysis is not None:
                    valid_analyses.append(analysis.dict())

            return {
                "status": "success",
                "files": valid_analyses,
                "file_count": len(valid_analyses),
                "cache_stats": {
                    "file_hits": self.cache_stats["file_hits"],
                    "file_misses": self.cache_stats["file_misses"]
                }
            }

        except Exception as e:
            logger.error(f"Error getting file content: {e}")
            return {"status": "error", "error": str(e)}

    async def _get_cached_file_analysis(self, full_path: str, relative_path: str):
        """Get file analysis with caching"""
        import os

        # Generate cache key based on file path and modification time
        try:
            mtime = os.path.getmtime(full_path)
            cache_key = self._generate_cache_key(relative_path, mtime)

            # Check file cache
            if cache_key in self.file_cache:
                self.cache_stats["file_hits"] += 1
                return self.file_cache[cache_key]

            # Cache miss - analyze file using optimized async method
            self.cache_stats["file_misses"] += 1
            analysis = await self.analyzer._analyze_single_file_async(full_path, relative_path)

            if analysis:
                self.file_cache[cache_key] = analysis

            return analysis

        except Exception as e:
            logger.warning(f"Error in cached file analysis for {relative_path}: {e}")
            return None

    async def _find_related_code(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find code entities related to a specific entity"""
        try:
            repo_path = arguments["repository_path"]
            entity_name = arguments["entity_name"]
            relation_types = arguments.get("relation_types", [])

            # Try to reuse cached analysis first
            cache_key = self._generate_cache_key(repo_path, entity_name, "focused")

            if cache_key in self.analysis_cache:
                logger.info(f"Reusing cached analysis for related code search")
                self.cache_stats["hits"] += 1
                response = self.analysis_cache[cache_key]
            else:
                # Analyze the repository to get the graph
                request = CodeAnalysisRequest(
                    repository_path=repo_path, query=entity_name, analysis_scope="focused"
                )
                self.cache_stats["misses"] += 1
                response = await self.analyzer.analyze_repository(request)
                self.analysis_cache[cache_key] = response

            # Find related entities
            related_entities = []
            target_entity = None

            # Find the target entity
            for entity in response.relevant_entities:
                if entity_name.lower() in entity.name.lower():
                    target_entity = entity
                    break

            if target_entity:
                # Find relations
                for relation in response.relations:
                    if (
                        relation.source_entity_id == target_entity.id
                        or relation.target_entity_id == target_entity.id
                    ):

                        if (
                            not relation_types
                            or relation.relation_type in relation_types
                        ):
                            # Find the related entity
                            related_id = (
                                relation.target_entity_id
                                if relation.source_entity_id == target_entity.id
                                else relation.source_entity_id
                            )

                            for entity in response.relevant_entities:
                                if entity.id == related_id:
                                    related_entities.append(
                                        {
                                            "entity": entity.dict(),
                                            "relation": relation.dict(),
                                        }
                                    )
                                    break

            return {
                "status": "success",
                "target_entity": target_entity.dict() if target_entity else None,
                "related_entities": related_entities,
                "relation_count": len(related_entities),
            }

        except Exception as e:
            logger.error(f"Error finding related code: {e}")
            return {"status": "error", "error": str(e)}

    async def _extract_context(self, arguments: Dict[str, Any]) -> str:
        """Extract context in specified format"""
        try:
            repo_path = arguments["repository_path"]
            query = arguments["query"]
            format_type = arguments.get("format", "structured")

            # Try to reuse cached analysis
            cache_key = self._generate_cache_key(repo_path, query, "focused")

            if cache_key in self.analysis_cache:
                logger.info(f"Reusing cached analysis for context extraction")
                self.cache_stats["hits"] += 1
                response = self.analysis_cache[cache_key]
            else:
                # Analyze repository
                request = CodeAnalysisRequest(
                    repository_path=repo_path, query=query, analysis_scope="focused"
                )
                self.cache_stats["misses"] += 1
                response = await self.analyzer.analyze_repository(request)
                self.analysis_cache[cache_key] = response

            if format_type == "markdown":
                return self._format_as_markdown(response)
            elif format_type == "prompt":
                return self._format_as_prompt(response)
            else:  # structured
                return json.dumps(response.dict(), indent=2, default=str)

        except Exception as e:
            logger.error(f"Error extracting context: {e}")
            return f"Error: {str(e)}"

    def _format_as_markdown(self, response: CodeAnalysisResponse) -> str:
        """Format analysis response as markdown"""
        md_parts = []

        md_parts.append(f"# Code Analysis: {response.repository_path}")
        md_parts.append(f"\n{response.context_summary}\n")

        if response.relevant_entities:
            md_parts.append("## Relevant Code Entities")
            # Limit entities to reduce memory usage
            for entity in response.relevant_entities[:8]:  # Reduced from 10 to 8
                md_parts.append(f"### {entity.type.title()}: {entity.name}")
                md_parts.append(f"**File:** `{entity.file_path}`")
                if entity.content_preview:
                    # Reduced preview size
                    preview = entity.content_preview[:150]
                    if len(entity.content_preview) > 150:
                        preview += "..."
                    md_parts.append(f"**Preview:** {preview}")
                md_parts.append("")

        if response.file_analyses:
            md_parts.append("## Key Files")
            # Limit files to reduce memory usage
            for file_analysis in response.file_analyses[:3]:  # Reduced from 5 to 3
                md_parts.append(f"### {file_analysis.file_path}")
                md_parts.append(
                    f"**Size:** {file_analysis.metadata.get('lines', 0)} lines"
                )
                md_parts.append(
                    f"**Language:** {file_analysis.metadata.get('language', 'unknown')}"
                )

                if file_analysis.structure.get("classes"):
                    classes = [c["name"] for c in file_analysis.structure["classes"]]
                    # Limit class names to reduce output size
                    md_parts.append(f"**Classes:** {', '.join(classes[:3])}")

                if file_analysis.structure.get("functions"):
                    functions = [
                        f["name"] for f in file_analysis.structure["functions"]
                    ]
                    # Limit function names
                    md_parts.append(f"**Functions:** {', '.join(functions[:3])}")

                md_parts.append("")

        return "\n".join(md_parts)

    def _format_as_prompt(self, response: CodeAnalysisResponse) -> str:
        """Format analysis response as a prompt for external models"""
        prompt_parts = []

        prompt_parts.append("# Repository Code Context")
        prompt_parts.append(f"Repository: {response.repository_path}")
        prompt_parts.append(f"Analysis Summary: {response.context_summary}")

        prompt_parts.append("\n## Code Structure")

        # Group entities by type (reduced limit for memory efficiency)
        entities_by_type = {}
        for entity in response.relevant_entities[:15]:  # Reduced from 20 to 15
            if entity.type not in entities_by_type:
                entities_by_type[entity.type] = []
            entities_by_type[entity.type].append(entity)

        for entity_type, entities in entities_by_type.items():
            prompt_parts.append(f"\n### {entity_type.title()}s:")
            for entity in entities:
                prompt_parts.append(f"- {entity.name} (in {entity.file_path})")

        # Add key file contents (optimized for memory)
        if response.file_analyses:
            prompt_parts.append("\n## Key File Contents")
            for file_analysis in response.file_analyses[:2]:  # Reduced from 3 to 2
                prompt_parts.append(f"\n### File: {file_analysis.file_path}")
                prompt_parts.append("```")
                # Reduced content size for memory efficiency
                content_limit = 1500  # Reduced from 2000 to 1500
                prompt_parts.append(file_analysis.content[:content_limit])
                if len(file_analysis.content) > content_limit:
                    prompt_parts.append("... (truncated)")
                prompt_parts.append("```")

        prompt_parts.append(
            "\nUse this context to understand the codebase structure and relationships."
        )

        return "\n".join(prompt_parts)

    async def _clear_gpu_cache(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Clear GPU caches to free memory"""
        try:
            if hasattr(self.analyzer, 'clear_gpu_caches'):
                # Get memory stats before clearing
                before_stats = self.analyzer.get_gpu_stats() if hasattr(self.analyzer, 'get_gpu_stats') else {}

                # Clear GPU caches
                self.analyzer.clear_gpu_caches()

                # Get memory stats after clearing
                after_stats = self.analyzer.get_gpu_stats() if hasattr(self.analyzer, 'get_gpu_stats') else {}

                return {
                    "status": "success",
                    "message": "GPU caches cleared successfully",
                    "before_stats": before_stats.get("memory", {}),
                    "after_stats": after_stats.get("memory", {}),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "info",
                    "message": "GPU acceleration not available - no caches to clear",
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Error clearing GPU cache: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def run(self):
        """Run the MCP server"""
        logger.info("Starting Model-agnostic CGM MCP Server")

        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="cgm-modelless",
                        server_version="0.1.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )
        except Exception as e:
            logger.error(f"MCP server error: {e}")
            logger.exception("Full traceback:")
            raise


async def main():
    """Main entry point for modelless server"""
    try:
        config = Config.load()
        server = ModellessCGMServer(config)
        await server.run()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        logger.exception("Full traceback:")
        raise


def cli_main():
    """Synchronous console entry point wrapper."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
