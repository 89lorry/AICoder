"""
Agent B: Coder
Breaks requirements into file structure and generates code
(main.py, utils.py, test_data.py)
"""

import logging
import os
from typing import Dict, Any, Optional
from config.settings import Settings
from utils.memory_manager import MemoryManager
from utils.langchain_wrapper import LangChainWrapper


class AgentCoder:
    """Agent responsible for code generation based on architectural plan"""
    
    def __init__(self, mcp_client, api_usage_tracker=None, workspace_dir=None, enable_memory=True, local_server=None):
        """
        Initialize the Coder agent
        
        Args:
            mcp_client: MCP client instance for AI interactions
            api_usage_tracker: Optional API usage tracker instance
            workspace_dir: Directory where generated code will be saved
            enable_memory: Whether to enable LangChain memory
            local_server: Optional LocalServer instance for file operations. If None, creates one.
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
            self.memory_manager = MemoryManager("coder", memory_type="buffer_window")
            self.langchain_wrapper = LangChainWrapper(
                mcp_client=mcp_client,
                memory_manager=self.memory_manager,
                llm_provider="openai"
            )
            # Add system message to memory
            self.memory_manager.add_system_message(
                "You are an expert software developer. You generate high-quality, "
                "executable Python code based on architectural plans. You follow best "
                "practices, include proper error handling, and write well-documented code."
            )
            self.logger.info("Initialized LangChain memory for Coder agent")
        
        # Internal state
        self.architectural_plan = None
        self.generated_code = {}
    
    def receive_architecture(self, architectural_plan: Dict[str, Any]) -> None:
        """
        Receive architectural plan from Agent A
        
        Args:
            architectural_plan: Architectural plan dictionary from AgentArchitect
        """
        self.architectural_plan = architectural_plan
        self.logger.info("Received architectural plan from Architect agent")
    
    def generate_code(self) -> Dict[str, str]:
        """
        Generate code based on architectural plan
        
        Returns:
            Dictionary mapping filenames to generated code content
        """
        if not self.architectural_plan:
            raise ValueError("No architectural plan available. Call receive_architecture() first.")
        
        self.logger.info("Starting code generation...")
        
        # Ensure workspace directory exists and set up LocalServer project path
        if not self.local_server.current_project_path:
            self.local_server.current_project_path = self.workspace_dir
            self.local_server.current_project = "code_project"
        
        # Generate each file
        file_structure = self.architectural_plan.get("file_structure", {})
        files = file_structure.get("files", {})
        
        # Default files if not specified
        if not files:
            files = {
                "main.py": "Main entry point and application logic",
                "utils.py": "Utility functions and helpers",
                "test_data.py": "Test data and sample inputs"
            }
        
        # Generate code for each file
        for filename, description in files.items():
            if filename.endswith('.py'):
                self.logger.info(f"Generating code for {filename}...")
                code = self._generate_file_code(filename, description)
                self.generated_code[filename] = code
        
        self.logger.info(f"Code generation complete. Generated {len(self.generated_code)} files")
        return self.generated_code
    
    def create_main_file(self) -> str:
        """Generate main.py file"""
        if "main.py" in self.generated_code:
            return self.generated_code["main.py"]
        
        self.logger.info("Generating main.py...")
        code = self._generate_file_code("main.py", "Main entry point and application logic")
        self.generated_code["main.py"] = code
        return code
    
    def create_utils_file(self) -> str:
        """Generate utils.py file"""
        if "utils.py" in self.generated_code:
            return self.generated_code["utils.py"]
        
        self.logger.info("Generating utils.py...")
        code = self._generate_file_code("utils.py", "Utility functions and helpers")
        self.generated_code["utils.py"] = code
        return code
    
    def create_test_data_file(self) -> str:
        """Generate test_data.py file"""
        if "test_data.py" in self.generated_code:
            return self.generated_code["test_data.py"]
        
        self.logger.info("Generating test_data.py...")
        code = self._generate_file_code("test_data.py", "Test data and sample inputs")
        self.generated_code["test_data.py"] = code
        return code
    
    def save_code_to_files(self) -> Dict[str, str]:
        """
        Save generated code to files using LocalServer
        
        Returns:
            Dictionary mapping filenames to file paths
        """
        if not self.generated_code:
            raise ValueError("No code generated. Call generate_code() first.")
        
        # Ensure project path is set
        if not self.local_server.current_project_path:
            self.local_server.current_project_path = self.workspace_dir
            self.local_server.current_project = "code_project"
        
        saved_files = {}
        
        for filename, code in self.generated_code.items():
            filepath = self.local_server.save_file(filename, code)
            saved_files[filename] = filepath
            self.logger.info(f"Saved {filename} to {filepath}")
        
        return saved_files
    
    def get_code_package(self) -> Dict[str, Any]:
        """
        Get complete code package ready for tester
        
        Returns:
            Dictionary containing code package information
        """
        if not self.generated_code:
            raise ValueError("No code generated. Call generate_code() first.")
        
        return {
            "code": self.generated_code,
            "workspace_dir": self.workspace_dir,
            "architectural_plan": self.architectural_plan,
            "files": list(self.generated_code.keys())
        }
    
    def pass_to_tester(self) -> Dict[str, Any]:
        """
        Pass generated code to Agent C (Tester)
        
        Returns:
            Code package dictionary for tester agent
        """
        if not self.generated_code:
            raise ValueError("No code generated. Call generate_code() first.")
        
        self.logger.info("Passing code package to Tester agent")
        return self.get_code_package()
    
    def _generate_file_code(self, filename: str, description: str) -> str:
        """Generate code for a specific file using MCP"""
        file_plan = None
        detailed_plan = self.architectural_plan.get("detailed_plan", {})
        file_plans = detailed_plan.get("file_plans", {})
        
        # Try to get specific plan for this file
        if filename in file_plans:
            file_plan = file_plans[filename]
        elif file_plans:
            # Try to find matching plan
            for key, plan in file_plans.items():
                if filename.replace('.py', '') in key.lower():
                    file_plan = plan
                    break
        
        prompt = f"""Generate complete, executable Python code for the file: {filename}

