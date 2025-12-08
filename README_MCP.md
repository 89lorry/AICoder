# AICoder - Multi-Agent Code Generation System

A sophisticated multi-agent system with **dual-mode operation**: traditional direct Python calls OR true Model Context Protocol (MCP) with JSON-RPC communication to automatically generate complete, tested software applications from natural language descriptions.

## ✨ Features

- 🤖 **Four Specialized AI Agents**: Architect, Coder, Tester, and Debugger working in sequence
- 🔗 **True MCP Protocol Support**: JSON-RPC 2.0 over stdio for standards-compliant agent communication
- 🔄 **Dual Mode Operation**: Choose between direct Python calls or MCP protocol
- 🌐 **Dual Interface**: CLI and web-based Gradio UI (both support MCP mode)
- ✅ **Automated Testing**: Generates and runs pytest test cases automatically
- 🐛 **Smart Debugging**: Automatically fixes failing tests with iterative retry
- 📊 **API Usage Tracking**: Session-based token consumption monitoring
- ⚡ **Rate Limiting**: Built-in rate limiting for API stability
- 🔄 **Feedback Loop**: Debugger iterates until all tests pass

## 🏗️ Architecture Modes

### Traditional Mode (Direct Python Calls)
```
WorkflowOrchestrator
    ├── Direct Method Calls → AgentArchitect
    ├── Direct Method Calls → AgentCoder
    ├── Direct Method Calls → AgentTester
    └── Direct Method Calls → AgentDebugger
```

### MCP Mode ⭐ NEW (JSON-RPC Protocol)
```
MCPOrchestrator (Client)
    ├── JSON-RPC/stdio → Architect MCP Server
    ├── JSON-RPC/stdio → Coder MCP Server
    ├── JSON-RPC/stdio → Tester MCP Server
    └── JSON-RPC/stdio → Debugger MCP Server
```

## 💻 Usage Modes

### Mode 1: Traditional CLI (Default)

Direct Python method calls:

```bash
python main.py
```

### Mode 2: MCP CLI ⭐ NEW

True Model Context Protocol with JSON-RPC:

```bash
python main.py --mcp
```

**MCP Features:**
- ✅ Standards-compliant JSON-RPC 2.0 protocol
- ✅ Stdio transport layer
- ✅ Process isolation (each agent = separate process)
- ✅ Tool-based architecture
- ✅ Follows official MCP specification

### Mode 3: Traditional Web UI

Gradio interface with direct Python calls:

```bash
python main.py --ui                    # Local only
python main.py --ui --share           # With public link
```

### Mode 4: MCP Web UI ⭐ NEW

Gradio interface with MCP protocol:

```bash
python main.py --ui --mcp             # Local with MCP
python main.py --ui --mcp --share     # Public link with MCP
```

UI shows mode indicator: "🔗 MCP Mode (JSON-RPC Protocol)" or "🔄 Direct Mode (Python Calls)"

## 📁 Project Structure

```
AICoder/
├── mcp_servers/                      # ⭐ NEW: MCP Server Implementation
│   └── python_mcp_server.py           # Unified Python MCP server for all agents
├── mcp_orchestrator/                  # ⭐ NEW: MCP Client
│   ├── __init__.py
│   └── orchestrator.py                 # JSON-RPC orchestrator
├── frontend/
│   ├── __init__.py
│   └── ui.py                           # Gradio UI (supports both modes)
├── backend/
│   ├── __init__.py
│   ├── mcp_handler.py                  # Legacy (unused)
│   └── api_usage_tracker.py
├── agents/                             # Original agent implementations
│   ├── __init__.py
│   ├── agent_architect.py
│   ├── agent_coder.py
│   ├── agent_tester.py
│   └── agent_debugger.py
├── server/
│   ├── __init__.py
│   └── local_server.py
├── utils/
│   ├── __init__.py
│   ├── mcp_client.py                   # LLM API client
│   ├── file_manager.py
│   ├── conversation_logger.py
│   ├── memory_manager.py
│   └── langchain_wrapper.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── logs/
│   └── conversations/
├── workspace/
├── tests/
├── workflow_orchestrator.py            # Traditional orchestrator
├── main.py                             # Entry point (supports all modes)
├── requirements.txt
├── IMPLEMENTATION_PLAN.md              # ⭐ NEW: MCP implementation details
├── MCP_IMPLEMENTATION_STATUS.md        # ⭐ NEW: Current status
└── README.md
```

## 🚀 Installation

### 1. Clone Repository
```bash
git clone https://github.com/89lorry/AICoder.git
cd AICoder
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
# Copy example
copy .env.example .env           # Windows
cp .env.example .env              # Linux/Mac

# Edit .env and add your API key
```

