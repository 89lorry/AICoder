# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

"""
Workflow Orchestrator
Implements the feedback loop: B → C → D → B → C → D ... until tests pass
"""

from typing import Dict, Any, Optional
import logging
import time


class WorkflowOrchestrator:
    """Orchestrates the agent workflow with feedback loop"""
    
    # Gemini API Free Tier Rate Limits
    # 10 requests per minute (RPM) = 6 seconds between requests minimum
    # Conservative delay to avoid 429 errors and accommodate retry logic
    REQUEST_DELAY = 6.0  # 6 seconds between requests (10 RPM limit)
    
    def __init__(self, architect, coder, tester, debugger, max_iterations=5, enable_rate_limiting=True):
        """
        Initialize workflow orchestrator
        
        Args:
            architect: AgentArchitect instance
            coder: AgentCoder instance
            tester: AgentTester instance
            debugger: AgentDebugger instance
            max_iterations: Maximum number of feedback loop iterations
            enable_rate_limiting: Whether to enable rate limiting (default: True)
        """
        self.architect = architect
        self.coder = coder
        self.tester = tester
        self.debugger = debugger
        self.max_iterations = max_iterations
        self.enable_rate_limiting = enable_rate_limiting
        self.logger = logging.getLogger(__name__)
        self.last_request_time = 0
        
        if self.enable_rate_limiting:
            self.logger.info(f"Rate limiting enabled: {self.REQUEST_DELAY}s delay between API calls")
    
    def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits"""
        if not self.enable_rate_limiting:
            return
        
        time_since_last_request = time.time() - self.last_request_time
        if time_since_last_request < self.REQUEST_DELAY:
            wait_time = self.REQUEST_DELAY - time_since_last_request
            self.logger.info(f"Rate limit: waiting {wait_time:.1f}s before next API call...")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def run_complete_workflow(self, requirements: str) -> Dict[str, Any]:
        """
        Run complete workflow: Architect → Coder → Tester → [IF FAIL] Debugger → END
        
        Args:
            requirements: Natural language requirements
            
        Returns:
            Dictionary containing final results
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting Complete Workflow")
        self.logger.info("=" * 60)
        
        result = {
            "final_status": "failed",
            "architectural_plan": None,
            "code_package": None,
            "test_results": None,
            "debugger_fixed": False
        }
        
        try:
            # Step 1: Architect - Create complete architecture (1 API call)
            self.logger.info("\n[Step 1] Architect: Creating complete architecture...")
            self._wait_for_rate_limit()
            architectural_plan = self.architect.create_complete_architecture(requirements)
            result["architectural_plan"] = architectural_plan
            
            # DEBUG: Log what architect returned
            self.logger.info(f"DEBUG: Architect returned plan with keys: {list(architectural_plan.keys())}")
            if 'detailed_plan' in architectural_plan:
                detailed_plan = architectural_plan['detailed_plan']
                self.logger.info(f"DEBUG: detailed_plan has {len(detailed_plan)} keys: {list(detailed_plan.keys())}")
            else:
                self.logger.error("DEBUG: Architect plan MISSING detailed_plan!")
            
            # Step 2: Coder - Generate all code files (1 API call)
            self.logger.info("\n[Step 2] Coder: Generating all code files...")
            self.logger.info(f"DEBUG: Passing plan to coder with keys: {list(architectural_plan.keys())}")
            self.coder.receive_architecture(architectural_plan)
            self._wait_for_rate_limit()
            code = self.coder.generate_code()
            
            # Get code package
            code_package = self.coder.get_code_package()
            result["code_package"] = code_package
            
            # Save code files to LocalServer (coder already has local_server)
            saved_files = {}
            if self.coder.local_server:
                import os
                # Build the code package for LocalServer
                local_code_package = {
                    "project_name": "code_project",
                    "files": code,
                    "entry_point": "main.py"
                }
                # First receive the package, then save it
                self.coder.local_server.receive_code_package(local_code_package)
                project_path = self.coder.local_server.save_code_to_directory(local_code_package)
                
                if project_path:
                    for filename in code.keys():
                        filepath = os.path.join(project_path, filename)
                        saved_files[filename] = filepath
                        self.logger.info(f"Saved {filename} to {filepath}")
                else:
                    self.logger.warning("Failed to save code to directory - project_path is None")
            result["saved_files"] = saved_files
            
            # Step 3: Tester - Generate tests and run them (1 API call)
            self.logger.info("\n[Step 3] Tester: Generating and running tests...")
            self.tester.receive_code(code_package)
            self._wait_for_rate_limit()
            test_code = self.tester.generate_test_cases()
            
            # Run tests
            test_results = self.tester.local_server.run_tests(
                test_file="test_main.py",
                timeout=300
            )
            self.tester.test_results = test_results
            result["test_results"] = test_results
            result["test_file_path"] = self.tester.test_file_path
            
            # Check if tests passed
            test_passed = test_results.get("passed", False)
            
            if test_passed:
                self.logger.info("\n✅ All tests passed! Workflow complete.")
                result["final_status"] = "success"
            else:
                # Step 4: Debugger - Fix code directly with internal retry loop (1 API call per attempt, up to 5 attempts)
                self.logger.info("\n⚠️  Tests failed. Debugger will fix the code with internal retry loop...")
                
                # Pass test results to debugger
                test_package = self.tester.get_code_and_test_results()
                self.debugger.receive_code_and_results(test_package)
                
                # Combined: Analyze + Fix + Update Tests + Retry until pass (with rate limiting)
                self.logger.info("\n[Step 4] Debugger: Starting combined fix with internal retry loop...")
                self._wait_for_rate_limit()
                
                debug_result = self.debugger.analyze_and_fix_combined()
                
                result["debugger_fixed"] = True
                result["debug_result"] = debug_result
                result["fixed_code"] = debug_result.get("fixed_code", {})
                result["debug_attempts"] = len(debug_result.get("attempts", []))
                
                if debug_result.get("success"):
                    self.logger.info(f"\n✅ All tests passed after {result['debug_attempts']} debugger attempt(s)! Workflow complete.")
                    result["final_status"] = "success"
                    result["final_test_results"] = debug_result.get("final_test_results")
                else:
                    self.logger.warning(f"\n⚠️  Tests still failing after {result['debug_attempts']} debugger attempt(s).")
                    result["final_status"] = "failed"
                    result["final_test_results"] = debug_result.get("final_test_results")
            
            # Cleanup
            if hasattr(self.tester, 'local_server'):
                self.tester.local_server.cleanup_workspace()
                
        except Exception as e:
            self.logger.error(f"Error in workflow: {str(e)}")
            result["final_status"] = "error"
            result["error"] = str(e)
            import traceback
            result["traceback"] = traceback.format_exc()
        
        # Final summary
        self.logger.info(f"\n{'=' * 60}")
        self.logger.info(f"Workflow Complete: {result['final_status'].upper()}")
        self.logger.info(f"Debugger Fixed Code: {result.get('debugger_fixed', False)}")
        self.logger.info(f"{'=' * 60}")
        
        return result
