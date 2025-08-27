# Model-agnostic CGM MCP Service Integration Guide

This document explains how to use the model-agnostic CGM MCP service, allowing any AI model to leverage CGM's code analysis capabilities.

## 🎯 Core Concepts

The model-agnostic CGM service separates code analysis capabilities from specific LLM implementations, providing pure tool and context services:

- **No API Keys Required** - Independent of any specific LLM provider
- **Pure Tool Service** - Provides structured code analysis results
- **Universal Integration** - Can integrate with any AI model or IDE
- **High-performance Caching** - Analysis results can be cached and reused

## 🚀 Quick Start

### 1. Start Model-agnostic Service

```bash
# Start model-agnostic CGM service
python main_modelless.py

# Or use custom configuration
python main_modelless.py --config config.json --log-level DEBUG
```

### 2. Available Tools

The service provides the following MCP tools:

#### `cgm_analyze_repository`
Analyze repository structure and extract code context

```json
{
  "repository_path": "/path/to/repo",
  "query": "authentication system",
  "analysis_scope": "focused",
  "focus_files": ["auth/models.py", "auth/views.py"],
  "max_files": 10
}
```

#### `cgm_get_file_content`
Get detailed content and analysis of specific files

```json
{
  "repository_path": "/path/to/repo",
  "file_paths": ["src/main.py", "src/utils.py"]
}
```

#### `cgm_find_related_code`
Find code related to specific entities

```json
{
  "repository_path": "/path/to/repo",
  "entity_name": "UserModel",
  "relation_types": ["contains", "imports", "inherits"]
}
```

#### `cgm_extract_context`
Extract structured context for external model consumption

```json
{
  "repository_path": "/path/to/repo",
  "query": "user authentication",
  "format": "prompt"  // structured, markdown, prompt
}
```

## 🔧 Integration in Different Environments

### Augment Integration

#### MCP Configuration
```json
{
  "mcpServers": {
    "cgm-modelless": {
      "command": "python",
      "args": ["/path/to/cgm-mcp/main_modelless.py"],
      "env": {
        "CGM_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

#### Usage Example
```
@cgm-modelless Analyze the authentication system in the current repository

Tool call: cgm_analyze_repository
Parameters: {
  "repository_path": "/workspace/current",
  "query": "authentication system",
  "analysis_scope": "focused"
}
```

### Cursor Integration

#### Configuration
```json
{
  "mcp.servers": {
    "cgm-modelless": {
      "command": "python",
      "args": ["/path/to/cgm-mcp/main_modelless.py"],
      "cwd": "/path/to/cgm-mcp"
    }
  }
}
```

#### Usage Methods
1. **Command Palette**: `Ctrl+Shift+P` → "CGM Analyze Repository"
2. **Chat Interface**: `@cgm-modelless Analyze the structure of this file`
3. **Context Menu**: Select code → "CGM Analysis"

### Claude Desktop Integration

#### Configuration File (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "cgm-modelless": {
      "command": "python",
      "args": ["/path/to/cgm-mcp/main_modelless.py"]
    }
  }
}
```

#### Usage Example
```
Please use the CGM tool to analyze this project's code structure, focusing on the user authentication parts.

Then based on the analysis results, help me:
1. Understand the authentication flow
2. Identify potential security issues
3. Suggest improvements
```

### VS Code Extension Integration

#### Extension Configuration
```json
{
  "cgm.serverPath": "/path/to/cgm-mcp/main_modelless.py",
  "cgm.autoAnalyze": true,
  "cgm.cacheResults": true
}
```

## 📊 输出格式

### 结构化格式 (JSON)
```json
{
  "repository_path": "/path/to/repo",
  "code_graph": {
    "files": ["src/main.py", "src/auth.py"],
    "entities": [
      {
        "id": "class:src/auth.py:UserAuth",
        "type": "class",
        "name": "UserAuth",
        "file_path": "src/auth.py",
        "metadata": {"methods": ["login", "logout"]}
      }
    ]
  },
  "relevant_entities": [...],
  "file_analyses": [...],
  "context_summary": "Repository contains authentication system..."
}
```

### Markdown 格式
```markdown
# Code Analysis: /path/to/repo

Repository contains authentication system with 15 files and 45 code entities.

## Relevant Code Entities

### Class: UserAuth
**File:** `src/auth.py`
**Preview:** User authentication class that handles login/logout...

### Function: validate_password
**File:** `src/utils.py`
**Preview:** Password validation function with security checks...
```

