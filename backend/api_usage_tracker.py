# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

"""
API Usage Tracker Module
Tracks and monitors API token usage for MCP calls
"""

from __future__ import annotations

import json
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import Settings


class APIUsageTracker:
    """Tracks API token consumption across agents."""
    
    def __init__(
        self,
        enabled: Optional[bool] = None,
        persist_file: Optional[str] = None,
    ):
        self.enabled = Settings.TRACK_API_USAGE if enabled is None else bool(enabled)
        self.persist_path = Path(persist_file or Settings.USAGE_LOG_FILE)
        self.total_tokens: int = 0
        self.usage_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._persisted_count = 0  # Track how many entries we've written to file
        
        # Start fresh each session - don't load previous usage
        # if self.enabled:
        #     self._load_existing_usage()
    
    def _load_existing_usage(self) -> None:
        """Load previous usage stats if a log file already exists."""
        if not self.persist_path.exists():
            return
        
        try:
            with self.persist_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            
            self.total_tokens = int(payload.get("total_tokens", 0))
            self.usage_log = list(payload.get("usage_log", []))
        except (json.JSONDecodeError, OSError, ValueError):
            # Corrupted or unreadable log; start fresh.
            self.total_tokens = 0
            self.usage_log = []
    
    def _persist_usage_locked(self) -> None:
        """Persist usage information to disk with merge support for multi-process."""
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing data from file to merge (for multi-process MCP mode)
        existing_total = 0
        existing_log = []
        if self.persist_path.exists():
            try:
                with self.persist_path.open("r", encoding="utf-8") as handle:
                    existing_data = json.load(handle)
                    existing_total = existing_data.get("total_tokens", 0)
                    existing_log = existing_data.get("usage_log", [])
            except (json.JSONDecodeError, OSError):
                # File corrupted, start fresh
                pass
        
        # Merge: Only add entries from THIS process that haven't been persisted yet
        # _persisted_count tracks how many of self.usage_log we've already written
        new_entries = self.usage_log[self._persisted_count:]
        
        # Calculate tokens only from new entries
        new_tokens = sum(entry.get("tokens", 0) for entry in new_entries)
        
        merged_total = existing_total + new_tokens
        merged_log = existing_log + new_entries
        
        payload = {
            "total_tokens": merged_total,
            "usage_log": merged_log,
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        with self.persist_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        
        # Update persisted count to reflect what we've written
        self._persisted_count = len(self.usage_log)
    
    def track_usage(
        self,
        agent_name: str,
        tokens_used: Any,
        metadata: Optional[Dict[str, Any]] = None,
        iteration: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Record API token usage for an agent.
        
        Args:
            agent_name: Name of the agent making the request.
            tokens_used: Number of tokens consumed (int or dict with token info).
            metadata: Optional contextual information (request id, prompt size, etc.).
            iteration: Optional iteration number (for debugger tracking).
        """
        if not self.enabled:
            return None
        
        # Handle both dictionary and integer inputs
        if isinstance(tokens_used, dict):
            # Extract total_tokens from dictionary
            tokens_count = tokens_used.get("total_tokens", 0)
            # Store the full dict as metadata if not provided
            if metadata is None:
                metadata = tokens_used.copy()
        elif tokens_used is None:
            tokens_count = 0
        else:
            tokens_count = int(tokens_used)
        
        if tokens_count < 0:
            raise ValueError("tokens_used must be a non-negative integer")
        
        # Add iteration to metadata if provided
        if metadata is None:
            metadata = {}
        if iteration is not None:
            metadata['iteration'] = iteration
        
        entry = {
            "agent": agent_name or "unknown",
            "tokens": int(tokens_count),
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata,
            "iteration": iteration,
        }
        
        with self._lock:
            self.total_tokens += entry["tokens"]
            self.usage_log.append(entry)
            self._persist_usage_locked()
        
        return entry
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics with iteration details."""
        with self._lock:
            agent_breakdown = defaultdict(int)
            agent_calls = defaultdict(int)
            debugger_iterations = defaultdict(int)
            
            for entry in self.usage_log:
                agent = entry["agent"]
                tokens = int(entry["tokens"])
                
                agent_breakdown[agent] += tokens
                agent_calls[agent] += 1
                
                # Track debugger iterations separately
                if agent == "debugger" and entry.get("iteration"):
                    iteration = entry["iteration"]
                    debugger_iterations[iteration] += tokens
            
            last_event = self.usage_log[-1] if self.usage_log else None
            
            return {
                "enabled": self.enabled,
                "total_tokens": self.total_tokens,
                "call_count": len(self.usage_log),
                "agent_breakdown": dict(agent_breakdown),
                "agent_calls": dict(agent_calls),
                "debugger_iterations": dict(debugger_iterations),
                "last_event": last_event,
                "log_file": str(self.persist_path),
            }
    
    def reset_tracker(self) -> None:
        """Reset usage statistics."""
        with self._lock:
            self.total_tokens = 0
            self.usage_log = []
            if self.persist_path.exists():
                self.persist_path.unlink()
