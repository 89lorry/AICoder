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
        
        if self.enabled:
            self._load_existing_usage()
    
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
        """Persist usage information to disk. Call only while holding the lock."""
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "total_tokens": self.total_tokens,
            "usage_log": self.usage_log,
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        with self.persist_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
    
    def track_usage(
        self,
        agent_name: str,
        tokens_used: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Record API token usage for an agent.
        
        Args:
            agent_name: Name of the agent making the request.
            tokens_used: Number of tokens consumed (int or dict with token info).
            metadata: Optional contextual information (request id, prompt size, etc.).
        """
        if not self.enabled:
            return None
        
        # Handle both dictionary and integer inputs
        if isinstance(tokens_used, dict):
            # Extract total_tokens from dictionary
            tokens_count = tokens_used.get("total_tokens", 0)
            # Store the full dict as metadata if not provided
            if metadata is None:
                metadata = tokens_used
        elif tokens_used is None:
            tokens_count = 0
        else:
            tokens_count = int(tokens_used)
        
        if tokens_count < 0:
            raise ValueError("tokens_used must be a non-negative integer")
        
        entry = {
            "agent": agent_name or "unknown",
            "tokens": int(tokens_count),
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        
        with self._lock:
            self.total_tokens += entry["tokens"]
            self.usage_log.append(entry)
            self._persist_usage_locked()
        
        return entry
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics."""
        with self._lock:
            agent_breakdown = defaultdict(int)
            for entry in self.usage_log:
                agent_breakdown[entry["agent"]] += int(entry["tokens"])
            
            last_event = self.usage_log[-1] if self.usage_log else None
            
            return {
                "enabled": self.enabled,
                "total_tokens": self.total_tokens,
                "call_count": len(self.usage_log),
                "agent_breakdown": dict(agent_breakdown),
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
