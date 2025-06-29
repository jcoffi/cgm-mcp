"""
Configuration management for CGM MCP Server
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv


@dataclass
class LLMConfig:
    """LLM configuration"""

    provider: str = "openai"  # openai, anthropic, azure, etc.
    model: str = "gpt-4"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout: int = 60

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMConfig":
        return cls(**data)


@dataclass
class GraphConfig:
    """Graph processing configuration"""

    max_nodes: int = 10000
    max_edges: int = 50000
    cache_enabled: bool = True
    cache_ttl: int = 3600  # seconds

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphConfig":
        return cls(**data)


@dataclass
class ServerConfig:
    """Server configuration"""

    host: str = "localhost"
    port: int = 8000
    log_level: str = "INFO"
    max_concurrent_tasks: int = 10
    task_timeout: int = 300  # seconds

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServerConfig":
        return cls(**data)


@dataclass
class Config:
    """Main configuration class"""

    llm_config: LLMConfig = field(default_factory=LLMConfig)
    graph_config: GraphConfig = field(default_factory=GraphConfig)
    server_config: ServerConfig = field(default_factory=ServerConfig)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration from file and environment variables"""

        # Load environment variables
        load_dotenv()

        # Default configuration
        config_data = {}

        # Load from config file if provided
        if config_path and Path(config_path).exists():
            with open(config_path, "r") as f:
                config_data = json.load(f)

        # Override with environment variables
        llm_config_data = config_data.get("llm", {})
        llm_config_data.update(
            {
                "provider": os.getenv(
                    "CGM_LLM_PROVIDER", llm_config_data.get("provider", "openai")
                ),
                "model": os.getenv(
                    "CGM_LLM_MODEL", llm_config_data.get("model", "gpt-4")
                ),
                "api_key": os.getenv("CGM_LLM_API_KEY", llm_config_data.get("api_key")),
                "api_base": os.getenv(
                    "CGM_LLM_API_BASE", llm_config_data.get("api_base")
                ),
                "temperature": float(
                    os.getenv(
                        "CGM_LLM_TEMPERATURE", llm_config_data.get("temperature", 0.1)
                    )
                ),
                "max_tokens": int(
                    os.getenv(
                        "CGM_LLM_MAX_TOKENS", llm_config_data.get("max_tokens", 4000)
                    )
                ),
                "timeout": int(
                    os.getenv("CGM_LLM_TIMEOUT", llm_config_data.get("timeout", 60))
                ),
            }
        )

        graph_config_data = config_data.get("graph", {})
        graph_config_data.update(
            {
                "max_nodes": int(
                    os.getenv(
                        "CGM_GRAPH_MAX_NODES", graph_config_data.get("max_nodes", 10000)
                    )
                ),
                "max_edges": int(
                    os.getenv(
                        "CGM_GRAPH_MAX_EDGES", graph_config_data.get("max_edges", 50000)
                    )
                ),
                "cache_enabled": os.getenv(
                    "CGM_GRAPH_CACHE_ENABLED",
                    str(graph_config_data.get("cache_enabled", True)),
                ).lower()
                == "true",
                "cache_ttl": int(
                    os.getenv(
                        "CGM_GRAPH_CACHE_TTL", graph_config_data.get("cache_ttl", 3600)
                    )
                ),
            }
        )

        server_config_data = config_data.get("server", {})
        server_config_data.update(
            {
                "host": os.getenv(
                    "CGM_SERVER_HOST", server_config_data.get("host", "localhost")
                ),
                "port": int(
                    os.getenv("CGM_SERVER_PORT", server_config_data.get("port", 8000))
                ),
                "log_level": os.getenv(
                    "CGM_LOG_LEVEL", server_config_data.get("log_level", "INFO")
                ),
                "max_concurrent_tasks": int(
                    os.getenv(
                        "CGM_MAX_CONCURRENT_TASKS",
                        server_config_data.get("max_concurrent_tasks", 10),
                    )
                ),
                "task_timeout": int(
                    os.getenv(
                        "CGM_TASK_TIMEOUT", server_config_data.get("task_timeout", 300)
                    )
                ),
            }
        )

        return cls(
            llm_config=LLMConfig.from_dict(llm_config_data),
            graph_config=GraphConfig.from_dict(graph_config_data),
            server_config=ServerConfig.from_dict(server_config_data),
        )

    def save(self, config_path: str):
        """Save configuration to file"""
        config_data = {
            "llm": {
                "provider": self.llm_config.provider,
                "model": self.llm_config.model,
                "api_base": self.llm_config.api_base,
                "temperature": self.llm_config.temperature,
                "max_tokens": self.llm_config.max_tokens,
                "timeout": self.llm_config.timeout,
            },
            "graph": {
                "max_nodes": self.graph_config.max_nodes,
                "max_edges": self.graph_config.max_edges,
                "cache_enabled": self.graph_config.cache_enabled,
                "cache_ttl": self.graph_config.cache_ttl,
            },
            "server": {
                "host": self.server_config.host,
                "port": self.server_config.port,
                "log_level": self.server_config.log_level,
                "max_concurrent_tasks": self.server_config.max_concurrent_tasks,
                "task_timeout": self.server_config.task_timeout,
            },
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
