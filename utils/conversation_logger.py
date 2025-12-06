"""
Conversation Logger Module
Logs agent conversations to separate text files for debugging and analysis
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


class ConversationLogger:
    """Logs conversations for debugging and analysis"""
    
    def __init__(self, agent_name: str, session_id: Optional[str] = None, log_dir: str = "./logs/conversations"):
        """
        Initialize conversation logger
        
        Args:
            agent_name: Name of the agent (e.g., "architect", "coder")
            session_id: Optional session identifier
            log_dir: Directory to store log files
        """
        self.agent_name = agent_name
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = Path(log_dir)
        self.logger = logging.getLogger(__name__)
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file path
        self.log_file = self.log_dir / f"{self.agent_name}_{self.session_id}.txt"
        
        # Initialize log file
        self._initialize_log_file()
    
    def _initialize_log_file(self):
        """Initialize log file with header"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"Conversation Log: {self.agent_name.upper()}\n")
            f.write(f"Session ID: {self.session_id}\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
    
    def log_interaction(self, prompt: str, response: str, metadata: Optional[dict] = None):
        """
        Log a single interaction (prompt + response)
        
        Args:
            prompt: The prompt sent to the AI
            response: The response received
            metadata: Optional metadata (tokens, timestamp, etc.)
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                # Log timestamp
                f.write(f"\n{'─' * 80}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                # Log metadata if provided
                if metadata:
                    f.write(f"Metadata: {metadata}\n")
                
                # Log prompt
                f.write(f"\n[PROMPT]\n{'-' * 80}\n")
                f.write(f"{prompt}\n")
                
                # Log response
                f.write(f"\n[RESPONSE]\n{'-' * 80}\n")
                f.write(f"{response}\n")
                f.write(f"{'─' * 80}\n")
                
        except Exception as e:
            self.logger.warning(f"Failed to log conversation: {e}")
    
    def log_error(self, error_msg: str, context: Optional[str] = None):
        """
        Log an error
        
        Args:
            error_msg: Error message
            context: Optional context information
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'═' * 80}\n")
                f.write(f"[ERROR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'═' * 80}\n")
                f.write(f"{error_msg}\n")
                if context:
                    f.write(f"\nContext: {context}\n")
                f.write(f"{'═' * 80}\n")
        except Exception as e:
            self.logger.warning(f"Failed to log error: {e}")
    
    def log_note(self, note: str):
        """
        Log a note or comment
        
        Args:
            note: Note text
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n[NOTE] {datetime.now().strftime('%H:%M:%S')}: {note}\n")
        except Exception as e:
            self.logger.warning(f"Failed to log note: {e}")
    
    def finalize(self):
        """Finalize log file with footer"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'=' * 80}\n")
                f.write(f"Session Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'=' * 80}\n")
        except Exception as e:
            self.logger.warning(f"Failed to finalize log: {e}")
    
    def get_log_path(self) -> str:
        """Get the path to the log file"""
        return str(self.log_file)