## ⚙️ Configuration

Edit `.env` file:

```env
# Required
MCP_API_KEY=your_api_key_here

# Optional
MCP_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent
WORKSPACE_DIR=./workspace
LOG_LEVEL=INFO
UI_HOST=localhost
UI_PORT=8000
TRACK_API_USAGE=true
ENABLE_MEMORY=false
```

## 🎯 Quick Start Examples

### Example 1: Traditional CLI
```bash
python main.py
# Uses default contact management requirements
# Direct Python method calls between agents
```

### Example 2: MCP CLI
```bash
python main.py --mcp
# Uses MCP protocol
# Agents communicate via JSON-RPC over stdio
```

### Example 3: UI with Custom Requirements
```bash
python main.py --ui
# Open http://localhost:8000
# Enter: "Create a todo list app"
# Click: "Generate Code & Tests"
```

### Example 4: MCP UI Mode
```bash
python main.py --ui --mcp
# Opens UI with MCP mode enabled
# Header shows: "🔗 MCP Mode (JSON-RPC Protocol)"
```

## 🔧 MCP Technical Details

### MCP Server

**File**: `mcp_servers/python_mcp_server.py`

**Features:**
- Wraps existing agent classes
- Exposes 6 tools via JSON-RPC:
  - `create_architecture` (Architect)
  - `generate_code` (Coder)
  - `generate_tests` (Tester)
  - `run_tests` (Tester)
  - `fix_code` (Debugger)
- Handles initialize/tools/list/tools/call requests
- Windows and Unix compatible

**Usage:**
```bash
python mcp_servers/python_mcp_server.py architect
python mcp_servers/python_mcp_server.py coder
python mcp_servers/python_mcp_server.py tester
python mcp_servers/python_mcp_server.py debugger
```

### MCP Orchestrator

**File**: `mcp_orchestrator/orchestrator.py`

**Features:**
- Async Python client
- Connects to multiple MCP servers
- JSON-RPC 2.0 protocol
- Stdio transport
- Timeout handling (120s per request)
- Enhanced error reporting

## 📊 Comparison: Traditional vs MCP Mode

| Feature | Traditional Mode | MCP Mode |
|---------|-----------------|----------|
| **Communication** | Direct Python calls | JSON-RPC over stdio |
| **Process Model** | Single process | Multi-process |
| **Isolation** | No | Yes |
| **Standards** | Custom | MCP specification |
| **Reusability** | Internal only | Can be used by other MCP clients |
| **Debugging** | Python debugger | Process logs + JSON-RPC traces |
| **Performance** | Faster | Slight overhead (process communication) |
| **Flexibility** | Python only | Can rewrite agents in any language |

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=. tests/

# Verbose
pytest -v tests/
```

## 🐛 Troubleshooting

### MCP Mode Issues

**Server not responding:**
```bash
# Check if Python can be found
python --version

# Check server file exists
ls mcp_servers/python_mcp_server.py

# Run server manually to see errors
python mcp_servers/python_mcp_server.py architect
```

**JSON parsing errors:**
- Check stderr output in logs
- Server may be outputting non-JSON to stdout
- Verify no print() statements in agent code going to stdout

### Port Already in Use

**Windows:**
```cmd
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Linux/Mac:**
```bash
lsof -iTCP:8000 -sTCP:LISTEN -n -P
kill -9 <PID>
```

### API Key Issues

```
⚠️  WARNING: MCP_API_KEY not set
```

**Solution:**
1. Create `.env` from `.env.example`
2. Add: `MCP_API_KEY=your_key_here`
3. Restart application

## 📝 Generated Code Structure

```
workspace/code_project/
├── main.py              # Main application
├── utils.py             # Helper functions
├── test_data.py         # Sample data
├── README.md            # Documentation
└── test_main.py         # Pytest tests
```

## 🎓 Learning More

- **MCP Documentation**: `IMPLEMENTATION_PLAN.md`
- **Implementation Status**: `MCP_IMPLEMENTATION_STATUS.md`
- **Agent Logs**: `logs/conversations/`
- **MCP Specification**: https://modelcontextprotocol.io/

## 🤝 Contributing

Contributions welcome! Areas of interest:
- Additional MCP servers
- Performance optimization
- New agent capabilities
- UI enhancements
- Testing improvements

## 📜 License

MIT License - see LICENSE file

## 🙏 Acknowledgments

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) - Standards-compliant agent communication
- [Gradio](https://gradio.app/) - Web UI framework
- [pytest](https://pytest.org/) - Testing framework
- Google's Gemini 1.5 Flash API - LLM backend

---

**Made with ❤️ by the AICoder Team**

**NEW**: Now with true MCP protocol support! 🔗
