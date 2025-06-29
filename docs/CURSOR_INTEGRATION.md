# Cursor 集成指南

本文档说明如何在 Cursor IDE 中集成和使用 CGM MCP 服务。

## 配置 Cursor MCP 扩展

### 1. 安装 MCP 扩展

在 Cursor 中安装 MCP 扩展：

1. 打开 Cursor
2. 进入扩展市场
3. 搜索 "Model Context Protocol" 或 "MCP"
4. 安装官方 MCP 扩展

### 2. 配置 MCP 服务器

在 Cursor 设置中添加 CGM MCP 服务器配置：

```json
{
  "mcp.servers": {
    "cgm": {
      "command": "python",
      "args": ["/path/to/cgm-mcp/main.py"],
      "cwd": "/path/to/cgm-mcp",
      "env": {
        "CGM_LLM_PROVIDER": "cursor_native",
        "CGM_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 3. 使用 Cursor 内置模型

创建 Cursor 原生客户端：

```python
class CursorNativeClient(BaseLLMClient):
    """Cursor 原生 LLM 客户端"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        
    async def generate(self, prompt: str, **kwargs) -> str:
        """使用 Cursor 内置模型"""
        try:
            # 使用 Cursor 的内置 API 或通过扩展接口
            # 这里需要根据 Cursor 的具体实现方式
            
            # 方案1: 通过 Cursor 扩展 API
            import cursor_api
            response = await cursor_api.complete(
                prompt=prompt,
                model=self.config.model or "cursor-default",
                temperature=kwargs.get("temperature", self.config.temperature)
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Cursor API error: {e}")
            # 降级到本地模型或其他提供商
            raise
            
    async def health_check(self) -> bool:
        """检查 Cursor API 状态"""
        try:
            import cursor_api
            return cursor_api.is_available()
        except:
            return False
```

## 本地模型服务配置

### 1. 使用 Ollama 本地服务

#### 安装和启动 Ollama

```bash
# 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 启动服务
ollama serve

# 下载推荐模型
ollama pull codellama:13b
ollama pull deepseek-coder:6.7b
ollama pull qwen2.5-coder:7b
```

#### 配置 Ollama 客户端

```python
class OllamaClient(BaseLLMClient):
    """Ollama 本地模型客户端"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.api_base or "http://localhost:11434"
        
    async def generate(self, prompt: str, **kwargs) -> str:
        """使用 Ollama 生成文本"""
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                payload = {
                    "model": self.config.model or "codellama:13b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature),
                        "num_predict": kwargs.get("max_tokens", self.config.max_tokens)
                    }
                }
                
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                return data["response"]
                
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise
```

### 2. 使用 LM Studio

#### 配置 LM Studio

```bash
# 下载并启动 LM Studio
# 在 LM Studio 中加载模型，启动本地服务器
# 默认端口: http://localhost:1234
```

#### LM Studio 客户端

```python
class LMStudioClient(BaseLLMClient):
    """LM Studio 本地模型客户端"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.api_base or "http://localhost:1234/v1"
        
    async def generate(self, prompt: str, **kwargs) -> str:
        """使用 LM Studio 生成文本"""
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                payload = {
                    "model": self.config.model or "local-model",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "max_tokens": kwargs.get("max_tokens", self.config.max_tokens)
                }
                
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.error(f"LM Studio API error: {e}")
            raise
```

## 推荐模型配置

### 1. 代码理解和生成模型

#### 高性能模型 (推荐)
```bash
# Ollama 模型
ollama pull deepseek-coder:33b      # 最佳代码理解
ollama pull codellama:34b           # Meta 官方代码模型
ollama pull qwen2.5-coder:32b       # 阿里巴巴代码模型

# LM Studio 模型 (HuggingFace)
- deepseek-ai/deepseek-coder-33b-instruct-gguf
- codellama/CodeLlama-34b-Instruct-hf
- Qwen/Qwen2.5-Coder-32B-Instruct
```

#### 中等性能模型 (平衡)
```bash
# Ollama 模型
ollama pull deepseek-coder:6.7b
ollama pull codellama:13b
ollama pull qwen2.5-coder:7b

# LM Studio 模型
- deepseek-ai/deepseek-coder-6.7b-instruct-gguf
- codellama/CodeLlama-13b-Instruct-hf
- Qwen/Qwen2.5-Coder-7B-Instruct
```

#### 轻量级模型 (快速)
```bash
# Ollama 模型
ollama pull deepseek-coder:1.3b
ollama pull codellama:7b
ollama pull starcoder2:3b

# LM Studio 模型
- deepseek-ai/deepseek-coder-1.3b-instruct-gguf
- bigcode/starcoder2-3b
```

### 2. 配置文件示例

#### 本地 Ollama 配置
```json
{
  "llm": {
    "provider": "ollama",
    "model": "deepseek-coder:6.7b",
    "api_base": "http://localhost:11434",
    "temperature": 0.1,
    "max_tokens": 4000,
    "timeout": 120
  }
}
```

#### LM Studio 配置
```json
{
  "llm": {
    "provider": "lmstudio",
    "model": "deepseek-coder-6.7b-instruct",
    "api_base": "http://localhost:1234/v1",
    "temperature": 0.1,
    "max_tokens": 4000,
    "timeout": 120
  }
}
```

## 在 Cursor 中使用

### 1. 通过命令面板

1. 按 `Ctrl+Shift+P` (Windows/Linux) 或 `Cmd+Shift+P` (Mac)
2. 输入 "CGM" 查找 CGM 相关命令
3. 选择相应的命令执行

### 2. 通过聊天界面

在 Cursor 的聊天界面中：

```
@cgm 分析当前文件的代码结构，找出潜在问题

@cgm 处理这个 bug：
用户登录时密码验证失败，错误信息：
ValidationError: Special characters not properly escaped
```

### 3. 通过右键菜单

1. 选中代码片段
2. 右键选择 "CGM Analysis"
3. 选择分析类型

## 性能优化建议

### 1. 模型选择策略

```python
# 根据任务类型选择模型
MODEL_MAPPING = {
    "code_analysis": "deepseek-coder:6.7b",
    "bug_fixing": "codellama:13b", 
    "feature_implementation": "qwen2.5-coder:7b",
    "quick_analysis": "deepseek-coder:1.3b"
}
```

### 2. 缓存策略

```json
{
  "graph": {
    "cache_enabled": true,
    "cache_ttl": 3600,
    "persistent_cache": true
  }
}
```

### 3. 并发控制

```json
{
  "server": {
    "max_concurrent_tasks": 2,
    "task_timeout": 300,
    "queue_size": 10
  }
}
```

## 故障排除

### 常见问题

1. **模型加载失败**
   ```bash
   # 检查模型状态
   ollama list
   
   # 重新下载模型
   ollama pull deepseek-coder:6.7b
   ```

2. **连接超时**
   ```json
   {
     "llm": {
       "timeout": 300,
       "max_retries": 3
     }
   }
   ```

3. **内存不足**
   ```bash
   # 使用更小的模型
   ollama pull deepseek-coder:1.3b
   
   # 或者调整模型参数
   ollama run deepseek-coder:6.7b --num-gpu 0
   ```

## 最佳实践

1. **模型选择**
   - 开发阶段：使用轻量级模型 (1.3B-3B)
   - 生产环境：使用中等模型 (6.7B-13B)
   - 复杂任务：使用大型模型 (33B+)

2. **资源管理**
   - 监控 GPU/CPU 使用率
   - 设置合理的超时时间
   - 启用缓存机制

3. **工作流优化**
   - 批量处理相似任务
   - 预热模型服务
   - 定期清理缓存
