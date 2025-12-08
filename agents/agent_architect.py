# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

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
        
        prompt = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║          🚨 CRITICAL ARCHITECTURE RULES - READ FIRST 🚨                 ║
╚══════════════════════════════════════════════════════════════════════════╝

⚠️ SELF-VALIDATION CHECKLIST - Before creating the plan:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☐ Have I specified that data methods must RETURN values?
☐ Have I specified that query/search methods must RETURN results?
☐ Have I specified that main() handles printing?
☐ Have I limited components to EXACTLY 3?
☐ Have I specified ALL classes go in main.py?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 THE ONE RULE THAT MATTERS:
   In your detailed_plan, specify: "Data methods RETURN, main() prints"

Create a COMPLETE architectural plan for the following requirements in a SINGLE response:

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

CRITICAL RULES:
- EXACTLY 3 components in analysis
- ALL classes defined in main.py ONLY
- utils.py and test_data.py import from main.py
- NO duplicate class definitions
- Return ONLY valid JSON, no markdown

Response MUST be parseable JSON starting with {{ and ending with }}.
"""
# Optional detailed plan, better code but increasing text content count that might dilute critical rules
# 3. "detailed_plan": {{
#     "overview": "overall architecture description",
#     "file_plans": {{
#         "main.py": {{
#             "purpose": "what it does",
#             "classes": ["Class1", "Class2"],
#             "functions": ["func1", "func2"],
#             "key_logic": "main logic flow",
#             "api_contracts": {{
#                 "ClassName.data_method": "RETURNS data/list/dict (does NOT print)",
#                 "ClassName.query_method": "RETURNS results (does NOT print)",
#                 "ClassName.action_method": "Can print confirmation, RETURNS success status"
#             }},
#             "design_principles": [
#                 "Data retrieval methods RETURN values",
#                 "Query/search methods RETURN results",
#                 "Action methods can print status, but RETURN success indicators",
#                 "main() or display functions handle printing",
#                 "Separation: data layer returns, presentation layer prints"
#             ]
#         }},
#         "utils.py": {{
#             "purpose": "what it does",
#             "functions": ["helper1", "helper2"],
#             "imports": ["from main import ClassName"]
#         }},
#         "test_data.py": {{
#             "purpose": "sample data",
#             "imports": ["from main import ClassName"],
#             "data_examples": ["sample1", "sample2"]
#         }}
#     }},
#     "implementation_order": ["main.py", "utils.py", "test_data.py"],
#     "test_considerations": ["what to test"],
#     "notes": ["important notes"]
# }}

        
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
            plan = self._parse_complete_architecture(response_text)
            plan["requirements"] = requirements
            plan["timestamp"] = datetime.now().isoformat()
            
            self.architectural_plan = plan
            self.logger.info("Complete architecture created in ONE API call")
            self.logger.info(f"Components: {len(plan.get('analysis', {}).get('components', []))}")
            self.logger.info(f"Files: {list(plan.get('file_structure', {}).get('files', {}).keys())}")
            
            # DEBUG: Verify detailed_plan was parsed
            detailed_plan = plan.get('detailed_plan', {})
            if detailed_plan:
                self.logger.info(f"✓ detailed_plan parsed with {len(detailed_plan)} keys: {list(detailed_plan.keys())}")
            else:
                self.logger.error("❌ detailed_plan is MISSING after parsing!")
            
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
            # DEBUG: Log what we're parsing
            self.logger.info(f"DEBUG: _parse_complete_architecture received type: {type(response)}")
            
            if isinstance(response, dict):
                self.logger.info("DEBUG: Response is dict, checking if it has detailed_plan...")
                if 'detailed_plan' in response:
                    self.logger.info(f"DEBUG: Dict has detailed_plan with {len(response['detailed_plan'])} keys")
                else:
                    self.logger.warning("DEBUG: Dict MISSING detailed_plan!")
                return response
            
            response_text = str(response)
            self.logger.info(f"DEBUG: Response text length: {len(response_text)}")
            self.logger.info(f"DEBUG: First 200 chars: {response_text[:200]}")
            
            # FIX: Strip markdown code blocks FIRST
            # Remove ```json or ``` from beginning
            lines = response_text.split('\n')
            cleaned_lines = []
            for line in lines:
                stripped = line.strip()
                # Skip markdown code block markers
                if stripped in ['```json', '```', '```JSON']:
                    continue
                cleaned_lines.append(line)
            
            response_text = '\n'.join(cleaned_lines)
            self.logger.info(f"DEBUG: After markdown removal, length: {len(response_text)}")
            
            # Extract JSON from response - find FIRST { and LAST }
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
                self.logger.info(f"DEBUG: Extracted JSON length: {len(json_str)}")
                self.logger.info(f"DEBUG: JSON first 100 chars: {json_str[:100]}")
                
                parsed = json.loads(json_str)
                self.logger.info(f"DEBUG: Parsed JSON has keys: {list(parsed.keys())}")
                
                # Validate structure
                if 'analysis' in parsed and 'file_structure' in parsed and 'detailed_plan' in parsed:
                    detailed_plan = parsed.get('detailed_plan', {})
                    self.logger.info(f"DEBUG: ✅ Validated! detailed_plan has {len(detailed_plan)} keys: {list(detailed_plan.keys())}")
                    return parsed
                else:
                    self.logger.error(f"DEBUG: ❌ Validation FAILED! Missing required keys. Has: {list(parsed.keys())}")
                    # Still return parsed if it has at least one of the required keys
                    if any(key in parsed for key in ['analysis', 'file_structure', 'detailed_plan']):
                        self.logger.warning("DEBUG: Returning partially valid structure")
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
