# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

"""
LangChain Wrapper Module
Integrates LangChain with MCP client for agent interactions
"""

import os
import logging
from typing import Optional, Dict, Any, List

# Try to import langchain components
try:
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.language_models import BaseLanguageModel
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    ChatPromptTemplate = None
    MessagesPlaceholder = None
    BaseLanguageModel = None
    ChatOpenAI = None

# Try to import anthropic
try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    ChatAnthropic = None

from utils.memory_manager import MemoryManager
from config.settings import Settings


class LangChainWrapper:
    """Wrapper to integrate LangChain with MCP client"""
    
    def __init__(self, mcp_client, memory_manager: Optional[MemoryManager] = None, 
                 llm_provider: str = "openai"):
        """
        Initialize LangChain wrapper
        
        Args:
            mcp_client: MCP client instance
            memory_manager: Optional memory manager instance
            llm_provider: LLM provider to use (openai, anthropic, or mcp)
        """
        self.mcp_client = mcp_client
        self.memory_manager = memory_manager
        self.llm_provider = llm_provider
        self.logger = logging.getLogger(__name__)
        self.llm = None
        self.chain = None
        
        # Initialize LLM and chain
        self._initialize_llm()
        self._initialize_chain()
    
    def _initialize_llm(self):
        """Initialize the LLM based on provider"""
        try:
            if self.llm_provider == "openai":
                api_key = Settings.MCP_API_KEY or os.getenv("OPENAI_API_KEY")
                if api_key:
                    self.llm = ChatOpenAI(
                        model_name="gpt-4",
                        temperature=0.7,
                        openai_api_key=api_key
                    )
                    self.logger.info("Initialized OpenAI LLM")
            
            elif self.llm_provider == "anthropic":
                api_key = Settings.MCP_API_KEY or os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self.llm = ChatAnthropic(
                        model="claude-3-opus-20240229",
                        temperature=0.7,
                        anthropic_api_key=api_key
                    )
                    self.logger.info("Initialized Anthropic LLM")
            
            else:
                # Use MCP client as fallback
                self.logger.info("Using MCP client as LLM provider")
        
        except Exception as e:
            self.logger.warning(f"Failed to initialize LLM: {str(e)}. Will use MCP client.")
    
    def _initialize_chain(self):
        """Initialize LangChain chain with memory"""
        if not self.llm:
            self.logger.info("No LLM available, will use MCP client directly")
            return
        
        # With newer LangChain, we can use the LLM directly without chains
        self.chain = self.llm
        self.logger.info("Initialized LangChain LLM (direct mode)")
    
    def invoke(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Invoke LangChain chain or fallback to MCP client
        
        Args:
            prompt: Input prompt
            context: Optional context dictionary
            
        Returns:
            Response string
        """
        # Try LangChain chain first
        if self.chain:
            try:
                inputs = {"input": prompt}
                
                # Add context if provided
                if context:
                    context_str = self._format_context(context)
                    inputs["input"] = f"{context_str}\n\n{prompt}"
                
                result = self.chain.invoke(inputs)
                
                # Extract response
                if isinstance(result, dict):
                    response = result.get("text", str(result))
                else:
                    response = str(result)
                
                # Save to memory if available
                if self.memory_manager:
                    self.memory_manager.save_context(prompt, response)
                
                return response
            
            except Exception as e:
                self.logger.warning(f"LangChain chain failed: {str(e)}, falling back to MCP client")
        
        # Fallback to MCP client
        return self._invoke_mcp(prompt, context)
    
    def _invoke_mcp(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Invoke MCP client directly"""
        try:
            # Connect if needed
            if not hasattr(self.mcp_client, 'session') or self.mcp_client.session is None:
                self.mcp_client.connect()
            
            # Add context to prompt if provided
            if context:
                context_str = self._format_context(context)
                prompt = f"{context_str}\n\n{prompt}"
            
            # Add memory context if available
            if self.memory_manager:
                memory_context = self.memory_manager.get_chat_history()
                if memory_context:
                    prompt = f"Previous conversation:\n{memory_context}\n\nCurrent request:\n{prompt}"
            
            # Send request
            response = self.mcp_client.send_request(prompt, context)
            
            # Save to memory if available
            if self.memory_manager:
                self.memory_manager.save_context(prompt, str(response))
            
            return str(response)
        
        except Exception as e:
            self.logger.error(f"MCP client invocation failed: {str(e)}")
            raise
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as string"""
        formatted = []
        for key, value in context.items():
            if isinstance(value, (dict, list)):
                import json
                formatted.append(f"{key}:\n{json.dumps(value, indent=2)}")
            else:
                formatted.append(f"{key}: {value}")
        return "\n".join(formatted)
    
    def get_token_usage(self) -> Optional[Dict[str, int]]:
        """Get token usage from last request"""
        if hasattr(self.mcp_client, 'get_token_usage'):
            return self.mcp_client.get_token_usage()
        return None
