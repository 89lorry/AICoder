# Full MCP Implementation Plan

## Overview
Convert the AICoder multi-agent system to use true MCP (Model Context Protocol) for inter-agent communication.

## Current Architecture (Before)
```
WorkflowOrchestrator
    ├── Direct Python method calls to agents
    ├── AgentArchitect (Python class)
    ├── AgentCoder (Python class)
    ├── AgentTester (Python class)
    └── AgentDebugger (Python class)
```

## Target Architecture (After)
```
MCP Orchestrator (Client)
    ├── JSON-RPC over stdio →  Architect MCP Server
    ├── JSON-RPC over stdio →  Coder MCP Server
    ├── JSON-RPC over stdio →  Tester MCP Server
    └── JSON-RPC over stdio →  Debugger MCP Server
```

## Implementation Steps

### Phase 1: Infrastructure Setup
1. ✅ Create project structure for MCP servers
2. Install required dependencies (mcp SDK for Python)
3. Create base MCP server class with common functionality
4. Create MCP client orchestrator

### Phase 2: Convert Agents to MCP Servers
Each agent becomes a standalone MCP server exposing tools:

**Architect Server** exposes:
- Tool: `create_architecture` - Analyzes requirements and creates architectural plan

**Coder Server** exposes:
- Tool: `generate_code` - Generates code from architectural plan

**Tester Server** exposes:
- Tool: `generate_tests` - Creates test cases
- Tool: `run_tests` - Executes tests and returns results

**Debugger Server** exposes:
- Tool: `analyze_failures` - Analyzes test failures
- Tool: `fix_code` - Fixes failing code

### Phase 3: MCP Orchestrator
Create new orchestrator that:
1. Starts all agent MCP servers
2. Connects to each server via stdio
3. Coordinates workflow using MCP protocol (CallToolRequest)
4. Handles JSON-RPC communication

### Phase 4: Configuration & Integration
1. Update package.json for TypeScript/Node.js MCP servers
2. Create Python MCP servers using mcp library
3. Update main.py to use MCP orchestrator
4. Add MCP server configuration

### Phase 5: Testing & Validation
1. Test individual MCP server tools
2. Test complete workflow with MCP communication
3. Verify rate limiting works across MCP calls
4. Update documentation

## Technical Details

### MCP Server Structure
```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

class ArchitectMCPServer:
    def __init__(self):
        self.server = Server("architect-server")
        self.setup_tools()
    
    def setup_tools(self):
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="create_architecture",
                    description="Create system architecture from requirements",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "requirements": {"type": "string"}
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            if name == "create_architecture":
                result = await self.create_architecture(arguments["requirements"])
                return [TextContent(type="text", text=json.dumps(result))]
```

### MCP Orchestrator Structure
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPOrchestrator:
    async def connect_to_agent(self, agent_name: str, command: str, args: list):
        server_params = StdioServerParameters(
            command=command,
            args=args
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Call tools on this agent
                result = await session.call_tool(tool_name, arguments)
                return result
```

## Benefits of MCP Architecture

1. **True Decoupling**: Agents run as separate processes
2. **Language Agnostic**: Can implement agents in different languages
3. **Scalability**: Can distribute agents across machines
4. **Standard Protocol**: Uses JSON-RPC standard
5. **Reusability**: Agents can be used by other MCP clients
6. **Security**: Process isolation between agents

## Dependencies Required

```json
// For TypeScript MCP servers
{
  "@modelcontextprotocol/sdk": "^0.5.0"
}
```

```txt
# For Python MCP servers
mcp>=0.1.0
```

## File Structure After Implementation

```
AICoder/
├── mcp_servers/                    # New directory
│   ├── architect_server/
│   │   ├── src/
│   │   │   └── index.ts           # Architect MCP server
│   │   ├── package.json
│   │   └── tsconfig.json
│   ├── coder_server/
│   │   ├── src/
│   │   │   └── index.ts           # Coder MCP server
│   │   ├── package.json
│   │   └── tsconfig.json
│   ├── tester_server/
│   │   ├── src/
│   │   │   └── index.ts           # Tester MCP server
│   │   ├── package.json
│   │   └── tsconfig.json
│   └── debugger_server/
│       ├── src/
│       │   └── index.ts           # Debugger MCP server
│       ├── package.json
│       └── tsconfig.json
├── mcp_orchestrator/               # New orchestrator
│   ├── __init__.py
│   └── orchestrator.py            # MCP client orchestrator
├── agents/                         # Keep for backward compatibility
│   └── (existing agent classes)
└── (existing files)
```
