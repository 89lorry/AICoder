# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

"""
Test script to verify LocalServer refactoring with FileManager
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.local_server import LocalServer

def test_local_server():
    print("=" * 60)
    print("Testing Refactored LocalServer with FileManager")
    print("=" * 60)
    
    # Create a simple test code package
    code_package = {
        "project_name": "test_refactor",
        "files": {
            "main.py": '''"""Test file"""
print("Hello from refactored LocalServer!")
print("FileManager integration working!")
result = 5 + 3
print(f"5 + 3 = {result}")
'''
        },
        "requirements": [],
        "entry_point": "main.py"
    }
    
    # Initialize local server
    print("\n[Test] Initializing LocalServer...")
    server = LocalServer(workspace_dir="./test_workspace")
    print("[Test] ✓ LocalServer initialized with FileManager")
    
    try:
        # Step 1: Receive code package
        print("\n[Test] Step 1: Receiving code package...")
        server.receive_code_package(code_package)
        print("[Test] ✓ Code package received")
        
        # Step 2: Save code to workspace
        print("\n[Test] Step 2: Saving code to workspace...")
        project_path = server.save_code_to_directory(code_package)
        print(f"[Test] ✓ Code saved to: {project_path}")
        
        # Step 3: Execute the code
        print("\n[Test] Step 3: Executing code...")
        results = server.execute_code(entry_point="main.py", timeout=10)
        print(f"[Test] ✓ Execution completed")
        
        # Step 4: Get execution results
        print("\n[Test] Step 4: Getting execution results...")
        execution_results = server.get_execution_results()
        
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"Success: {execution_results['success']}")
        print(f"Return Code: {execution_results['return_code']}")
        print(f"Execution Time: {execution_results['execution_time']:.3f} seconds")
        
        if execution_results['success']:
            print("\n✓ ALL TESTS PASSED!")
            print("✓ FileManager integration successful!")
            print("✓ Directory operations working correctly!")
        else:
            print("\n✗ Test failed!")
            print(f"Error: {execution_results.get('stderr', 'Unknown error')}")
        
        # Step 5: Cleanup
        print("\n[Test] Step 5: Cleaning up...")
        server.cleanup_workspace()
        print("[Test] ✓ Workspace cleaned up")
        
        return execution_results['success']
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_local_server()
    sys.exit(0 if success else 1)
