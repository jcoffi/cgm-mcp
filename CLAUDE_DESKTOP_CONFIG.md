# Claude Desktop MCP Configuration Examples

## CGM MCP Server (Full LLM Integration)

### Configuration for Claude Desktop
Add this to your Claude Desktop configuration file:

#### Option 1: Using uvx (recommended)
```json
{
  "mcpServers": {
    "cgm-mcp": {
      "command": "uvx",
      "args": ["cgm-mcp", "--config", "/path/to/cgm-mcp/config-cgm-mcp.json"],
      "env": {
        "CGM_LLM_API_KEY": "your-anthropic-api-key-here"
      }
    }
  }
}
```

#### Option 2: Using pip-installed package
```json
{
  "mcpServers": {
    "cgm-mcp": {
      "command": "cgm-mcp",
      "args": ["--config", "/path/to/cgm-mcp/config-cgm-mcp.json"],
      "env": {
        "CGM_LLM_API_KEY": "your-anthropic-api-key-here"
      }
    }
  }
}
```

#### Option 3: Direct Python execution
```json
{
  "mcpServers": {
    "cgm-mcp": {
      "command": "python",
      "args": ["/path/to/cgm-mcp/main.py", "--config", "/path/to/cgm-mcp/config-cgm-mcp.json"],
      "env": {
        "CGM_LLM_API_KEY": "your-anthropic-api-key-here"
      }
    }
  }
}
```

### Environment Variables (Alternative)
```bash
export CGM_LLM_PROVIDER=anthropic
export CGM_LLM_MODEL=claude-sonnet-4-20250514
export CGM_LLM_API_KEY=your-anthropic-api-key-here
```

### JSON Config File: config-cgm-mcp.json
```json
{
  "llm": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.1,
    "max_tokens": 4000,
    "timeout": 60
  },
  "graph": {
    "max_nodes": 10000,
    "max_edges": 50000,
    "cache_enabled": true,
    "cache_ttl": 3600
  },
  "server": {
    "host": "localhost",
    "port": 8000,
    "log_level": "INFO",
    "max_concurrent_tasks": 10,
    "task_timeout": 300
  }
}
```

### Available Tools
- `cgm_process_issue` - Process repository issues using CGM framework
- `cgm_get_task_status` - Get the status of a CGM task
- `cgm_health_check` - Check CGM server health status

---

## CGM MCP Modelless Server (Code Analysis Only)

### Configuration for Claude Desktop

#### Option 1: Using uvx (recommended)
```json
{
  "mcpServers": {
    "cgm-mcp-modelless": {
      "command": "uvx",
      "args": ["cgm-mcp-modelless", "--config", "/path/to/cgm-mcp/config-cgm-mcp-modelless.json"]
    }
  }
}
```

#### Option 2: Using pip-installed package
```json
{
  "mcpServers": {
    "cgm-mcp-modelless": {
      "command": "cgm-mcp-modelless",
      "args": ["--config", "/path/to/cgm-mcp/config-cgm-mcp-modelless.json"]
    }
  }
}
```

#### Option 3: Direct Python execution
```json
{
  "mcpServers": {
    "cgm-mcp-modelless": {
      "command": "python",
      "args": ["/path/to/cgm-mcp/main_modelless.py", "--config", "/path/to/cgm-mcp/config-cgm-mcp-modelless.json"]
    }
  }
}
```

### JSON Config File: config-cgm-mcp-modelless.json
```json
{
  "graph": {
    "max_nodes": 10000,
    "max_edges": 50000,
    "cache_enabled": true,
    "cache_ttl": 3600
  },
  "server": {
    "host": "localhost",
    "port": 8000,
    "log_level": "INFO",
    "max_concurrent_tasks": 10,
    "task_timeout": 300
  }
}
```

### Available Tools
- `cgm_analyze_repository` - Analyze repository structure and extract code context
- `cgm_get_file_content` - Get detailed content and analysis of specific files
- `cgm_find_related_code` - Find code entities related to a specific entity or concept
- `cgm_extract_context` - Extract structured context for external model consumption
- `clear_gpu_cache` - Clear GPU caches to free memory

---

## Usage Examples

### Starting Servers Manually

#### Using uvx (recommended - no installation needed):
**Full CGM MCP Server:**
```bash
export CGM_LLM_API_KEY=your-api-key
uvx cgm-mcp --config config-cgm-mcp.json
```

**Modelless CGM MCP Server:**
```bash
uvx cgm-mcp-modelless --config config-cgm-mcp-modelless.json
```

#### Using pip-installed package:
First install the package:
```bash
pip install cgm-mcp
```

Then run:
**Full CGM MCP Server:**
```bash
export CGM_LLM_API_KEY=your-api-key
cgm-mcp --config config-cgm-mcp.json
```

**Modelless CGM MCP Server:**
```bash
cgm-mcp-modelless --config config-cgm-mcp-modelless.json
```

#### Using direct Python execution:
**Full CGM MCP Server:**
```bash
cd /path/to/cgm-mcp
export CGM_LLM_API_KEY=your-api-key
python main.py --config config-cgm-mcp.json
```

**Modelless CGM MCP Server:**
```bash
cd /path/to/cgm-mcp
python main_modelless.py --config config-cgm-mcp-modelless.json
```

### Testing Tools

Both servers can be tested using the MCP protocol. The tools will appear in Claude Desktop once properly configured.

### Performance Tuning

- Adjust `max_nodes` and `max_edges` based on repository size
- Set `cache_ttl` for how long to cache analysis results
- Configure `max_concurrent_tasks` based on system resources
- Use GPU acceleration by ensuring CuPy is installed (automatically included)
