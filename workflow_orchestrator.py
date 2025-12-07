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
        Run complete workflow with feedback loop until tests pass
        
        Args:
            requirements: Natural language requirements
            
        Returns:
            Dictionary containing final results
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting Complete Workflow with Feedback Loop")
        self.logger.info("=" * 60)
        
        # Step 1: Architect
        self.logger.info("\n[Step 1] Architect: Analyzing requirements...")
        self._wait_for_rate_limit()
        analysis = self.architect.analyze_requirements(requirements)
        
        self._wait_for_rate_limit()
        file_structure = self.architect.design_file_structure(analysis)
        
        self._wait_for_rate_limit()
        architectural_plan = self.architect.create_architectural_plan(analysis, file_structure)
        
        # Initialize feedback loop
        iteration = 0
        all_iterations = []
        
        while iteration < self.max_iterations:
            iteration += 1
            self.logger.info(f"\n{'=' * 60}")
            self.logger.info(f"Iteration {iteration}/{self.max_iterations}")
            self.logger.info(f"{'=' * 60}")
            
            iteration_result = {
                "iteration": iteration,
                "status": "in_progress"
            }
            
            try:
                # Step 2: Coder (generate or regenerate)
                if iteration == 1:
                    self.logger.info("\n[Step 2] Coder: Generating initial code...")
                    self.coder.receive_architecture(architectural_plan)
                    self._wait_for_rate_limit()
                    code = self.coder.generate_code()
                else:
                    self.logger.info(f"\n[Step 2] Coder: Regenerating code (iteration {iteration})...")
                    self._wait_for_rate_limit()
                    code = self.coder.regenerate_code(regeneration_instructions)
                
                # Save code files (side effect: saves to LocalServer)
                saved_files = self.coder.save_code_to_files()
                code_package = self.coder.get_code_package()
                iteration_result["code_generated"] = True
                iteration_result["files"] = list(code.keys())
                iteration_result["saved_file_paths"] = saved_files
                
                # Step 3: Tester
                self.logger.info("\n[Step 3] Tester: Testing code...")
                self.tester.receive_code(code_package)
                # Generate test cases (side effect: saves test file to LocalServer)
                self._wait_for_rate_limit()
                test_code = self.tester.generate_test_cases()
                iteration_result["test_file_generated"] = True
                iteration_result["test_file_path"] = self.tester.test_file_path
                
                # Run tests
                test_results = self.tester.local_server.run_tests(
                    test_file="test_main.py",
                    timeout=300
                )
                self.tester.test_results = test_results
                
                test_passed = test_results.get("passed", False)
                iteration_result["tests_passed"] = test_passed
                iteration_result["test_results"] = test_results
                
                if test_passed:
                    self.logger.info("\n✅ All tests passed! Workflow complete.")
                    iteration_result["status"] = "success"
                    all_iterations.append(iteration_result)
                    break
                
                # Step 4: Debugger (analyze and provide feedback)
                self.logger.info("\n[Step 4] Debugger: Analyzing failures and generating feedback...")
                test_package = self.tester.get_code_and_test_results()
                self.debugger.receive_code_and_results(test_package)
                
                # Generate regeneration instructions
                self._wait_for_rate_limit()
                regeneration_instructions = self.debugger.pass_to_coder_for_regeneration()
                iteration_result["regeneration_instructions"] = regeneration_instructions
                iteration_result["status"] = "needs_regeneration"
                
                if not regeneration_instructions.get("needs_regeneration", False):
                    self.logger.warning("Debugger says no regeneration needed, but tests failed")
                    break
                
                # Cleanup workspace for next iteration
                self.tester.local_server.cleanup_workspace()
                self.logger.info(f"\nIteration {iteration} complete. Tests failed. Preparing for next iteration...")
                
            except Exception as e:
                self.logger.error(f"Error in iteration {iteration}: {str(e)}")
                iteration_result["status"] = "error"
                iteration_result["error"] = str(e)
                break
            
            all_iterations.append(iteration_result)
        
        # Final results
        final_status = "success" if all_iterations and all_iterations[-1].get("tests_passed") else "failed"
        
        result = {
            "final_status": final_status,
            "total_iterations": len(all_iterations),
            "iterations": all_iterations,
            "architectural_plan": architectural_plan,
            "final_code_package": code_package if 'code_package' in locals() else None
        }
        
        self.logger.info(f"\n{'=' * 60}")
        self.logger.info(f"Workflow Complete: {final_status.upper()}")
        self.logger.info(f"Total Iterations: {len(all_iterations)}")
        self.logger.info(f"{'=' * 60}")
        
        return result
