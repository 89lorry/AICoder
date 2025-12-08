# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

"""
MCP Handler Module
Orchestrates the multi-agent system and manages agent workflow
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from agents.agent_architect import AgentArchitect
from agents.agent_coder import AgentCoder
from agents.agent_tester import AgentTester
from agents.agent_debugger import AgentDebugger
from backend.api_usage_tracker import APIUsageTracker
from config.settings import Settings
from utils.mcp_client import MCPClient


class MCPHandler:
    """Main handler for coordinating MCP agents."""
    
    def __init__(
        self,
        mcp_client: Optional[MCPClient] = None,
        usage_tracker: Optional[APIUsageTracker] = None,
    ):
        self.settings = Settings
        self.mcp_client = mcp_client or MCPClient(
            api_key=self.settings.MCP_API_KEY,
            endpoint=self.settings.MCP_ENDPOINT,
        )
        self.usage_tracker = usage_tracker or APIUsageTracker()
        
        # Initialize agent instances
        self.architect = AgentArchitect(self.mcp_client)
        self.coder = AgentCoder(self.mcp_client)
        self.tester = AgentTester(self.mcp_client)
        self.debugger = AgentDebugger(self.mcp_client)
        
        self.current_request: Optional[Dict[str, Any]] = None
        self.pipeline_state: Dict[str, Any] = {}
        self.final_output: Optional[Dict[str, Any]] = None
    
    def process_request(self, user_input: Any) -> Dict[str, Any]:
        """
        Process user request through agent pipeline.
        
        Args:
            user_input: Either a string prompt or a dictionary containing
                "description" and "requirements".
        """
        normalized_input = self._normalize_user_input(user_input)
        self.current_request = normalized_input
        self.pipeline_state = {"request": normalized_input}
        self.final_output = None
        
        self.mcp_client.connect()
        try:
            result = self.coordinate_agents()
        finally:
            self.mcp_client.disconnect()
        
        return result
    
    def coordinate_agents(self) -> Dict[str, Any]:
        """Coordinate workflow between agents A -> B -> C -> D."""
        if not self.current_request:
            raise ValueError("No user request available. Call process_request first.")
        
        architecture = self._run_architect_stage(self.current_request)
        code_package = self._run_coder_stage(architecture)
        test_files, test_results = self._run_tester_stage(code_package)
        final_package = self._run_debugger_stage(code_package, test_files, test_results)
        
        self.final_output = final_package
        return final_package
    
    def get_final_output(self) -> Optional[Dict[str, Any]]:
        """Retrieve final generated code package."""
        return self.final_output
    
    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    
    def _normalize_user_input(self, user_input: Any) -> Dict[str, Any]:
        """Ensure the handler works with a consistent request format."""
        if isinstance(user_input, str):
            description = user_input.strip()
            requirements: List[str] = []
        elif isinstance(user_input, dict):
            description = str(user_input.get("description", "")).strip()
            requirements_raw = user_input.get("requirements", [])
            if isinstance(requirements_raw, str):
                requirements = [
                    req.strip() for req in requirements_raw.split("\n") if req.strip()
                ]
            else:
                requirements = [str(req).strip() for req in requirements_raw if str(req).strip()]
        else:
            raise TypeError("user_input must be either a string or a dictionary.")
        
        if not description:
            raise ValueError("Software description is required.")
        
        return {
            "request_id": uuid.uuid4().hex,
            "description": description,
            "requirements": requirements,
        }
    
    def _estimate_tokens(self, text: str) -> int:
        """Rudimentary token estimate used for tracking before LLM integration."""
        if not text:
            return 0
        return max(1, len(text.split()))
    
    def _track_usage(self, agent_name: str, payload: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Helper to send token stats to the usage tracker."""
        tokens = self._estimate_tokens(payload)
        meta = metadata or {}
        if self.current_request:
            meta.setdefault("request_id", self.current_request["request_id"])
        self.usage_tracker.track_usage(agent_name, tokens, meta)
    
    # ----------------------- Agent Stage Helpers ---------------------- #
    
    def _run_architect_stage(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate architect output based on the provided request."""
        description = request["description"]
        requirements = request["requirements"]
        project_name = self._derive_project_name(description)
        
        file_structure = self._suggest_file_structure(requirements)
        architectural_plan = {
            "project_name": project_name,
            "description": description,
            "requirements": requirements,
            "file_structure": file_structure,
            "notes": "Auto-generated architecture outline pending MCP integration.",
        }
        
        self.pipeline_state["architecture"] = architectural_plan
        self._track_usage("architect", description, {"files": len(file_structure)})
        return architectural_plan
    
    def _run_coder_stage(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Produce a placeholder code package derived from the architecture."""
        project_name = architecture["project_name"]
        requirements = architecture["requirements"]
        description = architecture["description"]
        
        files = {
            "main.py": self._build_main_py(project_name, description, requirements),
            "utils.py": self._build_utils_py(),
            "tests/__init__.py": "",
        }
        
        code_package = {
            "project_name": project_name,
            "files": files,
            "requirements": requirements,
            "entry_point": "main.py",
        }
        
        self.pipeline_state["code_package"] = code_package
        self._track_usage("coder", "\n".join(files.values()), {"files": list(files.keys())})
        return code_package
    
    def _run_tester_stage(self, code_package: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """Generate lightweight pytest scaffolding and synthetic results."""
        test_file_path = "tests/test_generated_app.py"
        test_content = self._build_pytest_file(code_package["project_name"])
        
        test_files = {test_file_path: test_content}
        self.pipeline_state["test_files"] = test_files
        
        test_results = {
            "status": "not_run",
            "summary": "Tests generated but execution deferred to runtime environment.",
            "total_tests": 1,
        }
        self.pipeline_state["test_results"] = test_results
        self._track_usage("tester", test_content, {"tests_generated": len(test_files)})
        return test_files, test_results
    
    def _run_debugger_stage(
        self,
        code_package: Dict[str, Any],
        test_files: Dict[str, str],
        test_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Aggregate final package; debugging is a placeholder until MCP integration."""
        final_files = {**code_package["files"], **test_files}
        final_package = {
            "project_name": code_package["project_name"],
            "files": final_files,
            "requirements": code_package["requirements"],
            "entry_point": code_package.get("entry_point", "main.py"),
            "test_results": test_results,
            "architecture": self.pipeline_state.get("architecture"),
        }
        
        self.pipeline_state["final_package"] = final_package
        self._track_usage("debugger", " ".join(final_files.keys()), {"files": len(final_files)})
        return final_package
    
    # ------------------------- Build helpers -------------------------- #
    
    def _derive_project_name(self, description: str) -> str:
        """Create a slugified project name from the description."""
        sanitized = "".join(ch if ch.isalnum() else "_" for ch in description.lower())
        sanitized = "_".join(filter(None, sanitized.split("_")))
        return sanitized[:40] or "generated_project"
    
    def _suggest_file_structure(self, requirements: List[str]) -> List[Dict[str, str]]:
        """Propose a file structure with sensible defaults."""
        structure = [
            {"path": "main.py", "purpose": "Application entry point"},
            {"path": "utils.py", "purpose": "Shared helpers and abstractions"},
            {"path": "tests/test_generated_app.py", "purpose": "Pytest suite"},
        ]
        
        for idx, requirement in enumerate(requirements, start=1):
            module_path = f"modules/feature_{idx}.py"
            summary = requirement[:120] or f"Feature {idx}"
            structure.append({"path": module_path, "purpose": summary})
        
        return structure
    
    def _build_main_py(self, project_name: str, description: str, requirements: List[str]) -> str:
        """Return a runnable placeholder for main.py."""
        requirements_literal = ", ".join(f'"{req}"' for req in requirements) or '"No explicit requirements provided."'
        return f'''"""Auto-generated entry point for {project_name}."""

def main():
    """Entry point placeholder that summarises requirements."""
    description = "{description}"
    requirements = [{requirements_literal}]
    
    print("=== Generated Application Skeleton ===")
    print(description)
    print("\\nRequirements:")
    for idx, req in enumerate(requirements, 1):
        print(f"  {{idx}}. {{req}}")
    
    print("\\nImplementation pending MCP-driven agents.")


if __name__ == "__main__":
    main()
'''
    
    def _build_utils_py(self) -> str:
        """Provide small helper utilities for the generated project."""
        return '''"""Utility helpers for the generated project."""

def format_requirement(requirement: str, index: int) -> str:
    """Return a human readable requirement line."""
    return f"{index}. {requirement}"


def summarize_requirements(requirements):
    """Return a dictionary summary for analytics."""
    return {
        "total": len(requirements),
        "empty": not requirements,
    }
'''
    
    def _build_pytest_file(self, project_name: str) -> str:
        """Create a simple pytest file validating the generated skeleton."""
        return f'''"""Auto-generated tests for {project_name}."""

import importlib
import types


def test_main_module_loads():
    module = importlib.import_module("main")
    assert isinstance(module, types.ModuleType)


def test_main_callable_exists():
    module = importlib.import_module("main")
    assert hasattr(module, "main")
    assert callable(module.main)
'''
