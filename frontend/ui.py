"""
User Interface Module
Handles user input for coding prompts and displays results
"""

from __future__ import annotations

from typing import Dict, Tuple

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

# ---------------------------------------------------------------------
# Backend compatibility shims (no new files added)
# ---------------------------------------------------------------------
def _install_backend_compat_shims() -> None:
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
    "The Data Integrity Analyzer is a software application that analyzes and evaluates the integrity "
    "of data sets, helping users identify and address data quality issues. It performs checks on data "
    "consistency, accuracy, completeness, and validity, providing users with a comprehensive assessment "
    "of the overall data integrity."
)


# -----------------------------
# Partition application/test files
# -----------------------------
def _partition_files(files: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    app_files, test_files = {}, {}
    for path, content in files.items():
        if path.startswith("tests/") or path.lower().endswith("_test.py") or path.lower().startswith("test_"):
            test_files[path] = content
        else:
            app_files[path] = content
    return app_files, test_files


# -----------------------------
# UI CLASS
# -----------------------------
class UI:
    """Gradio-based single-page UI to drive the code-generation workflow."""

    def __init__(self):
        self.handler = MCPHandler()

    def _on_generate(self, description: str, requirements: str):
        """
        Generate code & tests via backend multi-agent pipeline.

        Returns:
            - app_files_state (dict)
            - test_files_state (dict)
            - app_file_list update
            - test_file_list update
            - initial code content for code_view
            - usage panel markdown
            - token_progress (int)
        """
        request = {"description": description.strip(), "requirements": requirements}
        result = self.handler.process_request(request)

        files = result.get("files", {})
        app_files, test_files = _partition_files(files)

        # Build radio choices
        app_choices = sorted(app_files.keys())
        test_choices = sorted(test_files.keys())

        # Select default file (prefer application)
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

        # Usage stats
        stats = getattr(self.handler, "usage_tracker", None)
        stats = stats.get_usage_statistics() if stats else {"call_count": 0, "total_tokens": 0}

        usage_md = f"**API Calls**: {stats.get('call_count', 0)}  |  **Total Tokens**: {stats.get('total_tokens', 0)}"
        token_progress = stats.get("total_tokens", 0)

        return (
            app_files,
            test_files,
            app_update,
            test_update,
            unified_default,
            usage_md,
            token_progress,
        )

    def _on_clear(self):
        """Reset all fields and outputs."""
        return (
            DEFAULT_DESCRIPTION,               # description
            "",                                # requirements
            {},                                # app_files_state
            {},                                # test_files_state
            gr.update(choices=[], value=None), # app_file_list
            gr.update(choices=[], value=None), # test_file_list
            "",                                # code_view content
            "**API Calls**: 0  |  **Total Tokens**: 0",  # usage_panel
            0,                                 # token_progress
        )

    def _on_app_file_change(self, selected: str, app_files: Dict[str, str]):
        if selected:
            return app_files.get(selected, "")
        return ""

    def _on_test_file_change(self, selected: str, test_files: Dict[str, str]):
        if selected:
            return test_files.get(selected, "")
        return ""

    # -----------------------------
    # LAUNCH UI
    # -----------------------------
    def launch(self, share: bool = False):
        with gr.Blocks(title="SWE270P - Code Generator") as demo:

            gr.Markdown("## SWE270P Final Project — Multi-Agent Code & Test Generator")

            app_files_state = gr.State({})
            test_files_state = gr.State({})

            with gr.Row():

                # LEFT SIDE
                with gr.Column(scale=1):
                    description = gr.Textbox(
                        label="Software Description",
                        value=DEFAULT_DESCRIPTION,
                        lines=6,
                    )
                    requirements = gr.Textbox(
                        label="Requirements (free-form, one per line or paragraph)",
                        value="",
                        lines=8,
                        placeholder="- Validate nulls and types\n- Report duplicates\n- Provide auto-fix suggestions",
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
                with gr.Column(scale=3):  # wider right panel
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
                                lines=40,   # taller viewer
                            )

            # --- Callbacks ---

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
    UI().launch()