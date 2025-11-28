"""
Settings Module
Configuration settings for the MCP multi-agent system
"""

import os


class Settings:
    """Configuration settings"""
    
    # MCP Configuration
    MCP_API_KEY = os.getenv("MCP_API_KEY", "")
    MCP_ENDPOINT = os.getenv("MCP_ENDPOINT", "https://api.mcp.example.com")
    
    # Agent Configuration
    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 300
    
    # Server Configuration
    WORKSPACE_DIR = "./workspace"
    OUTPUT_DIR = "./output"
    
    # UI Configuration
    UI_PORT = 8000
    UI_HOST = "localhost"
    
    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = "system.log"
    
    # API Usage Tracking
    TRACK_API_USAGE = True
    USAGE_LOG_FILE = "api_usage.json"
