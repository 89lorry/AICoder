# AICoder MCP Mode Architecture

**Project Group 3**
- Peter Xie (28573670)
- Xin Tang (79554618)
- Keyan Miao (42708776)
- Keyi Feng (84254877)

## Overview

AICoder implements true **Model Context Protocol (MCP)** using JSON-RPC 2.0 over stdio for agent communication. This document provides a comprehensive description of the MCP mode architecture and how agent-related components work together.

---

## Architecture Comparison

### Traditional Mode (Direct Calls)
```
┌─────────────────────────────────────┐
│   Single Python Process             │
│                                     │
│   ┌───────────────────────┐         │
│   │ WorkflowOrchestrator  │         │
│   └───────────┬───────────┘         │
│               │                     │
│       ┌───────┼───────┬────────┐    │
│       ▼       ▼       ▼        ▼    │
│   ┌────┐  ┌────┐  ┌────┐  ┌────┐   │
│   │ A  │  │ B  │  │ C  │  │ D  │   │
│   └────┘  └────┘  └────┘  └────┘   │
│  Architect Coder Tester Debugger   │
│                                     │
│   (Direct Python function calls)    │
└─────────────────────────────────────┘
```

### MCP Mode (Process Isolation)
```
┌─────────────────────────────────────────────────────────────┐
│   Main Process                                               │
│   ┌───────────────────────┐                                 │
│   │  MCPOrchestrator      │                                 │
│   │  (Client)             │                                 │
│   └───────┬───────────────┘                                 │
│           │                                                  │
│           │ JSON-RPC 2.0 over stdio                         │
│           │                                                  │
│   ┌───────┼───────────┬────────────┬────────────┐          │
│   │       │           │            │            │          │
└───┼───────┼───────────┼────────────┼────────────┼──────────┘
    ▼       ▼           ▼            ▼            ▼
┌────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
│Process1│ │Process2 │ │Process3 │ │Process4  │ │   File   │
│        │ │         │ │         │ │          │ │  System  │
│ MCP    │ │  MCP    │ │  MCP    │ │   MCP    │ │          │
│Server  │ │ Server  │ │ Server  │ │  Server  │ │api_usage │
│        │ │         │ │         │ │          │ │  .json   │
│  ┌─┐   │ │   ┌─┐   │ │   ┌─┐   │ │   ┌─┐    │ │          │
│  │A│   │ │   │B│   │ │   │C│   │ │   │D│    │ │  Shared  │
│  └─┘   │ │   └─┘   │ │   └─┘   │ │   └─┘    │ │  State   │
└────────┘ └─────────┘ └─────────┘ └──────────┘ └──────────┘
```

---

## Core Components

### 1. MCPOrchestrator (`mcp_orchestrator/orchestrator.py`)

**Role**: Client that coordinates the workflow across multiple MCP server processes.

**Responsibilities**:
- Launch 4 separate MCP server processes (one per agent)
- Send JSON-RPC requests via stdin
- Receive JSON-RPC responses via stdout
- Manage workflow sequence (Architect → Coder → Tester → Debugger)
- Handle timeouts and errors
- Coordinate data passing between agents

**Key Methods**:
```python
async def connect_server(name, command, args, env)
    # Launches Python subprocess for each agent
    # Sets up stdin/stdout pipes
    # Initializes JSON-RPC connection

async def call_tool(server_name, tool_name, arguments)
    # Sends tool/call JSON-RPC request
    # Waits for response (with 300s timeout)
    # Returns parsed result

async def run_workflow(requirements)
    # Orchestrates complete workflow
    # 1. Connect to all 4 servers
    # 2. Call architect → coder → tester → (debugger if needed)
    # 3. Disconnect all servers
    # 4. Return final results
```

---

### 2. PythonMCPServer (`mcp_servers/python_mcp_server.py`)

**Role**: MCP server that wraps existing agent logic with JSON-RPC protocol.

**One instance runs per agent** (4 separate processes):
- `python python_mcp_server.py architect`
- `python python_mcp_server.py coder`
- `python python_mcp_server.py tester`
- `python python_mcp_server.py debugger`

