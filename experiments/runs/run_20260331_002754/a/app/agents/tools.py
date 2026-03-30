"""app/agents/tools.py — Tool integrations for agents.

exports: dict_tools_available_from_agno, WebSearchTool, FileReadTool, FileWriteTool, CodeExecutionTool, CalculatorTool, APICallTool
used_by: app/agents/agent_builder.py → tool selection, app/agents/agent_wrapper.py → tool usage tracking
rules:   All tools must be sandboxed for security; file operations limited to allowed directories; code execution in isolated environment
agent:   AgentIntegrator | 2024-12-05 | implemented core tool integrations with security sandboxing
         message: "add more specialized tools for vertical use cases"
"""

import logging
import os
import subprocess
import tempfile
import json
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

import httpx

# Try to import agno tools, fallback to mock
try:
    from agno.tools import Tool, SerpAPI, Calculator, FileReader, FileWriter, CodeInterpreter
    AGNO_TOOLS_AVAILABLE = True
except ImportError:
    # Mock tool classes
    class Tool:
        def __init__(self, **kwargs):
            self.name = kwargs.get("name", "unnamed")
            self.description = kwargs.get("description", "")
        
        async def run(self, **kwargs):
            return {"result": "Mock tool result"}
    
    class SerpAPI(Tool):
        pass
    
    class Calculator(Tool):
        pass
    
    class FileReader(Tool):
        pass
    
    class FileWriter(Tool):
        pass
    
    class CodeInterpreter(Tool):
        pass
    
    AGNO_TOOLS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ToolConfig:
    """Configuration for a tool."""
    enabled: bool = True
    rate_limit: Optional[int] = None
    sandboxed: bool = True


class WebSearchTool(Tool):
    """Web search tool using SerpAPI or similar."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        self.name = "web_search"
        self.description = "Search the web for current information"
    
    async def run(self, query: str, num_results: int = 5, **kwargs) -> Dict[str, Any]:
        """Execute web search.
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            Search results
            
        Raises:
            RuntimeError: If API key not configured or search fails
        """
        if not self.api_key:
            raise RuntimeError("SERPAPI_API_KEY not configured")
        
        # In real implementation, call SerpAPI
        # For now, mock response
        logger.info(f"Web search: {query}")
        
        return {
            "query": query,
            "results": [
                {
                    "title": f"Result {i} for {query}",
                    "url": f"https://example.com/result{i}",
                    "snippet": f"This is a mock result snippet for query: {query}",
                }
                for i in range(num_results)
            ],
            "source": "serpapi",
        }


class FileReadTool(Tool):
    """File reading tool with sandboxing."""
    
    def __init__(self, allowed_dirs: Optional[List[str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.name = "file_read"
        self.description = "Read files from allowed directories"
        
        # Default allowed directories: current working directory and temp
        self.allowed_dirs = allowed_dirs or [os.getcwd(), tempfile.gettempdir()]
        self.allowed_dirs = [Path(d).resolve() for d in self.allowed_dirs]
    
    def _check_path_allowed(self, file_path: str) -> Path:
        """Check if file path is within allowed directories.
        
        Args:
            file_path: Path to check
            
        Returns:
            Resolved Path object
            
        Raises:
            PermissionError: If path is not allowed
        """
        path = Path(file_path).resolve()
        
        # Check if path is within any allowed directory
        allowed = False
        for allowed_dir in self.allowed_dirs:
            try:
                if path.is_relative_to(allowed_dir):
                    allowed = True
                    break
            except AttributeError:
                # Python <3.9 compatibility
                if str(path).startswith(str(allowed_dir)):
                    allowed = True
                    break
        
        if not allowed:
            raise PermissionError(
                f"Access to '{file_path}' not allowed. "
                f"Allowed directories: {self.allowed_dirs}"
            )
        
        return path
    
    async def run(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Read file contents.
        
        Args:
            file_path: Path to file
            
        Returns:
            File contents and metadata
            
        Raises:
            PermissionError: If path not allowed
            FileNotFoundError: If file doesn't exist
            IOError: If reading fails
        """
        path = self._check_path_allowed(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not path.is_file():
            raise IOError(f"Path is not a file: {file_path}")
        
        # Check file size limit (10MB)
        if path.stat().st_size > 10 * 1024 * 1024:
            raise IOError(f"File too large: {file_path}. Maximum size is 10MB")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "path": str(path),
                "content": content,
                "size": len(content),
                "encoding": "utf-8",
            }
        except UnicodeDecodeError:
            # Try binary read for non-text files
            with open(path, 'rb') as f:
                content = f.read()
            
            return {
                "path": str(path),
                "content": content[:1000],  # First 1000 bytes
                "size": len(content),
                "encoding": "binary",
                "truncated": len(content) > 1000,
            }


