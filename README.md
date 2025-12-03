# MCP Multi-Agent Software Generation System

A sophisticated multi-agent system that leverages the Model Context Protocol (MCP) to automatically generate complete software applications from natural language descriptions and requirements.

## System Architecture

The system consists of four main components working in a coordinated pipeline:

### Frontend
- **UI Module**: Handles user input for software descriptions and requirements, displays generated code and API usage statistics

### Backend
- **MCP Handler**: Orchestrates the multi-agent workflow and coordinates agent communication
- **API Usage Tracker**: Monitors and tracks API token consumption across all agent operations

### Multi-Agent Pipeline

The system employs four specialized agents working sequentially:

1. **Agent A: Architect**
   - Analyzes software requirements
   - Designs file structure and architecture
   - Creates detailed architectural plans
   - Outputs: main.py, utils.py, test_data.py structure

2. **Agent B: Coder**
   - Receives architectural plans from Agent A
   - Generates executable code based on the architecture
   - Creates all necessary code files
   - Outputs: Complete code implementation

3. **Agent C: Tester/QA**
   - Receives code from Agent B
   - Generates comprehensive pytest test cases
   - Executes tests and analyzes results
   - Outputs: Test cases and execution reports

4. **Agent D: Debugger**
   - Receives code and test results from Agent C
   - Analyzes failures and identifies issues
   - Debugs and fixes code problems
   - Verifies fixes and prepares final package
   - Outputs: Production-ready code package

### Server
- **Local Server**: Executes generated code in isolated workspace, manages code packages, and returns results to UI

## Project Structure

```
AICoder/
├── frontend/
│   ├── __init__.py
│   └── ui.py                      # User interface module
├── backend/
│   ├── __init__.py
│   ├── mcp_handler.py             # Agent orchestration
│   └── api_usage_tracker.py       # Token usage tracking
├── agents/
│   ├── __init__.py
│   ├── agent_architect.py         # Agent A: Architecture design
│   ├── agent_coder.py             # Agent B: Code generation
│   ├── agent_tester.py            # Agent C: Testing & QA
│   └── agent_debugger.py          # Agent D: Debugging
├── server/
│   ├── __init__.py
│   └── local_server.py            # Code execution server
├── utils/
│   ├── __init__.py
│   ├── mcp_client.py              # MCP protocol client
│   └── file_manager.py            # File operations utility
├── config/
│   ├── __init__.py
│   └── settings.py                # Configuration settings
├── tests/
│   ├── __init__.py
│   ├── test_agents.py             # Agent unit tests
│   └── test_backend.py            # Backend unit tests
├── main.py                        # Application entry point
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules
└── README.md                      # This file
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/89lorry/AICoder.git
cd AICoder
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
copy .env.example .env
# Edit .env with your MCP API credentials
```

## Configuration

Edit the `.env` file with your settings:

- `MCP_API_KEY`: Your MCP API key
- `MCP_ENDPOINT`: MCP API endpoint URL
- `WORKSPACE_DIR`: Directory for generated code workspace
- `OUTPUT_DIR`: Directory for final output
- `UI_PORT`: UI server port (default: 8000)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

## Usage

Run the main application:
```bash
python main.py
```

The system will:
1. Prompt you for software description and requirements
2. Process your request through the agent pipeline
3. Generate complete software with tests
4. Display the generated code and API usage statistics

## Agent Workflow

```
User Input → UI → MCP Handler → Agent A (Architect) 
                                      ↓
                                Agent B (Coder)
                                      ↓
                                Agent C (Tester)
                                      ↓
                                Agent D (Debugger)
                                      ↓
                                Local Server → UI → User
```

## Testing

Run the test suite:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=. tests/
```

## Development

The project follows a modular architecture with clear separation of concerns:

- **Frontend**: User interaction layer
- **Backend**: Business logic and orchestration
- **Agents**: Specialized AI agents for different tasks
- **Server**: Code execution environment
- **Utils**: Shared utilities and helpers
- **Config**: Configuration management

## API Usage Tracking

The system automatically tracks API token usage for each agent. Usage statistics are:
- Displayed in the UI after each run
- Saved to `api_usage.json` for historical analysis
- Available through the `APIUsageTracker` class

## Frontend UI (Gradio)

`frontend/ui.py` provides a simple single-page Gradio interface that:
- Accepts a software description and free-form requirements
- Runs the existing backend workflow (`backend/mcp_handler.py`)
- Displays generated application code and test code
- Shows API usage stats from `backend/api_usage_tracker.py`
- Supports clearing inputs/outputs

### Run the UI

```bash
python -m frontend.ui
```

Open the browser at `http://localhost:8000`.

### Use the real MCP API

Option A: via `.env` (recommended)
```
MCP_API_KEY=your_real_key
MCP_ENDPOINT=your_endpoint_url   # optional if default works
```
Then:
```bash
python -m frontend.ui
```

Option B: one-off environment variables
```bash
cd /Users/fay/Documents/AICoder
MCP_API_KEY='your_real_key' python -m frontend.ui
# Optional custom port / endpoint:
# GRADIO_SERVER_PORT=7860 MCP_API_KEY='your_real_key' MCP_ENDPOINT='https://your-endpoint' python -m frontend.ui
```

### Troubleshooting
- Port 8000 is in use:
  ```bash
  lsof -iTCP:8000 -sTCP:LISTEN -n -P
  kill -9 <PID>
  ```
  Or start with a different port using `GRADIO_SERVER_PORT=7860`.

Notes:
- The UI integrates directly with the existing backend; no new wrappers, tools, or memory logic are introduced.
- Ensure `MCP_API_KEY` is set; otherwise the backend will raise “MCP API key is not configured.”

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with the Model Context Protocol (MCP)
- Powered by advanced AI agents for software generation
- Inspired by modern multi-agent AI systems
