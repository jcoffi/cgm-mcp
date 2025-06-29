# CGM MCP Server Architecture

This document describes the architecture and design principles of the CGM MCP Server.

## Overview

The CGM MCP Server implements the CodeFuse-CGM framework as a Model Context Protocol (MCP) server, enabling AI assistants to perform repository-level software engineering tasks through a graph-integrated approach.

## Core Architecture

### High-Level Design

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │    │   MCP Server    │    │   LLM Provider  │
│  (Claude, etc.) │◄──►│   (CGM Core)    │◄──►│ (OpenAI, etc.)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  Code Repository│
                       │   (File System) │
                       └─────────────────┘
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CGM MCP Server                       │
├─────────────────────────────────────────────────────────────┤
│  MCP Interface Layer                                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │   Tools     │ │ Resources   │ │      Notifications      ││
│  │ Handler     │ │ Handler     │ │       Handler           ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│  CGM Core Pipeline                                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐│
│  │  Rewriter   │→│  Retriever  │→│  Reranker   │→│ Reader  ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘│
├─────────────────────────────────────────────────────────────┤
│  Support Services                                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │Graph Builder│ │ LLM Client  │ │    Configuration        ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. MCP Interface Layer

#### Server (`src/cgm_mcp/server.py`)
- Implements MCP protocol handlers
- Manages tool calls and resource requests
- Handles client communication
- Coordinates the CGM pipeline

#### Tools
- `cgm_process_issue`: Main tool for processing repository issues
- `cgm_get_task_status`: Query task status
- `cgm_health_check`: Server health monitoring

#### Resources
- `cgm://health`: Server health information
- `cgm://tasks`: Active task information

### 2. CGM Core Pipeline

#### Rewriter (`src/cgm_mcp/components/rewriter.py`)
**Purpose**: Analyze and rewrite problem statements to extract relevant information.

**Functionality**:
- Extract code entities (files, classes, functions)
- Generate keywords related to the issue
- Create search queries for code retrieval
- Support both extraction and inference modes

**Input**: Problem statement, repository name
**Output**: Analysis, entities, keywords, queries

#### Retriever (`src/cgm_mcp/components/retriever.py`)
**Purpose**: Locate relevant code subgraphs based on extracted information.

**Functionality**:
- Find anchor nodes in the code graph
- Extract relevant subgraphs around anchor nodes
- Use fuzzy matching for entity location
- Support keyword and query-based search

**Input**: Entities, keywords, queries, code graph
**Output**: Anchor nodes, subgraph, relevant files

#### Reranker (`src/cgm_mcp/components/reranker.py`)
**Purpose**: Rank files by relevance to focus analysis on most important code.

**Functionality**:
- Two-stage ranking process
- Stage 1: Select top relevant files
- Stage 2: Score individual files (1-5 scale)
- LLM-based relevance assessment

**Input**: Problem statement, file lists, file contents
**Output**: Top-ranked files, detailed scores

#### Reader (`src/cgm_mcp/components/reader.py`)
**Purpose**: Generate specific code patches to resolve issues.

**Functionality**:
- Analyze issue context and code structure
- Generate targeted code modifications
- Provide explanations for changes
- Calculate confidence scores

**Input**: Problem statement, subgraph, top files
**Output**: Code patches, summary, confidence

### 3. Support Services

#### Graph Builder (`src/cgm_mcp/components/graph_builder.py`)
**Purpose**: Construct repository-level code graphs.

**Functionality**:
- Parse source code files (Python, JavaScript, etc.)
- Extract code structure (classes, functions, imports)
- Build graph relationships
- Support multiple programming languages

**Features**:
- AST-based Python analysis
- Generic analysis for other languages
- Configurable graph size limits
- Caching support

#### LLM Client (`src/cgm_mcp/utils/llm_client.py`)
**Purpose**: Provide unified interface to multiple LLM providers.

**Supported Providers**:
- OpenAI (GPT-3.5, GPT-4)
- Anthropic (Claude)
- Mock (for testing)

