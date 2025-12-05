# Workflow & Data Flow

## Pipeline Flow (with Feedback Loop)

```
Requirements (str)
    ↓
[Agent A: Architect]
    ├─ analyze_requirements(str) → Dict
    ├─ design_file_structure(Dict) → Dict
    └─ create_architectural_plan(Dict, Dict) → Dict
    ↓
Architectural Plan (Dict)
    ↓
┌─────────────────────────────────────────────────┐
│           FEEDBACK LOOP (until tests pass)      │
└─────────────────────────────────────────────────┘
    ↓
[Agent B: Coder]
    ├─ receive_architecture(Dict) → None
    ├─ generate_code() → Dict[str, str]  [First iteration]
    ├─ regenerate_code(Dict) → Dict[str, str]  [Subsequent iterations]
    └─ save_code_to_files() → Dict[str, str]
    ↓
Code Package (Dict)
    ↓
[Agent C: Tester]
    ├─ receive_code(Dict) → None
    ├─ generate_test_cases() → str
    ├─ local_server.run_tests() → Dict
    └─ [On failure] cleanup_workspace()
    ↓
Test Results + Code Package (Dict)
    ↓
[Agent D: Debugger]
    ├─ receive_code_and_results(Dict) → None
    ├─ analyze_failures() → Dict
    └─ pass_to_coder_for_regeneration() → Dict
    ↓
Regeneration Instructions (Dict)
    ↓
    └─ [If tests failed] → Loop back to Agent B
    └─ [If tests passed] → Continue
    ↓
Final Code Package (Dict)
    ↓
[LocalServer]
    ├─ receive_code_package(Dict) → bool
    ├─ save_code_to_directory(Dict) → str
    ├─ execute_code(str, int) → Dict
    └─ return_code_to_ui() → Dict
```

## Data Types

### Agent A: Architect

**Input:**
- `requirements: str` - Natural language requirements

**Output:**
- `analysis: Dict[str, Any]` - `{"components": List[str], "dependencies": List[str], "architecture_type": str, "complexity": str, "summary": str}`
- `file_structure: Dict[str, Any]` - `{"files": Dict[str, str], "file_structure": Dict, "imports": Dict, "entry_point": str}`
- `architectural_plan: Dict[str, Any]` - `{"requirements": str, "analysis": Dict, "file_structure": Dict, "detailed_plan": Dict, "timestamp": str}`

### Agent B: Coder

**Input:**
- `architectural_plan: Dict[str, Any]` - For initial generation
- `regeneration_instructions: Dict[str, Any]` - For regeneration (from Agent D)

**Output:**
- `generated_code: Dict[str, str]` - `{"main.py": "code...", "utils.py": "code..."}`
- `code_package: Dict[str, Any]` - `{"code": Dict[str, str], "workspace_dir": str, "architectural_plan": Dict, "files": List[str]}`

**Methods:**
- `generate_code() → Dict[str, str]` - Initial code generation
- `regenerate_code(regeneration_instructions: Dict) → Dict[str, str]` - Regenerate with feedback

**LocalServer Usage:**
- `receive_code_package({"project_name": str, "files": Dict[str, str], "entry_point": str})`
- `save_code_to_directory(code_package)`

### Agent C: Tester

**Input:**
- `code_package: Dict[str, Any]` - `{"code": Dict[str, str], "workspace_dir": str, "architectural_plan": Dict, "files": List[str]}`

**Output:**
- `test_code: str` - Generated pytest test file content
- `test_results: Dict[str, Any]` - `{"exit_code": int, "stdout": str, "stderr": str, "output": str, "passed": bool, "json_report": Dict, "test_file": str}`
- `test_package: Dict[str, Any]` - `{"code_package": Dict (with test file), "test_results": Dict, "test_analysis": Dict, "test_file": str}`

