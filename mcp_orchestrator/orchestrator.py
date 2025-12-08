# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

"""
MCP Orchestrator
Coordinates multiple MCP servers via JSON-RPC protocol over stdio
"""

import asyncio
import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional
import uuid


class MCPOrchestrator:
    """
    Orchestrates workflow across multiple MCP servers using JSON-RPC protocol
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.servers: Dict[str, Dict[str, Any]] = {}
        self.session_id = uuid.uuid4().hex
        
    async def connect_server(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """
        Connect to an MCP server via stdio
        
        Args:
            name: Server name (e.g., 'architect')
            command: Command to start server (e.g., 'node')
            args: Command arguments (e.g., ['path/to/server.js'])
            env: Optional environment variables
        """
        self.logger.info(f"Connecting to {name} MCP server...")
        
        # Prepare environment
        server_env = os.environ.copy()
        if env:
            server_env.update(env)
        
        # Start server process
        process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=server_env
        )
        
        self.servers[name] = {
            'process': process,
            'request_id': 0
        }
        
        # Initialize the connection
        await self._send_initialize(name)
        self.logger.info(f"Connected to {name} MCP server")
        
    async def _send_initialize(self, server_name: str):
        """Send initialize request to MCP server"""
        init_request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(server_name),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    }
                },
                "clientInfo": {
                    "name": "AICoder-MCP-Orchestrator",
                    "version": "1.0.0"
                }
            }
        }
        
        response = await self._send_request(server_name, init_request)
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        await self._send_notification(server_name, initialized_notification)
        
        return response
        
    def _get_next_id(self, server_name: str) -> int:
        """Get next request ID for a server"""
        self.servers[server_name]['request_id'] += 1
        return self.servers[server_name]['request_id']
        
    async def _send_request(self, server_name: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request to server and wait for response"""
        server = self.servers[server_name]
        process = server['process']
        
        # Send request
        request_str = json.dumps(request) + '\n'
        process.stdin.write(request_str.encode())
        await process.stdin.drain()
        
        # Read response with timeout
        try:
            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=120.0)
        except asyncio.TimeoutError:
            # Check stderr for errors
            stderr_output = await process.stderr.read(1000)
            self.logger.error(f"Timeout waiting for response from {server_name}")
            self.logger.error(f"Server stderr: {stderr_output.decode()}")
            raise RuntimeError(f"Timeout waiting for response from {server_name} server")
        
        if not response_line:
            # Check stderr for errors
            stderr_output = await process.stderr.read(1000)
            self.logger.error(f"No response from {server_name}")
            self.logger.error(f"Server stderr: {stderr_output.decode()}")
            raise RuntimeError(f"No response from {server_name} server")
        
        response_text = response_line.decode().strip()
        self.logger.debug(f"Response from {server_name}: {response_text[:200]}")
        
        try:
            response = json.loads(response_text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON from {server_name}: {response_text[:500]}")
            # Try to read stderr for additional context
            stderr_output = await process.stderr.read(1000)
            self.logger.error(f"Server stderr: {stderr_output.decode()}")
            raise RuntimeError(f"Invalid JSON response from {server_name}: {str(e)}")
        
        if 'error' in response:
            raise RuntimeError(f"Server error: {response['error']}")
            
        return response
        
    async def _send_notification(self, server_name: str, notification: Dict[str, Any]):
        """Send JSON-RPC notification (no response expected)"""
        server = self.servers[server_name]
        process = server['process']
        
        notification_str = json.dumps(notification) + '\n'
        process.stdin.write(notification_str.encode())
        await process.stdin.drain()
        
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on an MCP server
        
        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        self.logger.info(f"Calling tool '{tool_name}' on {server_name} server...")
        
        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(server_name),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = await self._send_request(server_name, request)
        
        if 'result' in response:
            result = response['result']
            if 'content' in result and len(result['content']) > 0:
                # Extract text from first content item
                content_item = result['content'][0]
                if content_item.get('type') == 'text':
                    return content_item.get('text')
            return result
        
        return None
        
    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """List available tools from an MCP server"""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(server_name),
            "method": "tools/list",
            "params": {}
        }
        
        response = await self._send_request(server_name, request)
        
        if 'result' in response and 'tools' in response['result']:
            return response['result']['tools']
        return []
        
    async def disconnect_server(self, server_name: str):
        """Disconnect from an MCP server"""
        if server_name in self.servers:
            self.logger.info(f"Disconnecting from {server_name} server...")
            server = self.servers[server_name]
            process = server['process']
            
            try:
                process.stdin.close()
                await process.wait()
            except Exception as e:
                self.logger.warning(f"Error disconnecting from {server_name}: {e}")
                process.kill()
                
            del self.servers[server_name]
            
    async def disconnect_all(self):
        """Disconnect from all MCP servers"""
        for server_name in list(self.servers.keys()):
            await self.disconnect_server(server_name)
            
    async def run_workflow(self, requirements: str, max_debug_attempts: int = 5) -> Dict[str, Any]:
        """
        Run the complete agent workflow using MCP protocol
        
        Args:
            requirements: Software requirements
            max_debug_attempts: Maximum debugging attempts
            
        Returns:
            Workflow results
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting MCP Workflow (Full Implementation)")
        self.logger.info("=" * 60)
        
        result = {
            "final_status": "failed",
            "architectural_plan": None,
            "code_package": None,
            "test_results": None,
            "debugger_fixed": False
        }
        
        try:
            # Python MCP server path
            python_server = os.path.join(
                os.getcwd(),
                "mcp_servers",
                "python_mcp_server.py"
            )
            
            # Environment for all servers
            server_env = {
                'MCP_API_KEY': os.getenv('MCP_API_KEY', ''),
                'MCP_ENDPOINT': os.getenv('MCP_ENDPOINT', ''),
                'PYTHONPATH': os.getcwd()
            }
            
            # Step 1: Connect to all agent servers
            self.logger.info("\n[Setup] Connecting to all MCP servers...")
            
            await self.connect_server(
                name='architect',
                command='python',
                args=[python_server, 'architect'],
                env=server_env
            )
            self.logger.info("✓ Architect server connected")
            
            await self.connect_server(
                name='coder',
                command='python',
                args=[python_server, 'coder'],
                env=server_env
            )
            self.logger.info("✓ Coder server connected")
            
            await self.connect_server(
                name='tester',
                command='python',
                args=[python_server, 'tester'],
                env=server_env
            )
            self.logger.info("✓ Tester server connected")
            
            await self.connect_server(
                name='debugger',
                command='python',
                args=[python_server, 'debugger'],
                env=server_env
            )
            self.logger.info("✓ Debugger server connected")
            
            # Step 2: Architect - Create architecture
            self.logger.info("\n[Step 1] Architect: Creating architecture via MCP...")
            arch_result = await self.call_tool(
                server_name='architect',
                tool_name='create_architecture',
                arguments={'requirements': requirements}
            )
            
            architectural_plan = json.loads(arch_result) if isinstance(arch_result, str) else arch_result
            result['architectural_plan'] = architectural_plan
            self.logger.info("✅ Architecture created successfully")
            
            # Step 3: Coder - Generate code
            self.logger.info("\n[Step 2] Coder: Generating code via MCP...")
            code_result = await self.call_tool(
                server_name='coder',
                tool_name='generate_code',
                arguments={'architectural_plan': architectural_plan}
            )
            
            code_package = json.loads(code_result) if isinstance(code_result, str) else code_result
            result['code_package'] = code_package
            self.logger.info("✅ Code generated successfully")
            
            # Step 4: Tester - Generate tests
            self.logger.info("\n[Step 3] Tester: Generating tests via MCP...")
            test_gen_result = await self.call_tool(
                server_name='tester',
                tool_name='generate_tests',
                arguments={'code_package': code_package}
            )
            
            test_info = json.loads(test_gen_result) if isinstance(test_gen_result, str) else test_gen_result
            self.logger.info("✅ Tests generated successfully")
            
            # Step 5: Tester - Run tests
            self.logger.info("\n[Step 4] Tester: Running tests via MCP...")
            test_run_result = await self.call_tool(
                server_name='tester',
                tool_name='run_tests',
                arguments={'test_file': 'test_main.py'}
            )
            
            test_results = json.loads(test_run_result) if isinstance(test_run_result, str) else test_run_result
            result['test_results'] = test_results
            
            # Check if tests passed
            if test_results.get('passed', False):
                self.logger.info("✅ All tests passed!")
                result['final_status'] = 'success'
            else:
                # Step 6: Debugger - Fix failing code
                self.logger.info("\n⚠️  Tests failed. Starting debugger via MCP...")
                self.logger.info(f"Test Results:")
                self.logger.info(f"  Exit Code: {test_results.get('exit_code', 'N/A')}")
                self.logger.info(f"  Passed: {test_results.get('passed', False)}")
                if test_results.get('output'):
                    self.logger.info(f"\nTest Output:")
                    for line in test_results['output'].split('\n')[:20]:  # Show first 20 lines
                        self.logger.info(f"  {line}")
                
                test_package = {
                    'code_package': code_package,
                    'test_results': test_results,
                    'test_file_path': test_info.get('test_file_path', 'test_main.py')
                }
                
                debug_result_str = await self.call_tool(
                    server_name='debugger',
                    tool_name='fix_code',
                    arguments={'test_package': test_package}
                )
                
                debug_result = json.loads(debug_result_str) if isinstance(debug_result_str, str) else debug_result_str
                result['debug_result'] = debug_result
                result['debugger_fixed'] = True
                
                # Display detailed debugger results
                if debug_result.get('attempts'):
                    self.logger.info(f"\n🔧 Debugger Iterations:")
                    for i, attempt in enumerate(debug_result['attempts'], 1):
                        self.logger.info(f"\n  Iteration {i}:")
                        self.logger.info(f"    Tests Passed: {attempt.get('tests_passed', False)}")
                        if attempt.get('test_results'):
                            tr = attempt['test_results']
                            self.logger.info(f"    Exit Code: {tr.get('exit_code', 'N/A')}")
                            if tr.get('output'):
                                self.logger.info(f"    Output Preview:")
                                for line in tr['output'].split('\n')[:10]:  # First 10 lines
                                    self.logger.info(f"      {line}")
                
                if debug_result.get('success', False):
                    self.logger.info(f"\n✅ Debugger fixed code after {len(debug_result.get('attempts', []))} attempts")
                    result['final_status'] = 'success'
                    
                    # Show final test results
                    if debug_result.get('attempts'):
                        final_attempt = debug_result['attempts'][-1]
                        if final_attempt.get('test_results'):
                            self.logger.info(f"\n📊 Final Test Results:")
                            tr = final_attempt['test_results']
                            self.logger.info(f"  Status: PASSED ✓")
                            self.logger.info(f"  Exit Code: {tr.get('exit_code', 0)}")
                else:
                    self.logger.warning(f"\n⚠️  Tests still failing after {len(debug_result.get('attempts', []))} attempts")
                    result['final_status'] = 'failed'
            
        except Exception as e:
            self.logger.error(f"Error in MCP workflow: {str(e)}")
            result['final_status'] = 'error'
            result['error'] = str(e)
            import traceback
            result['traceback'] = traceback.format_exc()
            
        finally:
            # Cleanup: disconnect from all servers
            await self.disconnect_all()
            
        self.logger.info(f"\n{'=' * 60}")
        self.logger.info(f"MCP Workflow Complete: {result['final_status'].upper()}")
        self.logger.info(f"{'=' * 60}")
        
        return result


async def main():
    """Example usage of MCP Orchestrator"""
    logging.basicConfig(level=logging.INFO)
    
    orchestrator = MCPOrchestrator()
    
    requirements = """
I need a simple calculator application that can:
- Add two numbers
- Subtract two numbers
- Multiply two numbers
- Divide two numbers (with zero check)
"""
    
    result = await orchestrator.run_workflow(requirements)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
