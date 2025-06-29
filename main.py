#!/usr/bin/env python3
"""
CGM MCP Server - Main Entry Point

Usage:
    python main.py                    # Start MCP server
    python main.py --config config.json  # Use custom config
    python main.py --help            # Show help
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cgm_mcp.server import main as server_main
from cgm_mcp.utils.config import Config
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
  python main.py                           # Start with default config
  python main.py --config config.json     # Use custom config file
  python main.py --log-level DEBUG        # Enable debug logging
  
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
        "--version",
        action="version",
        version="CGM MCP Server 0.1.0"
    )
    
    return parser.parse_args()


async def main():
    """Main entry point"""
    args = parse_args()
    
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
    logger.info(f"LLM Provider: {config.llm_config.provider}")
    logger.info(f"LLM Model: {config.llm_config.model}")
    logger.info(f"Log Level: {log_level}")
    
    # Validate configuration
    if not config.llm_config.api_key and config.llm_config.provider != "mock":
        logger.error(f"API key required for {config.llm_config.provider} provider")
        logger.error("Set CGM_LLM_API_KEY environment variable or provide in config file")
        sys.exit(1)
    
    try:
        # Start the MCP server
        await server_main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
