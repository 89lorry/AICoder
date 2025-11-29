"""
Agent C: Tester/QA
Writes pytest cases and executes them
"""

import logging
import os
import subprocess
import json
from typing import Dict, Any, List, Optional
from config.settings import Settings
from utils.file_manager import FileManager
from utils.memory_manager import MemoryManager
from utils.langchain_wrapper import LangChainWrapper


class AgentTester:
    """Agent responsible for writing and executing test cases"""
    
    def __init__(self, mcp_client, api_usage_tracker=None, workspace_dir=None, enable_memory=True):
        """
        Initialize the Tester agent
        
        Args:
            mcp_client: MCP client instance for AI interactions
            api_usage_tracker: Optional API usage tracker instance
            workspace_dir: Directory where test files will be created
            enable_memory: Whether to enable LangChain memory
        """
        self.mcp_client = mcp_client
        self.api_usage_tracker = api_usage_tracker
        self.file_manager = FileManager()
        self.logger = logging.getLogger(__name__)
        self.workspace_dir = workspace_dir or Settings.WORKSPACE_DIR
        
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
        Receive code package from Agent B
        
        Args:
            code_package: Dictionary containing generated code and metadata
        """
        self.code_package = code_package
        self.logger.info(f"Received code package with {len(code_package.get('code', {}))} files")
    
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

Generate a complete test file named test_main.py that can be executed with pytest.
Include all necessary imports and setup.

Generate ONLY the Python test code, no markdown formatting, no explanations, just the test code itself.
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
            
            # Extract test code from response
            test_code = self._extract_code_from_response(response)
            
            # Save test file
            self.test_file_path = os.path.join(self.workspace_dir, "test_main.py")
            self.file_manager.write_file(self.test_file_path, test_code)
            
            self.logger.info(f"Test cases generated and saved to {self.test_file_path}")
            self.test_cases.append(test_code)
            
            return test_code
            
        except Exception as e:
            self.logger.error(f"Error generating test cases: {str(e)}")
            raise
    
    def execute_tests(self) -> Dict[str, Any]:
        """
        Execute generated test cases using pytest
        
        Returns:
            Dictionary containing test execution results
        """
        if not self.test_file_path or not os.path.exists(self.test_file_path):
            raise ValueError("No test file found. Call generate_test_cases() first.")
        
        self.logger.info("Executing pytest tests...")
        
        try:
            # Change to workspace directory for execution
            original_cwd = os.getcwd()
            os.chdir(self.workspace_dir)
            
            # Run pytest with JSON output
            result = subprocess.run(
                ["pytest", "test_main.py", "-v", "--tb=short", "--json-report", "--json-report-file=pytest_report.json"],
                capture_output=True,
                text=True,
                timeout=Settings.TIMEOUT_SECONDS
            )
            
            # Restore original directory
            os.chdir(original_cwd)
            
            # Parse test results
            test_output = result.stdout + result.stderr
            exit_code = result.returncode
            
            # Try to load JSON report if available
            json_report_path = os.path.join(self.workspace_dir, "pytest_report.json")
            json_report = None
            if os.path.exists(json_report_path):
                try:
                    with open(json_report_path, 'r') as f:
                        json_report = json.load(f)
                except Exception as e:
                    self.logger.warning(f"Could not load JSON report: {str(e)}")
            
            # Build results dictionary
            test_results = {
                "exit_code": exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output": test_output,
                "passed": exit_code == 0,
                "json_report": json_report,
                "test_file": self.test_file_path
            }
            
            self.test_results = test_results
            
            if exit_code == 0:
                self.logger.info("All tests passed!")
            else:
                self.logger.warning(f"Tests failed with exit code {exit_code}")
            
            return test_results
            
        except subprocess.TimeoutExpired:
            self.logger.error("Test execution timed out")
            return {
                "exit_code": -1,
                "error": "Test execution timed out",
                "passed": False
            }
        except Exception as e:
            self.logger.error(f"Error executing tests: {str(e)}")
            return {
                "exit_code": -1,
                "error": str(e),
                "passed": False
            }
    
    def analyze_test_results(self) -> Dict[str, Any]:
        """
        Analyze test execution results
        
        Returns:
            Dictionary containing analysis of test results
        """
        if not self.test_results:
            raise ValueError("No test results available. Call execute_tests() first.")
        
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
            raise ValueError("No test results available. Run execute_tests() first.")
        
        return {
            "code_package": self.code_package,
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
            raise ValueError("No test results available. Run execute_tests() first.")
        
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
