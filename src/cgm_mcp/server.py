"""
CGM MCP Server Implementation

Main server implementation using the Model Context Protocol (MCP)
"""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

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
from .models import (
    CGMRequest,
    CGMResponse,
    HealthCheckResponse,
    ReaderRequest,
    RerankerRequest,
    RetrieverRequest,
    RewriterRequest,
    TaskType,
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

        # Task storage
        self.tasks: Dict[str, CGMResponse] = {}

        self._setup_handlers()

    def _setup_handlers(self):
        """Setup MCP server handlers"""

        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="cgm://health",
                    name="Health Check",
                    description="CGM server health status",
                    mimeType="application/json",
                ),
                Resource(
                    uri="cgm://tasks",
                    name="Active Tasks",
                    description="List of active CGM tasks",
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
            else:
                raise ValueError(f"Unknown resource: {uri}")

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
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
                if name == "cgm_process_issue":
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
    from pathlib import Path

    try:
        # Check if nvidia-smi is available (indicates GPU)
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode != 0:
            return  # No NVIDIA GPU detected, skip

        # Check if required packages are installed
        try:
            import cupy
            import torch
            if torch.cuda.is_available():
                return  # Dependencies already installed
        except ImportError:
            pass

        # Check if graphviz is installed
        result = subprocess.run(['which', 'dot'], capture_output=True)
        if result.returncode != 0:
            print("Installing GPU dependencies and graphviz...")

            # Run the install script
            script_path = Path(__file__).parent.parent.parent / "scripts" / "install_cuda_stack.py"
            if script_path.exists():
                result = subprocess.run([sys.executable, str(script_path)], check=True)
                print("GPU dependencies installed successfully!")
            else:
                print(f"Warning: CUDA install script not found at {script_path}")
    except Exception as e:
        print(f"Warning: Failed to check/install GPU dependencies: {e}")


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
