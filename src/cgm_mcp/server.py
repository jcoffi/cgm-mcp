"""
CGM MCP Server Implementation

Main server implementation using the Model Context Protocol (MCP)
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
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    EmbeddedResource,
    ImageContent,
    Resource,
    TextContent,
    Tool,
)
from pydantic import ValidationError

from .components import (
    GraphBuilder,
    ReaderComponent,
    RerankerComponent,
    RetrieverComponent,
    RewriterComponent,
)
from .core.analyzer import CGMAnalyzer
from .core.analyzer_optimized import OptimizedCGMAnalyzer

# Optional GPU imports for full server
try:
    # Only import GPU components if torch is available
    import torch
    from .core.gpu_enhanced_analyzer import GPUEnhancedAnalyzer
    from .core.gpu_accelerator import GPUAcceleratorConfig
    GPU_AVAILABLE = True
    logger.info("GPU components available for full server")
except ImportError as e:
    logger.info(f"GPU components not available in full server (this is normal): {e}")
    GPUEnhancedAnalyzer = None
    GPUAcceleratorConfig = None
    GPU_AVAILABLE = False

from .models import (
    CGMRequest,
    CGMResponse,
    HealthCheckResponse,
    ReaderRequest,
    RerankerRequest,
    RetrieverRequest,
    RewriterRequest,
    TaskType,
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    CodeEntity,
    CodeRelation,
    FileAnalysis,
)
from .utils.config import Config
from .utils.llm_client import LLMClient


class CGMServer:
    """CGM MCP Server implementation"""

    def __init__(self, config: Config):
        self.config = config
        self.server = Server("cgm-mcp")
        self.llm_client = LLMClient(config.llm_config)

        # Initialize components
        self.rewriter = RewriterComponent(self.llm_client)
        self.retriever = RetrieverComponent()
        self.reranker = RerankerComponent(self.llm_client)
        self.reader = ReaderComponent(self.llm_client)
        self.graph_builder = GraphBuilder()

        # Initialize analyzer - prefer optimized for full server to avoid GPU dependencies unless requested
        if GPU_AVAILABLE and getattr(config, 'use_gpu', False):
            try:
                # Setup GPU accelerator config only if available
                gpu_config = GPUAcceleratorConfig(
                    use_gpu=True,
                    batch_size=getattr(config, 'gpu_batch_size', 1024),
                    similarity_threshold=getattr(config, 'similarity_threshold', 0.1)
                )
                self.analyzer = GPUEnhancedAnalyzer(gpu_config)
                logger.info("GPU-enhanced analyzer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize GPU analyzer, falling back to optimized: {e}")
                self.analyzer = OptimizedCGMAnalyzer()
        else:
            self.analyzer = OptimizedCGMAnalyzer()
            if not GPU_AVAILABLE:
                logger.info("Using optimized analyzer (GPU components not available)")
            else:
                logger.info("Using optimized analyzer (GPU disabled in config)")

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

        # Task storage
        self.tasks: Dict[str, CGMResponse] = {}

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
                    uri="cgm://tasks",
                    name="Active Tasks",
                    description="List of active CGM tasks",
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
                    description="GPU acceleration status and memory usage",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read resource content"""
            if uri == "cgm://health":
                health = await self._get_health_status()
                return json.dumps(health.dict(), indent=2)
            elif uri == "cgm://tasks":
                return json.dumps(
                    {
                        "active_tasks": len(self.tasks),
                        "tasks": [
                            {
                                "task_id": task_id,
                                "task_type": task.task_type,
                                "status": task.status,
                            }
                            for task_id, task in self.tasks.items()
                        ],
                    },
                    indent=2,
                )
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
                # Analysis Tools (from modelless server)
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
                # LLM-powered Tools (original CGM pipeline)
                Tool(
                    name="cgm_process_issue",
                    description="Process a repository issue using CGM framework",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_type": {
                                "type": "string",
                                "enum": [
                                    "issue_resolution",
                                    "code_analysis",
                                    "bug_fixing",
                                    "feature_implementation",
                                ],
                                "description": "Type of task to perform",
                            },
                            "repository_name": {
                                "type": "string",
                                "description": "Name of the repository",
                            },
                            "issue_description": {
                                "type": "string",
                                "description": "Description of the issue or task",
                            },
                            "repository_context": {
                                "type": "object",
                                "description": "Optional repository context information",
                            },
                        },
                        "required": [
                            "task_type",
                            "repository_name",
                            "issue_description",
                        ],
                    },
                ),
                Tool(
                    name="cgm_get_task_status",
                    description="Get the status of a CGM task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "Task ID to check status for",
                            }
                        },
                        "required": ["task_id"],
                    },
                ),
                Tool(
                    name="cgm_health_check",
                    description="Check CGM server health status",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> List[TextContent]:
            """Handle tool calls"""
            try:
                # Handle modelless analysis tools
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

                # Handle LLM-powered CGM pipeline tools
                elif name == "cgm_process_issue":
                    result = await self._process_issue(arguments)
                    return [
                        TextContent(
                            type="text", text=json.dumps(result.dict(), indent=2)
                        )
                    ]

                elif name == "cgm_get_task_status":
                    task_id = arguments.get("task_id")
                    if not task_id:
                        raise ValueError("task_id is required")

                    task = self.tasks.get(task_id)
                    if not task:
                        raise ValueError(f"Task {task_id} not found")

                    return [
                        TextContent(type="text", text=json.dumps(task.dict(), indent=2))
                    ]

                elif name == "cgm_health_check":
                    health = await self._get_health_status()
                    return [
                        TextContent(
                            type="text", text=json.dumps(health.dict(), indent=2)
                        )
                    ]

                else:
                    raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                logger.error(f"Error handling tool call {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _process_issue(self, arguments: Dict[str, Any]) -> CGMResponse:
        """Process a repository issue using CGM framework"""
        try:
            # Validate request
            request = CGMRequest(**arguments)

            # Generate task ID
            task_id = str(uuid.uuid4())

            # Initialize response
            response = CGMResponse(
                task_id=task_id,
                task_type=request.task_type,
                status="processing",
                processing_time=0.0,
            )

            # Store task
            self.tasks[task_id] = response

            start_time = datetime.now()

            try:
                # Step 1: Rewriter
                logger.info(f"Task {task_id}: Starting Rewriter")
                rewriter_request = RewriterRequest(
                    problem_statement=request.issue_description,
                    repo_name=request.repository_name,
                    extraction_mode=True,
                )
                rewriter_result = await self.rewriter.process(rewriter_request)
                response.rewriter_result = rewriter_result
                response.status = "rewriter_completed"

                # Step 2: Build/Get Repository Graph
                logger.info(f"Task {task_id}: Building repository graph")
                repo_graph = await self.graph_builder.build_graph(
                    request.repository_name, request.repository_context
                )

                # Step 3: Retriever
                logger.info(f"Task {task_id}: Starting Retriever")
                retriever_request = RetrieverRequest(
                    entities=rewriter_result.related_entities,
                    keywords=rewriter_result.keywords,
                    queries=rewriter_result.queries,
                    repository_graph=repo_graph,
                )
                retriever_result = await self.retriever.process(retriever_request)
                response.retriever_result = retriever_result
                response.status = "retriever_completed"

                # Step 4: Reranker
                logger.info(f"Task {task_id}: Starting Reranker")
                reranker_request = RerankerRequest(
                    problem_statement=request.issue_description,
                    repo_name=request.repository_name,
                    python_files=[
                        f for f in retriever_result.relevant_files if f.endswith(".py")
                    ],
                    other_files=[
                        f
                        for f in retriever_result.relevant_files
                        if not f.endswith(".py")
                    ],
                    file_contents={},  # TODO: Load file contents
                )
                reranker_result = await self.reranker.process(reranker_request)
                response.reranker_result = reranker_result
                response.status = "reranker_completed"

                # Step 5: Reader
                logger.info(f"Task {task_id}: Starting Reader")
                reader_request = ReaderRequest(
                    problem_statement=request.issue_description,
                    subgraph=retriever_result.subgraph,
                    top_files=reranker_result.top_files,
                    repository_context=request.repository_context or {},
                )
                reader_result = await self.reader.process(reader_request)
                response.reader_result = reader_result
                response.status = "completed"

                logger.info(f"Task {task_id}: Completed successfully")

            except Exception as e:
                logger.error(f"Task {task_id}: Error during processing: {e}")
                response.status = "failed"
                response.error_message = str(e)

            finally:
                # Calculate processing time
                end_time = datetime.now()
                response.processing_time = (end_time - start_time).total_seconds()

                # Update stored task
                self.tasks[task_id] = response

            return response

        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            raise ValueError(f"Invalid request: {e}")

    async def _get_health_status(self) -> HealthCheckResponse:
        """Get server health status"""
        components = {
            "rewriter": "healthy",
            "retriever": "healthy",
            "reranker": "healthy",
            "reader": "healthy",
            "graph_builder": "healthy",
            "llm_client": (
                "healthy" if await self.llm_client.health_check() else "unhealthy"
            ),
        }

        overall_status = (
            "healthy"
            if all(status == "healthy" for status in components.values())
            else "degraded"
        )

        return HealthCheckResponse(
            status=overall_status,
            version="0.1.0",
            components=components,
            timestamp=datetime.now().isoformat(),
        )

    # Modelless tool handler methods (copied from server_modelless.py)

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
                    valid_analyses.append(analysis)

            return {
                "status": "success",
                "file_count": len(valid_analyses),
                "files": valid_analyses,
            }

        except Exception as e:
            logger.error(f"Error getting file content: {e}")
            return {"status": "error", "error": str(e)}

    async def _get_cached_file_analysis(self, full_path: str, relative_path: str) -> Optional[Dict[str, Any]]:
        """Get cached file analysis or analyze and cache it"""
        try:
            # Check file cache first
            if full_path in self.file_cache:
                self.cache_stats["file_hits"] += 1
                cached_data = self.file_cache[full_path]
                return {
                    "file_path": relative_path,
                    "content": cached_data["content"],
                    "metadata": cached_data["metadata"],
                    "structure": cached_data["structure"],
                    "dependencies": cached_data["dependencies"],
                }

            self.cache_stats["file_misses"] += 1

            # Analyze file
            analysis = await self.analyzer.analyze_file(full_path)

            # Cache the result
            self.file_cache[full_path] = {
                "content": analysis.content,
                "metadata": analysis.metadata,
                "structure": analysis.structure,
                "dependencies": analysis.dependencies,
            }

            return {
                "file_path": relative_path,
                "content": analysis.content,
                "metadata": analysis.metadata,
                "structure": analysis.structure,
                "dependencies": analysis.dependencies,
            }

        except Exception as e:
            logger.error(f"Error analyzing file {full_path}: {e}")
            return None

    async def _find_related_code(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find code entities related to a specific entity"""
        try:
            repo_path = arguments["repository_path"]
            entity_name = arguments["entity_name"]
            relation_types = arguments.get("relation_types")

            # Use analyzer to find related code
            related_result = await self.analyzer.find_related_code(
                repository_path=repo_path,
                entity_name=entity_name,
                relation_types=relation_types
            )

            return {
                "status": "success",
                "target_entity": related_result.target_entity.dict() if related_result.target_entity else None,
                "related_entities": [
                    {
                        "entity": item.entity.dict(),
                        "relation": item.relation.dict()
                    }
                    for item in related_result.related_entities
                ],
            }

        except Exception as e:
            logger.error(f"Error finding related code: {e}")
            return {"status": "error", "error": str(e)}

    async def _extract_context(self, arguments: Dict[str, Any]) -> str:
        """Extract structured context for external model consumption"""
        try:
            request = CodeAnalysisRequest(**arguments)

            # Get analysis result
            analysis_result = await self.analyzer.analyze_repository(request)

            # Format based on requested format
            format_type = arguments.get("format", "structured")

            if format_type == "structured":
                return json.dumps(analysis_result.dict(), indent=2)
            elif format_type == "markdown":
                return self._format_context_markdown(analysis_result)
            elif format_type == "prompt":
                return self._format_context_prompt(analysis_result)
            else:
                raise ValueError(f"Unknown format: {format_type}")

        except Exception as e:
            logger.error(f"Error extracting context: {e}")
            return f"Error: {str(e)}"

    def _format_context_markdown(self, analysis_result: CodeAnalysisResponse) -> str:
        """Format analysis result as markdown"""
        lines = [f"# Code Analysis: {analysis_result.repository_path}\n"]
        lines.append(f"Repository contains {len(analysis_result.file_analyses)} files and {len(analysis_result.relevant_entities)} code entities.\n")
        lines.append(f"**Summary:** {analysis_result.context_summary}\n")

        if analysis_result.relevant_entities:
            lines.append("## Relevant Code Entities\n")
            for entity in analysis_result.relevant_entities[:10]:  # Limit to 10
                lines.append(f"### {entity.type.title()}: {entity.name}")
                lines.append(f"**File:** `{entity.file_path}`")
                if entity.metadata:
                    lines.append(f"**Details:** {entity.metadata.get('description', 'N/A')}")
                lines.append("")

        return "\n".join(lines)

    def _format_context_prompt(self, analysis_result: CodeAnalysisResponse) -> str:
        """Format analysis result as a prompt for external models"""
        lines = [f"# Repository Code Context\n"]
        lines.append(f"Repository: {analysis_result.repository_path}")
        lines.append(f"Analysis Summary: {analysis_result.context_summary}\n")

        lines.append("## Code Structure\n")

        # Group entities by type
        entities_by_type = {}
        for entity in analysis_result.relevant_entities:
            entity_type = entity.type
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity.name)

        for entity_type, names in entities_by_type.items():
            lines.append(f"### {entity_type.title()}s:")
            for name in names[:5]:  # Limit to 5 per type
                lines.append(f"- {name}")
            lines.append("")

        lines.append("## Key File Contents\n")

        for file_analysis in analysis_result.file_analyses[:3]:  # Limit to 3 files
            lines.append(f"### File: {file_analysis.file_path}")
            lines.append("```python")            # Show first 20 lines or so
            content_lines = file_analysis.content.split('\n')[:20]
            lines.extend(content_lines)
            if len(file_analysis.content.split('\n')) > 20:
                lines.append("... (truncated)")
            lines.append("```")
            lines.append("")

        lines.append("Use this context to understand the codebase structure and relationships.")

        return "\n".join(lines)

    async def _clear_gpu_cache(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Clear GPU caches to free memory"""
        try:
            if hasattr(self.analyzer, 'clear_gpu_cache'):
                await self.analyzer.clear_gpu_cache()
                return {"status": "success", "message": "GPU cache cleared"}
            else:
                return {"status": "success", "message": "No GPU cache to clear"}
        except Exception as e:
            logger.error(f"Error clearing GPU cache: {e}")
            return {"status": "error", "error": str(e)}

    async def run(self):
        """Run the MCP server"""
        logger.info("Starting CGM MCP Server")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="cgm-mcp",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """Main async entry point"""
    config = Config.load()
    server = CGMServer(config)
    await server.run()


def check_gpu_dependencies():
    """Check if GPU dependencies are installed and install if needed"""
    import subprocess
    import sys
    import shutil

    try:
        # Check if nvidia-smi is available (indicates GPU)
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode != 0:
            return  # No NVIDIA GPU detected, skip

        # Check if required packages are installed
        try:
            import cupy
            import torch
            torch_cuda = torch.cuda.is_available()
            cupy_cuda = False
            try:
                cupy_cuda = cupy.cuda.runtime.getDeviceCount() > 0
            except Exception:
                cupy_cuda = False
            if torch_cuda and cupy_cuda:
                return  # Dependencies already installed and both libraries can use CUDA
        except ImportError:
            pass

        # Check if graphviz is installed (cross-platform)
        if shutil.which('dot') is None:
            print("Installing GPU dependencies and graphviz...")

            # Try to run the installed CLI command first
            try:
                result = subprocess.run([sys.executable, '-m', 'cgm_mcp.install_cuda_stack'],
                                      capture_output=True, text=True)
            except FileNotFoundError:
                # Fallback: try the direct command if available
                try:
                    result = subprocess.run(['install-cuda-stack'], capture_output=True, text=True)
                except FileNotFoundError:
                    print("Warning: install-cuda-stack command not found. Please run 'pip install -e .' to install the CLI command.")
                    return

            if result.returncode != 0:
                print(f"Warning: Failed to install GPU dependencies: {result.stderr}")
            else:
                print("GPU dependencies installed successfully!")
    except Exception as e:
        print(f"Warning: Error checking GPU dependencies: {e}")


def cli():
    """Synchronous CLI entry point for console_scripts"""
    import argparse
    import sys
    from pathlib import Path

    # Add src to path if running as module
    if not any("cgm_mcp" in p for p in sys.path):
        sys.path.insert(0, str(Path(__file__).parent.parent))

    from .utils.config import Config
    from loguru import logger

    def setup_logging(log_level: str = "INFO"):
        """Setup logging configuration"""
        logger.remove()  # Remove default handler
        logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )

    def parse_args():
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(
            description="CGM MCP Server - CodeFuse-CGM Model Context Protocol Server",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  cgm-mcp                           # Start with default config
  cgm-mcp --config config.json     # Use custom config file
  cgm-mcp --log-level DEBUG        # Enable debug logging

Environment Variables:
  CGM_LLM_PROVIDER     - LLM provider (openai, anthropic, mock)
  CGM_LLM_API_KEY      - API key for LLM provider
  CGM_LLM_MODEL        - Model name to use
  CGM_LOG_LEVEL        - Log level (DEBUG, INFO, WARNING, ERROR)
            """
        )

        parser.add_argument(
            "--config",
            type=str,
            help="Path to configuration file (JSON format)"
        )

        parser.add_argument(
            "--log-level",
            type=str,
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help="Set logging level"
        )

        parser.add_argument(
            "--cache-dir",
            type=str,
            help="Directory for caching analysis results"
        )

        parser.add_argument(
            "--max-file-size",
            type=int,
            default=1024*1024,  # 1MB
            help="Maximum file size to analyze (bytes)"
        )

        parser.add_argument(
            "--version",
            action="version",
            version="CGM MCP Server 0.1.0"
        )

        return parser.parse_args()

    args = parse_args()

    # Check and install GPU dependencies if needed
    check_gpu_dependencies()

    # Load configuration
    try:
        config = Config.load(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup logging
    log_level = args.log_level or config.server_config.log_level
    setup_logging(log_level)

    logger.info("Starting CGM MCP Server")
    logger.info(f"Log Level: {log_level}")

    if args.cache_dir:
        logger.info(f"Cache Directory: {args.cache_dir}")

    if args.max_file_size:
        logger.info(f"Max File Size: {args.max_file_size} bytes")

    logger.info("Available tools:")
    logger.info("  • cgm_process_issue - Process repository issues using CGM framework")
    logger.info("  • cgm_get_task_status - Get task status")
    logger.info("  • cgm_health_check - Health check")

    try:
        # Start the MCP server
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
