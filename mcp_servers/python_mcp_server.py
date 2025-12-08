# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)


#!/usr/bin/env python3
"""
Python-based MCP Server for AICoder Agents
Wraps existing agent logic with MCP protocol
"""
import sys
import json
import asyncio
import logging
from typing import Any, Dict, Optional
import os

# Add parent directory to path to import agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_architect import AgentArchitect
from agents.agent_coder import AgentCoder
from agents.agent_tester import AgentTester
from agents.agent_debugger import AgentDebugger
from utils.mcp_client import MCPClient
from server.local_server import LocalServer
from backend.api_usage_tracker import APIUsageTracker
from config.settings import Settings


class PythonMCPServer:
    # MCP Server that exposes all agent capabilities via JSON-RPC
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.request_id_counter = 0
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stderr
        )
        self.logger = logging.getLogger(f'MCP-{agent_type}')
        
        # Initialize components
        self.mcp_client = MCPClient()
        self.api_tracker = APIUsageTracker()
        self.local_server = LocalServer()
        
        # Initialize specific agent
        if agent_type == 'architect':
            self.agent = AgentArchitect(
                mcp_client=self.mcp_client,
                api_usage_tracker=self.api_tracker,
                enable_memory=False
            )
        elif agent_type == 'coder':
            self.agent = AgentCoder(
                mcp_client=self.mcp_client,
                api_usage_tracker=self.api_tracker,
                local_server=self.local_server,
                enable_memory=False
            )
        elif agent_type == 'tester':
            self.agent = AgentTester(
                mcp_client=self.mcp_client,
                api_usage_tracker=self.api_tracker,
                local_server=self.local_server,
                enable_memory=False
            )
        elif agent_type == 'debugger':
            self.agent = AgentDebugger(
                mcp_client=self.mcp_client,
                api_usage_tracker=self.api_tracker,
                local_server=self.local_server,
                enable_memory=False
            )
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
            
        self.logger.info(f"{agent_type.capitalize()} MCP server initialized")
    
    def send_response(self, response: Dict[str, Any]):
        json_str = json.dumps(response)
        sys.stdout.write(json_str + '\n')
        sys.stdout.flush()
    
    def send_error(self, request_id: Optional[int], code: int, message: str):
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        self.send_response(response)
    
    async def handle_initialize(self, request: Dict[str, Any]):
        response = {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": f"aicoder-{self.agent_type}-server",
                    "version": "1.0.0"
                }
            }
        }
        self.send_response(response)
    
    async def handle_tools_list(self, request: Dict[str, Any]):
        tools = []
        
        if self.agent_type == 'architect':
            tools.append({
                "name": "create_architecture",
                "description": "Analyze requirements and create comprehensive software architecture",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirements": {
                            "type": "string",
                            "description": "Natural language description of software requirements"
                        }
                    },
                    "required": ["requirements"]
                }
            })
        elif self.agent_type == 'coder':
            tools.append({
                "name": "generate_code",
                "description": "Generate code from architectural plan",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "architectural_plan": {
                            "type": "object",
                            "description": "Architectural plan from architect agent"
                        }
                    },
                    "required": ["architectural_plan"]
                }
            })
        elif self.agent_type == 'tester':
            tools.extend([
                {
                    "name": "generate_tests",
                    "description": "Generate test cases for code",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "code_package": {
                                "type": "object",
                                "description": "Code package with files"
                            }
                        },
                        "required": ["code_package"]
                    }
                },
                {
                    "name": "run_tests",
                    "description": "Run generated tests",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "test_file": {
                                "type": "string",
                                "description": "Path to test file"
                            }
                        },
                        "required": ["test_file"]
                    }
                }
            ])
        elif self.agent_type == 'debugger':
            tools.append({
                "name": "fix_code",
                "description": "Analyze test failures and fix code",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "test_package": {
                            "type": "object",
                            "description": "Code and test results package"
                        }
                    },
                    "required": ["test_package"]
                }
            })
        
        response = {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "tools": tools
            }
        }
        self.send_response(response)
    
    async def handle_tool_call(self, request: Dict[str, Any]):
        try:
            tool_name = request["params"]["name"]
            arguments = request["params"]["arguments"]
            
            result_text = None
            
            # Route to appropriate agent method
            if self.agent_type == 'architect' and tool_name == 'create_architecture':
                requirements = arguments["requirements"]
                arch_plan = self.agent.create_complete_architecture(requirements)
                result_text = json.dumps(arch_plan)
                
            elif self.agent_type == 'coder' and tool_name == 'generate_code':
                arch_plan = arguments["architectural_plan"]
                self.agent.receive_architecture(arch_plan)
                code = self.agent.generate_code()
                code_package = self.agent.get_code_package()
                result_text = json.dumps(code_package)
                
            elif self.agent_type == 'tester' and tool_name == 'generate_tests':
                code_package = arguments["code_package"]
                self.agent.receive_code(code_package)
                test_code = self.agent.generate_test_cases()
                result_text = json.dumps({
                    "test_code": test_code,
                    "test_file_path": self.agent.test_file_path
                })
                
            elif self.agent_type == 'tester' and tool_name == 'run_tests':
                test_file = arguments.get("test_file", "test_main.py")
                test_results = self.agent.local_server.run_tests(test_file=test_file, timeout=300)
                self.agent.test_results = test_results
                result_text = json.dumps(test_results)
                
            elif self.agent_type == 'debugger' and tool_name == 'fix_code':
                test_package = arguments["test_package"]
                self.agent.receive_code_and_results(test_package)
                debug_result = self.agent.analyze_and_fix_combined()
                result_text = json.dumps(debug_result)
                
            else:
                self.send_error(request["id"], -32601, f"Unknown tool: {tool_name}")
                return
            
            # Send success response
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                }
            }
            self.send_response(response)
            
        except Exception as e:
            self.logger.error(f"Error handling tool call: {e}", exc_info=True)
            self.send_error(request["id"], -32603, f"Internal error: {str(e)}")
    
    async def handle_request(self, request: Dict[str, Any]):
        method = request.get("method")
        
        if method == "initialize":
            await self.handle_initialize(request)
        elif method == "notifications/initialized":
            # Just acknowledge, no response needed
            pass
        elif method == "tools/list":
            await self.handle_tools_list(request)
        elif method == "tools/call":
            await self.handle_tool_call(request)
        else:
            self.send_error(request.get("id"), -32601, f"Method not found: {method}")
    
    async def run(self):
        self.logger.info(f"{self.agent_type.capitalize()} MCP server running on stdio")
        
        # Read requests from stdin line by line (Windows compatible)
        loop = asyncio.get_event_loop()
        
        # For Windows, use a different approach
        if sys.platform == 'win32':
            # Windows: read stdin in blocking mode from thread
            import concurrent.futures
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            
            def read_line():
                return sys.stdin.readline()
            
            while True:
                try:
                    # Read line from stdin in thread
                    line = await loop.run_in_executor(executor, read_line)
                    if not line:
                        break
                    
                    request = json.loads(line)
                    await self.handle_request(request)
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing request: {e}", exc_info=True)
        else:
            # Unix: use connect_read_pipe
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await loop.connect_read_pipe(lambda: protocol, sys.stdin)
            
            while True:
                try:
                    line = await reader.readline()
                    if not line:
                        break
                        
                    request = json.loads(line.decode())
                    await self.handle_request(request)
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing request: {e}", exc_info=True)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python python_mcp_server.py <agent_type>", file=sys.stderr)
        print("agent_type: architect, coder, tester, or debugger", file=sys.stderr)
        sys.exit(1)
    
    agent_type = sys.argv[1]
    server = PythonMCPServer(agent_type)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