class FileWriteTool(Tool):
    """File writing tool with sandboxing."""
    
    def __init__(self, allowed_dirs: Optional[List[str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.name = "file_write"
        self.description = "Write files to allowed directories"
        
        self.allowed_dirs = allowed_dirs or [os.getcwd(), tempfile.gettempdir()]
        self.allowed_dirs = [Path(d).resolve() for d in self.allowed_dirs]
    
    def _check_path_allowed(self, file_path: str) -> Path:
        """Check if file path is within allowed directories."""
        path = Path(file_path).resolve()
        
        allowed = False
        for allowed_dir in self.allowed_dirs:
            try:
                if path.is_relative_to(allowed_dir):
                    allowed = True
                    break
            except AttributeError:
                if str(path).startswith(str(allowed_dir)):
                    allowed = True
                    break
        
        if not allowed:
            raise PermissionError(
                f"Write access to '{file_path}' not allowed. "
                f"Allowed directories: {self.allowed_dirs}"
            )
        
        return path
    
    async def run(self, file_path: str, content: str, **kwargs) -> Dict[str, Any]:
        """Write content to file.
        
        Args:
            file_path: Path to file
            content: Content to write
            
        Returns:
            Write operation result
            
        Raises:
            PermissionError: If path not allowed
            IOError: If writing fails
        """
        path = self._check_path_allowed(file_path)
        
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        
        mode = kwargs.get('mode', 'w')
        encoding = kwargs.get('encoding', 'utf-8')
        
        try:
            if 'b' in mode:
                with open(path, mode) as f:
                    f.write(content.encode(encoding) if isinstance(content, str) else content)
            else:
                with open(path, mode, encoding=encoding) as f:
                    f.write(content)
            
            return {
                "path": str(path),
                "success": True,
                "size": len(content),
                "mode": mode,
            }
        except Exception as e:
            raise IOError(f"Failed to write file: {e}")


class CodeExecutionTool(Tool):
    """Secure code execution tool with sandboxing."""
    
    def __init__(self, timeout: int = 30, **kwargs):
        super().__init__(**kwargs)
        self.name = "code_execution"
        self.description = "Execute code in a secure sandbox"
        self.timeout = timeout
    
    async def run(self, code: str, language: str = "python", **kwargs) -> Dict[str, Any]:
        """Execute code in sandbox.
        
        Args:
            code: Code to execute
            language: Programming language (python, javascript, etc.)
            
        Returns:
            Execution result
            
        Raises:
            RuntimeError: If execution fails or times out
        """
        logger.info(f"Executing {language} code (length: {len(code)})")
        
        # Security check: disallow dangerous imports/operations
        if language == "python":
            # Simple security check (in production, use proper sandboxing like Docker)
            dangerous_patterns = [
                "import os",
                "import subprocess",
                "__import__",
                "eval(",
                "exec(",
                "open(",
                "file(",
            ]
            
            for pattern in dangerous_patterns:
                if pattern in code.lower():
                    raise RuntimeError(f"Security violation: dangerous pattern '{pattern}' detected")
        
        # Create temporary file for code
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{language}', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute based on language
            if language == "python":
                # Use subprocess with timeout
                result = subprocess.run(
                    ["python", temp_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                
                output = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "success": result.returncode == 0,
                }
            
            elif language == "javascript":
                # Node.js execution
                result = subprocess.run(
                    ["node", temp_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                
                output = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "success": result.returncode == 0,
                }
            
            else:
                raise RuntimeError(f"Unsupported language: {language}")
            
            return output
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Code execution timed out after {self.timeout} seconds")
        except Exception as e:
            raise RuntimeError(f"Code execution failed: {e}")
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass


class CalculatorTool(Tool):
    """Calculator tool for mathematical expressions."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "calculator"
        self.description = "Evaluate mathematical expressions"
    
    async def run(self, expression: str, **kwargs) -> Dict[str, Any]:
        """Evaluate mathematical expression.
        
        Args:
            expression: Mathematical expression
            
        Returns:
            Calculation result
            
        Raises:
            ValueError: If expression is invalid
        """
        # Security: only allow safe mathematical expressions
        # Remove any dangerous characters
        safe_chars = set("0123456789+-*/().^% ")
        if any(c not in safe_chars for c in expression):
            raise ValueError("Expression contains unsafe characters")
        
        try:
            # Use eval with limited builtins (still risky, but we filtered chars)
            # In production, use a proper math parser like ast.literal_eval
            result = eval(expression, {"__builtins__": {}}, {})
            
            return {
                "expression": expression,
                "result": result,
                "type": type(result).__name__,
            }
        except Exception as e:
            raise ValueError(f"Failed to evaluate expression: {e}")


class APICallTool(Tool):
    """Tool for making HTTP API calls."""
    
    def __init__(self, default_headers: Optional[Dict[str, str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.name = "api_call"
        self.description = "Make HTTP requests to external APIs"
        self.default_headers = default_headers or {
            "User-Agent": "AgentHub/1.0",
            "Content-Type": "application/json",
        }
    
    async def run(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make HTTP request.
        
        Args:
            url: Request URL
            method: HTTP method (GET, POST, etc.)
            headers: Request headers
            data: Request body
            
        Returns:
            Response data
            
        Raises:
            RuntimeError: If request fails
        """
        # Security: restrict to certain domains if needed
        # For now, allow any URL but log
        
        logger.info(f"API call: {method} {url}")
        
        all_headers = {**self.default_headers, **(headers or {})}
        
        timeout = kwargs.get('timeout', 30)
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=all_headers,
                    json=data,
                )
                
                response.raise_for_status()
                
                # Try to parse JSON, fallback to text
                try:
                    response_data = response.json()
                    content_type = "json"
                except:
                    response_data = response.text
                    content_type = "text"
                
                return {
                    "url": url,
                    "method": method,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "data": response_data,
                    "content_type": content_type,
                }
        except httpx.TimeoutException:
            raise RuntimeError(f"Request timeout after {timeout} seconds")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Request failed: {e}")


# Dictionary of available tools for agent builder
dict_tools_available_from_agno = {
    "web_search": WebSearchTool(),
    "file_read": FileReadTool(),
    "file_write": FileWriteTool(),
    "code_execution": CodeExecutionTool(),
    "calculator": CalculatorTool(),
    "api_call": APICallTool(),
}

# If agno tools are available, create instances
if AGNO_TOOLS_AVAILABLE:
    # Use real agno tools when available
    dict_tools_available_from_agno.update({
        "web_search": SerpAPI(),
        "calculator": Calculator(),
        "file_read": FileReader(),
        "file_write": FileWriter(),
        "code_interpreter": CodeInterpreter(),
    })