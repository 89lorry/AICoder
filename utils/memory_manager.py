# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

"""
Memory Manager Module
Manages LangChain memory for agents with conversation history
"""

import logging
import os
from typing import Optional, Dict, Any

# Try to import from langchain_community first (newer versions)
try:
    from langchain_community.chat_message_histories import ChatMessageHistory
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    HumanMessage = None
    AIMessage = None
    SystemMessage = None
    ChatMessageHistory = None

from config.settings import Settings


class MemoryManager:
    """Manages LangChain memory for agents"""
    
    def __init__(self, agent_name: str, memory_type: str = None, llm=None):
        """
        Initialize memory manager for an agent
        
        Args:
            agent_name: Name of the agent (e.g., "architect", "coder")
            memory_type: Type of memory to use (buffer, buffer_window, summary, summary_buffer)
            llm: Optional LLM instance for summary-based memory
        """
        self.agent_name = agent_name
        self.logger = logging.getLogger(__name__)
        self.memory_type = memory_type or Settings.MEMORY_BACKEND
        self.llm = llm
        self.memory = None
        
        # Initialize memory
        self._initialize_memory()
    
    def _initialize_memory(self):
        """Initialize the appropriate memory type"""
        if not Settings.ENABLE_MEMORY:
            self.logger.info(f"Memory disabled for {self.agent_name}")
            return
        
        if not LANGCHAIN_AVAILABLE:
            self.logger.warning(f"LangChain not available, using simple memory for {self.agent_name}")
            # Use simple list-based memory
            self.memory = {"chat_history": []}
            return
        
        try:
            # For now, use simple dict-based memory since langchain.memory module structure changed
            self.memory = {"chat_history": []}
            self.logger.info(f"Initialized simple memory for {self.agent_name}")
        except Exception as e:
            self.logger.warning(f"Failed to initialize memory for {self.agent_name}: {str(e)}")
            self.memory = None
    
    def save_context(self, input_str: str, output_str: str):
        """Save conversation context to memory"""
        if not self.memory or not Settings.ENABLE_MEMORY:
            return
        
        try:
            if isinstance(self.memory, dict):
                # Simple dict-based memory
                self.memory["chat_history"].append({
                    "input": input_str,
                    "output": output_str
                })
            else:
                # LangChain memory object
                self.memory.save_context(
                    {"input": input_str},
                    {"output": output_str}
                )
            self.logger.debug(f"Saved context to memory for {self.agent_name}")
        except Exception as e:
            self.logger.warning(f"Failed to save context: {str(e)}")
    
    def load_memory_variables(self) -> Dict[str, Any]:
        """Load memory variables for use in prompts"""
        if not self.memory or not Settings.ENABLE_MEMORY:
            return {"chat_history": []}
        
        try:
            if isinstance(self.memory, dict):
                return self.memory
            else:
                return self.memory.load_memory_variables({})
        except Exception as e:
            self.logger.warning(f"Failed to load memory variables: {str(e)}")
            return {"chat_history": []}
    
    def get_chat_history(self) -> str:
        """Get formatted chat history as string"""
        if not self.memory or not Settings.ENABLE_MEMORY:
            return ""
        
        try:
            memory_vars = self.load_memory_variables()
            chat_history = memory_vars.get("chat_history", [])
            
            if not chat_history:
                return ""
            
            # Format messages
            formatted = []
            for message in chat_history:
                if hasattr(message, 'content'):
                    if hasattr(message, 'type'):
                        role = "Human" if message.type == "human" else "Assistant"
                    else:
                        role = "Human" if isinstance(message, HumanMessage) else "Assistant"
                    formatted.append(f"{role}: {message.content}")
                else:
                    formatted.append(str(message))
            
            return "\n".join(formatted)
        except Exception as e:
            self.logger.warning(f"Failed to get chat history: {str(e)}")
            return ""
    
    def clear(self):
        """Clear memory"""
        if self.memory and Settings.ENABLE_MEMORY:
            try:
                self.memory.clear()
                self.logger.info(f"Cleared memory for {self.agent_name}")
            except Exception as e:
                self.logger.warning(f"Failed to clear memory: {str(e)}")
    
    def add_system_message(self, message: str):
        """Add a system message to memory"""
        if not self.memory or not Settings.ENABLE_MEMORY:
            return
        
        try:
            if hasattr(self.memory, 'chat_memory'):
                self.memory.chat_memory.add_message(SystemMessage(content=message))
                self.logger.debug(f"Added system message to memory for {self.agent_name}")
        except Exception as e:
            self.logger.warning(f"Failed to add system message: {str(e)}")
    
    def get_memory_summary(self) -> str:
        """Get a summary of memory contents"""
        if not self.memory or not Settings.ENABLE_MEMORY:
            return "Memory disabled"
        
        try:
            memory_vars = self.load_memory_variables()
            chat_history = memory_vars.get("chat_history", [])
            return f"Memory contains {len(chat_history)} messages"
        except Exception as e:
            return f"Memory error: {str(e)}"
