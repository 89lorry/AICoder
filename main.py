# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

"""
Main Application Entry Point
Multi-Agent MCP System for Software Generation
Using WorkflowOrchestrator with Real MCP Agents
Supports both CLI and Gradio UI modes
"""

import logging
import sys
import os
import argparse
from typing import Dict, Any, Tuple
from config.settings import Settings
from server.local_server import LocalServer
from frontend.ui import GradioUI


def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=getattr(logging, Settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(Settings.LOG_FILE, encoding='utf-8')
        ]
    )


def check_mcp_configuration():
    """Check if MCP is properly configured"""
    if not Settings.MCP_API_KEY:
        return False, "MCP_API_KEY not set in environment variables"
    return True, "MCP configuration valid"


def initialize_agents(enable_memory=False):
    """
    Initialize all MCP agents
    
    Args:
        enable_memory: Whether to enable LangChain memory (requires langchain)
        
    Returns:
        Tuple of (architect, coder, tester, debugger, local_server) or None if failed
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Generate session ID for all agents
        from datetime import datetime
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Import agents
        from agents.agent_architect import AgentArchitect
        from agents.agent_coder import AgentCoder
        from agents.agent_tester import AgentTester
        from agents.agent_debugger import AgentDebugger
        from backend.api_usage_tracker import APIUsageTracker
        
        logger.info("Agent modules imported successfully")
        
        # Initialize MCP client
        try:
            from utils.mcp_client import MCPClient
            mcp_client = MCPClient(
                api_key=Settings.MCP_API_KEY,
                endpoint=Settings.MCP_ENDPOINT
            )
            logger.info("MCP client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
            return None
        
        # Initialize API usage tracker
        api_tracker = APIUsageTracker() if Settings.TRACK_API_USAGE else None
        
        # Initialize LocalServer
        local_server = LocalServer(workspace_dir=Settings.WORKSPACE_DIR)
        logger.info("LocalServer initialized")
        
        # Initialize agents
        logger.info("Initializing agents...")
        
        architect = AgentArchitect(
            mcp_client=mcp_client,
            api_usage_tracker=api_tracker,
            enable_memory=enable_memory,
            session_id=session_id
        )
        logger.info("Agent A (Architect) initialized")
        
        coder = AgentCoder(
            mcp_client=mcp_client,
            api_usage_tracker=api_tracker,
            local_server=local_server,
            enable_memory=enable_memory,
            session_id=session_id
        )
        logger.info("Agent B (Coder) initialized")
        
        tester = AgentTester(
            mcp_client=mcp_client,
            api_usage_tracker=api_tracker,
            local_server=local_server,
            enable_memory=enable_memory,
            session_id=session_id
        )
        logger.info("Agent C (Tester) initialized")
        
        debugger = AgentDebugger(
            mcp_client=mcp_client,
            api_usage_tracker=api_tracker,
            local_server=local_server,
            enable_memory=enable_memory,
            session_id=session_id
        )
        logger.info("Agent D (Debugger) initialized")
        
        return architect, coder, tester, debugger, local_server, api_tracker, session_id
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        logger.error("Some dependencies may be missing. Install with: pip install -r requirements.txt")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize agents: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_with_workflow_orchestrator(requirements: str, enable_memory=False, max_iterations=5):
    """
    Run the complete workflow using WorkflowOrchestrator with real MCP agents
    
    Args:
        requirements: Software requirements
        enable_memory: Whether to enable LangChain memory
        max_iterations: Maximum feedback loop iterations
        
    Returns:
        Result dictionary or None if failed
    """
    logger = logging.getLogger(__name__)
    
    # Initialize agents
    logger.info("Initializing MCP agents...")
    agents_result = initialize_agents(enable_memory=enable_memory)
    
    if agents_result is None:
        logger.error("Failed to initialize agents")
        return None
    
    architect, coder, tester, debugger, local_server, api_tracker, session_id = agents_result
    
    try:
        # Import WorkflowOrchestrator
        from workflow_orchestrator import WorkflowOrchestrator
        
        # Create orchestrator
        orchestrator = WorkflowOrchestrator(
            architect=architect,
            coder=coder,
            tester=tester,
            debugger=debugger,
            max_iterations=max_iterations
        )
        logger.info("WorkflowOrchestrator initialized")
        
        # Run workflow
        logger.info("Starting workflow execution...")
        result = orchestrator.run_complete_workflow(requirements)
        
        # Display API usage if tracking
        if api_tracker:
            usage_stats = api_tracker.get_usage_statistics()
            logger.info(f"\nAPI Usage Statistics:")
            logger.info(f"Total tokens used: {usage_stats.get('total_tokens', 0):,}")
            logger.info(f"Total API calls: {usage_stats.get('call_count', 0)}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error running workflow: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_basic_test():
    """Run a basic LocalServer test without MCP agents"""
    logger = logging.getLogger(__name__)
    
    logger.info("Running basic LocalServer test (no MCP agents)...")
    
    test_code_package = {
        "project_name": "basic_test",
        "files": {
            "main.py": '''"""
