# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

"""
Unit tests for backend modules
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.api_usage_tracker import APIUsageTracker
from backend.mcp_handler import MCPHandler


@dataclass
class DummyMCPClient:
    """Minimal MCP client stub to satisfy handler dependencies."""
    
    connected: bool = False
    
    def connect(self) -> None:
        self.connected = True
    
    def disconnect(self) -> None:
        self.connected = False


class TestMCPHandler:
    """Tests for MCP Handler"""
    
    def test_process_request_generates_code_package(self, tmp_path):
        """Process a mock request and ensure code package is created."""
        usage_log = tmp_path / "usage.json"
        tracker = APIUsageTracker(enabled=True, persist_file=str(usage_log))
        handler = MCPHandler(mcp_client=DummyMCPClient(), usage_tracker=tracker)
        
        request = {
            "description": "CLI habit tracker",
            "requirements": ["Add habits", "Mark completion", "Summaries"],
        }
        
        result = handler.process_request(request)
        
        assert result["project_name"].startswith("cli_habit_tracker")
        assert "main.py" in result["files"]
        assert handler.get_final_output() == result
        
        stats = tracker.get_usage_statistics()
        assert stats["total_tokens"] > 0
        assert stats["call_count"] >= 1
    
    def test_coordinate_agents_requires_request(self):
        """Ensure coordinate_agents cannot run before process_request."""
        handler = MCPHandler(mcp_client=DummyMCPClient(), usage_tracker=APIUsageTracker(enabled=False))
        with pytest.raises(ValueError):
            handler.coordinate_agents()


class TestAPIUsageTracker:
    """Tests for API Usage Tracker"""
    
    def test_track_usage_records_entries(self, tmp_path):
        """Track usage and confirm persistence."""
        log_path = tmp_path / "usage.json"
        tracker = APIUsageTracker(enabled=True, persist_file=str(log_path))
        
        tracker.track_usage("architect", 42, {"stage": "analysis"})
        tracker.track_usage("coder", 10)
        
        stats = tracker.get_usage_statistics()
        assert stats["total_tokens"] == 52
        assert stats["agent_breakdown"]["architect"] == 42
        assert stats["call_count"] == 2
        assert log_path.exists()
    
    def test_reset_tracker_clears_state(self, tmp_path):
        """Resetting the tracker removes stats and log file."""
        log_path = tmp_path / "usage.json"
        tracker = APIUsageTracker(enabled=True, persist_file=str(log_path))
        tracker.track_usage("tester", 5)
        assert log_path.exists()
        
        tracker.reset_tracker()
        stats = tracker.get_usage_statistics()
        assert stats["total_tokens"] == 0
        assert stats["call_count"] == 0
        assert not log_path.exists()
