"""
Main Application Entry Point
Multi-Agent MCP System for Software Generation
"""

from frontend.ui import UI
from backend.mcp_handler import MCPHandler
from config.settings import Settings


def main():
    """Main application function"""
    print("=" * 60)
    print("MCP Multi-Agent Software Generation System")
    print("=" * 60)
    
    # Initialize components
    ui = UI()
    mcp_handler = MCPHandler()
    
    # Get user input
    user_input = ui.get_user_input()
    
    # Process request through agent pipeline
    result = mcp_handler.process_request(user_input)
    
    # Display results
    ui.display_results()
    ui.display_api_usage()
    
    print("\nProcess completed successfully!")


if __name__ == "__main__":
    main()