Basic Calculator Test
"""

class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
    
    def multiply(self, a, b):
        return a * b
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

def main():
    calc = Calculator()
    print("Basic Calculator Test")
    print(f"5 + 3 = {calc.add(5, 3)}")
    print(f"10 - 4 = {calc.subtract(10, 4)}")
    print(f"6 * 7 = {calc.multiply(6, 7)}")
    print(f"15 / 3 = {calc.divide(15, 3)}")
    print("All operations completed!")

if __name__ == "__main__":
    main()
'''
        },
        "requirements": [],
        "entry_point": "main.py"
    }
    
    local_server = LocalServer(workspace_dir="./workspace")
    local_server.receive_code_package(test_code_package)
    local_server.save_code_to_directory(test_code_package)
    results = local_server.execute_code(entry_point="main.py", timeout=10)
    local_server.cleanup_workspace()
    
    return results['success']




# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

def main():
    """Main entry point - handles both CLI and UI modes"""
    setup_logging()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='AICoder - Multi-Agent Code Generation System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python main.py              # Run in CLI mode (default)
  python main.py --mcp        # Run with MCP protocol (agent servers)
  python main.py --ui         # Launch Gradio web UI
  python main.py --ui --share # Launch Gradio web UI with public sharing
        '''
    )
    parser.add_argument(
        '--ui',
        action='store_true',
        help='Launch Gradio web UI instead of CLI mode'
    )
    parser.add_argument(
        '--share',
        action='store_true',
        help='Create a public Gradio share link (only works with --ui)'
    )
    parser.add_argument(
        '--mcp',
        action='store_true',
        help='Use MCP protocol for agent communication (JSON-RPC over stdio)'
    )
    
    args = parser.parse_args()
    
    # Check MCP configuration first
    config_valid, config_msg = check_mcp_configuration()
    
    if not config_valid:
        print(f"⚠️  WARNING: {config_msg}")
        print("Set MCP_API_KEY environment variable before running")
        print("\nℹ️  Setup instructions:")
        print("   1. Copy .env.example to .env")
        print("   2. Add your API key: MCP_API_KEY=your_key_here")
        print("   3. Run again")
        sys.exit(1)
    
    # Launch appropriate mode
    if args.ui:
        print("=" * 60)
        if args.mcp:
            print("AICoder - Multi-Agent Code Generator (UI Mode with MCP)")
            print("Using Model Context Protocol (JSON-RPC)")
        else:
            print("AICoder - Multi-Agent Code Generator (UI Mode)")
        print("=" * 60)
        print(f"✓ {config_msg}")
        print(f"🌐 Launching Gradio UI on {Settings.UI_HOST}:{Settings.UI_PORT}...")
        if args.share:
            print("🔗 Creating public share link...")
        if args.mcp:
            print("🔗 MCP mode enabled - agents will communicate via JSON-RPC")
        print("")
        
        ui = GradioUI(use_mcp=args.mcp)
        ui.launch(share=args.share)
    elif args.mcp:
        # Run MCP mode
        main_mcp()
    else:
        # Run CLI mode (default)
        main_cli()


def main_cli():
    """Main CLI application function"""
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("MCP Multi-Agent Software Generation System")
    print("WorkflowOrchestrator with Real MCP Agents")
    print("=" * 60)
    
    try:
        # Simple user requirements - Architect will expand these into detailed specs
        requirements = """