**Architecture**:
```python
class PythonMCPServer:
    def __init__(self, agent_type):
        # Initialize components FRESH in each process
        self.mcp_client = MCPClient()              # API client
        self.api_tracker = APIUsageTracker()       # Token tracking
        self.local_server = LocalServer()          # Code execution
        
        # Initialize specific agent
        if agent_type == 'architect':
            self.agent = AgentArchitect(...)
        elif agent_type == 'coder':
            self.agent = AgentCoder(...)
        # ...
    
    async def handle_tool_call(self, request):
        # Extract tool name and arguments from JSON-RPC request
        # Route to appropriate agent method
        # Return JSON-RPC response with results
```

**JSON-RPC Protocol Example**:
```json
Request:
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_architecture",
    "arguments": {
      "requirements": "Create a calculator..."
    }
  }
}

Response:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"detailed_plan\": {...}, ...}"
    }]
  }
}
```

---

### 3. Agent Classes

Each agent class (`AgentArchitect`, `AgentCoder`, `AgentTester`, `AgentDebugger`) exists in **its own process** in MCP mode.

**Shared Components Per Agent**:
```python
# Each agent gets its own instance of:
- MCPClient()              # API communication
- APIUsageTracker()        # Token tracking  
- LocalServer()            # Code execution (coder/tester/debugger only)
- ConversationLogger()     # Conversation history
- MemoryManager()          # Optional memory (if enabled)
```

**Agent Workflow in MCP Mode**:
```
1. MCP Server receives tool call request
2. Server routes to agent method (e.g., architect.create_complete_architecture())
3. Agent calls LLM API via mcp_client
4. Agent tracks token usage via api_tracker.track_usage()
5. api_tracker writes to shared api_usage.json file
6. Agent returns result
7. Server wraps result in JSON-RPC response
8. Response sent back to orchestrator via stdout
```

---

## Communication Flow

### Step-by-Step Workflow

#### 1. Startup Phase
```
MCPOrchestrator.run_workflow()
    │
    ├─> subprocess: python python_mcp_server.py architect
    │       └─> AgentArchitect initialized in Process 1
    │
    ├─> subprocess: python python_mcp_server.py coder
    │       └─> AgentCoder initialized in Process 2
    │
    ├─> subprocess: python python_mcp_server.py tester
    │       └─> AgentTester initialized in Process 3
    │
    └─> subprocess: python python_mcp_server.py debugger
            └─> AgentDebugger initialized in Process 4
```

#### 2. Architect Phase
```
MCPOrchestrator
    │
    │ JSON-RPC Request via stdin
    │ {"method": "tools/call", "params": {"name": "create_architecture", ...}}
    ▼
PythonMCPServer (Process 1)
    │
    │ Route to agent method
    ▼
AgentArchitect.create_complete_architecture()
    │
    │ Call LLM API
    ▼
MCPClient.generate_content()
    │
    │ Track usage
    ▼
APIUsageTracker.track_usage("architect", tokens)
    │
    │ Write to file
    ▼
api_usage.json (Shared File)
    {
      "total_tokens": 1767,
      "usage_log": [
        {"agent": "architect", "tokens": 1767, ...}
      ]
    }
    │
    │ Return result
    ▼
MCPOrchestrator receives architectural plan
```

#### 3. Coder Phase
```
MCPOrchestrator
    │
    │ JSON-RPC Request with architectural_plan
    ▼
PythonMCPServer (Process 2)
    │
    ▼
AgentCoder.receive_architecture(plan)
AgentCoder.generate_code()
    │
    │ Track usage
    ▼
APIUsageTracker.track_usage("coder", tokens)
    │
    │ Merge with existing file
    ▼
api_usage.json (Shared File)
    {
      "total_tokens": 7867,  // 1767 + 6100
      "usage_log": [
        {"agent": "architect", "tokens": 1767},
        {"agent": "coder", "tokens": 6100}     // NEW
      ]
    }
```

