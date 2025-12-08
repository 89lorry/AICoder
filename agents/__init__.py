# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

"""
Agents Package
Contains all MCP agents for the multi-agent system
"""

from .agent_architect import AgentArchitect
from .agent_coder import AgentCoder
from .agent_tester import AgentTester
from .agent_debugger import AgentDebugger

__all__ = [
    'AgentArchitect',
    'AgentCoder',
    'AgentTester',
    'AgentDebugger'
]
