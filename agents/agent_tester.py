"""
Agent C: Tester/QA
Writes pytest cases and executes them
"""

import logging
import os
import json
from typing import Dict, Any, List, Optional
from config.settings import Settings
from utils.file_manager import FileManager
from utils.memory_manager import MemoryManager
from utils.langchain_wrapper import LangChainWrapper
from utils.conversation_logger import ConversationLogger
from datetime import datetime


class AgentTester:
    """Agent responsible for writing and executing test cases"""
    
    def __init__(self, mcp_client, api_usage_tracker=None, workspace_dir=None, enable_memory=True, local_server=None, session_id=None):
        """
        Initialize the Tester agent
        
        Args:
            mcp_client: MCP client instance for AI interactions
            api_usage_tracker: Optional API usage tracker instance
            workspace_dir: Directory where test files will be created
            enable_memory: Whether to enable LangChain memory
            local_server: Optional LocalServer instance for test execution. If None, creates one.
            session_id: Optional session ID for conversation logging
        """
        self.mcp_client = mcp_client
        self.api_usage_tracker = api_usage_tracker
        self.file_manager = FileManager()
        self.logger = logging.getLogger(__name__)
        self.workspace_dir = workspace_dir or Settings.WORKSPACE_DIR
        
        # Initialize conversation logger
        self.conversation_logger = ConversationLogger(
            agent_name="tester",
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
            self.memory_manager = MemoryManager("tester", memory_type="buffer_window")
            self.langchain_wrapper = LangChainWrapper(
                mcp_client=mcp_client,
                memory_manager=self.memory_manager,
                llm_provider="openai"
            )
            # Add system message to memory
            self.memory_manager.add_system_message(
                "You are an expert QA engineer and test automation specialist. You write "
                "comprehensive pytest test cases that cover all functionality, edge cases, "
                "and error scenarios. Your tests are well-structured and follow best practices."
            )
            self.logger.info("Initialized LangChain memory for Tester agent")
        
        # Internal state
        self.code_package = None
        self.test_cases = []
        self.test_results = {}
        self.test_file_path = None
    
    def receive_code(self, code_package: Dict[str, Any]) -> None:
        """
        Receive code package from Agent B and save code files to LocalServer
        
        Args:
            code_package: Dictionary containing generated code and metadata
        """
        self.code_package = code_package
        self.logger.info(f"Received code package with {len(code_package.get('code', {}))} files")
        
        # Save code files to LocalServer so they're available for testing
        code_files = code_package.get("code", {})
        if code_files:
            # Build code package for LocalServer
            server_package = {
                "project_name": "test_project",
                "files": code_files,
                "entry_point": "main.py"
            }
            
            # Receive and save code package
            self.local_server.receive_code_package(server_package)
            self.local_server.save_code_to_directory(server_package)
            self.logger.debug(f"Saved {len(code_files)} code files to LocalServer")
    
    def generate_test_cases(self) -> str:
        """
        Generate pytest test cases for the code
        
        Returns:
            Generated test file content as string
        """
        if not self.code_package:
            raise ValueError("No code package available. Call receive_code() first.")
        
        self.logger.info("Generating pytest test cases...")
        
        # Prepare context for test generation
        code_files = self.code_package.get("code", {})
        
        prompt = f"""Generate comprehensive pytest test cases for the following Python code files:

Code Files:
{self._format_code_for_testing(code_files)}

Architectural Plan:
{self._format_architectural_plan()}

Requirements:
1. Create comprehensive test cases using pytest
2. Test all functions, classes, and main logic
3. Include edge cases and error handling tests
4. Use fixtures where appropriate
5. Follow pytest best practices
6. Include docstrings explaining what each test does
7. Make tests readable and maintainable
8. Import functions/classes directly - DO NOT test main() or if __name__ blocks

CRITICAL TESTING RULES:
9. **DO NOT** test methods with infinite loops (while True, .run(), .main_loop(), .start())
10. **DO NOT** test interactive CLI methods that block for input
11. For UI classes: Test individual methods, NOT the main loop
12. Add @pytest.mark.timeout(5) to tests using mocked input/print
13. Tests must complete within 5 seconds

DATA & FILE I/O RULES:
14. Understand library behavior (CSV missing values = None, not error)
15. CSV errors need EXTRA fields, not missing fields
16. Use tmp_path fixture for file tests
17. Create actual files for I/O tests
18. Check for None explicitly: `assert value is None`
19. Use pytest.approx() for floating-point comparisons

ASSERTION RULES:
20. Manually TRACE through logic - don't guess expected counts
21. Count INDIVIDUAL violations, not records with violations
22. Empty string "" and None are NOT equal
23. Empty string "" CAN be a duplicate of another ""
24. None CAN be a duplicate of another None
25. Understand range boundaries: `< 30` excludes 30, `<= 30` includes 30
26. Use specific assertions: `assert len(data) == 3`, not just `assert data`

Generate a complete test file named test_main.py that can be executed with pytest.
Include all necessary imports and setup.

CRITICAL: Your response must contain ONLY raw Python test code.
DO NOT wrap the code in markdown code blocks (```python or ```).
DO NOT include any explanations, comments outside the code, or formatting.
Start your response directly with the first line of Python code (imports).
"""
        
        try:
            # Prepare context for LangChain
            context = {
                "code_files": code_files,
                "architectural_plan": self.code_package.get("architectural_plan", {})
            }
            
            # Use LangChain wrapper if available
            if self.langchain_wrapper:
                response = self.langchain_wrapper.invoke(prompt, context=context)
                # Track API usage
                if self.api_usage_tracker:
                    token_usage = self.langchain_wrapper.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("tester", token_usage)
            else:
                # Fallback to direct MCP client
                if not hasattr(self.mcp_client, 'session') or self.mcp_client.session is None:
                    self.mcp_client.connect()
                response = self.mcp_client.send_request(prompt)
                # Track API usage
                if self.api_usage_tracker:
                    token_usage = self.mcp_client.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("tester", token_usage)
                
                # Extract text and log conversation
                response_text = self.mcp_client.extract_text_from_response(response)
                self.conversation_logger.log_interaction(
                    prompt=prompt,
                    response=response_text,
                    metadata=self.mcp_client.get_token_usage()
                )
            
            # Extract test code from response
            test_code = self._extract_code_from_response(response)
            
            # Validate test code for problematic patterns
            validation_warnings = self._validate_test_code(test_code)
            if validation_warnings:
                self.logger.warning("Test code validation detected problematic patterns:")
                for warning in validation_warnings:
                    self.logger.warning(f"  - {warning}")
                
                # Filter out problematic tests automatically
                self.logger.info("Removing problematic tests from test suite...")
                original_lines = len(test_code.split('\n'))
                test_code = self._remove_problematic_tests(test_code, validation_warnings)
                filtered_lines = len(test_code.split('\n'))
                self.logger.info(f"Filtered test code: {original_lines} → {filtered_lines} lines ({original_lines - filtered_lines} lines removed)")
            
            # Add test file to existing code package and save
            if not self.local_server.current_project_path:
                raise ValueError("No code package saved. Call receive_code() first.")
            
            # Add test file to the code package
            code_files = self.code_package.get("code", {}).copy()
            code_files["test_main.py"] = test_code
            
            # Update and save code package with test file
            server_package = {
                "project_name": "test_project",
                "files": code_files,
                "entry_point": "main.py"
            }
            
            self.local_server.save_code_to_directory(server_package)
            self.test_file_path = os.path.join(self.local_server.current_project_path, "test_main.py")
            
            self.logger.info(f"Test cases generated and saved to {self.test_file_path}")
            self.test_cases.append(test_code)
            
            return test_code
            
        except Exception as e:
            self.logger.error(f"Error generating test cases: {str(e)}")
            raise
    
    def analyze_test_results(self) -> Dict[str, Any]:
        """
        Analyze test execution results
        
        Returns:
            Dictionary containing analysis of test results
        """
        if not self.test_results:
            raise ValueError("No test results available. Call local_server.run_tests() first.")
        
        self.logger.info("Analyzing test results...")
        
        analysis = {
            "overall_status": "passed" if self.test_results.get("passed") else "failed",
            "exit_code": self.test_results.get("exit_code", -1),
            "has_failures": not self.test_results.get("passed", False),
            "test_output": self.test_results.get("output", ""),
        }
        
        # Extract failure information if any
        if not self.test_results.get("passed"):
            output = self.test_results.get("output", "")
            analysis["failures"] = self._extract_failures(output)
            analysis["failure_count"] = len(analysis.get("failures", []))
        else:
            analysis["failures"] = []
            analysis["failure_count"] = 0
        
        # Extract summary statistics
        json_report = self.test_results.get("json_report")
        if json_report:
            summary = json_report.get("summary", {})
            analysis["total_tests"] = summary.get("total", 0)
            analysis["passed_tests"] = summary.get("passed", 0)
            analysis["failed_tests"] = summary.get("failed", 0)
            analysis["error_tests"] = summary.get("error", 0)
        
        self.logger.info(f"Analysis complete. Status: {analysis['overall_status']}")
        return analysis
    
    def get_code_and_test_results(self) -> Dict[str, Any]:
        """
        Get complete package with code and test results for debugger
        
        Returns:
            Dictionary containing code package and test results
        """
        if not self.code_package:
            raise ValueError("No code package available")
        if not self.test_results:
            raise ValueError("No test results available. Run local_server.run_tests() first.")
        
        # Include test file content in code package so debugger has it after cleanup
        code_package_with_tests = self.code_package.copy()
        if self.test_file_path and os.path.exists(self.test_file_path):
            with open(self.test_file_path, 'r', encoding='utf-8') as f:
                test_content = f.read()
            # Add test file to code package
            if "code" not in code_package_with_tests:
                code_package_with_tests["code"] = {}
            code_package_with_tests["code"]["test_main.py"] = test_content
        
        return {
            "code_package": code_package_with_tests,
            "test_results": self.test_results,
            "test_analysis": self.analyze_test_results() if self.test_results else None,
            "test_file": self.test_file_path
        }
    
    def pass_to_debugger(self) -> Dict[str, Any]:
        """
        Pass code and test results to Agent D (Debugger)
        
        Returns:
            Dictionary containing code package and test results
        """
        if not self.test_results:
            raise ValueError("No test results available. Run local_server.run_tests() first.")
        
        self.logger.info("Passing code and test results to Debugger agent")
        return self.get_code_and_test_results()
    
    def _format_code_for_testing(self, code_files: Dict[str, str]) -> str:
        """Format code files for test generation prompt"""
        formatted = []
        for filename, code in code_files.items():
            formatted.append(f"\n=== {filename} ===\n{code}\n")
        return "\n".join(formatted)
    
    def _format_architectural_plan(self) -> str:
        """Format architectural plan for test generation"""
        if not self.code_package:
            return "No architectural plan available"
        
        plan = self.code_package.get("architectural_plan", {})
        if not plan:
            return "No architectural plan available"
        
        parts = []
        analysis = plan.get("analysis", {})
        if analysis:
            parts.append(f"Components: {analysis.get('components', [])}")
            parts.append(f"Summary: {analysis.get('summary', 'N/A')}")
        
        return "\n".join(parts) if parts else "No architectural plan details"
    
    def _extract_code_from_response(self, response: Any) -> str:
        """Extract Python code from MCP response, removing markdown if present"""
        # First, extract text from response if it's a dictionary
        if isinstance(response, dict):
            response_text = self.mcp_client.extract_text_from_response(response)
        else:
            response_text = str(response)
        
        # More aggressive markdown removal - line by line processing
        lines = response_text.split('\n')
        code_lines = []
        in_code_block = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Detect markdown code block start/end
            if stripped.startswith('```python') or stripped.startswith('```'):
                in_code_block = not in_code_block
                continue
            
            # Skip lines that are clearly not code
            if not in_code_block and (stripped.startswith('#') and i == 0):
                continue
                
            # Collect code lines
            if in_code_block or stripped:
                code_lines.append(line)
        
        result = '\n'.join(code_lines).strip()
        
        # If still empty or looks like it failed, try original simple method
        if not result or len(result) < 10:
            # Fallback: simple extraction
            if "```python" in response_text:
                start = response_text.find("```python") + 9
                end = response_text.find("```", start)
                if end != -1:
                    return response_text[start:end].strip()
            
            if "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                if end != -1:
                    return response_text[start:end].strip()
            
            return response_text.strip()
        
        return result
    
    def _remove_problematic_tests(self, test_code: str, warnings: List[str]) -> str:
        """
        Remove test functions that contain problematic patterns like .run() calls
        
        Args:
            test_code: The generated test code
            warnings: List of validation warnings with line numbers
            
        Returns:
            Filtered test code with problematic tests removed
        """
        lines = test_code.split('\n')
        filtered_lines = []
        current_test_start = None
        current_test_name = ""
        skip_current_test = False
        problematic_line_numbers = set()
        
        # Extract line numbers from warnings that indicate problematic patterns
        import re
        for warning in warnings:
            if any(pattern in warning for pattern in ['.run()', '.main_loop()', '.start()', 'while True']):
                match = re.search(r'Line (\d+):', warning)
                if match:
                    problematic_line_numbers.add(int(match.group(1)))
        
        # Process lines and filter out problematic tests
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Detect start of a test function
            if stripped.startswith('def test_'):
                # Save previous test if it was safe
                if current_test_start is not None and not skip_current_test:
                    # Add the previous test (already in filtered_lines)
                    pass
                
                # Start tracking new test
                current_test_start = i
                current_test_name = stripped.split('(')[0].replace('def ', '')
                skip_current_test = False
                
                # Check if any problematic lines are in this test's range
                # We'll check this as we go through the test body
            
            # Check if current line is problematic
            if i in problematic_line_numbers:
                skip_current_test = True
                self.logger.info(f"  Removing test '{current_test_name}' due to problematic pattern at line {i}")
            
            # Add line to filtered output if not skipping
            if current_test_start is None:
                # Before first test - keep imports, fixtures, etc.
                filtered_lines.append(line)
            elif not skip_current_test:
                # Inside a safe test - keep the line
                filtered_lines.append(line)
            elif stripped.startswith('def test_') or (stripped.startswith('def ') and not stripped.startswith('def test_')):
                # Hit next function while skipping - start fresh
                if not stripped.startswith('def test_'):
                    # Non-test function, keep it
                    filtered_lines.append(line)
                    current_test_start = None
                else:
                    # New test function while skipping previous
                    current_test_start = i
                    current_test_name = stripped.split('(')[0].replace('def ', '')
                    skip_current_test = i in problematic_line_numbers
                    if not skip_current_test:
                        filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def _validate_test_code(self, test_code: str) -> List[str]:
        """
        Validate test code for problematic patterns that may cause hanging
        
        Args:
            test_code: The generated test code to validate
            
        Returns:
            List of warning messages for any issues found
        """
        warnings = []
        lines = test_code.split('\n')
        
        # Patterns that indicate problematic tests
        problematic_patterns = [
            (r'\.run\(\)', "Test calls .run() method which may contain infinite loop"),
            (r'\.main_loop\(\)', "Test calls .main_loop() method which likely blocks forever"),
            (r'\.start\(\)', "Test calls .start() method which may run continuously"),
            (r'\.event_loop\(\)', "Test calls .event_loop() method which may block"),
            (r'while\s+True:', "Test contains 'while True' loop which may hang"),
            (r'while\s+running:', "Test contains 'while running' loop which may hang"),
        ]
        
        # Check for problematic patterns
        for i, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('#'):
                continue
            
            for pattern, message in problematic_patterns:
                import re
                if re.search(pattern, line):
                    warnings.append(f"Line {i}: {message} - '{line.strip()}'")
        
        # Check for UI test methods without timeout decorator
        in_test_function = False
        test_has_timeout = False
        test_name = ""
        test_uses_mock_input = False
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Detect test function start
            if stripped.startswith('def test_'):
                # Check if previous test needed timeout but didn't have it
                if in_test_function and test_uses_mock_input and not test_has_timeout:
                    warnings.append(f"Test '{test_name}' uses mock input but lacks @pytest.mark.timeout decorator")
                
                # Reset for new test
                in_test_function = True
                test_has_timeout = False
                test_uses_mock_input = False
                test_name = stripped.split('(')[0].replace('def ', '')
            
            # Check for timeout decorator
            if '@pytest.mark.timeout' in stripped:
                test_has_timeout = True
            
            # Check for mock input usage
            if 'mock_input' in stripped or 'monkeypatch' in stripped:
                test_uses_mock_input = True
        
        # Check last test
        if in_test_function and test_uses_mock_input and not test_has_timeout:
            warnings.append(f"Test '{test_name}' uses mock input but lacks @pytest.mark.timeout decorator")
        
        return warnings
    
    def _extract_failures(self, test_output: str) -> List[Dict[str, str]]:
        """Extract failure information from pytest output"""
        failures = []
        lines = test_output.split('\n')
        
        current_failure = None
        for i, line in enumerate(lines):
            if "FAILED" in line or "ERROR" in line:
                # New failure detected
                if current_failure:
                    failures.append(current_failure)
                
                # Extract test name
                parts = line.split()
                test_name = parts[0] if parts else "Unknown test"
                
                current_failure = {
                    "test_name": test_name,
                    "status": "FAILED" if "FAILED" in line else "ERROR",
                    "error_message": "",
                    "traceback": []
                }
            elif current_failure:
                # Collect error message and traceback
                if "AssertionError" in line or "Error" in line or "Exception" in line:
                    current_failure["error_message"] = line.strip()
                elif line.strip().startswith("E ") or line.strip().startswith(">"):
                    current_failure["traceback"].append(line.strip())
        
        if current_failure:
            failures.append(current_failure)
        
        return failures
