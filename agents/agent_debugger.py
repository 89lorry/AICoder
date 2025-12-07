"""
Agent D: Debugger
Reviews the results from the generated code and debugs
"""

import logging
import os
from typing import Dict, Any, List, Optional
from config.settings import Settings
from utils.memory_manager import MemoryManager
from utils.langchain_wrapper import LangChainWrapper
from utils.conversation_logger import ConversationLogger
from datetime import datetime


class AgentDebugger:
    """Agent responsible for debugging and fixing code issues"""
    
    def __init__(self, mcp_client, api_usage_tracker=None, workspace_dir=None, enable_memory=True, local_server=None, session_id=None):
        """
        Initialize the Debugger agent
        
        Args:
            mcp_client: MCP client instance for AI interactions
            api_usage_tracker: Optional API usage tracker instance
            workspace_dir: Directory where code files are located
            enable_memory: Whether to enable LangChain memory
            local_server: Optional LocalServer instance for file operations and test execution. If None, creates one.
            session_id: Optional session ID for conversation logging
        """
        self.mcp_client = mcp_client
        self.api_usage_tracker = api_usage_tracker
        self.logger = logging.getLogger(__name__)
        self.workspace_dir = workspace_dir or Settings.WORKSPACE_DIR
        
        # Initialize conversation logger
        self.conversation_logger = ConversationLogger(
            agent_name="debugger",
            session_id=session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        
        # Initialize LocalServer if not provided
        if local_server is None:
            from server.local_server import LocalServer
            self.local_server = LocalServer(workspace_dir=self.workspace_dir)
        else:
            self.local_server = local_server
        
        # Initialize LangChain memory
        self.memory_manager = None
        self.langchain_wrapper = None
        if enable_memory and Settings.ENABLE_MEMORY:
            self.memory_manager = MemoryManager("debugger", memory_type="buffer_window")
            self.langchain_wrapper = LangChainWrapper(
                mcp_client=mcp_client,
                memory_manager=self.memory_manager,
                llm_provider="openai"
            )
            # Add system message to memory
            self.memory_manager.add_system_message(
                "You are an expert software debugger. You analyze test failures, identify "
                "root causes, and fix code issues systematically. You learn from previous "
                "fixes and avoid repeating mistakes. You verify all fixes before considering "
                "them complete."
            )
            self.logger.info("Initialized LangChain memory for Debugger agent")
        
        # Internal state
        self.code_package = None
        self.test_results = None
        self.test_analysis = None
        self.debug_log = []
        self.fixed_code = {}
        self.max_fix_iterations = 5  # Maximum internal retry attempts
        self.current_iteration = 0
        self.max_retries = 3  # Maximum retries for API timeouts
    
    def validate_code(self, code: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate generated code for common issues before testing
        
        Args:
            code: Dictionary mapping filenames to code content
            
        Returns:
            Dictionary containing validation results
        """
        import ast
        import re
        
        validation_results = {
            "valid": True,
            "issues": [],
            "warnings": []
        }
        
        for filename, content in code.items():
            if not filename.endswith('.py'):
                continue
            
            # Check 1: Syntax validation
            try:
                ast.parse(content)
            except SyntaxError as e:
                validation_results["valid"] = False
                validation_results["issues"].append({
                    "file": filename,
                    "type": "syntax_error",
                    "message": f"Syntax error at line {e.lineno}: {e.msg}",
                    "severity": "critical"
                })
                continue  # Skip other checks if syntax is invalid
            
            # Check 2: Detect infinite loops (basic heuristic)
            # Look for 'while True:' without break/return within reasonable lines
            while_true_pattern = r'while\s+True\s*:'
            if re.search(while_true_pattern, content):
                # Check if there's a break or return nearby
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if re.search(while_true_pattern, line):
                        # Check next 20 lines for break/return
                        has_exit = False
                        for j in range(i + 1, min(i + 20, len(lines))):
                            if re.search(r'\b(break|return)\b', lines[j]):
                                has_exit = True
                                break
                        if not has_exit:
                            validation_results["warnings"].append({
                                "file": filename,
                                "type": "potential_infinite_loop",
                                "message": f"Line {i+1}: 'while True:' without visible break/return",
                                "severity": "high"
                            })
            
            # Check 3: Blocking input() calls
            if re.search(r'\binput\s*\(', content):
                validation_results["warnings"].append({
                    "file": filename,
                    "type": "blocking_input",
                    "message": "Code contains input() which may block execution",
                    "severity": "medium"
                })
            
            # Check 4: Infinite recursion risk (basic)
            # Look for functions that call themselves without obvious base case
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_name = node.name
                        # Check if function calls itself
                        for subnode in ast.walk(node):
                            if isinstance(subnode, ast.Call):
                                if isinstance(subnode.func, ast.Name) and subnode.func.id == func_name:
                                    # Check if there's an if statement (base case)
                                    has_if = any(isinstance(n, ast.If) for n in ast.walk(node))
                                    if not has_if:
                                        validation_results["warnings"].append({
                                            "file": filename,
                                            "type": "potential_infinite_recursion",
                                            "message": f"Function '{func_name}' appears recursive without obvious base case",
                                            "severity": "high"
                                        })
            except:
                pass  # AST parsing already validated above
            
            # Check 5: Network/socket operations that might block
            blocking_patterns = [
                (r'socket\.connect', 'socket.connect() may block'),
                (r'requests\.get|requests\.post', 'HTTP requests without timeout may block'),
                (r'urllib\.request', 'urllib requests without timeout may block'),
                (r'time\.sleep\(\s*\d{3,}', 'Long sleep() duration detected')
            ]
            
            for pattern, message in blocking_patterns:
                if re.search(pattern, content):
                    validation_results["warnings"].append({
                        "file": filename,
                        "type": "potential_blocking_operation",
                        "message": message,
                        "severity": "medium"
                    })
        
        # Overall validation status
        if validation_results["issues"]:
            validation_results["valid"] = False
        
        self.logger.info(f"Code validation: {len(validation_results['issues'])} errors, {len(validation_results['warnings'])} warnings")
        
        return validation_results
    
    def receive_code_and_results(self, package: Dict[str, Any]) -> None:
        """
        Receive code package and test results from Agent C
        
        Args:
            package: Dictionary containing code_package, test_results, and test_analysis
        """
        self.code_package = package.get("code_package")
        self.test_results = package.get("test_results")
        self.test_analysis = package.get("test_analysis")
        
        if not self.test_analysis and self.test_results:
            # Create a basic analysis if not provided
            self.test_analysis = {
                "overall_status": "passed" if self.test_results.get("passed") else "failed",
                "has_failures": not self.test_results.get("passed", False),
                "failures": []
            }
        
        self.logger.info(f"Received code package and test results. Status: {self.test_analysis.get('overall_status', 'unknown') if self.test_analysis else 'unknown'}")
    
    def analyze_and_fix_combined(self) -> Dict[str, Any]:
        """
        OPTIMIZED: Analyze failures + Fix code + Update tests in ONE API call
        Then run internal loop with LocalServer execution until tests pass
        
        Returns:
            Dictionary containing all fixed code and test results
        """
        if not self.test_analysis:
            raise ValueError("No test analysis available. Call receive_code_and_results() first.")
        
        if self.test_analysis.get("overall_status") == "passed":
            self.logger.info("No failures to fix - all tests passed")
            return {
                "success": True,
                "fixed_code": self.code_package.get("code", {}),
                "iterations": 0
            }
        
        self.logger.info("Starting combined analyze+fix+test in ONE API call with internal retry loop...")
        
        all_attempts = []
        
        for attempt in range(1, self.max_fix_iterations + 1):
            self.current_iteration = attempt
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Debugger Attempt {attempt}/{self.max_fix_iterations}")
            self.logger.info(f"{'='*60}")
            
            # Get current failures
            failures = self.test_analysis.get("failures", [])
            code = self.fixed_code if self.fixed_code else self.code_package.get("code", {})
            test_output = self.test_results.get('output', '') if self.test_results else ''
            
            # Build combined prompt for analyze + fix + update tests
            prompt = f"""You are debugging code that failed tests. Provide fixes as a structured response.

Test Failures:
{self._format_failures(failures)}

Current Code:
{self._format_code(code)}

Test Output (last 2000 chars):
{test_output[-2000:] if len(test_output) > 2000 else test_output}

Attempt: {attempt}/{self.max_fix_iterations}

Before analyzing complex logic:
1. Check if __str__ returns correct format
2. Check if object is being printed without str()
3. Check if mock inputs match actual input() calls
4. Check if return values are correct type

Most test failures are formatting issues, not logic issues!

Example: If test expects "Name: Bob" but gets "Contact(name='Bob')"
→ Fix __str__ to return "Name: Bob" format
→ DON'T redesign the entire class structure

⚠️ CRITICAL TESTING PATTERNS - Read carefully before fixing tests:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. MOCKING CLASSES: Use @patch, NEVER reassign class variables
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ WRONG - Causes UnboundLocalError:
    original_manager = ContactManager  
    ContactManager = MagicMock(...)

✅ CORRECT - Use @patch decorator:
    @patch('main.ContactManager')
    def test_function(MockContactManager, ...):
        MockContactManager.return_value = manager_fixture

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. MOCKING VS REAL OBJECTS: Choose the right approach
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When testing code that calls internal methods (e.g., add_contact calls save_contacts):

❌ WRONG - MagicMock prevents real method execution:
    mock_instance = MagicMock(spec=ContactManager)
    mock_instance.add_contact = MagicMock()  # Real add_contact never runs!
    MockContactManager.return_value = mock_instance
    # save_contacts is never called because add_contact mock doesn't execute real code

✅ CORRECT - Use REAL fixture objects:
    @patch('main.ContactManager')
    def test_add_contact(MockContactManager, contact_manager):
        MockContactManager.return_value = contact_manager  # Real object!
        # Now add_contact executes real code and calls save_contacts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. PRINTING OBJECTS: Extract string representations correctly
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When code does: print(contact)  # where contact has __str__ method

❌ WRONG - Gets object reference, not string:
    printed_calls = [call.args[0] for call in mock_print.call_args_list]
    # Results in: [<main.Contact object at 0x...>]

✅ CORRECT - Convert to string:
    printed_calls = [str(call.args[0]) if not isinstance(call.args[0], str) 
                     else call.args[0] for call in mock_print.call_args_list]
    # Results in: ["Name: Alice Smith, Email: alice@example.com, ..."]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. LEARNING FROM PREVIOUS ATTEMPTS: Don't repeat mistakes!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If previous attempts show:
- "Expected 'save_contacts' to have been called once. Called 0 times"
  → You're using MagicMock when you should use real fixture!

- "AssertionError: assert 'Name: ...' in [<main.Contact object>]"
  → You need to convert objects to strings in your assertions!

- Same error appears 2+ times
  → Your fix didn't work! Try a COMPLETELY DIFFERENT approach!

COMPLETE TESTING PATTERN EXAMPLE:
```python
from unittest.mock import patch

@patch('builtins.input', side_effect=['2', 'Alice', '5'])
@patch('builtins.print')
@patch('main.ContactManager')
def test_search(MockContactManager, mock_print, mock_input, populated_contact_manager):
    # Use REAL fixture, not MagicMock!
    MockContactManager.return_value = populated_contact_manager
    
    from main import main
    main()
    
    # Convert printed objects to strings
    printed_calls = []
    for call in mock_print.call_args_list:
        arg = call.args[0] if call.args else ""
        printed_calls.append(str(arg))
    
    # Now assertions work correctly
    assert "Name: Alice Smith, Email: alice@example.com, Phone: 123-456-7890" in printed_calls
```

YOUR TASK:
1. Analyze what's wrong - identify the ROOT CAUSE (not just symptoms)
2. Fix ALL code files that have issues using CORRECT patterns
3. Update test file if needed to match fixed code
4. DO NOT repeat the same mistake from previous attempts!

RESPONSE FORMAT:
First, provide analysis section:
ANALYSIS_START
- Issue 1: [file] [problem and ROOT CAUSE]
- Issue 2: [file] [problem and ROOT CAUSE]
Summary: [brief summary]
ANALYSIS_END

Then, provide each fixed file:
FILE_START: filename.py
[complete fixed code here]
FILE_END

FILE_START: another_file.py
[complete fixed code here]  
FILE_END

CRITICAL RULES:
- Use the exact format above with ANALYSIS_START/END and FILE_START/END markers
- Include complete code for each file that needs fixing
- No JSON, no markdown code blocks
- Only include files that actually need changes
- If this is attempt 2+, DO NOT repeat the same fix that failed before!

Previous attempts: {attempt - 1}
{f"⚠️ WARNING: You already tried {attempt - 1} time(s). Use a DIFFERENT approach!" if attempt > 1 else ""}
"""
            
            try:
                # Single combined API call
                if self.langchain_wrapper:
                    response = self.langchain_wrapper.invoke(prompt)
                    if self.api_usage_tracker:
                        token_usage = self.langchain_wrapper.get_token_usage()
                        if token_usage:
                            self.api_usage_tracker.track_usage("debugger", token_usage)
                    # Log conversation
                    response_text = response if isinstance(response, str) else self.mcp_client.extract_text_from_response(response)
                    self.conversation_logger.log_interaction(
                        prompt=prompt,
                        response=response_text,
                        metadata=self.langchain_wrapper.get_token_usage()
                    )
                else:
                    if not hasattr(self.mcp_client, 'session') or self.mcp_client.session is None:
                        self.mcp_client.connect()
                    response = self.mcp_client.send_request(prompt)
                    if self.api_usage_tracker:
                        token_usage = self.mcp_client.get_token_usage()
                        if token_usage:
                            self.api_usage_tracker.track_usage("debugger", token_usage)
                    # Log conversation
                    response_text = self.mcp_client.extract_text_from_response(response)
                    self.conversation_logger.log_interaction(
                        prompt=prompt,
                        response=response_text,
                        metadata=self.mcp_client.get_token_usage()
                    )
                
                # Parse combined response in text format
                if isinstance(response, dict):
                    response_text = self.mcp_client.extract_text_from_response(response)
                else:
                    response_text = str(response)
                
                # Parse text format with markers
                analysis_summary = ""
                fixed_files = {}
                
                # Extract analysis
                if 'ANALYSIS_START' in response_text and 'ANALYSIS_END' in response_text:
                    analysis_start = response_text.find('ANALYSIS_START')
                    analysis_end = response_text.find('ANALYSIS_END')
                    analysis_summary = response_text[analysis_start:analysis_end+12].strip()
                    self.logger.info(f"Analysis extracted: {len(analysis_summary)} chars")
                
                # Extract files
                import re
                file_pattern = r'FILE_START:\s*(.+?)\n(.*?)FILE_END'
                matches = re.findall(file_pattern, response_text, re.DOTALL)
                
                for filename, content in matches:
                    filename = filename.strip()
                    content = content.strip()
                    fixed_files[filename] = content
                    self.logger.info(f"Extracted fixed file: {filename} ({len(content)} chars)")
                
                if not fixed_files:
                    self.logger.warning("No fixed files found in response!")
                    # Try to continue with next attempt
                    attempt_result = {
                        "attempt": attempt,
                        "analysis": {"summary": "Failed to parse response"},
                        "fixed_files": [],
                        "test_passed": False,
                        "error": "No fixed files in response"
                    }
                    all_attempts.append(attempt_result)
                    continue
                
                # Apply fixes to code
                updated_code = code.copy()
                for filename, fixed_content in fixed_files.items():
                    updated_code[filename] = fixed_content
                    self.logger.info(f"  Applied fix to {filename}")
                
                self.fixed_code = updated_code
                
                # Save to LocalServer and run tests
                files_to_save = updated_code.copy()
                code_package = {
                    "project_name": "debug_project",
                    "files": files_to_save,
                    "entry_point": "main.py"
                }
                
                self.local_server.receive_code_package(code_package)
                project_path = self.local_server.save_code_to_directory(code_package)
                self.logger.info(f"Saved fixed code to {project_path}")
                
                # Run tests on LocalServer
                self.logger.info("Running tests on fixed code...")
                test_results = self.local_server.run_tests(
                    test_file="test_main.py",
                    timeout=300
                )
                
                attempt_result = {
                    "attempt": attempt,
                    "analysis": {"summary": analysis_summary},
                    "fixed_files": list(fixed_files.keys()),
                    "test_passed": test_results.get("passed", False),
                    "test_output": test_results.get("output", "")[:500]
                }
                all_attempts.append(attempt_result)
                
                if test_results.get("passed"):
                    self.logger.info(f"SUCCESS: All tests passed after attempt {attempt}!")
                    return {
                        "success": True,
                        "fixed_code": self.fixed_code,
                        "attempts": all_attempts,
                        "final_test_results": test_results
                    }
                else:
                    self.logger.warning(f"WARNING: Tests still failing after attempt {attempt}")
                    # Update test_results for next iteration
                    self.test_results = test_results
                    # Parse failures for next iteration
                    self.test_analysis = {
                        "overall_status": "failed",
                        "has_failures": True,
                        "failures": self._parse_test_failures(test_results.get("output", ""))
                    }
                        
            except Exception as e:
                self.logger.error(f"Error in attempt {attempt}: {str(e)}")
                all_attempts.append({
                    "attempt": attempt,
                    "error": str(e),
                    "test_passed": False
                })
        
        # Max attempts reached
        self.logger.warning(f"Maximum attempts ({self.max_fix_iterations}) reached without passing all tests")
        return {
            "success": False,
            "fixed_code": self.fixed_code if self.fixed_code else code,
            "attempts": all_attempts,
            "final_test_results": self.test_results
        }
    
    def _parse_test_failures(self, test_output: str) -> List[Dict[str, Any]]:
        """Parse test failures from pytest output"""
        failures = []
        if "FAILED" in test_output:
            lines = test_output.split('\n')
            for line in lines:
                if line.strip().startswith("FAILED"):
                    parts = line.split(" - ")
                    test_name = parts[0].replace("FAILED ", "").strip()
                    error_msg = parts[1] if len(parts) > 1 else "Test failed"
                    failures.append({
                        "test_name": test_name,
                        "status": "failed",
                        "error_message": error_msg
                    })
        return failures
    
    def get_final_package(self) -> Dict[str, Any]:
        """
        Get final code package ready for server
        
        Returns:
            Dictionary containing final code package
        """
        if not self.fixed_code:
            # Use original code if no fixes were made
            self.fixed_code = self.code_package.get("code", {}).copy()
        
        return {
            "code": self.fixed_code,
            "workspace_dir": self.workspace_dir,
            "debug_log": self.debug_log,
            "original_plan": self.code_package.get("architectural_plan"),
            "test_results": self.test_results,
            "files": list(self.fixed_code.keys())
        }
    
    def pass_to_server(self) -> Dict[str, Any]:
        """
        Pass final code package to server
        
        Returns:
            Final code package dictionary
        """
        self.logger.info("Passing final code package to server")
        return self.get_final_package()
    
    def _parse_regeneration_instructions(self, response: str) -> Dict[str, Any]:
        """Parse regeneration instructions from MCP response"""
        import json
        try:
            if isinstance(response, dict):
                return response
            
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                return json.loads(json_str)
            
            return {
                "regeneration_instructions": str(response)[:500],
                "key_changes": [],
                "priority_fixes": []
            }
        except json.JSONDecodeError:
            self.logger.warning("Could not parse regeneration instructions JSON")
            return {
                "regeneration_instructions": str(response)[:500],
                "key_changes": [],
                "priority_fixes": []
            }
    
    def _format_failures(self, failures: List[Dict[str, str]]) -> str:
        """Format failure information for prompts"""
        if not failures:
            return "No failures"
        
        formatted = []
        for i, failure in enumerate(failures, 1):
            formatted.append(f"\nFailure {i}:")
            formatted.append(f"  Test: {failure.get('test_name', 'Unknown')}")
            formatted.append(f"  Status: {failure.get('status', 'Unknown')}")
            formatted.append(f"  Error: {failure.get('error_message', 'No error message')}")
            if failure.get('traceback'):
                formatted.append(f"  Traceback: {' '.join(failure['traceback'][:3])}")
        
        return "\n".join(formatted)
    
    def _format_issues(self, issues: List[Dict[str, Any]]) -> str:
        """Format issues for fix prompts"""
        formatted = []
        for i, issue in enumerate(issues, 1):
            formatted.append(f"\nIssue {i}:")
            formatted.append(f"  Location: {issue.get('file', 'unknown')} - {issue.get('location', 'unknown')}")
            formatted.append(f"  Problem: {issue.get('problem', 'Unknown problem')}")
            formatted.append(f"  Root Cause: {issue.get('root_cause', 'Unknown')}")
            formatted.append(f"  Severity: {issue.get('severity', 'medium')}")
        
        return "\n".join(formatted)
    
    def _format_code(self, code: Dict[str, str]) -> str:
        """Format code files for prompts"""
        formatted = []
        for filename, content in code.items():
            formatted.append(f"\n=== {filename} ===\n{content}\n")
        return "\n".join(formatted)
    
    def _parse_failure_analysis(self, response: str) -> Dict[str, Any]:
        """Parse failure analysis from MCP response with robust markdown stripping"""
        import json
        import re
        
        try:
            if isinstance(response, dict):
                return response
            
            # Strip markdown code blocks if present
            response_clean = response.strip()
            
            # Remove ```json ... ``` blocks
            if '```json' in response_clean or '```' in response_clean:
                self.logger.warning("Detected markdown formatting in response - stripping it")
                # Remove ```json at start
                response_clean = re.sub(r'^```(?:json)?\s*\n?', '', response_clean)
                # Remove ``` at end
                response_clean = re.sub(r'\n?```\s*$', '', response_clean)
            
            # Extract JSON
            if '{' in response_clean and '}' in response_clean:
                start = response_clean.find('{')
                end = response_clean.rfind('}') + 1
                json_str = response_clean[start:end]
                
                # Try to parse
                parsed = json.loads(json_str)
                
                # Validate required fields
                if not isinstance(parsed.get('issues'), list):
                    self.logger.warning("Invalid JSON structure: 'issues' is not a list")
                    parsed['issues'] = []
                
                if 'summary' not in parsed:
                    parsed['summary'] = "No summary provided"
                
                # Set has_failures based on issues count
                if 'has_failures' not in parsed:
                    parsed['has_failures'] = len(parsed.get('issues', [])) > 0
                
                self.logger.info(f"Successfully parsed failure analysis with {len(parsed.get('issues', []))} issues")
                return parsed
            
            # Fallback: extract issues from text
            self.logger.warning("No JSON structure found in response, creating fallback analysis")
            return {
                "has_failures": True,
                "issues": [{
                    "file": "unknown.py",
                    "location": "unknown",
                    "problem": str(response_clean)[:200],
                    "root_cause": "Could not parse AI response",
                    "severity": "high"
                }],
                "fix_priority": ["unknown.py"],
                "summary": f"Failed to parse AI response. Raw response: {str(response_clean)[:500]}"
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {str(e)}")
            self.logger.error(f"Attempted to parse: {response[:200]}...")
            return {
                "has_failures": True,
                "issues": [{
                    "file": "unknown.py",
                    "location": "JSON parsing",
                    "problem": f"Failed to parse AI response as JSON: {str(e)}",
                    "root_cause": "AI returned invalid JSON or markdown-wrapped response",
                    "severity": "critical"
                }],
                "fix_priority": ["unknown.py"],
                "summary": f"JSON parsing failed: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Unexpected error parsing failure analysis: {str(e)}")
            return {
                "has_failures": True,
                "issues": [{
                    "file": "unknown.py",
                    "location": "parsing",
                    "problem": f"Unexpected error: {str(e)}",
                    "root_cause": "System error during parsing",
                    "severity": "critical"
                }],
                "fix_priority": ["unknown.py"],
                "summary": f"System error: {str(e)}"
            }
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract Python code from MCP response"""
        # Remove markdown code blocks if present
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        return response.strip()
    
    def _retry_with_timeout(self, func, *args, **kwargs):
        """
        Retry a function call with exponential backoff for timeout errors
        
        Args:
            func: Function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result from successful function call
            
        Raises:
            Exception: If all retries fail
        """
        import time
        from requests.exceptions import Timeout, ReadTimeout
        
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except (Timeout, ReadTimeout) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    self.logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All {self.max_retries} attempts failed due to timeout")
            except Exception as e:
                # For non-timeout errors, don't retry
                self.logger.error(f"Non-timeout error occurred: {str(e)}")
                raise
        
        # If we get here, all retries failed
        raise last_exception