I need a contact management system where I can:
- Save people's names, email addresses, and phone numbers
- Search for contacts by name
- See all my contacts in alphabetical order
- Remove contacts I don't need anymore
"""
        
        print("\n📋 Requirements:")
        print("-" * 60)
        print(requirements)
        print("-" * 60)
        
        # Check MCP configuration
        config_valid, config_msg = check_mcp_configuration()
        
        if not config_valid:
            print(f"\n⚠️  WARNING: {config_msg}")
            print("Set MCP_API_KEY environment variable to use MCP agents")
            print("Falling back to basic test...\n")
            
            # Run basic test
            if run_basic_test():
                print("\n✅ Basic test passed!")
                print("✅ LocalServer with FileManager working correctly")
            else:
                print("\n❌ Basic test failed")
            
            print("\nℹ️  To use full MCP agent workflow:")
            print("   1. Set environment variable: MCP_API_KEY=your_key")
            print("   2. Install dependencies: pip install -r requirements.txt")
            print("   3. Run again: python main.py")
            return
        
        print(f"\n✓ {config_msg}")
        print("🚀 Starting WorkflowOrchestrator with MCP agents...\n")
        
        # Decide whether to enable memory (requires langchain)
        enable_memory = Settings.ENABLE_MEMORY
        if enable_memory:
            print("ℹ️  LangChain memory enabled (requires langchain package)")
        else:
            print("ℹ️  LangChain memory disabled")
        
        # Run workflow with real agents
        result = run_with_workflow_orchestrator(
            requirements=requirements,
            enable_memory=enable_memory,
            max_iterations=5
        )
        
        if result is None:
            print("\n❌ Workflow execution failed")
            print("Falling back to basic test...\n")
            
            if run_basic_test():
                print("\n✅ Basic test passed!")
            
            return
        
        # Display results
        print("\n" + "=" * 60)
        print("📊 WORKFLOW RESULTS")
        print("=" * 60)
        print(f"Status: {result['final_status']}")
        
        # Only show iterations if they exist (not present in error cases)
        if 'total_iterations' in result:
            print(f"Iterations: {result['total_iterations']}")
        
        if result['final_status'] == 'success':
            print("\n✅ Code generation and testing completed successfully!")
            
            # Show generated files
            if result.get('final_code_package'):
                code_package = result['final_code_package']
                files = code_package.get('files', {})
                print(f"\n📁 Generated Files ({len(files)}):")
                
                # Handle both dict and list formats
                if isinstance(files, dict):
                    for filename in files:  # More Pythonic, no need for .keys()
                        print(f"   - {filename}")
                elif isinstance(files, list):
                    for filename in files:
                        print(f"   - {filename}")
                else:
                    # Handle unexpected format
                    print(f"   (Unexpected format: {type(files)})")
        else:
            print("\n⚠️  Workflow completed but tests did not pass")
            print(f"Completed {result['total_iterations']} iterations")
        
        print("\n✅ Process completed!")
        
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
        print("\n\n⚠️  Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def main_mcp():
    """Main MCP mode - uses true MCP protocol with JSON-RPC"""
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("MCP Multi-Agent Software Generation System")
    print("Using Model Context Protocol (JSON-RPC over stdio)")
    print("=" * 60)
    
    try:
        # Check MCP configuration
        config_valid, config_msg = check_mcp_configuration()
        
        if not config_valid:
            print(f"\n⚠️  WARNING: {config_msg}")
            print("Set MCP_API_KEY environment variable to use MCP mode")
            return
        
        print(f"\n✓ {config_msg}")
        print("🚀 Starting MCP Orchestrator with agent servers...\n")
        
        requirements = """
Create a basic calculator
"""
        
        print("📋 Requirements:")
        print("-" * 60)
        print(requirements)
        print("-" * 60)
        
        # Run MCP workflow using asyncio
        import asyncio
        from mcp_orchestrator import MCPOrchestrator
        
        async def run_mcp_workflow():
            orchestrator = MCPOrchestrator()
            result = await orchestrator.run_workflow(requirements)
            return result
        
        result = asyncio.run(run_mcp_workflow())
        
        # Display results
        print("\n" + "=" * 60)
        print("📊 MCP WORKFLOW RESULTS")
        print("=" * 60)
        print(f"Status: {result['final_status']}")
        
        if result['final_status'] == 'success':
            print("\n✅ Code generation and testing completed successfully via MCP!")
            
            if result.get('code_package'):
                code_package = result['code_package']
                files = code_package.get('files', {})
                print(f"\n📁 Generated Files ({len(files)}):")
                for filename in files:
                    print(f"   - {filename}")
        elif result['final_status'] == 'error':
            print(f"\n❌ Error occurred: {result.get('error', 'Unknown error')}")
        else:
            print("\n⚠️  Workflow completed but tests did not pass")
        
        print("\n✅ MCP Process completed!")
        print("\nℹ️  All agents communicated via JSON-RPC protocol over stdio")
        
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
        print("\n\n⚠️  Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in MCP mode: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