**LocalServer Usage:**
- `receive_code_package({"project_name": "test_project", "files": Dict[str, str], "entry_point": "main.py"})`
- `save_code_to_directory(server_package)` - Saves code + test file
- `run_tests("test_main.py", timeout)` - Executes pytest
- `cleanup_workspace()` - On test failure

### Agent D: Debugger

**Input:**
- `package: Dict[str, Any]` - `{"code_package": Dict (includes test file), "test_results": Dict, "test_analysis": Dict, "test_file": str}`

**Output:**
- `failure_analysis: Dict[str, Any]` - `{"has_failures": bool, "issues": List[Dict], "fix_priority": List[int], "summary": str}`
- `regeneration_instructions: Dict[str, Any]` - `{"needs_regeneration": bool, "regeneration_instructions": str, "key_changes": List[str], "priority_fixes": List[str], "original_architectural_plan": Dict}`
- `fixed_code: Dict[str, str]` - `{"main.py": "fixed_code...", "utils.py": "fixed_code..."}` (optional, for direct fixes)
- `verification: Dict[str, Any]` - `{"exit_code": int, "passed": bool, "stdout": str, "stderr": str, "output": str, "iteration": int}` (optional)
- `final_package: Dict[str, Any]` - `{"code": Dict[str, str], "workspace_dir": str, "debug_log": List, "original_plan": Dict, "test_results": Dict, "files": List[str]}`

**Methods:**
- `analyze_failures() → Dict` - Analyze test failures
- `pass_to_coder_for_regeneration() → Dict` - Generate instructions for Agent B to regenerate code
- `debug_code(Dict) → Dict[str, str]` - Direct code fixing (optional)
- `verify_fixes() → Dict` - Verify fixes (optional)

**LocalServer Usage:**
- `receive_code_package({"project_name": "debug_project", "files": Dict[str, str] (includes test file), "entry_point": "main.py"})`
- `save_code_to_directory(code_package)` - Saves fixed code + test file (if using direct fixes)
- `run_tests("test_main.py", timeout)` - Verifies fixes (if using direct fixes)

### LocalServer

**Code Package Format:**
```python
{
    "project_name": str,
    "files": Dict[str, str],  # filename -> content
    "requirements": List[str],  # Optional
    "entry_point": str  # Optional, default: "main.py"
}
```

**Methods:**
- `receive_code_package(Dict) -> bool`
- `save_code_to_directory(Dict) -> str` - Returns project_path
- `execute_code(str, int) -> Dict` - Returns execution results
- `run_tests(str, int) -> Dict` - Returns test results
- `cleanup_workspace() -> None` - Deletes project directory

## Key Workflow Rules

1. **Atomic Operations**: All file operations use `save_code_to_directory()` with complete code packages
2. **Clean State**: Tester cleans workspace on test failure, debugger regenerates from scratch
3. **Test File Preservation**: Test file included in package passed to debugger
4. **Project Isolation**: Each agent uses its own project name (code_project, test_project, debug_project)
5. **Feedback Loop**: If tests fail, Agent D provides feedback → Agent B regenerates → Agent C tests again → Loop until tests pass
6. **Maximum Iterations**: Feedback loop continues up to max_iterations (default: 5) or until tests pass

## Workflow Orchestrator

Use `WorkflowOrchestrator` to run the complete workflow with feedback loop:

```python
from workflow_orchestrator import WorkflowOrchestrator
from agents.agent_architect import AgentArchitect
from agents.agent_coder import AgentCoder
from agents.agent_tester import AgentTester
from agents.agent_debugger import AgentDebugger

# Initialize agents
architect = AgentArchitect(mcp_client, tracker)
coder = AgentCoder(mcp_client, tracker, local_server=local_server)
tester = AgentTester(mcp_client, tracker, local_server=local_server)
debugger = AgentDebugger(mcp_client, tracker, local_server=local_server)

# Create orchestrator
orchestrator = WorkflowOrchestrator(architect, coder, tester, debugger, max_iterations=5)

# Run complete workflow
result = orchestrator.run_complete_workflow("Create a calculator app")
```

