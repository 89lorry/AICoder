"""
Server (Local Directory) Module
Runs the written code and manages code packages
"""

import os
import subprocess
import shutil
import time
from datetime import datetime


class LocalServer:
    """Server for running and managing generated code"""
    
    def __init__(self, workspace_dir="./workspace"):
        self.workspace_dir = workspace_dir
        self.current_project = None
        self.current_project_path = None
        self.execution_results = {
            "stdout": "",
            "stderr": "",
            "return_code": None,
            "execution_time": 0,
            "success": False
        }
    
    def receive_code_package(self, code_package):
        """
        Receive final code package from Agent D (Debugger)
        
        Args:
            code_package (dict): Dictionary containing:
                - project_name (str): Name of the project
                - files (dict): Dictionary of filename: content pairs
                - requirements (list): List of required packages (optional)
                - entry_point (str): Main file to execute (default: "main.py")
        
        Returns:
            bool: True if package received successfully
        """
        if not isinstance(code_package, dict):
            raise ValueError("Code package must be a dictionary")
        
        self.current_project = code_package.get("project_name", f"project_{int(time.time())}")
        self.current_project_path = os.path.join(self.workspace_dir, self.current_project)
        
        print(f"[LocalServer] Received code package: {self.current_project}")
        return True
    
    def save_code_to_directory(self, code_package):
        """
        Save code files to local directory
        
        Args:
            code_package (dict): The code package to save
        
        Returns:
            str: Path to the created project directory
        """
        # Create workspace directory if it doesn't exist
        os.makedirs(self.workspace_dir, exist_ok=True)
        
        # Create project directory
        if os.path.exists(self.current_project_path):
            print(f"[LocalServer] Cleaning existing project directory: {self.current_project_path}")
            shutil.rmtree(self.current_project_path)
        
        os.makedirs(self.current_project_path)
        print(f"[LocalServer] Created project directory: {self.current_project_path}")
        
        # Save all code files
        files = code_package.get("files", {})
        for filename, content in files.items():
            filepath = os.path.join(self.current_project_path, filename)
            
            # Create subdirectories if needed (only if filename contains path separators)
            file_dir = os.path.dirname(filepath)
            if file_dir and file_dir != self.current_project_path:
                os.makedirs(file_dir, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"[LocalServer] Saved file: {filename}")
        
        # Save requirements.txt if provided
        requirements = code_package.get("requirements", [])
        if requirements:
            req_path = os.path.join(self.current_project_path, "requirements.txt")
            with open(req_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(requirements))
            print(f"[LocalServer] Saved requirements.txt with {len(requirements)} packages")
        
        return self.current_project_path
    
    def execute_code(self, entry_point="main.py", timeout=30):
        """
        Execute the generated code
        
        Args:
            entry_point (str): The file to execute (default: "main.py")
            timeout (int): Maximum execution time in seconds (default: 30)
        
        Returns:
            dict: Execution results containing stdout, stderr, return_code, etc.
        """
        if not self.current_project_path or not os.path.exists(self.current_project_path):
            raise ValueError("Project path not found. Call save_code_to_directory first.")
        
        entry_file = os.path.join(self.current_project_path, entry_point)
        
        if not os.path.exists(entry_file):
            raise FileNotFoundError(f"Entry point '{entry_point}' not found in project directory")
        
        print(f"\n[LocalServer] Executing: {entry_point}")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Execute the code using subprocess
            # Use just the filename since we're setting cwd
            result = subprocess.run(
                ["python", entry_point],
                cwd=self.current_project_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            # Store execution results
            self.execution_results = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "execution_time": execution_time,
                "success": result.returncode == 0,
                "timestamp": datetime.now().isoformat()
            }
            
            # Print results
            print(f"[LocalServer] Execution completed in {execution_time:.2f} seconds")
            print(f"[LocalServer] Return code: {result.returncode}")
            
            if result.stdout:
                print("\n--- STDOUT ---")
                print(result.stdout)
            
            if result.stderr:
                print("\n--- STDERR ---")
                print(result.stderr)
            
            print("=" * 60)
            
            return self.execution_results
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            self.execution_results = {
                "stdout": "",
                "stderr": f"Execution timeout after {timeout} seconds",
                "return_code": -1,
                "execution_time": execution_time,
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
            print(f"[LocalServer] ERROR: Execution timeout after {timeout} seconds")
            return self.execution_results
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.execution_results = {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "execution_time": execution_time,
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
            print(f"[LocalServer] ERROR: {str(e)}")
            return self.execution_results
    
    def get_execution_results(self):
        """
        Get code execution results and feed back to debugger
        
        Returns:
            dict: Execution results
        """
        return self.execution_results
    
    def return_code_to_ui(self):
        """
        Return working code to UI for display
        
        Returns:
            dict: Package containing code files and execution results
        """
        if not self.current_project_path or not os.path.exists(self.current_project_path):
            return None
        
        # Read all files from the project directory
        code_files = {}
        for root, dirs, files in os.walk(self.current_project_path):
            for filename in files:
                if filename.endswith('.py') or filename == 'requirements.txt':
                    filepath = os.path.join(root, filename)
                    relative_path = os.path.relpath(filepath, self.current_project_path)
                    
                    with open(filepath, 'r', encoding='utf-8') as f:
                        code_files[relative_path] = f.read()
        
        return {
            "project_name": self.current_project,
            "files": code_files,
            "execution_results": self.execution_results,
            "project_path": self.current_project_path
        }
    
    def cleanup_workspace(self):
        """Clean up workspace directory"""
        if self.current_project_path and os.path.exists(self.current_project_path):
            shutil.rmtree(self.current_project_path)
            print(f"[LocalServer] Cleaned up workspace: {self.current_project_path}")
            self.current_project = None
            self.current_project_path = None


# Example usage and testing
# You can test it anytime by running: python server/local_server.py

# from server.local_server import LocalServer

# server = LocalServer(workspace_dir="./workspace")
# server.receive_code_package(code_package)
# server.save_code_to_directory(code_package)
# results = server.execute_code(entry_point="main.py")
# ui_package = server.return_code_to_ui()
if __name__ == "__main__":
    print("=" * 60)
    print("Local Server - Hello World Example")
    print("=" * 60)
    
    # Create a simple "Hello World" code package
    code_package = {
        "project_name": "hello_world_example",
        "files": {
            "main.py": '''"""
                        Hello World Example
                        """

                        def main():
                            print("Hello World!")
                            print("This is a simple example of generated code.")
                            print("The code is running in an isolated workspace.")
                            
                            # Some basic calculations
                            result = 2 + 2
                            print(f"2 + 2 = {result}")
                            
                            # A simple loop
                            print("\\nCounting to 5:")
                            for i in range(1, 6):
                                print(f"  {i}")
                            
                            print("\\nExecution completed successfully!")

                        if __name__ == "__main__":
                            main()
                        ''',
            "utils.py": '''"""
                        Utility functions
                        """

                        def greet(name):
                            """Return a greeting message"""
                            return f"Hello, {name}!"

                        def add(a, b):
                            """Add two numbers"""
                            return a + b
                        '''
        },
        "requirements": [],  # No external requirements for this simple example
        "entry_point": "main.py"
    }
    
    # Initialize local server
    server = LocalServer(workspace_dir="./workspace")
    
    # Process the code package
    try:
        # Step 1: Receive code package
        server.receive_code_package(code_package)
        
        # Step 2: Save code to workspace
        project_path = server.save_code_to_directory(code_package)
        print(f"\n[LocalServer] Code saved to: {project_path}")
        
        # Step 3: Execute the code
        results = server.execute_code(entry_point="main.py", timeout=10)
        
        # Step 4: Get execution results
        execution_results = server.get_execution_results()
        
        print("\n" + "=" * 60)
        print("EXECUTION RESULTS SUMMARY")
        print("=" * 60)
        print(f"Success: {execution_results['success']}")
        print(f"Return Code: {execution_results['return_code']}")
        print(f"Execution Time: {execution_results['execution_time']:.3f} seconds")
        
        # Step 5: Prepare code package for UI
        ui_package = server.return_code_to_ui()
        print(f"\n[LocalServer] Code package ready for UI")
        print(f"[LocalServer] Files in package: {list(ui_package['files'].keys())}")
        
        # Optional: Cleanup (commented out so you can inspect the workspace)
        # server.cleanup_workspace()
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
