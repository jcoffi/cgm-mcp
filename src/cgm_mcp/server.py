"""
CGM MCP Server Implementation

Main server implementation using the Model Context Protocol (MCP)
"""

import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
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
    ReaderResponse,
    RerankerRequest,
    RetrieverRequest,
    RewriterRequest,
    TaskType,
)
from .utils.config import Config
from .utils.llm_client import LLMClient
from .utils.source_loader import load_file_contents, resolve_repo_path


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
                Resource(
                    uri="cgm://agent_tooling",
                    name="Agent Tooling Guide",
                    description="Machine-readable JSON guide for tools available on the primary MCP server.",
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
            elif uri == "cgm://agent_tooling":
                # Machine-readable payload describing tools available on the primary MCP server.
                payload = {
                    "version": "1.0",
                    "source": "primary",
                    "tools": [
                        {
                            "name": "cgm_process_issue",
                            "description": "Process a repository issue using CGM framework",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "task_type": {"type": "string"},
                                    "repository_name": {"type": "string"},
                                    "issue_description": {"type": "string"},
                                },
                                "required": ["task_type", "repository_name", "issue_description"],
                            },
                            "example_input": {"task_type": "issue_resolution", "repository_name": "myrepo", "issue_description": "Fix bug in X"},
                            "example_call": "{\"name\": \"cgm_process_issue\", \"input\": {\"task_type\": \"issue_resolution\", \"repository_name\": \"myrepo\", \"issue_description\": \"Fix bug in X\"}}",
                            "parse_instructions": "Return a JSON object with keys: task_id (string), status (string), summary (string)."
                        },
                        {
                            "name": "cgm_get_task_status",
                            "description": "Get the status of a CGM task",
                            "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
                            "example_input": {"task_id": "<task-id>"},
                            "example_call": "{\"name\": \"cgm_get_task_status\", \"input\": {\"task_id\": \"<task-id>\"}}",
                            "parse_instructions": "Return a JSON object representing the task with its current status."
                        }
                    ],
                    "how_to_call": [
                        "Call list_resources() on the MCP server to discover cgm://agent_tooling.",
                        "Call read_resource('cgm://agent_tooling') to retrieve this JSON payload.",
                        "Find the tool by name and format a call matching the 'example_call' field.",
                        "Send the call using the server's call_tool method and parse the result per parse_instructions."
                    ],
                    "polling_guidance": "If a tool returns a task id for long-running work, poll the cgm://tasks resource for status updates."
                }
                return json.dumps(payload, indent=2)
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
                # Step 0: Validate repository path before any I/O
                allowed_root = self.config.server_config.allowed_root or os.getcwd()
                repo_path = resolve_repo_path(
                    request.repository_name,
                    request.repository_context,
                    allowed_root=allowed_root,
                )
                if not repo_path:
                    response.status = "insufficient_context"
                    response.error_message = (
                        "Repository path could not be resolved or is outside "
                        "the allowed root directory."
                    )
                    response.processing_time = (
                        datetime.now() - start_time
                    ).total_seconds()
                    self.tasks[task_id] = response
                    return response

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

                # Step 2: Build/Get Repository Graph (using validated path)
                logger.info(f"Task {task_id}: Building repository graph")
                validated_context = dict(request.repository_context or {})
                validated_context["path"] = repo_path
                repo_graph = await self.graph_builder.build_graph(
                    request.repository_name, validated_context
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

                # Load file contents for reranker and reader
                file_contents = load_file_contents(
                    repo_path, retriever_result.relevant_files
                ) if repo_path else {}

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
                    file_contents=file_contents,
                )
                reranker_result = await self.reranker.process(reranker_request)
                response.reranker_result = reranker_result
                response.status = "reranker_completed"

                # Step 5: Reader
                logger.info(f"Task {task_id}: Starting Reader")

                # Load source for top files specifically
                top_file_contents = load_file_contents(
                    repo_path, reranker_result.top_files
                ) if repo_path else {}

                reader_request = ReaderRequest(
                    problem_statement=request.issue_description,
                    subgraph=retriever_result.subgraph,
                    top_files=reranker_result.top_files,
                    repository_context=validated_context,
                    file_contents=top_file_contents,
                )
                reader_result = await self.reader.process(reader_request)
                response.reader_result = reader_result

                # Validate reader output
                response.status, response.error_message = self._validate_reader_output(
                    task_id, request.task_type, reader_result, top_file_contents
                )

                logger.info(f"Task {task_id}: Completed with status {response.status}")

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

    def _validate_reader_output(
        self,
        task_id: str,
        task_type: str,
        reader_result: "ReaderResponse",
        file_contents: Dict[str, str],
    ) -> tuple:
        """
        Validate reader output consistency.

        Returns (status, error_message) tuple.
        """
        # Task types that require patches to be "completed"
        fix_task_types = {
            TaskType.BUG_FIXING,
            TaskType.FEATURE_IMPLEMENTATION,
            TaskType.ISSUE_RESOLUTION,
            "bug_fixing",
            "feature_implementation",
            "issue_resolution",
        }

        if not reader_result.patches:
            # No patches produced
            if not file_contents:
                return (
                    "insufficient_context",
                    "Could not load source files for reader analysis.",
                )

            if task_type in fix_task_types:
                # Fix/implementation tasks with no patches => not successful
                logger.warning(
                    f"Task {task_id}: No patches produced for {task_type} task."
                )
                reader_result.summary = (
                    "Analysis completed but no applicable patches could be generated. "
                    "No concrete code changes were produced."
                )
                reader_result.confidence = min(reader_result.confidence, 0.3)
                return ("completed_no_patches", None)

            # Analysis-only task type with no patches is acceptable
            return ("completed", None)

        # Patches were produced - validate them
        valid_patches = []
        invalid_patch_count = 0
        for patch in reader_result.patches:
            # Check patch targets a loaded file
            if patch.file_path not in file_contents:
                logger.warning(
                    f"Task {task_id}: Patch targets unknown file: {patch.file_path}"
                )
                invalid_patch_count += 1
                continue

            source = file_contents[patch.file_path]

            # Require non-empty original and modified code
            if not patch.original_code or not patch.original_code.strip():
                logger.warning(
                    f"Task {task_id}: Patch has empty original_code "
                    f"for {patch.file_path}"
                )
                invalid_patch_count += 1
                continue

            if not patch.modified_code or not patch.modified_code.strip():
                logger.warning(
                    f"Task {task_id}: Patch has empty modified_code "
                    f"for {patch.file_path}"
                )
                invalid_patch_count += 1
                continue

            # Validate line range
            source_line_count = len(source.splitlines())
            if not (1 <= patch.line_start <= patch.line_end <= source_line_count):
                logger.warning(
                    f"Task {task_id}: Patch has invalid line range "
                    f"{patch.line_start}-{patch.line_end} "
                    f"(source has {source_line_count} lines) "
                    f"for {patch.file_path}"
                )
                invalid_patch_count += 1
                continue

            original_code = patch.original_code.strip("\r\n")
            source_range = "\n".join(
                source.splitlines()[patch.line_start - 1 : patch.line_end]
            )
            if original_code not in source_range:
                logger.warning(
                    f"Task {task_id}: Patch original_code not found in claimed "
                    f"source range for {patch.file_path}"
                )
                invalid_patch_count += 1
                continue

            valid_patches.append(patch)

        if invalid_patch_count:
            logger.warning(
                f"Task {task_id}: Rejecting patch response because "
                f"{invalid_patch_count} of {len(reader_result.patches)} patches "
                "failed validation."
            )
            valid_patches = []

        if not valid_patches:
            # At least one patch failed validation, or none were valid.
            logger.warning(f"Task {task_id}: Patch response failed source validation.")
            reader_result.patches = []
            reader_result.summary = (
                "Analysis completed but generated patches could not be validated "
                "against the source code. No applicable changes were produced."
            )
            reader_result.confidence = min(reader_result.confidence, 0.2)

            if task_type in fix_task_types:
                return ("completed_no_patches", None)
            return ("completed", None)

        # Some patches are valid
        reader_result.patches = valid_patches
        return ("completed", None)

    async def _get_health_status(self) -> HealthCheckResponse:
        """Get server health status"""
        # Perform health checks for each component, with error handling for LLM client
        components = {
            "rewriter": "healthy",
            "retriever": "healthy",
            "reranker": "healthy",
            "reader": "healthy",
            "graph_builder": "healthy",
        }

        # Check LLM client health with exception handling to prevent server crashes
        try:
            llm_healthy = await self.llm_client.health_check()
            components["llm_client"] = "healthy" if llm_healthy else "unhealthy"
        except Exception as e:
            logger.warning(f"LLM client health check failed: {e}")
            components["llm_client"] = "unhealthy"

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

        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="cgm-mcp",
                        server_version="0.1.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(resources_changed=True),
                            experimental_capabilities=None,
                        ),
                    ),
                )
        except Exception as e:
            logger.error(f"MCP Server error: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise


async def main(config: Optional[Config] = None):
    """Main entry point"""
    config = config or Config.load()
    server = CGMServer(config)
    await server.run()


def cli_main():
    """Synchronous console entry point wrapper."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
