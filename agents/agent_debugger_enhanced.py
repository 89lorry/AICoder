# Project Group 3
# Enhanced Response Parsing Module for Debugger
# This file contains robust parsing methods to extract fixed code from AI responses

import re
import logging

class EnhancedResponseParser:
    """Robust parser for AI debugger responses with multiple fallback strategies"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def parse_debugger_response(self, response_text: str) -> dict:
        """
        Robust parser for debugger AI responses with multiple fallback strategies
        
        Args:
            response_text: Raw text response from AI
            
        Returns:
            Dictionary with 'analysis' and 'fixed_files' keys
        """
        result = {
            "analysis": "",
            "fixed_files": {}
        }
        
        self.logger.info("Starting robust response parsing...")
        
        # Step 1: Clean response - remove common markdown artifacts
        cleaned_text = self._clean_response_text(response_text)
        
        # Step 2: Extract analysis section
        result["analysis"] = self._extract_analysis(cleaned_text)
        
        # Step 3: Try multiple parsing strategies for code files
        parsing_strategies = [
            ("FILE_START/END markers", self._parse_file_start_end_markers),
            ("Markdown code blocks", self._parse_markdown_code_blocks),
            ("Filename headers", self._parse_filename_headers),
            ("Fallback heuristic", self._parse_fallback_heuristic)
        ]
        
        for i, (strategy_name, strategy_func) in enumerate(parsing_strategies, 1):
            self.logger.info(f"Trying parsing strategy {i}/{len(parsing_strategies)}: {strategy_name}")
            
            try:
                fixed_files = strategy_func(cleaned_text)
                if fixed_files:
                    result["fixed_files"] = fixed_files
                    self.logger.info(f"✓ Successfully parsed {len(fixed_files)} file(s) using {strategy_name}")
                    for filename in fixed_files.keys():
                        self.logger.info(f"  - {filename}: {len(fixed_files[filename])} chars")
                    break
            except Exception as e:
                self.logger.warning(f"✗ Strategy '{strategy_name}' failed: {str(e)}")
                continue
        
        if not result["fixed_files"]:
            self.logger.error("❌ All parsing strategies failed - no files extracted")
            self.logger.debug(f"Response text (first 500 chars): {cleaned_text[:500]}")
        
        return result
    
    def _clean_response_text(self, text: str) -> str:
        """Remove common markdown and formatting artifacts"""
        cleaned = text
        
        # Remove markdown code block markers but preserve content
        # This handles: ```python\ncode\n``` or ```\ncode\n```
        cleaned = re.sub(r'^```(?:python|py)?\s*\n', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\n```\s*$', '', cleaned, flags=re.MULTILINE)
        
        # Remove inline markdown code markers (`) but only if they're wrapping filenames
        cleaned = re.sub(r'`([a-zA-Z0-9_]+\.py)`', r'\1', cleaned)
        
        return cleaned
    
    def _extract_analysis(self, text: str) -> str:
        """Extract analysis section from response"""
        if 'ANALYSIS_START' in text and 'ANALYSIS_END' in text:
            start = text.find('ANALYSIS_START')
            end = text.find('ANALYSIS_END')
            if start < end:
                analysis = text[start:end+12].strip()
                self.logger.info(f"Extracted analysis section: {len(analysis)} chars")
                return analysis
        
        # Fallback: Look for analysis-like content at the beginning
        lines = text.split('\n')
        analysis_lines = []
        for line in lines[:20]:  # Check first 20 lines
            if any(keyword in line.lower() for keyword in ['issue', 'problem', 'fix', 'error', 'bug']):
                analysis_lines.append(line)
        
        if analysis_lines:
            return '\n'.join(analysis_lines)
        
        return "No analysis found"
    
    def _parse_file_start_end_markers(self, text: str) -> dict:
        """
        Strategy 1: Parse FILE_START: filename / FILE_END markers (original format)
        """
        fixed_files = {}
        
        # Original pattern with more flexibility
        patterns = [
            r'FILE_START:\s*(.+?)\n(.*?)FILE_END',  # Original
            r'FILE_START\s*:\s*(.+?)(?:\n|\r\n)(.*?)FILE_END',  # Extra spaces
            r'FILE[-_]START:\s*(.+?)\n(.*?)FILE[-_]END',  # Underscore variant
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            
            for filename, content in matches:
                filename = filename.strip()
                content = content.strip()
                
                # Remove any remaining markdown code blocks inside
                content = re.sub(r'^```(?:python|py)?\s*\n', '', content, flags=re.MULTILINE)
                content = re.sub(r'\n```\s*$', '', content, flags=re.MULTILINE)
                
                if filename and content and len(content) > 10:
                    fixed_files[filename] = content
            
            if fixed_files:
                break  # Stop if we found files with this pattern
        
        return fixed_files
    
    def _parse_markdown_code_blocks(self, text: str) -> dict:
        """
        Strategy 2: Parse markdown code blocks with filename comments
        Handles: # filename.py followed by ```python code ```
        """
        fixed_files = {}
        
        # Pattern 1: Filename as header before code block
        # # filename.py or ## filename.py or **filename.py**
        pattern1 = r'(?:#+\s*|\*{2})([a-zA-Z0-9_]+\.py)\**\s*\n+```(?:python|py)?\s*\n(.*?)\n```'
        matches1 = re.findall(pattern1, text, re.DOTALL | re.MULTILINE)
        
        for filename, content in matches1:
            filename = filename.strip()
            content = content.strip()
            if filename and content:
                fixed_files[filename] = content
        
        # Pattern 2: Filename as comment inside code block
        # ```python followed by # filename.py comment inside
        if not fixed_files:
            pattern2 = r'```(?:python|py)?\s*\n#\s*([a-zA-Z0-9_]+\.py)\s*\n(.*?)\n```'
            matches2 = re.findall(pattern2, text, re.DOTALL)
            for filename, content in matches2:
                filename = filename.strip()
                content = content.strip()
                if filename and content:
                    fixed_files[filename] = content
        
        # Pattern 3: Look for filename mentions followed by code blocks
        if not fixed_files:
            # Find all .py filenames mentioned
            filenames_mentioned = re.findall(r'\b([a-zA-Z0-9_]+\.py)\b', text)
            # Find all code blocks
            code_blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)\n```', text, re.DOTALL)
            
            # Match them up (simplistic approach: same count = match by position)
            if len(filenames_mentioned) == len(code_blocks):
                for filename, content in zip(filenames_mentioned, code_blocks):
                    content = content.strip()
                    if content and len(content) > 20:
                        fixed_files[filename] = content
        
        return fixed_files
    
    def _parse_filename_headers(self, text: str) -> dict:
        """
        Strategy 3: Parse files with filename headers followed by code
        Handles various header formats:
        - === filename.py ===
        - --- filename.py ---
        - filename.py:
        - [filename.py]
        """
        fixed_files = {}
        
        # Split by common header patterns
        patterns = [
            (r'\n===+\s*([a-zA-Z0-9_]+\.py)\s*===+\n(.*?)(?=\n===+|$)', "triple equals"),
            (r'\n---+\s*([a-zA-Z0-9_]+\.py)\s*---+\n(.*?)(?=\n---+|$)', "triple dashes"),
            (r'\n\[([a-zA-Z0-9_]+\.py)\]\n(.*?)(?=\n\[|$)', "square brackets"),
            (r'\n([a-zA-Z0-9_]+\.py):\s*\n(.*?)(?=\n[a-zA-Z0-9_]+\.py:|$)', "colon separator")
        ]
        
        for pattern, pattern_name in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for filename, content in matches:
                filename = filename.strip()
                content = content.strip()
                
                # Remove markdown code blocks if present
                content = re.sub(r'^```(?:python|py)?\s*\n', '', content, flags=re.MULTILINE)
                content = re.sub(r'\n```\s*$', '', content, flags=re.MULTILINE)
                
                if filename and content and len(content) > 20:  # Ensure meaningful content
                    fixed_files[filename] = content
            
            if fixed_files:
                self.logger.info(f"Found files using pattern: {pattern_name}")
                break  # Stop if we found files with this pattern
        
        return fixed_files
    
    def _parse_fallback_heuristic(self, text: str) -> dict:
        """
        Strategy 4: Last resort - extract any Python code blocks and guess filenames
        """
        fixed_files = {}
        
        # Find all code blocks (markdown or plain Python code)
        code_blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)\n```', text, re.DOTALL)
        
        if not code_blocks:
            # Look for Python-like code (starts with def, class, import, etc.)
            lines = text.split('\n')
            current_block = []
            in_code = False
            
            for line in lines:
                if re.match(r'^(def |class |import |from |if |while |for |@)', line):
                    in_code = True
                    current_block.append(line)
                elif in_code:
                    if line.strip() == '' or line.startswith(' ') or line.startswith('\t'):
                        current_block.append(line)
                    else:
                        if len(current_block) > 5:  # Meaningful code block
                            code_blocks.append('\n'.join(current_block))
                        current_block = []
                        in_code = False
            
            # Add last block
            if len(current_block) > 5:
                code_blocks.append('\n'.join(current_block))
        
        # Try to identify filename from content or context
        for i, code_block in enumerate(code_blocks):
            code_block = code_block.strip()
            if not code_block or len(code_block) < 20:
                continue
            
            # Look for filename hints in the code
            filename = None
            
            # Check for docstring or comment with filename
            filename_match = re.search(r'(?:file(?:name)?|module):\s*([a-zA-Z0-9_]+\.py)', code_block, re.IGNORECASE)
            if filename_match:
                filename = filename_match.group(1)
            
            # Check if it's a test file
            elif 'import pytest' in code_block or 'def test_' in code_block or 'import unittest' in code_block:
                filename = 'test_main.py'
            
            # Check if it's main application code
            elif 'if __name__' in code_block or 'def main(' in code_block:
                filename = 'main.py'
            
            # Look in surrounding context for filename mentions
            if not filename:
                # Search backwards from code block position
                code_pos = text.find(code_block)
                if code_pos > 0:
                    context = text[max(0, code_pos-200):code_pos]
                    context_match = re.search(r'([a-zA-Z0-9_]+\.py)', context)
                    if context_match:
                        filename = context_match.group(1)
            
            # Default fallback names
            if not filename:
                if i == 0:
                    filename = 'main.py'
                else:
                    filename = f'file_{i}.py'
            
            # Avoid duplicates
            if filename in fixed_files:
                base, ext = filename.rsplit('.', 1)
                filename = f'{base}_{i}.{ext}'
            
            fixed_files[filename] = code_block
            self.logger.warning(f"Heuristically identified file: {filename}")
        
        return fixed_files
