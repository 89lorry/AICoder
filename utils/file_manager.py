"""
File Manager Module
Utilities for managing file operations
"""

import os
import json
import shutil


class FileManager:
    """Utility class for file management operations"""
    
    def __init__(self):
        pass
    
    def create_directory(self, path, exist_ok=True):
        """
        Create a directory if it doesn't exist
        
        Args:
            path (str): Directory path to create
            exist_ok (bool): If True, don't raise error if directory exists
        
        Returns:
            str: Path to the created directory
        """
        os.makedirs(path, exist_ok=exist_ok)
        return path
    
    def delete_directory(self, path):
        """
        Delete a directory and all its contents
        
        Args:
            path (str): Directory path to delete
        
        Returns:
            bool: True if deleted successfully
        """
        if os.path.exists(path):
            shutil.rmtree(path)
            return True
        return False
    
    def directory_exists(self, path):
        """
        Check if a directory exists
        
        Args:
            path (str): Directory path to check
        
        Returns:
            bool: True if directory exists
        """
        return os.path.exists(path) and os.path.isdir(path)
    
    def file_exists(self, filepath):
        """
        Check if a file exists
        
        Args:
            filepath (str): File path to check
        
        Returns:
            bool: True if file exists
        """
        return os.path.exists(filepath) and os.path.isfile(filepath)
    
    def write_file(self, filepath, content, encoding='utf-8'):
        """
        Write content to a file
        
        Args:
            filepath (str): Path to the file
            content (str): Content to write
            encoding (str): File encoding (default: 'utf-8')
        
        Returns:
            str: Path to the written file
        """
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(filepath)
        if parent_dir:
            self.create_directory(parent_dir)
        
        with open(filepath, 'w', encoding=encoding) as f:
            f.write(content)
        
        return filepath
    
    def read_file(self, filepath, encoding='utf-8'):
        """
        Read content from a file
        
        Args:
            filepath (str): Path to the file
            encoding (str): File encoding (default: 'utf-8')
        
        Returns:
            str: File content
        """
        with open(filepath, 'r', encoding=encoding) as f:
            return f.read()
    
    def delete_file(self, filepath):
        """
        Delete a file
        
        Args:
            filepath (str): Path to the file to delete
        
        Returns:
            bool: True if deleted successfully
        """
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    
    def list_files(self, directory, recursive=True, pattern=None):
        """
        List all files in a directory
        
        Args:
            directory (str): Directory path
            recursive (bool): If True, list files recursively
            pattern (str): Optional file pattern to match (e.g., '*.py')
        
        Returns:
            list: List of file paths
        """
        files = []
        
        if not os.path.exists(directory):
            return files
        
        if recursive:
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    if pattern is None or filename.endswith(pattern.replace('*', '')):
                        files.append(os.path.join(root, filename))
        else:
            for item in os.listdir(directory):
                filepath = os.path.join(directory, item)
                if os.path.isfile(filepath):
                    if pattern is None or item.endswith(pattern.replace('*', '')):
                        files.append(filepath)
        
        return files
    
    def write_multiple_files(self, base_dir, files_dict, clean_first=False):
        """
        Write multiple files to a directory
        
        Args:
            base_dir (str): Base directory path
            files_dict (dict): Dictionary mapping filenames to content
            clean_first (bool): If True, delete existing directory first
        
        Returns:
            list: List of written file paths
        """
        # Clean directory if requested
        if clean_first and os.path.exists(base_dir):
            self.delete_directory(base_dir)
        
        # Create base directory
        self.create_directory(base_dir)
        
        written_files = []
        for filename, content in files_dict.items():
            filepath = os.path.join(base_dir, filename)
            self.write_file(filepath, content)
            written_files.append(filepath)
        
        return written_files
    
    def read_directory_files(self, directory, extensions=None):
        """
        Read all files in a directory and return as dictionary
        
        Args:
            directory (str): Directory path
            extensions (list): Optional list of file extensions to include (e.g., ['.py', '.txt'])
        
        Returns:
            dict: Dictionary mapping relative paths to file contents
        """
        files_dict = {}
        
        if not os.path.exists(directory):
            return files_dict
        
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(root, filename)
                
                # Check extension filter
                if extensions is not None:
                    if not any(filename.endswith(ext) for ext in extensions):
                        continue
                
                # Get relative path
                relative_path = os.path.relpath(filepath, directory)
                
                # Read file content
                try:
                    content = self.read_file(filepath)
                    files_dict[relative_path] = content
                except Exception as e:
                    print(f"Warning: Could not read file {filepath}: {str(e)}")
        
        return files_dict
    
    def save_json(self, filepath, data, indent=2):
        """
        Save data as JSON file
        
        Args:
            filepath (str): Path to save JSON file
            data: Data to save (must be JSON serializable)
            indent (int): JSON indentation (default: 2)
        
        Returns:
            str: Path to the saved file
        """
        json_content = json.dumps(data, indent=indent)
        return self.write_file(filepath, json_content)
    
    def load_json(self, filepath):
        """
        Load data from JSON file
        
        Args:
            filepath (str): Path to JSON file
        
        Returns:
            Data loaded from JSON file
        """
        content = self.read_file(filepath)
        return json.loads(content)
    
    def get_file_size(self, filepath):
        """
        Get the size of a file in bytes
        
        Args:
            filepath (str): Path to the file
        
        Returns:
            int: File size in bytes
        """
        if os.path.exists(filepath):
            return os.path.getsize(filepath)
        return 0
    
    def join_path(self, *paths):
        """
        Join path components
        
        Args:
            *paths: Path components to join
        
        Returns:
            str: Joined path
        """
        return os.path.join(*paths)
