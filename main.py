"""
Main Application Entry Point
Multi-Agent MCP System for Software Generation
Using WorkflowOrchestrator with Real MCP Agents
"""

import logging
import sys
import os
from config.settings import Settings
from server.local_server import LocalServer


def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=getattr(logging, Settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(Settings.LOG_FILE)
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
            enable_memory=enable_memory
        )
        logger.info("✓ Agent A (Architect) initialized")
        
        coder = AgentCoder(
            mcp_client=mcp_client,
            api_usage_tracker=api_tracker,
            local_server=local_server,
            enable_memory=enable_memory
        )
        logger.info("✓ Agent B (Coder) initialized")
        
        tester = AgentTester(
            mcp_client=mcp_client,
            api_usage_tracker=api_tracker,
            local_server=local_server,
            enable_memory=enable_memory
        )
        logger.info("✓ Agent C (Tester) initialized")
        
        debugger = AgentDebugger(
            mcp_client=mcp_client,
            api_usage_tracker=api_tracker,
            local_server=local_server,
            enable_memory=enable_memory
        )
        logger.info("✓ Agent D (Debugger) initialized")
        
        return architect, coder, tester, debugger, local_server, api_tracker
        
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
    
    architect, coder, tester, debugger, local_server, api_tracker = agents_result
    
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
            logger.info(f"Total tokens used: {usage_stats.get('total_tokens', 0)}")
        
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


def main():
    """Main application function"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("MCP Multi-Agent Software Generation System")
    print("WorkflowOrchestrator with Real MCP Agents")
    print("=" * 60)
    
    try:
        # Sample requirements
        requirements = """
Create a simple calculator program in Python that can:
1. Add two numbers
2. Subtract two numbers
3. Multiply two numbers
4. Divide two numbers (with zero division handling)

The program should have:
- A Calculator class with the four basic operations
- Proper error handling for division by zero
- A main function that demonstrates all operations
- Clean, well-documented code
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
        print(f"Iterations: {result['total_iterations']}")
        
        if result['final_status'] == 'success':
            print("\n✅ Code generation and testing completed successfully!")
            
            # Show generated files
            if result.get('final_code_package'):
                code_package = result['final_code_package']
                files = code_package.get('files', {})
                print(f"\n📁 Generated Files ({len(files)}):")
                for filename in files.keys():
                    print(f"   - {filename}")
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


if __name__ == "__main__":
    main()
