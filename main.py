#!/usr/bin/env python3
"""
Main entry point for the Dash MCP Showcase application.
This file ensures the application can be run from the project root.
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dash_mcp_showcase.init_app import dash_app

# For App Engine deployment
app = dash_app.server

if __name__ == '__main__':
    # For local development
    dash_app.run_server(debug=True, host='0.0.0.0', port=8080)
