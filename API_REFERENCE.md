# API Reference - Input/Output Types

## Agent A: Architect

```python
analyze_requirements(requirements: str) -> Dict[str, Any]
# Input: "Create a calculator app"
# Output: {"components": [...], "dependencies": [...], "architecture_type": str, "complexity": str, "summary": str}

design_file_structure(analysis: Dict[str, Any]) -> Dict[str, Any]
# Input: analysis dict
# Output: {"files": {filename: description}, "file_structure": Dict, "imports": Dict, "entry_point": str}

create_architectural_plan(analysis: Dict, file_structure: Dict) -> Dict[str, Any]
# Input: analysis dict, file_structure dict
# Output: {"requirements": str, "analysis": Dict, "file_structure": Dict, "detailed_plan": Dict, "timestamp": str}

pass_to_coder() -> Dict[str, Any]
# Output: architectural_plan dict
```

## Agent B: Coder

```python
receive_architecture(architectural_plan: Dict[str, Any]) -> None

generate_code() -> Dict[str, str]
# Output: {"main.py": "code...", "utils.py": "code..."}

save_code_to_files() -> Dict[str, str]
# Output: {"main.py": "/path/to/main.py", ...}

get_code_package() -> Dict[str, Any]
# Output: {"code": Dict[str, str], "workspace_dir": str, "architectural_plan": Dict, "files": List[str]}

pass_to_tester() -> Dict[str, Any]
# Output: code_package dict
```

## Agent C: Tester

```python
receive_code(code_package: Dict[str, Any]) -> None
# Input: {"code": Dict[str, str], "workspace_dir": str, "architectural_plan": Dict, "files": List[str]}

generate_test_cases() -> str
# Output: test code as string

execute_tests() -> Dict[str, Any]
# Output: {"exit_code": int, "stdout": str, "stderr": str, "output": str, "passed": bool, "json_report": Dict, "test_file": str}

analyze_test_results() -> Dict[str, Any]
# Output: {"overall_status": str, "exit_code": int, "has_failures": bool, "failures": List[Dict], "failure_count": int, ...}

pass_to_debugger() -> Dict[str, Any]
# Output: {"code_package": Dict, "test_results": Dict, "test_analysis": Dict, "test_file": str}
```

## Agent D: Debugger

```python
receive_code_and_results(package: Dict[str, Any]) -> None
# Input: {"code_package": Dict, "test_results": Dict, "test_analysis": Dict, "test_file": str}

analyze_failures() -> Dict[str, Any]
# Output: {"has_failures": bool, "issues": List[Dict], "fix_priority": List[int], "summary": str}

debug_code(failure_analysis: Optional[Dict] = None) -> Dict[str, str]
# Output: {"main.py": "fixed_code...", "utils.py": "fixed_code..."}

verify_fixes() -> Dict[str, Any]
# Output: {"exit_code": int, "passed": bool, "stdout": str, "stderr": str, "output": str, "iteration": int}

debug_and_verify() -> Dict[str, Any]
# Output: {"iterations": List[Dict], "final_status": str, "total_iterations": int}

pass_to_server() -> Dict[str, Any]
# Output: {"code": Dict[str, str], "workspace_dir": str, "debug_log": List, "original_plan": Dict, "test_results": Dict, "files": List[str]}
```

## LocalServer

```python
receive_code_package(code_package: Dict) -> bool
# Input: {"project_name": str, "files": Dict[str, str], "requirements": List[str], "entry_point": str}
# Output: bool

save_code_to_directory(code_package: Dict) -> str
# Input: {"project_name": str, "files": Dict[str, str], "requirements": List[str], "entry_point": str}
# Output: project_path (str)
# Note: This is the ONLY method for saving files. Deletes existing project directory if it exists.

execute_code(entry_point: str = "main.py", timeout: int = 30) -> Dict
# Output: {"stdout": str, "stderr": str, "return_code": int, "execution_time": float, "success": bool, "timestamp": str}

run_tests(test_file: str = "test_main.py", timeout: int = 300) -> Dict
# Output: {"exit_code": int, "stdout": str, "stderr": str, "output": str, "return_code": int, "execution_time": float, "success": bool, "passed": bool, "json_report": Dict, "test_file": str, "timestamp": str}

get_execution_results() -> Dict
# Output: last execution results dict

return_code_to_ui() -> Dict
# Output: {"project_name": str, "files": Dict[str, str], "execution_results": Dict, "project_path": str}

cleanup_workspace() -> None
# Deletes current project directory and resets state
```

