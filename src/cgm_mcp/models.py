"""
Data models for CGM MCP Server
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """CGM task types"""

    ISSUE_RESOLUTION = "issue_resolution"
    CODE_ANALYSIS = "code_analysis"
    BUG_FIXING = "bug_fixing"
    FEATURE_IMPLEMENTATION = "feature_implementation"


# Model-agnostic data models
class CodeEntity(BaseModel):
    """Represents a code entity (file, class, function, etc.)"""

    id: str = Field(..., description="Unique identifier for the entity")
    type: str = Field(..., description="Type of entity (file, class, function, etc.)")
    name: str = Field(..., description="Name of the entity")
    file_path: str = Field(..., description="Path to the file containing this entity")
    content_preview: str = Field("", description="Preview of the entity content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class CodeRelation(BaseModel):
    """Represents a relationship between code entities"""

    source_entity_id: str = Field(..., description="Source entity ID")
    target_entity_id: str = Field(..., description="Target entity ID")
    relation_type: str = Field(..., description="Type of relationship")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class CodeGraph(BaseModel):
    """Represents the code graph structure"""

    files: List[str] = Field(..., description="List of files in the repository")
    entities: List[CodeEntity] = Field(..., description="List of code entities")
    graph_data: Dict[str, Any] = Field(..., description="Serialized graph data")


class FileAnalysis(BaseModel):
    """Detailed analysis of a single file"""

    file_path: str = Field(..., description="Path to the file")
    content: str = Field(..., description="Full file content")
    structure: Dict[str, Any] = Field(
        ..., description="File structure (classes, functions, etc.)"
    )
    dependencies: List[str] = Field(..., description="File dependencies")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class CodeAnalysisRequest(BaseModel):
    """Request for code analysis"""

    repository_path: str = Field(..., description="Path to the repository")
    query: str = Field(..., description="Analysis query or focus area")
    analysis_scope: str = Field(
        "full", description="Scope of analysis (full, focused, minimal)"
    )
    focus_files: Optional[List[str]] = Field(
        None, description="Specific files to focus on"
    )
    max_files: int = Field(
        10, description="Maximum number of files to analyze in detail"
    )


class CodeAnalysisResponse(BaseModel):
    """Response from code analysis"""

    repository_path: str = Field(..., description="Path to the analyzed repository")
    code_graph: CodeGraph = Field(..., description="Code graph structure")
    relevant_entities: List[CodeEntity] = Field(
        ..., description="Entities relevant to the query"
    )
    file_analyses: List[FileAnalysis] = Field(..., description="Detailed file analyses")
    relations: List[CodeRelation] = Field(..., description="Code entity relationships")
    context_summary: str = Field(..., description="Human-readable context summary")
    analysis_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Analysis metadata"
    )


class CGMRequest(BaseModel):
    """Base request model for CGM operations"""

    task_type: TaskType
    repository_name: str = Field(..., description="Name of the repository")
    issue_description: str = Field(..., description="Description of the issue or task")
    repository_context: Optional[Dict[str, Any]] = Field(
        None, description="Repository context information"
    )

    model_config = {"use_enum_values": True}


class RewriterRequest(BaseModel):
    """Request model for Rewriter component"""

    problem_statement: str = Field(..., description="Original problem statement")
    repo_name: str = Field(..., description="Repository name")
    extraction_mode: bool = Field(True, description="Whether to use extraction mode")


class RewriterResponse(BaseModel):
    """Response model for Rewriter component"""

    analysis: str = Field(..., description="Detailed analysis of the problem")
    related_entities: List[str] = Field(..., description="Related code entities")
    keywords: List[str] = Field(..., description="Extracted keywords")
    queries: Optional[List[str]] = Field(
        None, description="Generated queries for inference mode"
    )


class RetrieverRequest(BaseModel):
    """Request model for Retriever component"""

    entities: List[str] = Field(..., description="Code entities from rewriter")
    keywords: List[str] = Field(..., description="Keywords from rewriter")
    queries: Optional[List[str]] = Field(None, description="Queries from rewriter")
    repository_graph: Dict[str, Any] = Field(..., description="Repository code graph")


class RetrieverResponse(BaseModel):
    """Response model for Retriever component"""

    anchor_nodes: List[str] = Field(..., description="Identified anchor nodes")
    subgraph: Dict[str, Any] = Field(..., description="Retrieved code subgraph")
    relevant_files: List[str] = Field(..., description="List of relevant files")


class RerankerRequest(BaseModel):
    """Request model for Reranker component"""

    problem_statement: str = Field(..., description="Original problem statement")
    repo_name: str = Field(..., description="Repository name")
    python_files: List[str] = Field(..., description="Python files to rank")
    other_files: List[str] = Field(..., description="Other files to rank")
    file_contents: Dict[str, str] = Field(..., description="File contents for scoring")


class FileScore(BaseModel):
    """File relevance score"""

    file_path: str = Field(..., description="Path to the file")
    score: int = Field(..., ge=1, le=5, description="Relevance score (1-5)")
    analysis: str = Field(..., description="Analysis for the score")


class RerankerResponse(BaseModel):
    """Response model for Reranker component"""

    top_files: List[str] = Field(..., description="Top ranked files")
    file_scores: List[FileScore] = Field(..., description="Detailed file scores")


class ReaderRequest(BaseModel):
    """Request model for Reader component"""

    problem_statement: str = Field(..., description="Original problem statement")
    subgraph: Dict[str, Any] = Field(..., description="Code subgraph from retriever")
    top_files: List[str] = Field(..., description="Top files from reranker")
    repository_context: Dict[str, Any] = Field(..., description="Repository context")


class CodePatch(BaseModel):
    """Code patch information"""

    file_path: str = Field(..., description="Path to the file to be modified")
    original_code: str = Field(..., description="Original code")
    modified_code: str = Field(..., description="Modified code")
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")
    explanation: str = Field(..., description="Explanation of the changes")


class ReaderResponse(BaseModel):
    """Response model for Reader component"""

    patches: List[CodePatch] = Field(..., description="Generated code patches")
    summary: str = Field(..., description="Summary of the changes")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class CGMResponse(BaseModel):
    """Complete CGM response"""

    task_id: str = Field(..., description="Unique task identifier")
    task_type: TaskType
    status: str = Field(..., description="Task status")
    rewriter_result: Optional[RewriterResponse] = None
    retriever_result: Optional[RetrieverResponse] = None
    reranker_result: Optional[RerankerResponse] = None
    reader_result: Optional[ReaderResponse] = None
    error_message: Optional[str] = None
    processing_time: float = Field(..., description="Total processing time in seconds")

    model_config = {"use_enum_values": True}


class HealthCheckResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    components: Dict[str, str] = Field(..., description="Component status")
    timestamp: str = Field(..., description="Response timestamp")
