"""
Main Application Entry Point
Multi-Agent MCP System for Software Generation
"""

from dotenv import load_dotenv

# Ensure environment variables are available before importing modules that rely on them.
load_dotenv()

from frontend.ui import UI
from backend.mcp_handler import MCPHandler


def main():
    """Main application function"""
    print("=" * 60)
    print("MCP Multi-Agent Software Generation System")
    print("=" * 60)
    
    # Initialize components
    ui = UI()
    mcp_handler = MCPHandler()
    
    # Get user input (fallback to sample request until UI implemented)
    user_input = ui.get_user_input()
    if user_input is None:
        user_input = {
            "description": "Sample CLI for tracking daily habits",
            "requirements": [
                "Add habits and mark completion per day",
                "Persist data to local JSON file",
                "Show weekly summary report",
            ],
        }
        print("[main] UI not implemented yet – using sample input for backend smoke test.\n")
    
    # Process request through agent pipeline
    result = mcp_handler.process_request(user_input)
    
    # Display results
    ui.display_results()
    ui.display_api_usage()
    
    print("\nProcess completed successfully!")
    return result


if __name__ == "__main__":
    main()
