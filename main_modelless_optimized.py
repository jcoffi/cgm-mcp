#!/usr/bin/env python3
"""
CGM MCP Server - Optimized Model-agnostic Entry Point

Performance optimizations:
- Advanced caching with LRU and TTL
- Concurrent request processing
- Memory monitoring and management
- Request deduplication
- Background maintenance tasks

Usage:
    python main_modelless_optimized.py                    # Start optimized server
    python main_modelless_optimized.py --config config.json  # Use custom config
    python main_modelless_optimized.py --help            # Show help
"""

import asyncio
import argparse
import sys
import signal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cgm_mcp.server_modelless_optimized import main as server_main
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
        description="CGM MCP Server (Optimized) - High-performance code analysis without LLM dependency",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Performance Features:
  • LRU cache with TTL for analysis results
  • Concurrent request processing with semaphores
  • Memory monitoring and automatic cleanup
  • Request deduplication for identical queries
  • Background maintenance tasks
  • System resource monitoring

Examples:
  python main_modelless_optimized.py                     # Start with default config
  python main_modelless_optimized.py --config config.json  # Use custom config file
  python main_modelless_optimized.py --log-level DEBUG   # Enable debug logging
  python main_modelless_optimized.py --max-cache 200     # Increase cache size
  
Performance Tuning:
  --max-cache SIZE      Maximum cache entries (default: 100)
  --cache-ttl SECONDS   Cache TTL in seconds (default: 3600)
  --max-concurrent N    Maximum concurrent requests (default: 5)
  --memory-limit MB     Memory limit for auto-cleanup (default: 1000)
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
        "--max-cache",
        type=int,
        default=100,
        help="Maximum cache entries (default: 100)"
    )
    
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=3600,
        help="Cache TTL in seconds (default: 3600)"
    )
    
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Maximum concurrent requests (default: 5)"
    )
    
    parser.add_argument(
        "--memory-limit",
        type=int,
        default=1000,
        help="Memory limit in MB for auto-cleanup (default: 1000)"
    )
    
    parser.add_argument(
        "--disable-cache",
        action="store_true",
        help="Disable caching completely"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="CGM MCP Server (Optimized) 0.2.0"
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
    
    # Apply command line overrides
    if args.disable_cache:
        config.graph_config.cache_enabled = False
    else:
        config.graph_config.cache_enabled = True
        
    # Override cache settings if provided
    if hasattr(config.graph_config, 'cache_ttl'):
        config.graph_config.cache_ttl = args.cache_ttl
    else:
        config.graph_config.cache_ttl = args.cache_ttl
        
    if hasattr(config.server_config, 'max_concurrent_tasks'):
        config.server_config.max_concurrent_tasks = args.max_concurrent
    else:
        config.server_config.max_concurrent_tasks = args.max_concurrent
    
    # Setup logging
    log_level = args.log_level or config.server_config.log_level
    setup_logging(log_level)
    
    logger.info("Starting CGM MCP Server (Optimized)")
    logger.info("Performance features enabled:")
    logger.info(f"  • Cache: {'Enabled' if config.graph_config.cache_enabled else 'Disabled'}")
    if config.graph_config.cache_enabled:
        logger.info(f"    - Max entries: {args.max_cache}")
        logger.info(f"    - TTL: {args.cache_ttl}s")
    logger.info(f"  • Max concurrent requests: {args.max_concurrent}")
    logger.info(f"  • Memory limit: {args.memory_limit}MB")
    logger.info(f"  • Request deduplication: Enabled")
    logger.info(f"  • Background maintenance: Enabled")
    logger.info(f"  • System monitoring: Enabled")
    logger.info(f"Log Level: {log_level}")
    
    logger.info("Available optimized tools:")
    logger.info("  • cgm_analyze_repository - Repository analysis with caching")
    logger.info("  • cgm_get_file_content - Concurrent file analysis")
    logger.info("  • cgm_clear_cache - Manual cache management")
    logger.info("  • cgm_get_performance_stats - Performance monitoring")
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        # The server will handle cleanup in its finally block
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the optimized MCP server
        await server_main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
