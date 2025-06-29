#!/usr/bin/env python3
"""
CGM MCP Server - Model-agnostic Entry Point

This version provides CGM capabilities without requiring any specific LLM.
It serves as a pure tool and context provider for external models.

Usage:
    python main_modelless.py                    # Start modelless MCP server
    python main_modelless.py --config config.json  # Use custom config
    python main_modelless.py --help            # Show help
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cgm_mcp.server_modelless import main as server_main
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
        description="CGM MCP Server (Model-agnostic) - Code analysis tools without LLM dependency",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_modelless.py                     # Start with default config
  python main_modelless.py --config config.json  # Use custom config file
  python main_modelless.py --log-level DEBUG   # Enable debug logging
  
Features:
  • Repository structure analysis
  • Code entity extraction
  • Dependency mapping
  • Context generation for external models
  • No LLM API keys required
  
Integration:
  This server provides tools that external models can use to understand
  code structure and relationships without requiring direct LLM integration.
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
        "--cache-dir",
        type=str,
        help="Directory for caching analysis results"
    )
    
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=1024*1024,  # 1MB
        help="Maximum file size to analyze (bytes)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="CGM MCP Server (Model-agnostic) 0.1.0"
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
    
    logger.info("Starting CGM MCP Server (Model-agnostic)")
    logger.info("This server provides code analysis tools without LLM dependency")
    logger.info(f"Log Level: {log_level}")
    
    if args.cache_dir:
        logger.info(f"Cache Directory: {args.cache_dir}")
        
    if args.max_file_size:
        logger.info(f"Max File Size: {args.max_file_size} bytes")
    
    logger.info("Available tools:")
    logger.info("  • cgm_analyze_repository - Analyze repository structure")
    logger.info("  • cgm_get_file_content - Get detailed file analysis")
    logger.info("  • cgm_find_related_code - Find code relationships")
    logger.info("  • cgm_extract_context - Extract context for external models")
    
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
