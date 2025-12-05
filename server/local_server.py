"""
Server (Local Directory) Module
Runs the written code and manages code packages
"""

import os
import subprocess
import time
from datetime import datetime
from utils.file_manager import FileManager


class LocalServer:
    """Server for running and managing generated code"""
    
    def __init__(self, workspace_dir="./workspace"):
        self.workspace_dir = workspace_dir
        self.current_project = None
        self.current_project_path = None
        self.file_manager = FileManager()
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
        self.current_project_path = self.file_manager.join_path(self.workspace_dir, self.current_project)
        
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
        self.file_manager.create_directory(self.workspace_dir)
        
        # Create project directory (clean first if exists)
        if self.file_manager.directory_exists(self.current_project_path):
            print(f"[LocalServer] Cleaning existing project directory: {self.current_project_path}")
            self.file_manager.delete_directory(self.current_project_path)
        
        self.file_manager.create_directory(self.current_project_path)
        print(f"[LocalServer] Created project directory: {self.current_project_path}")
        
        # Save all code files using FileManager
        files = code_package.get("files", {})
        for filename, content in files.items():
            filepath = self.file_manager.join_path(self.current_project_path, filename)
            self.file_manager.write_file(filepath, content)
            print(f"[LocalServer] Saved file: {filename}")
        
        # Save requirements.txt if provided
        requirements = code_package.get("requirements", [])
        if requirements:
            req_path = self.file_manager.join_path(self.current_project_path, "requirements.txt")
            req_content = '\n'.join(requirements)
            self.file_manager.write_file(req_path, req_content)
            print(f"[LocalServer] Saved requirements.txt with {len(requirements)} packages")
        
        return self.current_project_path
    
    def save_file(self, filename, content, project_path=None):
        """
        Save a single file to the project directory
        
        Args:
            filename (str): Name of the file to save
            content (str): Content of the file
            project_path (str, optional): Project path to save to. If None, uses current_project_path
        
        Returns:
            str: Path to the saved file
        """
        target_path = project_path or self.current_project_path
        if not target_path:
            raise ValueError("No project path available. Call receive_code_package() first or provide project_path.")
        
        # Ensure project directory exists
        self.file_manager.create_directory(target_path)
        
        # Save file using FileManager
        filepath = self.file_manager.join_path(target_path, filename)
        self.file_manager.write_file(filepath, content)
        
        print(f"[LocalServer] Saved file: {filename}")
        return filepath
    
    def execute_code(self, entry_point="main.py", timeout=30):
        """
        Execute the generated code
        
        Args:
            entry_point (str): The file to execute (default: "main.py")
            timeout (int): Maximum execution time in seconds (default: 30)
        
        Returns:
            dict: Execution results containing stdout, stderr, return_code, etc.
        """
        if not self.current_project_path or not self.file_manager.directory_exists(self.current_project_path):
            raise ValueError("Project path not found. Call save_code_to_directory first.")
        
        entry_file = self.file_manager.join_path(self.current_project_path, entry_point)
        
        if not self.file_manager.file_exists(entry_file):
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
    
    def run_tests(self, test_file="test_main.py", timeout=300):
        """
        Run pytest tests in the current project directory
        
        Args:
            test_file (str): Test file to run (default: "test_main.py")
            timeout (int): Maximum execution time in seconds (default: 300)
        
        Returns:
            dict: Test execution results containing exit_code, passed, stdout, stderr, etc.
        """
        if not self.current_project_path or not self.file_manager.directory_exists(self.current_project_path):
            raise ValueError("Project path not found. Call save_code_to_directory first.")
        
        test_file_path = self.file_manager.join_path(self.current_project_path, test_file)
        
        if not self.file_manager.file_exists(test_file_path):
            return {
                "exit_code": -1,
                "passed": False,
                "stdout": "",
                "stderr": f"Test file '{test_file}' not found in project directory",
                "output": f"Test file '{test_file}' not found in project directory",
                "error": f"Test file not found: {test_file}",
                "test_file": test_file_path,
                "timestamp": datetime.now().isoformat()
            }
        
        print(f"\n[LocalServer] Running tests: {test_file}")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Try to run pytest with JSON report plugin first
            result = subprocess.run(
                ["python", "-m", "pytest", test_file, "-v", "--tb=short", 
                 "--json-report", "--json-report-file=pytest_report.json"],
                cwd=self.current_project_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # If pytest-json-report is not installed, fall back to regular pytest
            if "No module named" in result.stderr and "json_report" in result.stderr:
                print("[LocalServer] JSON report plugin not available, using standard pytest")
                result = subprocess.run(
                    ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
                    cwd=self.current_project_path,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            
            execution_time = time.time() - start_time
            
            # Try to load JSON report if available
            json_report = None
            json_report_path = self.file_manager.join_path(self.current_project_path, "pytest_report.json")
            if self.file_manager.file_exists(json_report_path):
                try:
                    json_report = self.file_manager.load_json(json_report_path)
                except Exception as e:
                    print(f"[LocalServer] Warning: Could not load JSON report: {str(e)}")
            
            # Store execution results
            test_output = result.stdout + result.stderr
            self.execution_results = {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output": test_output,
                "return_code": result.returncode,
                "execution_time": execution_time,
                "success": result.returncode == 0,
                "passed": result.returncode == 0,
                "json_report": json_report,
                "test_file": test_file_path,
                "timestamp": datetime.now().isoformat()
            }
            
            # Print results
            print(f"[LocalServer] Test execution completed in {execution_time:.2f} seconds")
            print(f"[LocalServer] Return code: {result.returncode}")
            print(f"[LocalServer] Tests {'PASSED' if result.returncode == 0 else 'FAILED'}")
            
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
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Test execution timeout after {timeout} seconds",
                "output": f"Test execution timeout after {timeout} seconds",
                "return_code": -1,
                "execution_time": execution_time,
                "success": False,
                "passed": False,
                "error": "Test execution timed out",
                "test_file": test_file_path,
                "timestamp": datetime.now().isoformat()
            }
            print(f"[LocalServer] ERROR: Test execution timeout after {timeout} seconds")
            return self.execution_results
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.execution_results = {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "output": str(e),
                "return_code": -1,
                "execution_time": execution_time,
                "success": False,
                "passed": False,
                "error": str(e),
                "test_file": test_file_path,
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
        if not self.current_project_path or not self.file_manager.directory_exists(self.current_project_path):
            return None
        
        # Read all Python and requirements files using FileManager
        code_files = self.file_manager.read_directory_files(
            self.current_project_path,
            extensions=['.py', 'requirements.txt']
        )
        
        return {
            "project_name": self.current_project,
            "files": code_files,
            "execution_results": self.execution_results,
            "project_path": self.current_project_path
        }
    
    def cleanup_workspace(self):
        """Clean up workspace directory"""
        if self.current_project_path and self.file_manager.directory_exists(self.current_project_path):
            self.file_manager.delete_directory(self.current_project_path)
            print(f"[LocalServer] Cleaned up workspace: {self.current_project_path}")
            self.current_project = None
            self.current_project_path = None


# Example usage and testing
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
        "requirements": [],
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
