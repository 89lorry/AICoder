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


class AgentDebugger:
    """Agent responsible for debugging and fixing code issues"""
    
    def __init__(self, mcp_client, api_usage_tracker=None, workspace_dir=None, enable_memory=True, local_server=None):
        """
        Initialize the Debugger agent
        
        Args:
            mcp_client: MCP client instance for AI interactions
            api_usage_tracker: Optional API usage tracker instance
            workspace_dir: Directory where code files are located
            enable_memory: Whether to enable LangChain memory
            local_server: Optional LocalServer instance for file operations and test execution. If None, creates one.
        """
        self.mcp_client = mcp_client
        self.api_usage_tracker = api_usage_tracker
        self.logger = logging.getLogger(__name__)
        self.workspace_dir = workspace_dir or Settings.WORKSPACE_DIR
        
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
        self.max_fix_iterations = 3
        self.current_iteration = 0
    
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
    
    def analyze_failures(self) -> Dict[str, Any]:
        """
        Analyze test failures and identify issues
        
        Returns:
            Dictionary containing failure analysis
        """
        if not self.test_analysis:
            raise ValueError("No test analysis available. Call receive_code_and_results() first.")
        
        if self.test_analysis.get("overall_status") == "passed":
            self.logger.info("No failures to analyze - all tests passed")
            return {
                "has_failures": False,
                "issues": [],
                "recommendation": "No debugging needed"
            }
        
        self.logger.info("Analyzing test failures...")
        
        failures = self.test_analysis.get("failures", [])
        code = self.code_package.get("code", {})
        
        prompt = f"""Analyze the following test failures and identify the root causes:

Test Failures:
{self._format_failures(failures)}

Original Code:
{self._format_code(code)}

Test Output:
{self.test_results.get('output', '')[:2000] if self.test_results else 'N/A'}

Provide a JSON analysis with:
1. "issues": List of identified issues, each with:
   - "file": Which file has the issue
   - "location": Where in the file (function/class name)
   - "problem": Description of the problem
   - "root_cause": Why this is happening
   - "severity": "critical", "high", "medium", or "low"
2. "fix_priority": Order in which to fix issues
3. "summary": Overall summary of issues

Be specific and actionable in your analysis.
"""
        
        try:
            # Prepare context for LangChain
            context = {
                "failures": failures,
                "code": code,
                "test_output": self.test_results.get('output', '')[:2000] if self.test_results else 'N/A',
                "iteration": self.current_iteration
            }
            
            # Use LangChain wrapper if available
            if self.langchain_wrapper:
                response = self.langchain_wrapper.invoke(prompt, context=context)
                # Track API usage
                if self.api_usage_tracker:
                    token_usage = self.langchain_wrapper.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("debugger", token_usage)
            else:
                # Fallback to direct MCP client
                if not hasattr(self.mcp_client, 'session') or self.mcp_client.session is None:
                    self.mcp_client.connect()
                response = self.mcp_client.send_request(prompt)
                # Track API usage
                if self.api_usage_tracker:
                    token_usage = self.mcp_client.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("debugger", token_usage)
            
            # Parse analysis
            failure_analysis = self._parse_failure_analysis(response)
            self.debug_log.append({
                "action": "analyze_failures",
                "analysis": failure_analysis
            })
            
            self.logger.info(f"Identified {len(failure_analysis.get('issues', []))} issues")
            return failure_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing failures: {str(e)}")
            raise
    
    def debug_code(self, failure_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Debug and fix code issues
        
        Args:
            failure_analysis: Optional failure analysis from analyze_failures()
            
        Returns:
            Dictionary mapping filenames to fixed code
        """
        if not failure_analysis:
            failure_analysis = self.analyze_failures()
        
        if not failure_analysis.get("has_failures", True):
            self.logger.info("No issues to fix")
            self.fixed_code = self.code_package.get("code", {}).copy()
            return self.fixed_code
        
        self.current_iteration += 1
        if self.current_iteration > self.max_fix_iterations:
            self.logger.warning(f"Maximum fix iterations ({self.max_fix_iterations}) reached")
            self.fixed_code = self.code_package.get("code", {}).copy()
            return self.fixed_code
        
        self.logger.info(f"Debugging and fixing code (iteration {self.current_iteration})...")
        
        issues = failure_analysis.get("issues", [])
        code = self.code_package.get("code", {})
        
        # Group issues by file
        issues_by_file = {}
        for issue in issues:
            file = issue.get("file", "unknown.py")
            if file not in issues_by_file:
                issues_by_file[file] = []
            issues_by_file[file].append(issue)
        
        # Fix each file that has issues
        fixed_code = code.copy()
        
        for filename, file_issues in issues_by_file.items():
            if filename not in fixed_code:
                self.logger.warning(f"File {filename} mentioned in issues but not in code package")
                continue
            
            self.logger.info(f"Fixing issues in {filename}...")
            
            prompt = f"""Fix the following issues in the Python file {filename}:

Current Code:
{fixed_code[filename]}

Issues to Fix:
{self._format_issues(file_issues)}

Requirements:
1. Fix all identified issues
2. Maintain the original code structure and logic intent
3. Ensure the code follows Python best practices
4. Add proper error handling if missing
5. Ensure all tests should pass after fixes
6. Do not break any existing functionality that works

Generate ONLY the complete fixed Python code for {filename}, no markdown formatting, no explanations, just the fixed code itself.
"""
            
            try:
                # Prepare context for LangChain
                context = {
                    "filename": filename,
                    "current_code": fixed_code[filename],
                    "issues": file_issues,
                    "iteration": self.current_iteration,
                    "previous_fixes": [log for log in self.debug_log if log.get("action") == "fix_code"]
                }
                
                # Use LangChain wrapper if available
                if self.langchain_wrapper:
                    response = self.langchain_wrapper.invoke(prompt, context=context)
                    # Track API usage
                    if self.api_usage_tracker:
                        token_usage = self.langchain_wrapper.get_token_usage()
                        if token_usage:
                            self.api_usage_tracker.track_usage("debugger", token_usage)
                else:
                    # Fallback to direct MCP client
                    response = self.mcp_client.send_request(prompt)
                    # Track API usage
                    if self.api_usage_tracker:
                        token_usage = self.mcp_client.get_token_usage()
                        if token_usage:
                            self.api_usage_tracker.track_usage("debugger", token_usage)
                
                # Extract fixed code
                fixed_file_code = self._extract_code_from_response(response)
                fixed_code[filename] = fixed_file_code
                
                self.debug_log.append({
                    "action": "fix_code",
                    "file": filename,
                    "iteration": self.current_iteration
                })
                
                self.logger.info(f"Fixed code for {filename}")
                
            except Exception as e:
                self.logger.error(f"Error fixing {filename}: {str(e)}")
                # Keep original code if fix fails
        
        self.fixed_code = fixed_code
        
        # Save all fixed code as a code package (include test file if available)
        if fixed_code:
            # Include test file from code package if it exists
            files_to_save = fixed_code.copy()
            code_package_data = self.code_package.get("code", {})
            if "test_main.py" in code_package_data:
                files_to_save["test_main.py"] = code_package_data["test_main.py"]
            
            code_package = {
                "project_name": "debug_project",
                "files": files_to_save,
                "entry_point": "main.py"
            }
            
            # Receive and save fixed code package
            self.local_server.receive_code_package(code_package)
            project_path = self.local_server.save_code_to_directory(code_package)
            self.logger.info(f"Saved fixed code package to {project_path}")
        
        return fixed_code
    
    def verify_fixes(self) -> Dict[str, Any]:
        """
        Verify that fixes resolve the issues by re-running tests via LocalServer
        
        Returns:
            Dictionary containing verification results
        """
        if not self.fixed_code:
            raise ValueError("No fixed code available. Call debug_code() first.")
        
        self.logger.info("Verifying fixes by re-running tests via LocalServer...")
        
        if not self.local_server.current_project_path:
            raise ValueError("No fixed code package saved. Call debug_code() first.")
        
        # Re-run tests using LocalServer
        try:
            # Determine test file name
            test_file = "test_main.py"
            if self.test_results:
                # Extract just the filename from the full path
                test_file_path = self.test_results.get("test_file", "")
                if test_file_path:
                    test_file = os.path.basename(test_file_path)
            
            # Use LocalServer to run tests
            test_results = self.local_server.run_tests(
                test_file=test_file,
                timeout=Settings.TIMEOUT_SECONDS
            )
            
            verification = {
                "exit_code": test_results.get("exit_code", -1),
                "passed": test_results.get("passed", False),
                "stdout": test_results.get("stdout", ""),
                "stderr": test_results.get("stderr", ""),
                "output": test_results.get("output", ""),
                "iteration": self.current_iteration
            }
            
            if verification["passed"]:
                self.logger.info("All tests passed after fixes!")
            else:
                self.logger.warning("Some tests still failing after fixes")
            
            self.debug_log.append({
                "action": "verify_fixes",
                "result": verification
            })
            
            return verification
            
        except Exception as e:
            self.logger.error(f"Error verifying fixes: {str(e)}")
            return {
                "passed": False,
                "error": str(e),
                "iteration": self.current_iteration
            }
    
    def debug_and_verify(self) -> Dict[str, Any]:
        """
        Complete debug cycle: analyze, fix, and verify
        
        Returns:
            Dictionary containing final results
        """
        all_results = []
        
        for iteration in range(self.max_fix_iterations):
            self.current_iteration = iteration + 1
            self.logger.info(f"Debug iteration {self.current_iteration}/{self.max_fix_iterations}")
            
            # Analyze failures
            failure_analysis = self.analyze_failures()
            
            if not failure_analysis.get("has_failures", True):
                self.logger.info("No failures found - debugging complete")
                break
            
            # Fix code
            self.debug_code(failure_analysis)
            
            # Verify fixes
            verification = self.verify_fixes()
            all_results.append({
                "iteration": self.current_iteration,
                "failure_analysis": failure_analysis,
                "verification": verification
            })
            
            if verification.get("passed"):
                self.logger.info(f"All tests passed after iteration {self.current_iteration}")
                break
        
        return {
            "iterations": all_results,
            "final_status": "passed" if all_results and all_results[-1]["verification"].get("passed") else "failed",
            "total_iterations": len(all_results)
        }
    
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
    
    def generate_regeneration_instructions(self) -> Dict[str, Any]:
        """
        Generate instructions for Agent B to regenerate code based on test failures
        
        Returns:
            Dictionary containing regeneration instructions and feedback
        """
        if not self.test_analysis or self.test_analysis.get("overall_status") == "passed":
            return {
                "needs_regeneration": False,
                "message": "No regeneration needed - all tests passed"
            }
        
        failure_analysis = self.analyze_failures()
        
        prompt = f"""Based on the test failures, provide clear instructions for regenerating the code:

Test Failures:
{self._format_failures(self.test_analysis.get('failures', []))}

Failure Analysis:
{failure_analysis}

Current Code Issues:
{self._format_issues(failure_analysis.get('issues', []))}

Provide JSON with:
1. "regeneration_instructions": Clear instructions for what needs to be fixed
2. "key_changes": List of specific changes needed
3. "priority_fixes": Most critical issues to address first
4. "architectural_notes": Any architectural changes needed
"""
        
        try:
            context = {
                "test_analysis": self.test_analysis,
                "failure_analysis": failure_analysis,
                "code_package": self.code_package
            }
            
            if self.langchain_wrapper:
                response = self.langchain_wrapper.invoke(prompt, context=context)
                if self.api_usage_tracker:
                    token_usage = self.langchain_wrapper.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("debugger", token_usage)
            else:
                if not hasattr(self.mcp_client, 'session') or self.mcp_client.session is None:
                    self.mcp_client.connect()
                response = self.mcp_client.send_request(prompt)
                if self.api_usage_tracker:
                    token_usage = self.mcp_client.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("debugger", token_usage)
            
            # Parse response
            instructions = self._parse_regeneration_instructions(response)
            instructions["needs_regeneration"] = True
            instructions["original_architectural_plan"] = self.code_package.get("architectural_plan")
            
            self.logger.info("Generated regeneration instructions for Agent B")
            return instructions
            
        except Exception as e:
            self.logger.error(f"Error generating regeneration instructions: {str(e)}")
            return {
                "needs_regeneration": True,
                "regeneration_instructions": f"Fix test failures: {str(e)}",
                "key_changes": [],
                "original_architectural_plan": self.code_package.get("architectural_plan")
            }
    
    def pass_to_coder_for_regeneration(self) -> Dict[str, Any]:
        """
        Pass regeneration instructions back to Agent B (Coder)
        
        Returns:
            Dictionary containing instructions for code regeneration
        """
        if not self.test_analysis:
            raise ValueError("No test analysis available. Call receive_code_and_results() first.")
        
        if self.test_analysis.get("overall_status") == "passed":
            self.logger.info("All tests passed - no regeneration needed")
            return {"needs_regeneration": False}
        
        self.logger.info("Passing regeneration instructions to Coder agent")
        return self.generate_regeneration_instructions()
    
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
        """Parse failure analysis from MCP response"""
        import json
        try:
            if isinstance(response, dict):
                return response
            
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                return json.loads(json_str)
            
            # Fallback: extract issues from text
            return {
                "has_failures": True,
                "issues": [{
                    "file": "unknown.py",
                    "location": "unknown",
                    "problem": str(response)[:200],
                    "root_cause": "Unknown",
                    "severity": "medium"
                }],
                "summary": str(response)[:500]
            }
        except json.JSONDecodeError:
            self.logger.warning("Could not parse failure analysis JSON, using fallback")
            return {
                "has_failures": True,
                "issues": [],
                "summary": str(response)[:500]
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
