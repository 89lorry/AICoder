"""
Agent A: Architect
Combines all architectural tasks into ONE API request
"""

import logging
from typing import Dict, Any, Optional
from config.settings import Settings
from utils.file_manager import FileManager
from utils.memory_manager import MemoryManager
from utils.langchain_wrapper import LangChainWrapper
from utils.conversation_logger import ConversationLogger
from datetime import datetime
import json


class AgentArchitect:
    """Agent responsible for architectural design - ONE API CALL per iteration"""
    
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
            self.memory_manager.add_system_message(
                "You are an expert software architect. You analyze requirements and design "
                "comprehensive software architectures with proper file structures."
            )
            self.logger.info("Initialized LangChain memory for Architect agent")
        
        # Internal state
        self.requirements = None
        self.architectural_plan = None
    
    def create_complete_architecture(self, requirements: str) -> Dict[str, Any]:
        """
        SINGLE API CALL - Analyze requirements, design structure, create detailed plan
        
        Args:
            requirements: Natural language description of software requirements
            
        Returns:
            Complete architectural plan dictionary
        """
        self.requirements = requirements
        self.logger.info("Creating complete architecture in ONE API call...")
        
        prompt = f"""Create a COMPLETE architectural plan for the following requirements in a SINGLE response:

Requirements:
{requirements}

Provide a comprehensive JSON response with ALL of the following sections:

1. "analysis": {{
    "components": [EXACTLY 3 main components/modules - NO MORE],
    "dependencies": [external libraries needed],
    "architecture_type": "CLI/API/GUI/etc",
    "complexity": "simple/medium/complex",
    "summary": "brief project summary"
}}

2. "file_structure": {{
    "files": {{
        "main.py": "Contains ALL core classes and application logic",
        "utils.py": "ONLY helper functions (imports from main.py)",
        "test_data.py": "ONLY sample data (imports from main.py)",
        "README.md": "Project documentation"
    }},
    "entry_point": "main.py",
    "class_definitions": {{
        "ClassName": "main.py"  // ALL classes defined in main.py
    }}
}}

3. "detailed_plan": {{
    "overview": "overall architecture description",
    "file_plans": {{
        "main.py": {{
            "purpose": "what it does",
            "classes": ["Class1", "Class2"],
            "functions": ["func1", "func2"],
            "key_logic": "main logic flow"
        }},
        "utils.py": {{
            "purpose": "what it does",
            "functions": ["helper1", "helper2"],
            "imports": ["from main import ClassName"]
        }},
        "test_data.py": {{
            "purpose": "sample data",
            "imports": ["from main import ClassName"],
            "data_examples": ["sample1", "sample2"]
        }}
    }},
    "implementation_order": ["main.py", "utils.py", "test_data.py"],
    "test_considerations": ["what to test"],
    "notes": ["important notes"]
}}

CRITICAL RULES:
- EXACTLY 3 components in analysis
- ALL classes defined in main.py ONLY
- utils.py and test_data.py import from main.py
- NO duplicate class definitions
- Return ONLY valid JSON, no markdown

Response MUST be parseable JSON starting with {{ and ending with }}.
"""
        
        try:
            # Use MCP client to get complete architecture
            if self.langchain_wrapper:
                response = self.langchain_wrapper.invoke(prompt)
                if self.api_usage_tracker:
                    token_usage = self.langchain_wrapper.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("architect", token_usage)
            else:
                if not hasattr(self.mcp_client, 'session') or self.mcp_client.session is None:
                    self.mcp_client.connect()
                response = self.mcp_client.send_request(prompt)
                if self.api_usage_tracker:
                    token_usage = self.mcp_client.get_token_usage()
                    if token_usage:
                        self.api_usage_tracker.track_usage("architect", token_usage)
                
                response_text = self.mcp_client.extract_text_from_response(response)
                self.conversation_logger.log_interaction(
                    prompt=prompt,
                    response=response_text,
                    metadata=self.mcp_client.get_token_usage()
                )
            
            # Parse complete response
            plan = self._parse_complete_architecture(response)
            plan["requirements"] = requirements
            plan["timestamp"] = datetime.now().isoformat()
            
            self.architectural_plan = plan
            self.logger.info("Complete architecture created in ONE API call")
            self.logger.info(f"Components: {len(plan.get('analysis', {}).get('components', []))}")
            self.logger.info(f"Files: {list(plan.get('file_structure', {}).get('files', {}).keys())}")
            
            return plan
            
        except Exception as e:
            self.logger.error(f"Error creating architecture: {str(e)}")
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
            raise ValueError("No architectural plan available. Run create_complete_architecture() first.")
        
        self.logger.info("Passing architectural plan to Coder agent")
        return self.architectural_plan
    
    def _parse_complete_architecture(self, response: Any) -> Dict[str, Any]:
        """Parse complete architecture response from MCP"""
        try:
            if isinstance(response, dict):
                return response
            
            response_text = str(response)
            
            # Extract JSON from response
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
                parsed = json.loads(json_str)
                
                # Validate structure
                if 'analysis' in parsed and 'file_structure' in parsed and 'detailed_plan' in parsed:
                    return parsed
            
            # Fallback: create structured response
            self.logger.warning("Could not parse complete JSON, using fallback structure")
            return {
                "analysis": {
                    "components": ["Core Application", "Data Management", "User Interface"],
                    "dependencies": [],
                    "architecture_type": "CLI",
                    "complexity": "medium",
                    "summary": "Multi-component application"
                },
                "file_structure": {
                    "files": {
                        "main.py": "Main entry point and core classes",
                        "utils.py": "Utility functions",
                        "test_data.py": "Sample data",
                        "README.md": "Documentation"
                    },
                    "entry_point": "main.py"
                },
                "detailed_plan": {
                    "overview": "Simple application architecture",
                    "file_plans": {
                        "main.py": {
                            "purpose": "Core application logic",
                            "classes": [],
                            "functions": [],
                            "key_logic": "Main application flow"
                        }
                    },
                    "implementation_order": ["main.py", "utils.py", "test_data.py"],
                    "notes": []
                }
            }
        except (json.JSONDecodeError, Exception) as e:
            self.logger.error(f"Error parsing architecture: {str(e)}")
            # Return fallback structure
            return {
                "analysis": {
                    "components": ["Core Application", "Data Management", "User Interface"],
                    "dependencies": [],
                    "architecture_type": "CLI",
                    "complexity": "medium",
                    "summary": "Multi-component application"
                },
                "file_structure": {
                    "files": {
                        "main.py": "Main entry point and core classes",
                        "utils.py": "Utility functions",
                        "test_data.py": "Sample data",
                        "README.md": "Documentation"
                    },
                    "entry_point": "main.py"
                },
                "detailed_plan": {
                    "overview": "Simple application architecture",
                    "file_plans": {},
                    "implementation_order": ["main.py"],
                    "notes": []
                }
            }
    
    # Legacy methods for backwards compatibility (now just call the combined method)
    def analyze_requirements(self, requirements: str) -> Dict[str, Any]:
        """Legacy method - now uses combined architecture creation"""
        plan = self.create_complete_architecture(requirements)
        return plan.get("analysis", {})
    
    def design_file_structure(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - returns cached file structure"""
        if self.architectural_plan:
            return self.architectural_plan.get("file_structure", {})
        return {}
    
    def create_architectural_plan(self, analysis: Dict[str, Any], 
                                   file_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - returns complete cached plan"""
        return self.architectural_plan if self.architectural_plan else {}