#### 4. Tester Phase
```
Similar flow:
- Receives code_package from orchestrator
- Generates tests via LLM
- Runs tests via LocalServer
- Tracks tokens → api_usage.json
- Returns test results
```

#### 5. Debugger Phase (if tests fail)
```
MCPOrchestrator detects test failure
    │
    │ Send code + test_results to debugger
    ▼
AgentDebugger.analyze_and_fix_combined()
    │
    │ INTERNAL RETRY LOOP (up to 5 iterations)
    │
    ├─> Iteration 1:
    │   ├─> Call LLM to analyze errors
    │   ├─> Track tokens (iteration=1)
    │   ├─> Save fixed code
    │   ├─> Run tests
    │   └─> If fail, continue to iteration 2
    │
    ├─> Iteration 2:
    │   ├─> Track tokens (iteration=2)
    │   └─> ...
    │
    └─> Returns after success or max iterations

Each iteration writes to api_usage.json:
    {
      "usage_log": [
        ...
        {"agent": "debugger", "tokens": 14119, "iteration": 1},
        {"agent": "debugger", "tokens": 21103, "iteration": 2},
        {"agent": "debugger", "tokens": 78018, "iteration": 3}
      ]
    }
```

---

## Debugger Internal Loop: Deep Dive

The debugger agent implements a sophisticated **internal retry loop** that enables iterative code fixing without external orchestration. This is a key architectural decision that provides the debugger with "memory" of previous attempts.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  AgentDebugger.analyze_and_fix_combined()                       │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Internal Loop (max_fix_iterations = 5)                │     │
│  │                                                         │     │
│  │  all_attempts = []  ← Accumulates history             │     │
│  │                                                         │     │
│  │  for attempt in range(1, 6):                          │     │
│  │                                                         │     │
│  │    ┌──────────────────────────────────────┐           │     │
│  │    │ 1. Build Context with History        │           │     │
│  │    │    - Current failures                │           │     │
│  │    │    - Current code                    │           │     │
│  │    │    - Test output                     │           │     │
│  │    │    - Previous attempts summary ★     │           │     │
│  │    └──────────────────────────────────────┘           │     │
│  │              │                                         │     │
│  │              ▼                                         │     │
│  │    ┌──────────────────────────────────────┐           │     │
│  │    │ 2. Call LLM with Full Context        │           │     │
│  │    │    - Single combined prompt          │           │     │
│  │    │    - Analyze + Fix + Update Tests    │           │     │
│  │    └──────────────────────────────────────┘           │     │
│  │              │                                         │     │
│  │              ▼                                         │     │
│  │    ┌──────────────────────────────────────┐           │     │
│  │    │ 3. Parse Response                    │           │     │
│  │    │    - Extract ANALYSIS_START/END      │           │     │
│  │    │    - Extract FILE_START/END          │           │     │
│  │    └──────────────────────────────────────┘           │     │
│  │              │                                         │     │
│  │              ▼                                         │     │
│  │    ┌──────────────────────────────────────┐           │     │
│  │    │ 4. Apply Fixes & Run Tests           │           │     │
│  │    │    - Save to LocalServer             │           │     │
│  │    │    - Execute pytest                   │           │     │
│  │    └──────────────────────────────────────┘           │     │
│  │              │                                         │     │
│  │              ▼                                         │     │
│  │    ┌──────────────────────────────────────┐           │     │
│  │    │ 5. Store Attempt Result              │           │     │
│  │    │    all_attempts.append({             │           │     │
│  │    │      "attempt": N,                   │           │     │
│  │    │      "fixed_files": [...],           │           │     │
│  │    │      "test_passed": bool,            │           │     │
│  │    │      "test_output": "...",           │           │     │
│  │    │      "analysis": {...}               │           │     │
│  │    │    })                                 │           │     │
│  │    └──────────────────────────────────────┘           │     │
│  │              │                                         │     │
│  │              ▼                                         │     │
│  │         Tests Passed?                                 │     │
│  │         YES → Return Success                          │     │
│  │         NO  → Continue to next iteration              │     │
│  │                                                         │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                                  │
│  Return: {                                                      │
│    "success": bool,                                             │
│    "fixed_code": {...},                                         │
│    "attempts": all_attempts,                                    │
│    "final_test_results": {...}                                  │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

### The "Memory" Mechanism

The debugger achieves **learning from previous attempts** through an explicit feedback loop, NOT through LangChain's conversation memory. This is more effective for debugging because it provides structured, task-specific context.

#### Implementation (agent_debugger.py, lines 274-293)

```python
# Build summary of previous attempts if any
previous_attempts_summary = ""
if attempt > 1:
    previous_attempts_summary = "\n\n" + "="*60 + "\n"
    previous_attempts_summary += "PREVIOUS ATTEMPTS - LEARN FROM THESE!\n"
    previous_attempts_summary += "="*60 + "\n"
    
    for prev in all_attempts:
        previous_attempts_summary += f"\n--- Attempt {prev['attempt']} ---\n"
        
        # What files were changed
        if prev.get('fixed_files'):
            previous_attempts_summary += f"Files modified: {', '.join(prev.get('fixed_files', []))}\n"
        
        # Did tests pass?
        previous_attempts_summary += f"Test result: {'✓ PASSED' if prev.get('test_passed') else '✗ FAILED'}\n"
        
        # What were the test errors?
        if not prev.get('test_passed'):
            test_output_snippet = prev.get('test_output', 'Unknown')[:300]
            previous_attempts_summary += f"Test errors:\n{test_output_snippet}...\n"
        
        # What analysis was done?
        if 'analysis' in prev and 'summary' in prev['analysis']:
            analysis_snippet = prev['analysis']['summary'][:400]
            previous_attempts_summary += f"Analysis done:\n{analysis_snippet}...\n"
        
        # Were there any system errors?
        if 'error' in prev:
            previous_attempts_summary += f"Error encountered: {prev['error']}\n"
    
    # Critical warnings
    previous_attempts_summary += "\n" + "="*60 + "\n"
    previous_attempts_summary += "⚠️ CRITICAL: Review the above attempts carefully!\n"
    previous_attempts_summary += "⚠️ DO NOT repeat the same approach that failed!\n"
    previous_attempts_summary += "⚠️ Try a COMPLETELY DIFFERENT fix strategy!\n"
    previous_attempts_summary += "="*60 + "\n"
```

#### Injected into LLM Prompt (line 296)

```python
prompt = f"""You are debugging code that failed tests. Provide fixes as a structured response.
{previous_attempts_summary}  # ← INJECTED HISTORY

Test Failures:
{self._format_failures(failures)}

Current Code:
{self._format_code(code)}

Test Output (last 2000 chars):
{test_output[-2000:] if len(test_output) > 2000 else test_output}

Attempt: {attempt}/{self.max_fix_iterations}
...
"""
```

### Example: 3-Iteration Debugging Session

#### Iteration 1 (No History)
```
PROMPT:
  Test Failures:
    - test_main.py::test_contact_manager - UnboundLocalError
  
  Current Code:
    === main.py ===
    class ContactManager:
        def add_contact(self, name):
            ContactManager = MagicMock()  # ← BUG
    ...

RESPONSE:
  ANALYSIS_START
  - Issue 1: main.py - Variable reassignment causing UnboundLocalError
  ANALYSIS_END
  
  FILE_START: main.py
  class ContactManager:
      def add_contact(self, name):
          self.contacts.append(name)  # Fixed
  FILE_END

RESULT:
  ✗ Tests still fail (different error: AttributeError: 'ContactManager' has no attribute 'contacts')
  
STORED IN all_attempts[0]:
  {
    "attempt": 1,
    "fixed_files": ["main.py"],
    "test_passed": False,
    "test_output": "AttributeError: 'ContactManager' has no attribute 'contacts'",
    "analysis": {"summary": "Variable reassignment causing UnboundLocalError"}
  }
```

#### Iteration 2 (With History from Iteration 1)
```
PROMPT:
  ============================================================
  PREVIOUS ATTEMPTS - LEARN FROM THESE!
  ============================================================
  
  --- Attempt 1 ---
  Files modified: main.py
  Test result: ✗ FAILED
  Test errors:
  AttributeError: 'ContactManager' has no attribute 'contacts'
  Analysis done:
  - Issue 1: main.py - Variable reassignment causing UnboundLocalError
  
  ============================================================
  ⚠️ CRITICAL: Review the above attempts carefully!
  ⚠️ DO NOT repeat the same approach that failed!
  ⚠️ Try a COMPLETELY DIFFERENT fix strategy!
  ============================================================
  
  Test Failures:
    - test_main.py::test_contact_manager - AttributeError
  
  Current Code:
    === main.py ===
    class ContactManager:
        def add_contact(self, name):
            self.contacts.append(name)  # Previous fix
    ...

RESPONSE:
  ANALYSIS_START
  - Issue 1: main.py - Missing __init__ method to initialize contacts list
  - Previous attempt fixed variable reassignment but didn't initialize storage
  ANALYSIS_END
  
  FILE_START: main.py
  class ContactManager:
      def __init__(self):
          self.contacts = []  # Initialize list
      
      def add_contact(self, name):
          self.contacts.append(name)
  FILE_END

RESULT:
  ✗ Tests still fail (different error: Test expects save_contacts to be called)
  
STORED IN all_attempts[1]:
  {
    "attempt": 2,
    "fixed_files": ["main.py"],
    "test_passed": False,
    "test_output": "Expected 'save_contacts' to have been called once. Called 0 times.",
    "analysis": {"summary": "Missing __init__ method to initialize contacts list"}
  }
```

#### Iteration 3 (With History from Iterations 1 & 2)
```
PROMPT:
  ============================================================
  PREVIOUS ATTEMPTS - LEARN FROM THESE!
  ============================================================
  
  --- Attempt 1 ---
  Files modified: main.py
  Test result: ✗ FAILED
  Test errors: AttributeError: 'ContactManager' has no attribute 'contacts'
  Analysis done: Variable reassignment causing UnboundLocalError
  
  --- Attempt 2 ---
  Files modified: main.py
  Test result: ✗ FAILED
  Test errors: Expected 'save_contacts' to have been called once. Called 0 times.
  Analysis done: Missing __init__ method to initialize contacts list
  
  ============================================================
  ⚠️ CRITICAL: Review the above attempts carefully!
  ⚠️ DO NOT repeat the same approach that failed!
  ⚠️ Try a COMPLETELY DIFFERENT fix strategy!
  ============================================================
  
  Test Failures:
    - test_main.py::test_contact_manager - Mock assertion failed
  
  Current Code:
    === main.py ===
    class ContactManager:
        def __init__(self):
            self.contacts = []
        
        def add_contact(self, name):
            self.contacts.append(name)
    ...

RESPONSE:
  ANALYSIS_START
  - Issue 1: main.py - Missing save_contacts method call
  - Previous attempts fixed initialization but didn't implement persistence
  - Test expects add_contact to call save_contacts internally
  ANALYSIS_END
  
  FILE_START: main.py
  class ContactManager:
      def __init__(self):
          self.contacts = []
      
      def add_contact(self, name):
          self.contacts.append(name)
          self.save_contacts()  # Call persistence method
      
      def save_contacts(self):
          # Save to file
          with open('contacts.json', 'w') as f:
              json.dump(self.contacts, f)
  FILE_END

RESULT:
  ✓ All tests passed!
  
STORED IN all_attempts[2]:
  {
    "attempt": 3,
    "fixed_files": ["main.py"],
    "test_passed": True,
    "test_output": "All tests passed",
    "analysis": {"summary": "Missing save_contacts method call"}
  }

RETURN SUCCESS with 3 attempts
```

### Why This Works Better Than LangChain Memory

| Aspect | LangChain Memory | Debugger Internal Loop |
|--------|------------------|------------------------|
| **Context Type** | Generic conversation history | Structured debugging feedback |
| **Relevance** | May include irrelevant chat | Only iteration results |
| **Format** | Unstructured text | Structured: files, errors, analysis |
| **Control** | Automatic (buffer window) | Explicit injection |
| **Clarity** | May be ambiguous | Clear markers and warnings |
| **Task-Specific** | No | Yes - optimized for debugging |
| **Token Efficiency** | May waste tokens on noise | Only includes actionable info |
| **Learning Signal** | Weak | Strong (explicit "don't repeat X") |

### Key Design Decisions

1. **Single MCP Call, Multiple Internal Iterations**
   - MCP orchestrator makes ONE call to debugger
   - Debugger runs its own loop internally
   - Reduces JSON-RPC overhead (only 1 request/response per debug session)

2. **Structured History Format**
   - Uses clear sections: "Attempt N", "Files modified", "Test result"
   - Makes it easy for LLM to parse previous attempts
   - Includes actionable warnings

3. **Progressive Refinement**
   - Each iteration sees ALL previous iterations
   - LLM can identify patterns (e.g., "I tried X in attempt 1, Y in attempt 2, both failed, so try Z")
   - Prevents repetition of failed approaches

4. **Local Test Execution**
   - Each iteration runs tests locally via LocalServer
   - No need to return to orchestrator for each test run
   - Faster iteration cycle (~seconds per iteration vs. ~minutes with MCP round-trips)

5. **Comprehensive Result Tracking**
   - Stores not just pass/fail, but also:
     - Which files were modified
     - What the test output was
     - What analysis was performed
     - Any system errors encountered
   - Provides rich debugging information for final report

### Performance Characteristics

**Without Internal Loop (hypothetical)**:
```
MCP Call 1 → Debugger fixes → Return to orchestrator
Orchestrator runs tests → Tests fail
MCP Call 2 → Debugger fixes → Return to orchestrator
Orchestrator runs tests → Tests fail
MCP Call 3 → Debugger fixes → Return to orchestrator
Orchestrator runs tests → Tests pass

Total Time: ~15-20 seconds (5s per MCP round-trip × 3)
```

**With Internal Loop (actual)**:
```
MCP Call 1 → Debugger internal loop:
  Iteration 1 → Fix → Test locally (fail)
  Iteration 2 → Fix → Test locally (fail)
  Iteration 3 → Fix → Test locally (pass)
Return to orchestrator

Total Time: ~8-10 seconds (1 MCP call + 3 fast local iterations)
```

### Token Tracking Per Iteration

Each iteration is tracked separately in `api_usage.json`:

```json
{
  "usage_log": [
    {"agent": "debugger", "tokens": 14119, "iteration": 1, "timestamp": "..."},
    {"agent": "debugger", "tokens": 21103, "iteration": 2, "timestamp": "..."},
    {"agent": "debugger", "tokens": 15892, "iteration": 3, "timestamp": "..."}
  ]
}
```

This allows:
- Per-iteration cost analysis
- Identification of expensive iterations (often iteration 1 is largest due to initial analysis)
- Debugging of token usage patterns

### Error Handling

The internal loop handles multiple failure scenarios:

1. **Parse Failure**: If LLM response doesn't match expected format
   - Logs error
   - Continues to next iteration
   - Stores parse failure in `all_attempts`

2. **Test Execution Failure**: If tests crash/timeout
   - Captures error
   - Includes in next iteration's context
   - Allows LLM to fix test infrastructure issues

3. **Max Iterations Reached**: If 5 iterations all fail
   - Returns `success: False`
   - Includes all attempts in result
   - Orchestrator can decide next steps (e.g., return to coder)

### Future Enhancements

Potential improvements to the internal loop:

1. **Adaptive Max Iterations**
   - Increase limit if making progress
   - Decrease if stuck in loop

2. **Early Success Detection**
   - If test count increases significantly, likely on right track
   - Could adjust strategy based on progress

3. **Parallel Test Execution**
   - Run tests for multiple fix candidates
   - Choose best result

4. **Learning Across Sessions**
   - Store successful fix patterns
   - Apply similar strategies to similar failures

5. **Cost-Based Early Exit**
   - If token cost exceeds budget, stop early
   - Return partial fix with explanation

---

## Multi-Process Token Tracking

### Challenge

Each agent runs in a separate process with its own `APIUsageTracker` instance. They must coordinate writes to a single shared file (`api_usage.json`) without:
- Overwriting each other's data
- Creating duplicate entries
- Losing token counts

### Solution: File-Based Merge with Persisted Count

```python
class APIUsageTracker:
    def __init__(self):
        self.usage_log = []  # This process's entries
        self._persisted_count = 0  # How many we've written to file
    
    def _persist_usage_locked(self):
        # 1. Load existing file data
        existing_data = json.load(api_usage.json)
        existing_log = existing_data["usage_log"]  # e.g., 2 entries
        
        # 2. Identify NEW entries from THIS process
        new_entries = self.usage_log[self._persisted_count:]
        # If self.usage_log has 1 entry and _persisted_count is 0,
        # new_entries = [our 1 entry]
        
        # 3. Merge: existing + new
        merged_log = existing_log + new_entries
        # Result: [architect, coder, THIS_AGENT]
        
        # 4. Write merged data back
        json.dump(merged_log, api_usage.json)
        
        # 5. Update persisted count
        self._persisted_count = len(self.usage_log)
        # Next time, we won't re-add this entry
```

### Example Timeline

**Time T1: Architect finishes**
```python
# Process 1 (Architect)
self.usage_log = [{"agent": "architect", "tokens": 1767}]
self._persisted_count = 0

# Call _persist_usage_locked()
existing_log = []  # File doesn't exist yet
new_entries = [architect_entry]  # Slice [0:]
merged_log = [] + [architect_entry]

# Write to file:
api_usage.json = {"usage_log": [architect_entry]}

self._persisted_count = 1  # Don't re-write this entry next time
```

**Time T2: Coder finishes**
```python
# Process 2 (Coder)
self.usage_log = [{"agent": "coder", "tokens": 6100}]
self._persisted_count = 0

# Call _persist_usage_locked()
existing_log = [architect_entry]  # Load from file
new_entries = [coder_entry]  # Slice [0:]
merged_log = [architect_entry] + [coder_entry]

# Write to file:
api_usage.json = {"usage_log": [architect_entry, coder_entry]}

self._persisted_count = 1
```

**Time T3: Tester finishes**
```python
# Process 3 (Tester)
existing_log = [architect_entry, coder_entry]
new_entries = [tester_entry]
merged_log = [architect, coder, tester]

# Result: All 3 agents in file! ✓
```

---

## Process Isolation Benefits

### 1. Independence
- Each agent runs in its own process
- Crash in one agent doesn't affect others
- Can restart individual agents

### 2. Scalability
- Agents can run on different machines
- Parallel execution possible (not implemented yet)
- Distributed deployment ready

### 3. Security
- Process-level isolation
- Separate memory spaces
- Can apply different permissions per agent

### 4. Standards Compliance
- True MCP implementation
- JSON-RPC 2.0 protocol
- Compatible with other MCP clients/servers

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input                                │
│              "Create a calculator"                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              MCPOrchestrator (Main Process)                  │
│  • Launches 4 server subprocesses                           │
│  • Manages workflow sequence                                │
│  • Handles JSON-RPC communication                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┬─────────────┬──────────────┐
    │             │             │             │              │
    ▼             ▼             ▼             ▼              ▼
┌────────┐   ┌────────┐   ┌────────┐   ┌──────────┐   ┌──────────┐
│Process1│   │Process2│   │Process3│   │Process 4 │   │   File   │
│Architect│   │Coder  │   │Tester │   │Debugger  │   │  System  │
└────┬───┘   └────┬───┘   └────┬───┘   └────┬─────┘   └────┬─────┘
     │            │            │            │              │
     │ API Call   │ API Call   │ API Call   │ API Call     │
     │   ▼        │   ▼        │   ▼        │   ▼          │
     │ ┌────┐     │ ┌────┐     │ ┌────┐     │ ┌────┐       │
     │ │LLM │     │ │LLM │     │ │LLM │     │ │LLM │       │
     │ └────┘     │ └────┘     │ └────┘     │ └────┘       │
     │            │            │            │              │
     │Track Tokens│Track Tokens│Track Tokens│Track Tokens  │
     └────┬───────┴────┬───────┴────┬───────┴────┬─────────┤
          │            │            │            │         │
          └────────────┴────────────┴────────────┴────────►│
                                                            │
                                                      api_usage.json
                                                   (Shared State)
```

---

## Key Differences from Traditional Mode

| Aspect | Traditional Mode | MCP Mode |
|--------|------------------|----------|
| **Process Model** | Single process | 4+ processes (1 orchestrator + 4 servers) |
| **Communication** | Direct function calls | JSON-RPC 2.0 over stdio |
| **Agent Initialization** | Once at startup | 4 times (once per server) |
| **API Tracker** | Shared instance | 4 separate instances → merge to file |
| **Timeout** | None (only rate limiting) | 300s per tool call |
| **Overhead** | Minimal (~ms) | ~1-2s per agent (process startup + JSON) |
| **Token Tracking** | In-memory list | File-based merge |
| **Memory** | Shared | Isolated (4x base memory) |
| **Debugging** | Easier (single process) | Complex (multi-process) |
| **Standards** | Custom | MCP specification compliant |
| **Portability** | Python only | Works with any MCP client |
| **Scalability** | Limited to single machine | Can distribute across machines |

---

## File Structure

```
AICoder/
├── mcp_orchestrator/
│   ├── __init__.py
│   └── orchestrator.py           # MCPOrchestrator (Client)
│
├── mcp_servers/
│   └── python_mcp_server.py      # PythonMCPServer (Server wrapper)
│
├── agents/
│   ├── agent_architect.py        # Agent A - wrapped by server
│   ├── agent_coder.py            # Agent B - wrapped by server
│   ├── agent_tester.py           # Agent C - wrapped by server
│   └── agent_debugger.py         # Agent D - wrapped by server
│
├── backend/
│   └── api_usage_tracker.py      # Multi-process token tracking
│
├── utils/
│   └── mcp_client.py             # LLM API client
│
├── server/
│   └── local_server.py           # Code execution environment
│
└── api_usage.json                # Shared state file
```

---

## Usage

### Start MCP Mode

**CLI**:
```bash
python main.py --mcp
```

**UI**:
```bash
python main.py --ui --mcp
```

### What Happens

1. **UI/Main** calls `MCPOrchestrator.run_workflow(requirements)`
2. **Orchestrator** launches 4 MCP server subprocesses
3. **Each server** initializes its agent + components
4. **Orchestrator** sequences workflow:
   - Architect: `call_tool("architect", "create_architecture", ...)`
   - Coder: `call_tool("coder", "generate_code", ...)`
   - Tester: `call_tool("tester", "generate_tests", ...)` then `call_tool("tester", "run_tests", ...)`
   - Debugger (if needed): `call_tool("debugger", "fix_code", ...)`
5. **Each agent** tracks tokens → `api_usage.json`
6. **Orchestrator** returns final results
7. **UI** displays results and token breakdown

---

## Conclusion

AICoder's MCP mode implements **true Model Context Protocol** with:
- ✅ Process isolation (4 server processes)
- ✅ JSON-RPC 2.0 over stdio
- ✅ Standards-compliant implementation
- ✅ Multi-process token tracking with file-based merge
- ✅ Complete workflow (Architect → Coder → Tester → Debugger)
- ✅ Production-ready architecture

The architecture demonstrates how **standard protocols** (MCP) enable **interoperability** and **scalability** while maintaining **feature parity** with traditional direct-call mode.
