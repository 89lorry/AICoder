# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

"""
User Interface Module
Handles user input for coding prompts and displays results
"""

import logging
import sys
import os
from typing import Dict, Tuple

# Add parent directory to path for imports
_CURRENT_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.abspath(os.path.join(_CURRENT_DIR, os.pardir))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config.settings import Settings


def _partition_files(files) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Partition files into application and test files"""
    app_files, test_files = {}, {}
    
    # Handle both dict and list formats
    if isinstance(files, dict):
        items = files.items()
    elif isinstance(files, list):
        # If it's a list of dicts, extract name/filename and content
        items = []
        for f in files:
            if isinstance(f, dict):
                # Try different key names
                name = f.get('name') or f.get('filename') or f.get('file_name') or f.get('path', '')
                content = f.get('content') or f.get('code', '')
                if name:  # Only add if we got a name
                    items.append((name, content))
                    logging.debug(f"List item: name={name}, content_len={len(content)}")
            elif isinstance(f, str):
                # If it's just a string (filename), skip it
                continue
        logging.info(f"Processed list into {len(items)} items")
    else:
        logging.warning(f"Unexpected files type: {type(files)}")
        return app_files, test_files
    
    for path, content in items:
        # Extract just the filename from the path for checking
        filename = path.split('/')[-1].lower()
        
        # Classify as test file if:
        # 1. Path starts with "tests/" directory
        # 2. Filename ends with "_test.py"
        # 3. Filename starts with "test_" (matches both test_main.py and test_data.py)
        if path.startswith("tests/") or filename.endswith("_test.py") or filename.startswith("test_"):
            test_files[path] = content
            logging.debug(f"Classified as test file: {path}")
        else:
            app_files[path] = content
            logging.debug(f"Classified as app file: {path}")
    
    logging.info(f"Partitioned: {len(app_files)} app files, {len(test_files)} test files")
    logging.info(f"Test files: {list(test_files.keys())}")
    logging.info(f"App files: {list(app_files.keys())}")
    return app_files, test_files


class GradioUI:
    """Gradio-based UI for code generation workflow"""
    
    def __init__(self, use_mcp=False):
        # Initialize backend handler lazily
        self.backend_initialized = False
        self.orchestrator = None
        self.api_tracker = None
        self.use_mcp = use_mcp
    
    def _initialize_backend(self):
        """Initialize backend components once"""
        if self.backend_initialized:
            return True
        
        try:
            from main import initialize_agents
            agents_result = initialize_agents(enable_memory=Settings.ENABLE_MEMORY)
            if agents_result is None:
                return False
            
            architect, coder, tester, debugger, local_server, api_tracker, session_id = agents_result
            
            from workflow_orchestrator import WorkflowOrchestrator
            self.orchestrator = WorkflowOrchestrator(
                architect=architect,
                coder=coder,
                tester=tester,
                debugger=debugger,
                max_iterations=5
            )
            self.api_tracker = api_tracker
            
            self.backend_initialized = True
            return True
        except Exception as e:
            logging.error(f"Failed to initialize backend: {e}")
            return False
    
    def _on_generate(self, description: str, requirements: str, progress=None):
        """Generate code & tests via backend multi-agent pipeline"""
        try:
            import gradio as gr
            
            # Combine description and requirements
            full_requirements = f"{description.strip()}\n\n{requirements.strip()}"
            
            # Use MCP mode if enabled
            if self.use_mcp:
                return self._on_generate_mcp(full_requirements, progress)
            
            # Initialize backend if needed (original mode)
            if not self._initialize_backend():
                return (
                    {},
                    {},
                    gr.update(choices=[], value=None),
                    gr.update(choices=[], value=None),
                    "❌ Failed to initialize backend. Check MCP_API_KEY.",
                    "**API Calls**: 0  |  **Total Tokens**: 0",
                    0,
                )
            
            # Reset API usage tracker for this generation
            if self.api_tracker:
                self.api_tracker.reset_tracker()
            
            # Also delete the api_usage.json file to ensure clean reset
            import json
            from pathlib import Path
            api_usage_file = Path("api_usage.json")
            if api_usage_file.exists():
                try:
                    api_usage_file.unlink()
                except Exception as e:
                    logging.error(f"Failed to delete api_usage.json: {e}")
            
            # Update progress if available
            if progress is not None:
                progress(0, desc="🏗️ Architect: Designing system architecture...")
            
            # Run workflow
            result = self.orchestrator.run_complete_workflow(full_requirements)
            
            # Signal workflow completion to stop progress animation
            if progress is not None:
                progress(1.0, desc="✅ Workflow completed!")
            
            if result and result.get('final_status') == 'success':
                # Extract generated files
                code_package = result.get('code_package', {})
                files = code_package.get('code', {})
                
                app_files, test_files = _partition_files(files)
                
                # Build radio choices
                app_choices = sorted(app_files.keys())
                test_choices = sorted(test_files.keys())
                
                # Select default file
                if app_choices:
                    default_file = app_choices[0]
                    unified_default = app_files[default_file]
                    app_update = gr.update(choices=app_choices, value=default_file)
                    test_update = gr.update(choices=test_choices, value=None)
                elif test_choices:
                    default_file = test_choices[0]
                    unified_default = test_files[default_file]
                    app_update = gr.update(choices=app_choices, value=None)
                    test_update = gr.update(choices=test_choices, value=default_file)
                else:
                    unified_default = ""
                    app_update = gr.update(choices=[], value=None)
                    test_update = gr.update(choices=[], value=None)
                
                # Usage stats - read from api_usage.json
                usage_md, token_progress = self._generate_usage_display()
                
                return (
                    app_files,
                    test_files,
                    app_update,
                    test_update,
                    unified_default,
                    usage_md,
                    token_progress,
                )
            else:
                # Workflow failed
                error_msg = result.get('error', 'Workflow failed') if result else 'Workflow failed'
            return (
                {},
                {},
                gr.update(choices=[], value=None),
                gr.update(choices=[], value=None),
                f"❌ Error: {error_msg}",
                self._generate_usage_display()[0],
                0,
            )
        except Exception as e:
            import gradio as gr
            logging.error(f"Error in _on_generate: {e}")
            return (
                {},
                {},
                gr.update(choices=[], value=None),
                gr.update(choices=[], value=None),
                f"❌ Exception: {str(e)}",
                self._generate_usage_display()[0],
                0,
            )
    
    def _generate_usage_display(self):
        """Generate formatted usage display from api_usage.json"""
        import json
        from pathlib import Path
        from collections import defaultdict
        
        try:
            api_usage_path = Path("api_usage.json")
            if not api_usage_path.exists():
                return "**API Calls**: 0  |  **Total Tokens**: 0", 0
            
            with open(api_usage_path, 'r') as f:
                usage_data = json.load(f)
            
            total_tokens = usage_data.get('total_tokens', 0)
            usage_log = usage_data.get('usage_log', [])
            
            # Calculate per-agent breakdown
            agent_stats = defaultdict(lambda: {'calls': 0, 'tokens': 0, 'iterations': {}})
            
            for entry in usage_log:
                agent = entry.get('agent', 'unknown')
                tokens = entry.get('tokens', 0)
                iteration = entry.get('iteration')
                
                agent_stats[agent]['calls'] += 1
                agent_stats[agent]['tokens'] += tokens
                
                # Track debugger iterations
                if agent == 'debugger' and iteration:
                    if iteration not in agent_stats[agent]['iterations']:
                        agent_stats[agent]['iterations'][iteration] = 0
                    agent_stats[agent]['iterations'][iteration] += tokens
            
            # Build formatted display
            lines = [
                f"### 📊 API Usage Summary",
                f"**Total Tokens**: {total_tokens:,} | **Total Calls**: {len(usage_log)}",
                "",
                "#### 🤖 Agent Breakdown:"
            ]
            
            # Agent order for display
            agent_order = ['architect', 'coder', 'tester', 'debugger']
            agent_icons = {
                'architect': '🏗️',
                'coder': '💻',
                'tester': '🧪',
                'debugger': '🐛'
            }
            
            for agent in agent_order:
                if agent in agent_stats:
                    stats = agent_stats[agent]
                    icon = agent_icons.get(agent, '🔧')
                    lines.append(f"- **{icon} {agent.capitalize()}**: {stats['tokens']:,} tokens ({stats['calls']} calls)")
                    
                    # Show iteration breakdown for debugger
                    if agent == 'debugger' and stats['iterations']:
                        for iteration in sorted(stats['iterations'].keys()):
                            tokens = stats['iterations'][iteration]
                            lines.append(f"  - Iteration {iteration}: {tokens:,} tokens")
            
            usage_md = "\n".join(lines)
            return usage_md, total_tokens
            
        except Exception as e:
            logging.error(f"Error reading api_usage.json: {e}")
            return "**API Calls**: 0  |  **Total Tokens**: 0", 0
    
    def _on_clear(self):
        """Reset all fields and outputs"""
        import gradio as gr
        return (
            "",  # description
            "",  # requirements
            {},  # app_files_state
            {},  # test_files_state
            gr.update(choices=[], value=None),  # app_file_list
            gr.update(choices=[], value=None),  # test_file_list
            "",  # code_view content
            "**API Calls**: 0  |  **Total Tokens**: 0",  # usage_panel
            0,  # token_progress
        )
    
    def _on_app_file_change(self, selected: str, app_files: Dict[str, str]):
        """Handle application file selection"""
        if selected:
            return app_files.get(selected, "")
        return ""
    
    def _on_test_file_change(self, selected: str, test_files: Dict[str, str]):
        """Handle test file selection"""
        if selected:
            return test_files.get(selected, "")
        return ""
    
    def _on_generate_mcp(self, full_requirements: str, progress=None):
        """Generate code & tests using MCP protocol"""
        try:
            import gradio as gr
            import asyncio
            from mcp_orchestrator import MCPOrchestrator
            import json
            from pathlib import Path
            
            # Clear api_usage.json at start of new session (like traditional mode)
            api_usage_file = Path("api_usage.json")
            if api_usage_file.exists():
                try:
                    api_usage_file.unlink()
                    logging.info("Cleared api_usage.json for new MCP session")
                except Exception as e:
                    logging.error(f"Failed to delete api_usage.json: {e}")
            
            # Update progress if available
            if progress is not None:
                progress(0, desc="🔗 Connecting to MCP servers...")
            
            # Run MCP workflow
            async def run_workflow():
                orchestrator = MCPOrchestrator()
                return await orchestrator.run_workflow(full_requirements)
            
            result = asyncio.run(run_workflow())
            
            # Signal workflow completion
            if progress is not None:
                progress(1.0, desc="✅ MCP Workflow completed!")
            
            if result and result.get('final_status') in ['success', 'partial_success']:
                # Extract generated files
                code_package = result.get('code_package', {})
                
                # Debug logging
                logging.info(f"MCP result keys: {result.keys()}")
                logging.info(f"code_package type: {type(code_package)}")
                logging.info(f"code_package keys: {code_package.keys() if isinstance(code_package, dict) else 'not a dict'}")
                
                # Extract files - use 'code' key which has the actual content dictionary
                files = None
                if isinstance(code_package, dict):
                    # Use 'code' first - this has the actual file contents dict
                    files = code_package.get('code')
                    # Fallback to 'files' only if it's a dict (not a list of filenames)
                    if not files or isinstance(files, list):
                        files_candidate = code_package.get('files')
                        if isinstance(files_candidate, dict):
                            files = files_candidate
                    # Try direct code_package if it looks like files dict
                    if not files and any(k.endswith('.py') for k in code_package.keys()):
                        files = code_package
                
                if not files or not isinstance(files, dict):
                    files = {}
                    logging.warning(f"No valid files dict found in code_package")
                    
                logging.info(f"Extracted files type: {type(files)}")
                logging.info(f"Extracted files count: {len(files) if isinstance(files, (dict, list)) else 0}")
                
                # Debug: Show first file structure
                if isinstance(files, list) and len(files) > 0:
                    logging.info(f"First file item type: {type(files[0])}")
                    logging.info(f"First file item keys: {files[0].keys() if isinstance(files[0], dict) else 'not a dict'}")
                    logging.info(f"First file item: {files[0]}")
                
                app_files, test_files = _partition_files(files)
                
                logging.info(f"After partition - app_files: {list(app_files.keys())}")
                logging.info(f"After partition - test_files: {list(test_files.keys())}")
                
                # Build radio choices
                app_choices = sorted(app_files.keys())
                test_choices = sorted(test_files.keys())
                
                # Select default file
                if app_choices:
                    default_file = app_choices[0]
                    unified_default = app_files[default_file]
                    app_update = gr.update(choices=app_choices, value=default_file)
                    test_update = gr.update(choices=test_choices, value=None)
                elif test_choices:
                    default_file = test_choices[0]
                    unified_default = test_files[default_file]
                    app_update = gr.update(choices=app_choices, value=None)
                    test_update = gr.update(choices=test_choices, value=default_file)
                else:
                    unified_default = ""
                    app_update = gr.update(choices=[], value=None)
                    test_update = gr.update(choices=[], value=None)
                
                # Usage stats - read from api_usage.json (same as traditional mode)
                usage_md, token_progress = self._generate_usage_display()
                
                return (
                    app_files,
                    test_files,
                    app_update,
                    test_update,
                    unified_default,
                    usage_md,
                    token_progress,
                )
            else:
                # Workflow failed
                error_msg = result.get('error', 'MCP workflow failed') if result else 'MCP workflow failed'
                return (
                    {},
                    {},
                    gr.update(choices=[], value=None),
                    gr.update(choices=[], value=None),
                    f"❌ MCP Error: {error_msg}",
                    "**MCP Mode**: Error occurred",
                    0,
                )
        except Exception as e:
            import gradio as gr
            logging.error(f"Error in MCP mode: {e}", exc_info=True)
            return (
                {},
                {},
                gr.update(choices=[], value=None),
                gr.update(choices=[], value=None),
                f"❌ MCP Exception: {str(e)}",
                "**MCP Mode**: Exception occurred",
                0,
            )
    
    def launch(self, share: bool = False):
        """Launch Gradio UI"""
        try:
            import gradio as gr
        except ImportError:
            print("❌ Gradio not installed. Install with: pip install gradio")
            return
        
        mode_indicator = "🔗 MCP Mode (JSON-RPC Protocol)" if self.use_mcp else "🔄 Direct Mode (Python Calls)"
        
        with gr.Blocks(title="AICoder - Multi-Agent Code Generator") as demo:
            gr.Markdown(f"## AICoder — Multi-Agent Code & Test Generator\n\n{mode_indicator}")
            
            app_files_state = gr.State({})
            test_files_state = gr.State({})
            
            with gr.Row():
                # LEFT SIDE
                with gr.Column(scale=1):
                    description = gr.Textbox(
                        label="Software Description",
                        value="",
                        lines=6,
                        placeholder="Describe what software you want to build..."
                    )
                    requirements = gr.Textbox(
                        label="Requirements (optional)",
                        value="",
                        lines=8,
                        placeholder="- Feature 1\n- Feature 2\n- Feature 3",
                    )
                    
                    with gr.Row():
                        generate_btn = gr.Button("Generate Code & Tests", variant="primary")
                        clear_btn = gr.Button("Clear", variant="secondary")
                    
                    usage_panel = gr.Markdown(
                        "**API Calls**: 0  |  **Total Tokens**: 0",
                        elem_id="usage-panel",
                    )
                    
                    token_progress = gr.Slider(
                        minimum=0,
                        maximum=20000,
                        value=0,
                        step=1,
                        interactive=False,
                        label="Token Usage Progress",
                    )
                
                # RIGHT SIDE
                with gr.Column(scale=3):
                    with gr.Row():
                        with gr.Column(scale=1):
                            app_file_list = gr.Radio(
                                label="Application Files",
                                choices=[],
                                value=None,
                                interactive=True,
                            )
                            test_file_list = gr.Radio(
                                label="Test Files",
                                choices=[],
                                value=None,
                                interactive=True,
                            )
                        
                        with gr.Column(scale=4):
                            code_view = gr.Code(
                                label="File Content",
                                value="",
                                language="python",
                                lines=40,
                            )
            
            # Callbacks
            generate_btn.click(
                fn=self._on_generate,
                inputs=[description, requirements],
                outputs=[
                    app_files_state,
                    test_files_state,
                    app_file_list,
                    test_file_list,
                    code_view,
                    usage_panel,
                    token_progress,
                ],
                show_progress="full",  # Enable Gradio's progress tracking
            )
            
            clear_btn.click(
                fn=self._on_clear,
                inputs=[],
                outputs=[
                    description,
                    requirements,
                    app_files_state,
                    test_files_state,
                    app_file_list,
                    test_file_list,
                    code_view,
                    usage_panel,
                    token_progress,
                ],
            )
            
            app_file_list.change(
                fn=self._on_app_file_change,
                inputs=[app_file_list, app_files_state],
                outputs=[code_view],
            )
            
            test_file_list.change(
                fn=self._on_test_file_change,
                inputs=[test_file_list, test_files_state],
                outputs=[code_view],
            )
        
        demo.launch(
            share=share,
            server_name=Settings.UI_HOST,
            server_port=Settings.UI_PORT,
        )


if __name__ == "__main__":
    # For testing UI standalone
    ui = GradioUI()
    ui.launch()
