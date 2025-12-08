# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

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
from utils.conversation_logger import ConversationLogger
from datetime import datetime


class AgentCoder:
    """Agent responsible for code generation based on architectural plan"""
    
    def __init__(self, mcp_client, api_usage_tracker=None, workspace_dir=None, enable_memory=True, local_server=None, session_id=None):
        """
        Initialize the Coder agent
        
        Args:
            mcp_client: MCP client instance for AI interactions
            api_usage_tracker: Optional API usage tracker instance
            workspace_dir: Directory where generated code will be saved
            enable_memory: Whether to enable LangChain memory
            local_server: Optional LocalServer instance for file operations. If None, creates one.
            session_id: Optional session ID for conversation logging
        """
        self.mcp_client = mcp_client
        self.api_usage_tracker = api_usage_tracker
        self.logger = logging.getLogger(__name__)
        self.workspace_dir = workspace_dir or Settings.WORKSPACE_DIR
        
        # Initialize conversation logger
        self.conversation_logger = ConversationLogger(
            agent_name="coder",
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
        
        # DEBUG: Log what was actually received
        detailed_plan = architectural_plan.get('detailed_plan', {})
        if detailed_plan:
            self.logger.info(f"✓ detailed_plan received with {len(detailed_plan)} keys: {list(detailed_plan.keys())}")
        else:
            self.logger.warning("⚠️ detailed_plan is EMPTY or missing!")
            self.logger.warning(f"Architectural plan keys: {list(architectural_plan.keys())}")
    
    def regenerate_code(self, regeneration_instructions: Dict[str, Any]) -> Dict[str, str]:
        """
        Regenerate code based on feedback from Agent D (Debugger)
        
        Args:
            regeneration_instructions: Dictionary containing feedback and instructions from debugger
        
        Returns:
            Dictionary mapping filenames to regenerated code content
        """
        if not regeneration_instructions.get("needs_regeneration", False):
            self.logger.info("No regeneration needed")
            return self.generated_code
        
        self.logger.info("Regenerating code based on debugger feedback...")
        
        # Get original architectural plan
        original_plan = regeneration_instructions.get("original_architectural_plan", self.architectural_plan)
        if not original_plan:
            raise ValueError("No architectural plan available for regeneration")
        
        # Update architectural plan with feedback
        updated_plan = original_plan.copy()
        if "architectural_notes" in regeneration_instructions:
            # Add feedback to the plan
            if "detailed_plan" not in updated_plan:
                updated_plan["detailed_plan"] = {}
            updated_plan["detailed_plan"]["regeneration_feedback"] = regeneration_instructions
        
        # Store updated plan
        self.architectural_plan = updated_plan
        
        # Clear previous generated code
        self.generated_code = {}
        
        # Regenerate code with feedback context
        instructions = regeneration_instructions.get("regeneration_instructions", "")
        key_changes = regeneration_instructions.get("key_changes", [])
        
        # Generate each file with feedback
        file_structure = updated_plan.get("file_structure", {})
        files = file_structure.get("files", {})
        
        if not files:
            files = {
                "main.py": "Main entry point and application logic",
                "utils.py": "Utility functions and helpers",
                "test_data.py": "Test data and sample inputs"
            }
        
        # Always ensure README.md is included
        if "README.md" not in files:
            files["README.md"] = "Project documentation and usage instructions"
        
        for filename, description in files.items():
            if filename.endswith('.py'):
                self.logger.info(f"Regenerating code for {filename} with feedback...")
                code = self._generate_file_code_with_feedback(
                    filename, 
                    description, 
                    instructions,
                    key_changes
                )
                self.generated_code[filename] = code
            elif filename.endswith('.md'):
                self.logger.info(f"Regenerating documentation for {filename}...")
                readme = self._generate_readme()
                self.generated_code[filename] = readme
        
        self.logger.info(f"Code regeneration complete. Generated {len(self.generated_code)} files")
        return self.generated_code
    
    def _generate_file_code_with_feedback(self, filename: str, description: str, 
                                         instructions: str, key_changes: list) -> str:
        """Generate code for a specific file with feedback from debugger"""
        file_plan = None
        detailed_plan = self.architectural_plan.get("detailed_plan", {})
        file_plans = detailed_plan.get("file_plans", {})
        
        if filename in file_plans:
            file_plan = file_plans[filename]
        
        prompt = f"""Regenerate the Python code for the file: {filename}

File Description: {description}

Original Architectural Context:
{self._format_architectural_context()}

Regeneration Instructions:
{instructions}

Key Changes Needed:
{chr(10).join(f'- {change}' for change in key_changes) if key_changes else 'None specified'}

File-Specific Plan:
{file_plan if file_plan else 'No specific plan provided'}

CRITICAL FILE COORDINATION RULES:
1. If this is main.py: Include ALL core class definitions needed for this project
   - ALL application-specific classes must be defined here
   - This is the single source of truth for the project's classes
   - Implement proper validation and error handling
   - Only include classes that are actually needed for the requirements

2. If this is utils.py: ONLY helper functions, NO class definitions
   - Import classes from main.py if needed: "from main import ClassName"
   - Only add utility functions that don't duplicate main.py
   - Keep it minimal and focused on the actual project needs

3. If this is test_data.py: ONLY sample data, NO class definitions
   - Import classes DIRECTLY from "main" (the filename is main.py):
     CORRECT: from main import ClassName, AnotherClass
     WRONG: from project_name import ClassName
   - DO NOT create hypothetical module names
   - Use ONLY the actual filename: "main" (without .py extension)
   - The main code file is ALWAYS named "main.py"
   - Create only necessary sample data instances
   - NO duplicate class definitions

Requirements:
- Fix all issues mentioned in the regeneration instructions
- Address all key changes
- Write complete, working Python code
- Include all necessary imports
- Add comprehensive docstrings for functions and classes
- Follow Python best practices (PEP 8)
- Make the code modular and well-structured
- Include proper error handling where appropriate
- Ensure the code will pass the tests
- If this is main.py: DO NOT include 'if __name__ == "__main__":' block that calls main() - tests will import and call functions directly
- If this includes a main() function: Keep it as a regular function without the if __name__ guard

CRITICAL: Your response must contain ONLY raw Python code.
DO NOT wrap the code in markdown code blocks (```python or ```).
DO NOT include any explanations, comments outside the code, or formatting.
Start your response directly with the first line of Python code (imports or docstrings).
"""
        
        try:
            context = {
                "architectural_plan": self.architectural_plan,
                "file_plan": file_plan,
                "filename": filename,
                "description": description,
                "instructions": instructions,
                "key_changes": key_changes
            }
            
            if self.langchain_wrapper:
                response = self.langchain_wrapper.invoke(prompt, context=context)
                if self.api_usage_tracker:
                    token_usage = self.langchain_wrapper.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("coder", token_usage)
            else:
                if not hasattr(self.mcp_client, 'session') or self.mcp_client.session is None:
                    self.mcp_client.connect()
                response = self.mcp_client.send_request(prompt)
                if self.api_usage_tracker:
                    token_usage = self.mcp_client.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("coder", token_usage)
            
            code = self._extract_code_from_response(response, filename)
            return code
            
        except Exception as e:
            self.logger.error(f"Error regenerating code for {filename}: {str(e)}")
            return f'"""\n{description}\n\n# TODO: Regenerate based on feedback\n'
    
    def generate_code(self) -> Dict[str, str]:
        """
        OPTIMIZED: Generate ALL files in ONE API call
        
        Returns:
            Dictionary mapping filenames to generated code content
        """
        if not self.architectural_plan:
            raise ValueError("No architectural plan available. Call receive_architecture() first.")
        
        self.logger.info("Generating ALL code files in ONE API call...")
        
        # Use combined generation method
        self.generated_code = self._generate_all_files_combined()
        
        self.logger.info(f"Code generation complete. Generated {len(self.generated_code)} files in 1 API call")
        return self.generated_code
    
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
        
        # Validate code before passing to tester (requires debugger's validation method)
        try:
            from agents.agent_debugger import AgentDebugger
            temp_debugger = AgentDebugger(self.mcp_client, workspace_dir=self.workspace_dir, enable_memory=False)
            validation_results = temp_debugger.validate_code(self.generated_code)
            
            if validation_results.get("issues"):
                self.logger.warning(f"Code validation found {len(validation_results['issues'])} issues:")
                for issue in validation_results['issues']:
                    self.logger.warning(f"  - {issue['file']}: {issue['message']}")
            
            if validation_results.get("warnings"):
                self.logger.warning(f"Code validation found {len(validation_results['warnings'])} warnings:")
                for warning in validation_results['warnings']:
                    self.logger.warning(f"  - {warning['file']}: {warning['message']}")
        except Exception as e:
            self.logger.warning(f"Could not validate code: {str(e)}")
        
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
        
        prompt = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    🚨 CRITICAL RULES - READ FIRST 🚨                     ║
╚══════════════════════════════════════════════════════════════════════════╝

⚠️ SELF-VALIDATION CHECKLIST - Before writing ANY code, verify:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☐ ALL data retrieval methods RETURN values (not print)
☐ ALL query/search methods RETURN results (not print)
☐ ONLY main() or display_* functions print to user
☐ Action methods can print confirmations BUT must RETURN status
☐ Data layer is completely separated from presentation layer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 THE ONE RULE THAT MATTERS:
   DATA METHODS → RETURN VALUES
   MAIN FUNCTION → PRINTS RESULTS

⚠️ API CONTRACT RULES (THIS DETERMINES IF TESTS PASS OR FAIL):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CORE PRINCIPLE: Separate Data Logic from Presentation Logic
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. DATA METHODS (CRUD, Queries, Calculations):
   ✓ RETURN the data/results
   ✗ DO NOT print the data
   
   Examples:
   - search_items() → RETURNS list of found items
   - get_all_records() → RETURNS list of records
   - calculate_total() → RETURNS numeric result
   - find_by_id() → RETURNS object or None
   - process_data() → RETURNS processed data

2. ACTION METHODS (Create, Update, Delete):
   ✓ Can print confirmation/status messages
   ✓ MUST RETURN success indicator (bool, status code, or object)
   
   Examples:
   - add_item() → Prints "Item added", RETURNS True/object
   - delete_record() → Prints "Deleted", RETURNS success status
   - update_data() → Prints "Updated", RETURNS updated object

3. PRESENTATION/DISPLAY METHODS:
   ✓ Print formatted output for user
   ✓ Can return None or void
   
   Examples:
   - display_results() → Prints formatted data
   - show_menu() → Prints menu options
   - print_report() → Prints formatted report

4. MAIN/CONTROLLER FUNCTIONS:
   ✓ Coordinate data methods and display methods
   ✓ Handle user interaction and printing
   
   Pattern:
   ```python
   def main():
       # Get data
       results = manager.search_items(query)
       # Display data
       if results:
           print(f"Found {len(results)} items:")
           for item in results:
               print(item)
   ```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHY THIS MATTERS FOR TESTING:
- Tests verify data operations by checking RETURN values
- If methods print instead of return, tests fail
- Separation enables independent testing of logic and display
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL FILE COORDINATION RULES:
1. If this is main.py: Include ONLY the classes and functions needed for this specific project
   - Define ALL application-specific classes here
   - This is the single source of truth for the project's classes
   - Implement proper validation and error handling as needed by the requirements
   - Only include what is actually required - do NOT add extra unrelated classes
   - RESPECT API CONTRACTS: Methods return data, main() handles printing

2. If this is utils.py: ONLY helper functions, NO class definitions
   - Import classes from main.py if needed: "from main import ClassName"
   - Only add utility functions that support the main application
   - Keep it minimal and focused on actual project needs

3. If this is test_data.py: ONLY sample data, NO class definitions
   - Import classes DIRECTLY from "main" (the filename is main.py):
     CORRECT: from main import ClassName, AnotherClass
     WRONG: from project_name import ClassName
   - DO NOT create hypothetical module names
   - Use ONLY the actual filename: "main" (without .py extension)
   - The main code file is ALWAYS named "main.py"
   - Create only the sample data needed for this project
   - NO duplicate class definitions

General Requirements:
- Write complete, working Python code
- Include all necessary imports
- Add comprehensive docstrings for functions and classes
- Follow Python best practices (PEP 8)
- Make the code modular and well-structured
- Include proper error handling where appropriate
- Ensure the code is ready to be executed
- If this is main.py: DO NOT include 'if __name__ == "__main__":' block that calls main() - tests will import and call functions directly
- If this includes a main() function: Keep it as a regular function without the if __name__ guard

CRITICAL: Your response must contain ONLY raw Python code. 
DO NOT wrap the code in markdown code blocks (```python or ```).
DO NOT include any explanations, comments outside the code, or formatting.
Start your response directly with the first line of Python code (imports or docstrings).
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
                
                # Extract text and log conversation
                response_text = self.mcp_client.extract_text_from_response(response)
                self.conversation_logger.log_interaction(
                    prompt=prompt,
                    response=response_text,
                    metadata=self.mcp_client.get_token_usage()
                )
            
            # Extract code from response (remove markdown if present)
            code = self._extract_code_from_response(response, filename)
            
            return code
            
        except Exception as e:
            self.logger.error(f"Error generating code for {filename}: {str(e)}")
            # Return a minimal valid Python file as fallback
            return f'"""\n{description}\n"""\n\n# TODO: Implement based on requirements\n'
    
    def _generate_all_files_combined(self) -> Dict[str, str]:
        """
        OPTIMIZED: Generate ALL code files in ONE API call (like Architect)
        
        Returns:
            Dictionary mapping filenames to generated code content
        """
        file_structure = self.architectural_plan.get("file_structure", {})
        files = file_structure.get("files", {})
        
        # Default files if not specified
        if not files:
            files = {
                "main.py": "Main entry point and application logic",
                "utils.py": "Utility functions and helpers",
                "test_data.py": "Test data and sample inputs",
                "README.md": "Project documentation"
            }
        
        # Build combined prompt for all files
        # Format detailed plan as readable text - ALWAYS show it, even if empty
        detailed_plan = self.architectural_plan.get('detailed_plan', {})
        import json
        # Always format as JSON so coder can see the structure
        # COMMENTED OUT: detailed_plan_str = json.dumps(detailed_plan, indent=2)
        # SUPPRESSED: Passing detailed_plan to coder - analysis shows it causes cognitive overload
        detailed_plan_str = "{}"  # Suppressed - too much context confuses AI
        
        prompt = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    🚨 CRITICAL RULES - READ FIRST 🚨                     ║
╚══════════════════════════════════════════════════════════════════════════╝

⚠️ SELF-VALIDATION CHECKLIST - Before generating ANY code:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☐ ALL data retrieval methods RETURN values (not print)
☐ ALL query/search methods RETURN results (not print)
☐ ONLY main() or display_* functions print to user
☐ Action methods can print confirmations BUT must RETURN status
☐ Data layer is completely separated from presentation layer
☐ NO 'if __name__ == "__main__":' block in main.py (tests import directly!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 THE ONE RULE: Data methods RETURN, main() prints

Generate ALL code files for this Python project in ONE response as JSON.

Architectural Context:
{self._format_architectural_context()}

Detailed Plan:
{detailed_plan_str}

FILES TO GENERATE:
{chr(10).join(f'- {fname}: {desc}' for fname, desc in files.items())}

CRITICAL FILE COORDINATION RULES:
1. main.py: Include ONLY classes/functions needed for this project
   - ALL application classes defined here
   - This is the single source of truth
   - NO extra unrelated classes

2. utils.py: ONLY helper functions, NO class definitions
   - Import from main.py if needed: "from main import ClassName"
   - Keep minimal and focused

3. test_data.py: ONLY sample data, NO class definitions  
   - Import from "main": "from main import ClassName"
   - NO hypothetical module names

4. README.md: Project documentation in markdown

RESPONSE FORMAT - Return ONLY valid JSON (no markdown):
{{
  "main.py": "complete Python code here",
  "utils.py": "complete Python code here",
  "test_data.py": "complete Python code here",
  "README.md": "markdown content here"
}}

CRITICAL: 
- Return ONLY parseable JSON starting with {{ and ending with }}
- NO markdown code blocks (```json or ```)
- NO explanations outside the JSON
- Each file's code should be a complete, valid string
- Escape quotes properly in JSON strings
"""
        
        try:
            if self.langchain_wrapper:
                response = self.langchain_wrapper.invoke(prompt)
                if self.api_usage_tracker:
                    token_usage = self.langchain_wrapper.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("coder", token_usage)
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
                        self.api_usage_tracker.track_usage("coder", token_usage)
                # Log conversation
                response_text = self.mcp_client.extract_text_from_response(response)
                self.conversation_logger.log_interaction(
                    prompt=prompt,
                    response=response_text,
                    metadata=self.mcp_client.get_token_usage()
                )
            
            # Parse JSON response
            import json
            if isinstance(response, dict):
                response_text = self.mcp_client.extract_text_from_response(response)
            else:
                response_text = str(response)
            
            # Extract JSON from response
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
                generated_files = json.loads(json_str)
                
                # Validate all expected files are present
                for filename in files.keys():
                    if filename not in generated_files:
                        self.logger.warning(f"Missing {filename}, generating fallback")
                        if filename.endswith('.py'):
                            generated_files[filename] = f'"""{files[filename]}"""\n\n# TODO: Implement\n'
                        else:
                            generated_files[filename] = f"# {filename}\n\nDocumentation pending."
                
                return generated_files
            
            # Fallback if JSON parsing fails
            self.logger.warning("Failed to parse JSON, falling back to individual generation")
            return self._generate_files_individually()
            
        except Exception as e:
            self.logger.error(f"Error in combined generation: {str(e)}")
            self.logger.info("Falling back to individual file generation")
            return self._generate_files_individually()
    
    def _generate_files_individually(self) -> Dict[str, str]:
        """Fallback: Generate files individually (original method)"""
        file_structure = self.architectural_plan.get("file_structure", {})
        files = file_structure.get("files", {})
        
        if not files:
            files = {
                "main.py": "Main entry point and application logic",
                "utils.py": "Utility functions and helpers",
                "test_data.py": "Test data and sample inputs",
                "README.md": "Project documentation"
            }
        
        generated = {}
        for filename, description in files.items():
            if filename.endswith('.py'):
                self.logger.info(f"Generating code for {filename}...")
                code = self._generate_file_code(filename, description)
                generated[filename] = code
            elif filename.endswith('.md'):
                self.logger.info(f"Generating documentation for {filename}...")
                readme = self._generate_readme()
                generated[filename] = readme
        
        return generated
    
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
    
    def _generate_readme(self) -> str:
        """Generate README.md documentation for the project"""
        prompt = f"""Generate a comprehensive README.md file for this Python project.

Project Context:
{self._format_architectural_context()}

Generated Files:
{', '.join(self.generated_code.keys())}

The README should include:
1. **Project Title** - Clear, descriptive name
2. **Description** - What the project does and its purpose
3. **Features** - List of key features and capabilities
4. **Requirements** - Python version and dependencies (if any)
5. **Installation** - How to set up the project
6. **Usage** - How to run and use the application with examples
7. **Project Structure** - Brief description of each file
8. **Examples** - Sample usage scenarios or command examples
9. **Testing** - How to run tests (if applicable)
10. **License** - (Optional) Licensing information

Format Requirements:
- Use proper Markdown formatting
- Include code blocks where appropriate (use ```python for Python code)
- Use headers (#, ##, ###) for sections
- Use bullet points and numbered lists
- Make it clear, concise, and user-friendly
- Include actual commands users can copy and run

CRITICAL: Your response should be a complete README.md file in Markdown format.
Start with the main heading (# Project Name) and include all sections.
DO NOT wrap the entire response in markdown code blocks.
Just provide the raw markdown content.
"""
        
        try:
            # Use MCP client to generate README
            if self.langchain_wrapper:
                response = self.langchain_wrapper.invoke(prompt, context={
                    "architectural_plan": self.architectural_plan,
                    "generated_files": list(self.generated_code.keys())
                })
                if self.api_usage_tracker:
                    token_usage = self.langchain_wrapper.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("coder", token_usage)
            else:
                if not hasattr(self.mcp_client, 'session') or self.mcp_client.session is None:
                    self.mcp_client.connect()
                response = self.mcp_client.send_request(prompt)
                if self.api_usage_tracker:
                    token_usage = self.mcp_client.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("coder", token_usage)
                
                # Extract text and log conversation
                response_text = self.mcp_client.extract_text_from_response(response)
                self.conversation_logger.log_interaction(
                    prompt=prompt,
                    response=response_text,
                    metadata=self.mcp_client.get_token_usage()
                )
            
            # Extract README content from response
            if isinstance(response, dict):
                readme_content = self.mcp_client.extract_text_from_response(response)
            else:
                readme_content = str(response)
            
            # Clean up - remove outer code blocks if present
            lines = readme_content.split('\n')
            if lines and lines[0].strip().startswith('```'):
                # Remove first and last lines if they're code block markers
                if lines[0].strip() in ['```markdown', '```md', '```']:
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                readme_content = '\n'.join(lines)
            
            return readme_content.strip()
            
        except Exception as e:
            self.logger.error(f"Error generating README.md: {str(e)}")
            # Return a basic README as fallback
            analysis = self.architectural_plan.get("analysis", {}) if self.architectural_plan else {}
            components = analysis.get("components", [])
            requirements = self.architectural_plan.get("requirements", "N/A") if self.architectural_plan else "N/A"
            
            return f"""# Project

## Description
{requirements}

## Features
{chr(10).join(f'- {comp}' for comp in components) if components else '- To be documented'}

## Requirements
- Python 3.7+

## Installation
```bash
# Clone or download the project
# No additional dependencies required
```

## Usage
```bash
python main.py
```

## Project Structure
{chr(10).join(f'- `{filename}`: Generated code file' for filename in self.generated_code.keys())}

## License
This project is provided as-is.
"""
    
    def _extract_code_from_response(self, response: Any, filename: str) -> str:
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
        skip_next = False
        
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
