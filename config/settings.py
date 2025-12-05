"""
Settings Module
Configuration settings for the MCP multi-agent system
"""

import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Get the project root directory (parent of config directory)
    root_dir = Path(__file__).parent.parent
    env_path = root_dir / '.env'
    load_dotenv(dotenv_path=env_path)
    print(f"[Settings] Loaded environment from {env_path}")
except ImportError:
    print("[Settings] python-dotenv not installed, using system environment variables only")
except Exception as e:
    print(f"[Settings] Error loading .env file: {e}")


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
    
    # LangChain Configuration
    MEMORY_BACKEND = os.getenv("MEMORY_BACKEND", "buffer")  # buffer, conversation_buffer, or vector
    MEMORY_DIR = os.getenv("MEMORY_DIR", "./memory")
    ENABLE_MEMORY = os.getenv("ENABLE_MEMORY", "true").lower() == "true"
    MAX_MEMORY_TOKENS = int(os.getenv("MAX_MEMORY_TOKENS", "4000"))
