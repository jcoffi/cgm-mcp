"""
CGM MCP Server - CodeFuse-CGM Model Context Protocol Server

A Graph-Integrated Large Language Model for Repository-Level Software Engineering Tasks
"""

__version__ = "0.1.0"
__author__ = "CGM MCP Team"
__email__ = "cgm-mcp@example.com"

from .components import *
from .models import *
from .server import CGMServer

__all__ = [
    "CGMServer",
    "__version__",
    "__author__",
    "__email__",
]