File Description: {description}

Architectural Context:
{self._format_architectural_context()}

File-Specific Plan:
{file_plan if file_plan else 'No specific plan provided'}

Requirements:
- Write complete, working Python code
- Include all necessary imports
- Add docstrings for functions and classes
- Follow Python best practices (PEP 8)
- Make the code modular and well-structured
- Include error handling where appropriate
- Ensure the code is ready to be executed

Generate ONLY the Python code, no markdown formatting, no explanations, just the code itself.
"""
        
        try:
            # Prepare context for LangChain
            context = {
                "architectural_plan": self.architectural_plan,
                "file_plan": file_plan,
                "filename": filename,
                "description": description
            }
            
            # Use LangChain wrapper if available
            if self.langchain_wrapper:
                response = self.langchain_wrapper.invoke(prompt, context=context)
                # Track API usage
                if self.api_usage_tracker:
                    token_usage = self.langchain_wrapper.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("coder", token_usage)
            else:
                # Fallback to direct MCP client
                if not hasattr(self.mcp_client, 'session') or self.mcp_client.session is None:
                    self.mcp_client.connect()
                response = self.mcp_client.send_request(prompt)
                # Track API usage
                if self.api_usage_tracker:
                    token_usage = self.mcp_client.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("coder", token_usage)
            
            # Extract code from response (remove markdown if present)
            code = self._extract_code_from_response(response, filename)
            
            return code
            
        except Exception as e:
            self.logger.error(f"Error generating code for {filename}: {str(e)}")
            # Return a minimal valid Python file as fallback
            return f'"""\n{description}\n"""\n\n# TODO: Implement based on requirements\n'
    
    def _format_architectural_context(self) -> str:
        """Format architectural plan for context in prompts"""
        if not self.architectural_plan:
            return "No architectural context available"
        
        context_parts = []
        
        # Add requirements
        if self.architectural_plan.get("requirements"):
            context_parts.append(f"Requirements: {self.architectural_plan['requirements']}")
        
        # Add analysis
        analysis = self.architectural_plan.get("analysis", {})
        if analysis:
            context_parts.append(f"Components: {analysis.get('components', [])}")
            context_parts.append(f"Architecture Type: {analysis.get('architecture_type', 'N/A')}")
        
        # Add file structure
        file_structure = self.architectural_plan.get("file_structure", {})
        if file_structure:
            context_parts.append(f"File Structure: {file_structure.get('files', {})}")
        
        return "\n".join(context_parts)
    
    def _extract_code_from_response(self, response: str, filename: str) -> str:
        """Extract Python code from MCP response, removing markdown if present"""
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
        
        # If response is already code, return as is
        return response.strip()