### Prompt 格式
```
# Repository Code Context
Repository: /path/to/repo
Analysis Summary: Repository contains authentication system...

## Code Structure

### Classes:
- UserAuth (in src/auth.py)
- PasswordValidator (in src/utils.py)

### Functions:
- login_user (in src/auth.py)
- validate_password (in src/utils.py)

## Key File Contents

### File: src/auth.py
```python
class UserAuth:
    def login(self, username, password):
        # Authentication logic
        ...
```

Use this context to understand the codebase structure and relationships.
```

## 🔄 Workflow Examples

### 1. Code Review Workflow

```python
# 1. Analyze repository
analysis = cgm_analyze_repository({
    "repository_path": "/project",
    "query": "security vulnerabilities",
    "analysis_scope": "full"
})

# 2. Get key file details
files = cgm_get_file_content({
    "repository_path": "/project", 
    "file_paths": analysis["key_files"]
})

# 3. Find related code
related = cgm_find_related_code({
    "repository_path": "/project",
    "entity_name": "authenticate_user"
})

# 4. Generate review report
context = cgm_extract_context({
    "repository_path": "/project",
    "query": "security analysis",
    "format": "markdown"
})
```

### 2. Feature Development Workflow

```python
# 1. Understand existing code structure
structure = cgm_analyze_repository({
    "repository_path": "/project",
    "query": "user management system"
})

# 2. Find related components
components = cgm_find_related_code({
    "repository_path": "/project", 
    "entity_name": "User"
})

# 3. Get implementation context
context = cgm_extract_context({
    "repository_path": "/project",
    "query": "user management implementation",
    "format": "prompt"
})

# 4. Develop new features based on context
```

### 3. Bug Fix Workflow

```python
# 1. Analyze problem-related code
bug_analysis = cgm_analyze_repository({
    "repository_path": "/project",
    "query": "authentication error login failure",
    "focus_files": ["auth/views.py", "auth/models.py"]
})

# 2. Get detailed file content
file_details = cgm_get_file_content({
    "repository_path": "/project",
    "file_paths": bug_analysis["relevant_files"]
})

# 3. Find related dependencies
dependencies = cgm_find_related_code({
    "repository_path": "/project",
    "entity_name": "login_view"
})
```

## 🎛️ Advanced Configuration

### Cache Configuration
```json
{
  "cache": {
    "enabled": true,
    "ttl": 3600,
    "max_size": 100,
    "persist": true
  }
}
```

### Analysis Configuration
```json
{
  "analysis": {
    "max_file_size": 1048576,
    "supported_extensions": [".py", ".js", ".ts", ".java"],
    "exclude_patterns": ["*/node_modules/*", "*/__pycache__/*"],
    "max_depth": 10
  }
}
```

### Performance Configuration
```json
{
  "performance": {
    "concurrent_files": 5,
    "timeout": 30,
    "memory_limit": "1GB"
  }
}
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Analysis Timeout
```bash
# Increase timeout
python main_modelless.py --timeout 60

# Or reduce analysis scope
{
  "analysis_scope": "minimal",
  "max_files": 5
}
```

#### 2. High Memory Usage
```bash
# Limit file size
python main_modelless.py --max-file-size 512000

# Or use smaller analysis scope
{
  "analysis_scope": "focused",
  "max_files": 3
}
```

#### 3. Cache Issues
```bash
# Clear cache
rm -rf ~/.cgm_cache

# Or disable caching
{
  "cache": {"enabled": false}
}
```

## 📈 Performance Optimization

### 1. Caching Strategy
- Enable analysis result caching
- Use persistent caching
- Regularly clean up expired cache

### 2. Analysis Optimization
- Limit file size and quantity
- Use appropriate analysis scope
- Exclude unnecessary file types

### 3. Concurrency Control
- Limit concurrent file analysis count
- Use asynchronous processing
- Implement request queuing

## 🚀 Best Practices

1. **Progressive Analysis**: Start with `minimal` scope for quick overview, then use `focused` for deep analysis
2. **Cache Utilization**: Enable caching for same queries to improve response speed
3. **Format Selection**: Choose appropriate output format based on usage
4. **Error Handling**: Implement graceful error handling and fallback strategies
5. **Resource Management**: Monitor memory and CPU usage to avoid resource exhaustion

## 🔮 Future Extensions

- Support for more programming languages
- Enhanced code relationship analysis
- Distributed analysis implementation
- Code quality assessment additions
- Version control information integration
