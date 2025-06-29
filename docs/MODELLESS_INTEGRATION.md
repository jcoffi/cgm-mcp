# 模型无关的 CGM MCP 服务集成指南

本文档说明如何使用模型无关的 CGM MCP 服务，让任何 AI 模型都能利用 CGM 的代码分析能力。

## 🎯 核心概念

模型无关的 CGM 服务将代码分析能力从特定的 LLM 实现中剥离出来，提供纯粹的工具和上下文服务：

- **无需 API 密钥** - 不依赖任何特定的 LLM 提供商
- **纯工具服务** - 提供结构化的代码分析结果
- **通用集成** - 可与任何 AI 模型或 IDE 集成
- **高性能缓存** - 分析结果可缓存和重用

## 🚀 快速开始

### 1. 启动模型无关服务

```bash
# 启动模型无关的 CGM 服务
python main_modelless.py

# 或使用自定义配置
python main_modelless.py --config config.json --log-level DEBUG
```

### 2. 可用工具

服务提供以下 MCP 工具：

#### `cgm_analyze_repository`
分析仓库结构并提取代码上下文

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
获取特定文件的详细内容和分析

```json
{
  "repository_path": "/path/to/repo",
  "file_paths": ["src/main.py", "src/utils.py"]
}
```

#### `cgm_find_related_code`
查找与特定实体相关的代码

```json
{
  "repository_path": "/path/to/repo",
  "entity_name": "UserModel",
  "relation_types": ["contains", "imports", "inherits"]
}
```

#### `cgm_extract_context`
提取结构化上下文供外部模型使用

```json
{
  "repository_path": "/path/to/repo",
  "query": "user authentication",
  "format": "prompt"  // structured, markdown, prompt
}
```

## 🔧 在不同环境中集成

### Augment 集成

#### MCP 配置
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

#### 使用示例
```
@cgm-modelless 分析当前仓库的认证系统

工具调用：cgm_analyze_repository
参数：{
  "repository_path": "/workspace/current",
  "query": "authentication system",
  "analysis_scope": "focused"
}
```

### Cursor 集成

#### 配置
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

#### 使用方式
1. **命令面板**: `Ctrl+Shift+P` → "CGM Analyze Repository"
2. **聊天界面**: `@cgm-modelless 分析这个文件的结构`
3. **右键菜单**: 选中代码 → "CGM Analysis"

### Claude Desktop 集成

#### 配置文件 (`claude_desktop_config.json`)
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

#### 使用示例
```
请使用 CGM 工具分析这个项目的代码结构，重点关注用户认证部分。

然后基于分析结果，帮我：
1. 理解认证流程
2. 识别潜在的安全问题
3. 建议改进方案
```

### VS Code 扩展集成

#### 扩展配置
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

## 🔄 工作流示例

### 1. 代码审查工作流

```python
# 1. 分析仓库
analysis = cgm_analyze_repository({
    "repository_path": "/project",
    "query": "security vulnerabilities",
    "analysis_scope": "full"
})

# 2. 获取关键文件详情
files = cgm_get_file_content({
    "repository_path": "/project", 
    "file_paths": analysis["key_files"]
})

# 3. 查找相关代码
related = cgm_find_related_code({
    "repository_path": "/project",
    "entity_name": "authenticate_user"
})

# 4. 生成审查报告
context = cgm_extract_context({
    "repository_path": "/project",
    "query": "security analysis",
    "format": "markdown"
})
```

### 2. 功能开发工作流

```python
# 1. 理解现有代码结构
structure = cgm_analyze_repository({
    "repository_path": "/project",
    "query": "user management system"
})

# 2. 找到相关组件
components = cgm_find_related_code({
    "repository_path": "/project", 
    "entity_name": "User"
})

# 3. 获取实现上下文
context = cgm_extract_context({
    "repository_path": "/project",
    "query": "user management implementation",
    "format": "prompt"
})

# 4. 基于上下文开发新功能
```

### 3. Bug 修复工作流

```python
# 1. 分析问题相关代码
bug_analysis = cgm_analyze_repository({
    "repository_path": "/project",
    "query": "authentication error login failure",
    "focus_files": ["auth/views.py", "auth/models.py"]
})

# 2. 获取详细文件内容
file_details = cgm_get_file_content({
    "repository_path": "/project",
    "file_paths": bug_analysis["relevant_files"]
})

# 3. 查找相关依赖
dependencies = cgm_find_related_code({
    "repository_path": "/project",
    "entity_name": "login_view"
})
```

## 🎛️ 高级配置

### 缓存配置
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

### 分析配置
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

### 性能配置
```json
{
  "performance": {
    "concurrent_files": 5,
    "timeout": 30,
    "memory_limit": "1GB"
  }
}
```

## 🔍 故障排除

### 常见问题

#### 1. 分析超时
```bash
# 增加超时时间
python main_modelless.py --timeout 60

# 或减少分析范围
{
  "analysis_scope": "minimal",
  "max_files": 5
}
```

#### 2. 内存使用过高
```bash
# 限制文件大小
python main_modelless.py --max-file-size 512000

# 或使用更小的分析范围
{
  "analysis_scope": "focused",
  "max_files": 3
}
```

#### 3. 缓存问题
```bash
# 清理缓存
rm -rf ~/.cgm_cache

# 或禁用缓存
{
  "cache": {"enabled": false}
}
```

## 📈 性能优化

### 1. 缓存策略
- 启用分析结果缓存
- 使用持久化缓存
- 定期清理过期缓存

### 2. 分析优化
- 限制文件大小和数量
- 使用合适的分析范围
- 排除不必要的文件类型

### 3. 并发控制
- 限制并发文件分析数量
- 使用异步处理
- 实现请求队列

## 🚀 最佳实践

1. **渐进式分析**: 先用 `minimal` 范围快速了解，再用 `focused` 深入分析
2. **缓存利用**: 对相同查询启用缓存，提高响应速度
3. **格式选择**: 根据用途选择合适的输出格式
4. **错误处理**: 实现优雅的错误处理和降级策略
5. **资源管理**: 监控内存和 CPU 使用，避免资源耗尽

## 🔮 未来扩展

- 支持更多编程语言
- 增强代码关系分析
- 实现分布式分析
- 添加代码质量评估
- 集成版本控制信息
