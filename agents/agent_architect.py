"""
Agent A: Architect
Breaks requirements into file structure (main.py, utils.py, test_data.py)
"""

import logging
from typing import Dict, Any, Optional
from config.settings import Settings
from utils.file_manager import FileManager
from utils.memory_manager import MemoryManager
from utils.langchain_wrapper import LangChainWrapper
from utils.conversation_logger import ConversationLogger
from datetime import datetime


class AgentArchitect:
    """Agent responsible for architectural design and file structure planning"""
    
    def __init__(self, mcp_client, api_usage_tracker=None, enable_memory=True, session_id=None):
        """
        Initialize the Architect agent
        
        Args:
            mcp_client: MCP client instance for AI interactions
            api_usage_tracker: Optional API usage tracker instance
            enable_memory: Whether to enable LangChain memory
            session_id: Optional session ID for conversation logging
        """
        self.mcp_client = mcp_client
        self.api_usage_tracker = api_usage_tracker
        self.file_manager = FileManager()
        self.logger = logging.getLogger(__name__)
        
        # Initialize conversation logger
        self.conversation_logger = ConversationLogger(
            agent_name="architect",
            session_id=session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        
        # Initialize LangChain memory
        self.memory_manager = None
        self.langchain_wrapper = None
        if enable_memory and Settings.ENABLE_MEMORY:
            self.memory_manager = MemoryManager("architect", memory_type="buffer_window")
            self.langchain_wrapper = LangChainWrapper(
                mcp_client=mcp_client,
                memory_manager=self.memory_manager,
                llm_provider="openai"
            )
            # Add system message to memory
            self.memory_manager.add_system_message(
                "You are an expert software architect. You analyze requirements and design "
                "comprehensive software architectures with proper file structures."
            )
            self.logger.info("Initialized LangChain memory for Architect agent")
        
        # Internal state
        self.requirements = None
        self.file_structure = {}
        self.architectural_plan = None
    
    def analyze_requirements(self, requirements: str) -> Dict[str, Any]:
        """
        Analyze software requirements and design architecture
        
        Args:
            requirements: Natural language description of software requirements
            
        Returns:
            Dictionary containing analyzed requirements and initial architecture
        """
        self.requirements = requirements
        self.logger.info("Analyzing requirements...")
        
        prompt = f"""Analyze the following software requirements and create a high-level architectural design:

Requirements:
{requirements}

Provide a JSON response with:
1. "components": List of main components/modules needed
2. "dependencies": List of external dependencies (libraries, frameworks)
3. "architecture_type": Type of architecture (CLI, API, GUI, etc.)
4. "complexity": Estimated complexity level (simple, medium, complex)
5. "summary": Brief summary of what the software should do
"""
        
        try:
            # Use LangChain wrapper if available, otherwise use MCP client directly
            if self.langchain_wrapper:
                response = self.langchain_wrapper.invoke(prompt)
                # Track API usage
                if self.api_usage_tracker:
                    token_usage = self.langchain_wrapper.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("architect", token_usage)
            else:
                # Fallback to direct MCP client
                if not hasattr(self.mcp_client, 'session') or self.mcp_client.session is None:
                    self.mcp_client.connect()
                response = self.mcp_client.send_request(prompt)
                # Track API usage
                if self.api_usage_tracker:
                    token_usage = self.mcp_client.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("architect", token_usage)
                
                # Extract text from response
                response_text = self.mcp_client.extract_text_from_response(response)
                
                # Log conversation
                self.conversation_logger.log_interaction(
                    prompt=prompt,
                    response=response_text,
                    metadata=self.mcp_client.get_token_usage()
                )
            
            # Parse response
            analysis = self._parse_analysis(response_text)
            self.logger.info(f"Requirements analyzed. Components: {len(analysis.get('components', []))}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing requirements: {str(e)}")
            raise
    
    def design_file_structure(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Design file structure for the target software
        
        Args:
            analysis: Analyzed requirements from analyze_requirements()
            
        Returns:
            Dictionary containing file structure design
        """
        self.logger.info("Designing file structure...")
        
        prompt = f"""Based on the following architectural analysis, design a file structure for the software:

Architecture Analysis:
{analysis}

Design a file structure that includes at minimum:
- main.py: Main entry point and application logic
- utils.py: Utility functions and helpers
- test_data.py: Test data and sample inputs

Provide a JSON response with:
1. "files": Dictionary mapping filename to brief description of contents
2. "file_structure": Hierarchical structure if directories are needed
3. "imports": Dictionary showing what imports each file will need
4. "entry_point": Which file is the entry point (typically main.py)

Be specific about what functions, classes, and logic should go in each file.
"""
        
        try:
            # Use LangChain wrapper if available
            if self.langchain_wrapper:
                response = self.langchain_wrapper.invoke(prompt, context={"analysis": analysis})
                # Track API usage
                if self.api_usage_tracker:
                    token_usage = self.langchain_wrapper.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("architect", token_usage)
            else:
                # Fallback to direct MCP client
                response = self.mcp_client.send_request(prompt)
                # Track API usage
                if self.api_usage_tracker:
                    token_usage = self.mcp_client.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("architect", token_usage)
            
            # Parse file structure
            file_structure = self._parse_file_structure(response)
            self.file_structure = file_structure
            self.logger.info(f"File structure designed. Files: {list(file_structure.get('files', {}).keys())}")
            
            return file_structure
            
        except Exception as e:
            self.logger.error(f"Error designing file structure: {str(e)}")
            raise
    
    def create_architectural_plan(self, analysis: Dict[str, Any], 
                                   file_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create detailed architectural plan combining analysis and file structure
        
        Args:
            analysis: Analyzed requirements
            file_structure: Designed file structure
            
        Returns:
            Complete architectural plan dictionary
        """
        self.logger.info("Creating architectural plan...")
        
        prompt = f"""Create a detailed architectural plan combining the analysis and file structure:

Requirements Analysis:
{analysis}

File Structure:
{file_structure}

Create a comprehensive architectural plan as JSON with:
1. "overview": Overall architecture description
2. "file_plans": Detailed plan for each file including:
   - "purpose": What the file does
   - "functions": List of functions with descriptions
   - "classes": List of classes with descriptions
   - "key_logic": Main logic flow
3. "implementation_order": Suggested order for implementing files
4. "test_considerations": What should be tested
5. "notes": Any important implementation notes
"""
        
        try:
            # Use LangChain wrapper if available
            if self.langchain_wrapper:
                response = self.langchain_wrapper.invoke(
                    prompt, 
                    context={"analysis": analysis, "file_structure": file_structure}
                )
                # Track API usage
                if self.api_usage_tracker:
                    token_usage = self.langchain_wrapper.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("architect", token_usage)
            else:
                # Fallback to direct MCP client
                response = self.mcp_client.send_request(prompt)
                # Track API usage
                if self.api_usage_tracker:
                    token_usage = self.mcp_client.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("architect", token_usage)
            
            # Build comprehensive plan
            plan = {
                "requirements": self.requirements,
                "analysis": analysis,
                "file_structure": file_structure,
                "detailed_plan": self._parse_detailed_plan(response),
                "timestamp": self._get_timestamp()
            }
            
            self.architectural_plan = plan
            self.logger.info("Architectural plan created successfully")
            
            return plan
            
        except Exception as e:
            self.logger.error(f"Error creating architectural plan: {str(e)}")
            raise
    
    def get_architectural_plan(self) -> Optional[Dict[str, Any]]:
        """Get the created architectural plan"""
        return self.architectural_plan
    
    def pass_to_coder(self) -> Dict[str, Any]:
        """
        Pass architectural plan to Agent B (Coder)
        
        Returns:
            Architectural plan ready for coder agent
        """
        if not self.architectural_plan:
            raise ValueError("No architectural plan available. Run create_architectural_plan() first.")
        
        self.logger.info("Passing architectural plan to Coder agent")
        return self.architectural_plan
    
    def _parse_analysis(self, response: str) -> Dict[str, Any]:
        """Parse analysis response from MCP"""
        import json
        try:
            # Try to extract JSON from response
            if isinstance(response, dict):
                return response
            
            # Look for JSON in the response
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                return json.loads(json_str)
            
            # Fallback: create structured response
            return {
                "components": ["main", "utils"],
                "dependencies": [],
                "architecture_type": "CLI",
                "complexity": "medium",
                "summary": response[:200] if len(response) > 200 else response
            }
        except json.JSONDecodeError:
            self.logger.warning("Could not parse JSON from response, using fallback")
            return {
                "components": ["main", "utils"],
                "dependencies": [],
                "architecture_type": "CLI",
                "complexity": "medium",
                "summary": str(response)[:200]
            }
    
    def _parse_file_structure(self, response: str) -> Dict[str, Any]:
        """Parse file structure response from MCP"""
        import json
        try:
            if isinstance(response, dict):
                return response
            
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                return json.loads(json_str)
            
            # Fallback: default structure
            return {
                "files": {
                    "main.py": "Main entry point and application logic",
                    "utils.py": "Utility functions and helpers",
                    "test_data.py": "Test data and sample inputs"
                },
                "entry_point": "main.py"
            }
        except json.JSONDecodeError:
            self.logger.warning("Could not parse file structure JSON, using fallback")
            return {
                "files": {
                    "main.py": "Main entry point and application logic",
                    "utils.py": "Utility functions and helpers",
                    "test_data.py": "Test data and sample inputs"
                },
                "entry_point": "main.py"
            }
    
    def _parse_detailed_plan(self, response: str) -> Dict[str, Any]:
        """Parse detailed plan response from MCP"""
        import json
        try:
            if isinstance(response, dict):
                return response
            
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                return json.loads(json_str)
            
            return {"overview": str(response)[:500]}
        except json.JSONDecodeError:
            self.logger.warning("Could not parse detailed plan JSON, using fallback")
            return {"overview": str(response)[:500]}
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.now().isoformat()
