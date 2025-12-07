# AICoder - Multi-Agent Code Generation System

A sophisticated multi-agent system that leverages the Model Context Protocol (MCP) to automatically generate complete, tested software applications from natural language descriptions.

## ✨ Features

- 🤖 **Four Specialized AI Agents**: Architect, Coder, Tester, and Debugger working in sequence
- 🌐 **Dual Interface**: CLI and web-based Gradio UI
- ✅ **Automated Testing**: Generates and runs pytest test cases automatically
- 🐛 **Smart Debugging**: Automatically fixes failing tests with iterative retry
- 📊 **API Usage Tracking**: Session-based token consumption monitoring
- ⚡ **Rate Limiting**: Built-in rate limiting for API stability
- 🔄 **Feedback Loop**: Debugger iterates until all tests pass

## 🏗️ System Architecture

### Agent Pipeline

```
User Input → Architect → Coder → Tester → [if fail] → Debugger → Output
              ↓           ↓        ↓                      ↓
          Design        Code    Tests                 Fixes
```

**Workflow:**

1. **Agent A: Architect**
   - Analyzes requirements and designs system architecture
   - Creates detailed component specifications
   - Outputs: File structure plan (main.py, utils.py, test_data.py, README.md)

2. **Agent B: Coder**
   - Receives architectural plan from Architect
   - Generates complete, executable code
   - Outputs: All application files with full implementation

3. **Agent C: Tester**
   - Receives code from Coder
   - Generates comprehensive pytest test cases
   - Executes tests and analyzes results
   - Outputs: Test file and execution report

4. **Agent D: Debugger**
   - Activates only if tests fail
   - Analyzes failures and fixes code/tests
   - Retries until tests pass (max 5 attempts)
   - Outputs: Production-ready, tested code

## 📁 Project Structure

```
AICoder/
├── frontend/
│   ├── __init__.py
│   └── ui.py                      # Gradio web interface
├── backend/
│   ├── __init__.py
│   ├── mcp_handler.py             # Legacy handler (unused)
│   └── api_usage_tracker.py       # Session-based token tracking
├── agents/
│   ├── __init__.py
│   ├── agent_architect.py         # Agent A: Architecture design
│   ├── agent_coder.py             # Agent B: Code generation
│   ├── agent_tester.py            # Agent C: Testing & QA
│   └── agent_debugger.py          # Agent D: Debugging & fixing
├── server/
│   ├── __init__.py
│   └── local_server.py            # Isolated code execution
├── utils/
│   ├── __init__.py
│   ├── mcp_client.py              # MCP API client
│   ├── file_manager.py            # File operations
│   ├── conversation_logger.py     # Agent conversation logging
│   ├── memory_manager.py          # Optional LangChain memory
│   └── langchain_wrapper.py       # LangChain integration
├── config/
│   ├── __init__.py
│   └── settings.py                # Configuration management
├── logs/
│   └── conversations/             # Agent conversation logs
├── workspace/                     # Generated code workspace
├── tests/
│   ├── __init__.py
│   ├── test_agents.py
│   └── test_backend.py
├── workflow_orchestrator.py       # Main workflow controller
├── main.py                        # Application entry point
├── requirements.txt               # Python dependencies
├── pytest.ini                     # Pytest configuration
├── .env.example                   # Environment template
├── .gitignore
└── README.md
```

## 🚀 Installation

### 1. Clone the Repository
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
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env

# Edit .env with your MCP API key
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

## 💻 Usage

### CLI Mode (Default)

Run the application in command-line mode:

```bash
python main.py
```

The system will:
1. Use predefined requirements (contact management system)
2. Execute the full agent pipeline
3. Display results and API usage in terminal

### Web UI Mode (Recommended)

Launch the Gradio web interface:

```bash
# Local access only
python main.py --ui

# With public sharing link
python main.py --ui --share
```

Then open your browser to `http://localhost:8000`

**UI Features:**
- 📝 Input software description and requirements
- ⚡ Real-time code generation with progress indicator
- 📂 Browse generated application and test files
- 📊 View session API usage (calls and tokens)
- 🎯 Token usage progress bar

## 📊 API Usage Tracking

The system tracks API usage **per session**:

- **Session-based**: Resets to 0 each time you start the application
- **Real-time**: Updates after each generation
- **Persistent Log**: Saves to `api_usage.json` for history
- **UI Display**: Shows calls and tokens used in current session

Example output:
```
API Calls: 4  |  Total Tokens: 12,543
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=. tests/

# Verbose output
pytest -v tests/
```

## 🎯 Example Workflow

### Using Web UI:

1. Start UI: `python main.py --ui`
2. Enter description: "I need a calculator app"
3. Add requirements:
   ```
   - Support +, -, *, / operations
   - Handle division by zero
   - Interactive CLI interface
   ```
4. Click "Generate Code & Tests"
5. View generated files (main.py, utils.py, test_main.py, etc.)
6. Check API usage statistics

### Using CLI:

1. Run: `python main.py`
2. System uses default requirements (contact management)
3. Watch agent pipeline execute
4. View results in terminal
5. Generated code saved to `./workspace/code_project/`

## 🔧 Development

### Architecture Highlights

- **WorkflowOrchestrator**: Coordinates agent pipeline with rate limiting
- **Session Management**: Each agent has unique session ID for logging
- **Rate Limiting**: 6-second delay between API calls (10 RPM limit)
- **Retry Logic**: Debugger attempts up to 5 fixes
- **Isolated Execution**: Code runs in dedicated workspace directories

### Key Components

| Component | Purpose |
|-----------|---------|
| `workflow_orchestrator.py` | Main pipeline controller |
| `agents/agent_*.py` | Specialized AI agents |
| `frontend/ui.py` | Gradio web interface |
| `backend/api_usage_tracker.py` | Token monitoring |
| `server/local_server.py` | Code execution sandbox |
| `utils/mcp_client.py` | MCP API wrapper |

## 🐛 Troubleshooting

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

Or use a different port:
```bash
UI_PORT=7860 python main.py --ui
```

### MCP API Key Not Set

```
⚠️  WARNING: MCP_API_KEY not set in environment variables
```

**Solution:**
1. Create `.env` from `.env.example`
2. Add your API key: `MCP_API_KEY=your_key_here`
3. Restart the application

### Tests Failing After Generation

The system automatically handles this:
- Debugger analyzes failures
- Fixes code and/or tests
- Retries up to 5 times
- Reports success or final failure

## 📝 Generated Code Structure

Each generation creates:

```
workspace/code_project/
├── main.py              # Main application logic
├── utils.py             # Helper functions/classes
├── test_data.py         # Sample data for testing
├── README.md            # Project documentation
└── test_main.py         # Pytest test cases
```

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- UI powered by [Gradio](https://gradio.app/)
- Testing with [pytest](https://pytest.org/)
- Powered by Google's Gemini 1.5 Flash API

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review logs in `./logs/` directory

---

**Made with ❤️ by the AICoder Team**
