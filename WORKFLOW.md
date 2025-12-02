# Workflow & Data Flow

## Pipeline Flow

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
[Agent B: Coder]
    ├─ receive_architecture(Dict) → None
    ├─ generate_code() → Dict[str, str]
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
    ├─ debug_code(Dict) → Dict[str, str]
    └─ verify_fixes() → Dict
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
- `architectural_plan: Dict[str, Any]`

**Output:**
- `generated_code: Dict[str, str]` - `{"main.py": "code...", "utils.py": "code..."}`
- `code_package: Dict[str, Any]` - `{"code": Dict[str, str], "workspace_dir": str, "architectural_plan": Dict, "files": List[str]}`

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
- `fixed_code: Dict[str, str]` - `{"main.py": "fixed_code...", "utils.py": "fixed_code..."}`
- `verification: Dict[str, Any]` - `{"exit_code": int, "passed": bool, "stdout": str, "stderr": str, "output": str, "iteration": int}`
- `final_package: Dict[str, Any]` - `{"code": Dict[str, str], "workspace_dir": str, "debug_log": List, "original_plan": Dict, "test_results": Dict, "files": List[str]}`

**LocalServer Usage:**
- `receive_code_package({"project_name": "debug_project", "files": Dict[str, str] (includes test file), "entry_point": "main.py"})`
- `save_code_to_directory(code_package)` - Saves fixed code + test file
- `run_tests("test_main.py", timeout)` - Verifies fixes

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