**Features**:
- Async API calls
- Error handling and retries
- Health checking
- Batch processing

#### Configuration (`src/cgm_mcp/utils/config.py`)
**Purpose**: Manage server configuration from multiple sources.

**Configuration Sources**:
- Environment variables
- JSON configuration files
- Command-line arguments
- Default values

**Configuration Sections**:
- LLM settings (provider, model, API keys)
- Graph processing limits
- Server settings (logging, timeouts)

## Data Flow

### Issue Processing Flow

```
1. Issue Input
   ├─ Task Type (issue_resolution, code_analysis, etc.)
   ├─ Repository Name
   ├─ Issue Description
   └─ Repository Context

2. Rewriter Stage
   ├─ Generate extraction/inference prompts
   ├─ Call LLM for analysis
   ├─ Parse response for entities/keywords
   └─ Output: Analysis, entities, keywords, queries

3. Graph Building
   ├─ Locate repository path
   ├─ Parse source files
   ├─ Build code graph
   └─ Output: NetworkX graph structure

4. Retriever Stage
   ├─ Locate anchor nodes using entities/keywords
   ├─ Extract subgraph around anchors
   ├─ Identify relevant files
   └─ Output: Subgraph, anchor nodes, file list

5. Reranker Stage
   ├─ Stage 1: Select top files using LLM
   ├─ Stage 2: Score each file (1-5)
   ├─ Rank by relevance scores
   └─ Output: Top files, detailed scores

6. Reader Stage
   ├─ Generate patch prompts with context
   ├─ Call LLM for code generation
   ├─ Parse patches and explanations
   └─ Output: Code patches, confidence score

7. Response Assembly
   ├─ Combine all stage results
   ├─ Calculate processing time
   ├─ Store task for status queries
   └─ Return complete response
```

### Error Handling

```
┌─────────────────┐
│   Error Occurs  │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  Log Error      │
│  (with context) │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Update Task     │
│ Status to       │
│ "failed"        │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Return Error    │
│ Response to     │
│ Client          │
└─────────────────┘
```

## Design Principles

### 1. Modularity
- Each component has a single responsibility
- Clear interfaces between components
- Easy to test and maintain individual parts

### 2. Async/Await Pattern
- Non-blocking I/O operations
- Concurrent processing where possible
- Responsive to client requests

### 3. Configuration-Driven
- Flexible configuration from multiple sources
- Environment-specific settings
- Runtime configuration updates

### 4. Error Resilience
- Graceful error handling at each stage
- Detailed error logging
- Partial results when possible

### 5. Extensibility
- Plugin architecture for new LLM providers
- Support for additional programming languages
- Configurable pipeline stages

## Performance Considerations

### Graph Processing
- Configurable node/edge limits
- Efficient subgraph extraction
- Caching of built graphs

### LLM Calls
- Async processing
- Batch operations where possible
- Timeout handling

### Memory Management
- Streaming for large files
- Garbage collection of completed tasks
- Configurable cache sizes

## Security Considerations

### API Key Management
- Environment variable storage
- No logging of sensitive data
- Secure configuration file handling

### Code Access
- Sandboxed repository access
- Path validation
- File size limits

### Input Validation
- Request parameter validation
- Sanitization of user inputs
- Rate limiting (future enhancement)

## Monitoring and Observability

### Logging
- Structured logging with loguru
- Configurable log levels
- Component-specific loggers

### Health Checks
- Component health monitoring
- LLM provider availability
- Resource usage tracking

### Metrics (Future)
- Processing time tracking
- Success/failure rates
- Resource utilization

## Future Enhancements

### Planned Features
- Support for more programming languages
- Advanced graph analysis algorithms
- Distributed processing capabilities
- Web UI for monitoring and debugging
- Integration with version control systems

### Performance Improvements
- Graph caching and persistence
- Parallel processing of pipeline stages
- Optimized LLM prompt engineering
- Result caching and memoization
