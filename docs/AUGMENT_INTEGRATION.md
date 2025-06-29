# Augment 集成指南

本文档说明如何在 Augment 中集成和使用 CGM MCP 服务。

## 配置 MCP 服务器

### 1. 创建 Augment MCP 配置

在 Augment 的配置目录中创建 MCP 配置文件：

```json
{
  "mcpServers": {
    "cgm": {
      "command": "python",
      "args": ["/path/to/cgm-mcp/main.py"],
      "env": {
        "CGM_LLM_PROVIDER": "augment_native",
        "CGM_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 2. 使用 Augment 内置模型

修改 `src/cgm_mcp/utils/llm_client.py` 添加 Augment 原生支持：

```python
class AugmentNativeClient(BaseLLMClient):
    """Augment 原生 LLM 客户端，使用 Augment 内置模型能力"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        # 使用 Augment 的内置 API
        
    async def generate(self, prompt: str, **kwargs) -> str:
        """使用 Augment 内置模型生成文本"""
        try:
            # 调用 Augment 内置模型 API
            # 这里需要根据 Augment 的具体 API 进行实现
            from augment_api import generate_text
            
            response = await generate_text(
                prompt=prompt,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens)
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Augment API error: {e}")
            raise
            
    async def health_check(self) -> bool:
        """检查 Augment API 健康状态"""
        try:
            from augment_api import health_check
            return await health_check()
        except:
            return False
```

### 3. 环境配置

创建专用的 Augment 环境配置：

```bash
# .env.augment
CGM_LLM_PROVIDER=augment_native
CGM_LOG_LEVEL=INFO
CGM_GRAPH_MAX_NODES=5000
CGM_GRAPH_MAX_EDGES=25000
CGM_MAX_CONCURRENT_TASKS=5
```

### 4. 启动脚本

```bash
#!/bin/bash
# scripts/start_augment.sh

export $(cat .env.augment | xargs)
python main.py --config config.augment.json
```

## 在 Augment 中使用

### 1. 基本使用

在 Augment 中，您可以直接调用 CGM 工具：

```
@cgm 请分析这个仓库中的认证模块，找出可能的安全漏洞

Repository: my-project
Issue: 用户登录时密码验证存在问题
```

### 2. 高级用法

```
@cgm 处理以下问题：

Task Type: issue_resolution
Repository: /workspace/my-app
Issue: 
当用户密码包含特殊字符时登录失败

错误日志：
File "auth/views.py", line 45, in authenticate_user
    if validate_password(password):
ValidationError: Special characters not properly escaped

请生成修复补丁。
```

### 3. 代码分析

```
@cgm 分析代码结构

Task Type: code_analysis  
Repository: current
Focus: 分析整个认证系统的架构，识别潜在的设计问题
```

## 性能优化

### 1. 缓存配置

```json
{
  "graph": {
    "cache_enabled": true,
    "cache_ttl": 7200,
    "max_nodes": 5000,
    "max_edges": 25000
  }
}
```

### 2. 并发限制

```json
{
  "server": {
    "max_concurrent_tasks": 3,
    "task_timeout": 180
  }
}
```

## 故障排除

### 常见问题

1. **模型调用失败**
   - 检查 Augment API 连接
   - 验证权限配置
   - 查看日志文件

2. **性能问题**
   - 减少图节点限制
   - 启用缓存
   - 调整并发数量

3. **内存使用过高**
   - 限制仓库大小
   - 清理缓存
   - 重启服务

### 调试模式

```bash
python main.py --log-level DEBUG
```

## 最佳实践

1. **仓库准备**
   - 确保代码结构清晰
   - 添加适当的文档注释
   - 保持合理的文件大小

2. **问题描述**
   - 提供详细的错误信息
   - 包含相关的代码片段
   - 说明预期行为

3. **性能监控**
   - 定期检查服务状态
   - 监控资源使用情况
   - 优化配置参数
