"""
User Interface Module
Handles user input for coding prompts and displays results
"""

from __future__ import annotations

from typing import Dict, Tuple, List

import gradio as gr
import os
import sys
from dotenv import load_dotenv

_CURRENT_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.abspath(os.path.join(_CURRENT_DIR, os.pardir))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load environment from .env so real API keys can be used when available
load_dotenv()

def _install_backend_compat_shims() -> None:
    """
    Install minimal runtime shims so backend imports succeed even if optional
    memory/langchain modules are not present. No new files or memory logic added.
    """
    import types as _types
    if "utils.memory_manager" not in sys.modules:
        mm = _types.ModuleType("utils.memory_manager")
        class MemoryManager:
            def __init__(self, *args, **kwargs): ...
            def save_context(self, *args, **kwargs): ...
            def load_memory_variables(self, *args, **kwargs): return {"chat_history": []}
            def get_chat_history(self): return ""
            def add_system_message(self, *args, **kwargs): ...
            def clear(self): ...
        mm.MemoryManager = MemoryManager
        sys.modules["utils.memory_manager"] = mm
    if "utils.langchain_wrapper" not in sys.modules:
        lw = _types.ModuleType("utils.langchain_wrapper")
        class LangChainWrapper:
            def __init__(self, *args, **kwargs): ...
            def invoke(self, *args, **kwargs): return ""
            def get_token_usage(self): return {}
        lw.LangChainWrapper = LangChainWrapper
        sys.modules["utils.langchain_wrapper"] = lw

_install_backend_compat_shims()

from backend.mcp_handler import MCPHandler
from config.settings import Settings


DEFAULT_DESCRIPTION = (
    "The Data Integrity Analyzer is a software application that analyzes and evaluates the integrity of data sets, helping users identify and address data quality issues. It performs checks on data consistency, accuracy, completeness, and validity, providing users with a comprehensive assessment of the overall data integrity."
)


def _partition_files(files: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Split files into application vs tests based on path prefix."""
    app_files: Dict[str, str] = {}
    test_files: Dict[str, str] = {}
    for path, content in files.items():
        if path.startswith("tests/") or path.lower().endswith("_test.py") or path.lower().startswith("test_"):
            test_files[path] = content
        else:
            app_files[path] = content
    return app_files, test_files


def _files_to_markdown(files: Dict[str, str]) -> str:
    """Render a mapping of filename -> content into a Markdown string with code fences."""
    if not files:
        return "_No files generated._"
    sections: List[str] = []
    for filename in sorted(files.keys()):
        content = files[filename]
        lang = "python" if filename.endswith(".py") else "text"
        sections.append(f"### `{filename}`\n\n```{lang}\n{content}\n```")
    return "\n\n".join(sections)


class UI:
    """Gradio-based single-page UI to drive the code-generation workflow."""

    def __init__(self):
        # Always use the real backend client; requires MCP_API_KEY to be set
        self.handler = MCPHandler()
        self._last_result: Dict[str, str] | None = None

    # Compatibility methods for main.py (not used in Gradio flow)
    def get_user_input(self):
        return None

    def display_results(self):
        return None

    def display_api_usage(self):
        return None

    def _on_generate(self, description: str, requirements: str) -> Tuple[str, str, str]:
        """Backend callback for the Generate button."""
        request = {"description": description.strip(), "requirements": requirements}
        result = self.handler.process_request(request)
        files = result.get("files", {})
        app_files, test_files = _partition_files(files)
        app_md = _files_to_markdown(app_files)
        test_md = _files_to_markdown(test_files)

        stats = getattr(self.handler, "usage_tracker", None)
        stats = stats.get_usage_statistics() if stats else {"call_count": 0, "total_tokens": 0}
        usage_md = (
            f"**API Calls**: {stats.get('call_count', 0)}  |  "
            f"**Total Tokens**: {stats.get('total_tokens', 0)}"
        )
        self._last_result = result
        return app_md, test_md, usage_md

    def _on_clear(self) -> Tuple[str, str, str, str, str]:
        """Reset all fields and outputs."""
        return DEFAULT_DESCRIPTION, "", "", "", "**API Calls**: 0  |  **Total Tokens**: 0"

    def launch(self, share: bool = False) -> None:
        """Create and launch the Gradio interface."""
        with gr.Blocks(title="SWE270P - Multi-Agent Code Generator") as demo:
            gr.Markdown("## SWE270P Final Project — Multi-Agent Code & Test Generator")
            with gr.Row():
                with gr.Column(scale=1):
                    description = gr.Textbox(
                        label="Software Description",
                        value=DEFAULT_DESCRIPTION,
                        lines=6,
                        placeholder="Describe the software to generate...",
                    )
                    requirements = gr.Textbox(
                        label="Requirements (free-form, one per line or paragraph)",
                        value="",
                        lines=8,
                        placeholder="e.g.,\n- Validate nulls and types\n- Report duplicates\n- Provide auto-fix suggestions",
                    )
                    with gr.Row():
                        generate_btn = gr.Button("Generate Code & Tests", variant="primary")
                        clear_btn = gr.Button("Clear", variant="secondary")
                    usage_panel = gr.Markdown(
                        "**API Calls**: 0  |  **Total Tokens**: 0",
                        elem_id="usage-panel",
                    )
                with gr.Column(scale=1):
                    gr.Markdown("### Application Code")
                    app_code = gr.Markdown(value="_Awaiting generation..._", elem_id="app-code",)
                    gr.Markdown("### Test Code")
                    test_code = gr.Markdown(value="_Awaiting generation..._", elem_id="test-code",)

            # Wire interactions
            generate_btn.click(
                fn=self._on_generate,
                inputs=[description, requirements],
                outputs=[app_code, test_code, usage_panel],
                api_name="generate",
            )
            clear_btn.click(
                fn=self._on_clear,
                inputs=[],
                outputs=[description, requirements, app_code, test_code, usage_panel],
            )

        demo.launch(
            share=share,
            server_name=Settings.UI_HOST,
            server_port=Settings.UI_PORT,
        )


if __name__ == "__main__":
    UI().launch()
