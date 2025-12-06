"""
Utils Package
Contains utility modules for the multi-agent system
"""

# Import FileManager (no external dependencies)
from .file_manager import FileManager
from .conversation_logger import ConversationLogger

# Import other modules with error handling for optional dependencies
__all__ = ['FileManager', 'ConversationLogger']

try:
    from .mcp_client import MCPClient
    __all__.append('MCPClient')
except ImportError:
    pass

try:
    from .memory_manager import MemoryManager
    __all__.append('MemoryManager')
except ImportError:
    pass

try:
    from .langchain_wrapper import LangChainWrapper
    __all__.append('LangChainWrapper')
except ImportError:
    pass
