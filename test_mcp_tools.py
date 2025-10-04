#!/usr/bin/env python3
"""
Test script to verify MCP tools are properly exposed and accessible.
"""

import sys
import os
import tempfile
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    # Try to import the ModellessCGMServer directly
    from cgm_mcp.server_modelless import ModellessCGMServer
    from cgm_mcp.utils.config import Config
    
    print("✅ Successfully imported ModellessCGMServer")
    
    # Create a minimal config
    config = Config()
    print("✅ Created config")
    
    # Create server instance
    server = ModellessCGMServer(config)
    print("✅ Created server instance")
    
    # Check if the server has the expected tools
    if hasattr(server, 'server'):
        print("✅ Server has MCP server instance")
    else:
        print("❌ Server missing MCP server instance")
        
    print("\nTesting tool definitions...")
    
    # Test if we can access the handlers
    print("Server object attributes:", [attr for attr in dir(server) if not attr.startswith('_')])
    
except ImportError as e:
    print(f"❌ Failed to import: {e}")
    # Let's try to identify what specific module is missing
    import traceback
    traceback.print_exc()
    
except Exception as e:
    print(f"❌ Error creating server: {e}")
    import traceback
    traceback.print_exc()