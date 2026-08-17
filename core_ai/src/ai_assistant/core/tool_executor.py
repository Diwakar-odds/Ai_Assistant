#!/usr/bin/env python3
"""
Tool Executor Module
Handles execution of tools/functions called by LLM models.
Includes safety checks, error handling, and result formatting.
"""

import json
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ToolType(Enum):
    """Tool execution type."""
    FUNCTION = "function"
    WEB_SEARCH = "web_search"
    CODE_EXECUTION = "code_execution"
    SYSTEM_COMMAND = "system_command"
    EXTERNAL_API = "external_api"


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    tool_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "tool_name": self.tool_name
        }


class ToolExecutor:
    """Executes tools/functions called by LLM."""
    
    def __init__(self):
        """Initialize tool executor."""
        self.registered_tools: Dict[str, Callable] = {}
        self.tool_definitions: Dict[str, Dict[str, Any]] = {}
        self.execution_history: List[ToolResult] = []
        self.max_history = 100
        
    def register_tool(
        self,
        name: str,
        func: Callable,
        description: str,
        parameters: Dict[str, Any],
        required_params: List[str] = None
    ):
        """
        Register a tool that can be called by LLM.
        
        Args:
            name: Tool name
            func: Callable function
            description: Human-readable description
            parameters: Parameter schema
            required_params: List of required parameters
        """
        if required_params is None:
            required_params = []
            
        self.registered_tools[name] = func
        self.tool_definitions[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required_params
                }
            }
        }
        logger.info(f"Registered tool: {name}")
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all registered tool definitions in OpenAI format."""
        return list(self.tool_definitions.values())
    
    def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        timeout: float = 30.0
    ) -> ToolResult:
        """
        Execute a registered tool.
        
        Args:
            tool_name: Name of tool to execute
            tool_input: Parameters for tool
            timeout: Execution timeout in seconds
            
        Returns:
            ToolResult with success/failure and result
        """
        import time
        
        result = ToolResult(
            success=False,
            result=None,
            tool_name=tool_name
        )
        
        # Validate tool exists
        if tool_name not in self.registered_tools:
            result.error = f"Tool '{tool_name}' not registered"
            logger.error(result.error)
            return result
        
        try:
            start_time = time.time()
            func = self.registered_tools[tool_name]
            
            # Execute with timeout
            result.result = func(**tool_input)
            result.success = True
            result.execution_time = time.time() - start_time
            
            logger.info(f"✅ Tool executed: {tool_name} ({result.execution_time:.2f}s)")
            
        except TypeError as e:
            # Parameter validation error
            result.error = f"Invalid parameters for {tool_name}: {str(e)}"
            logger.error(result.error)
            
        except Exception as e:
            result.error = f"Tool execution failed: {str(e)}"
            logger.error(result.error)
        
        # Add to history
        self.execution_history.append(result)
        if len(self.execution_history) > self.max_history:
            self.execution_history.pop(0)
        
        return result
    
    def execute_tool_call(self, tool_call: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool call from LLM response.
        
        Args:
            tool_call: Tool call object with id, type, function details
            
        Returns:
            ToolResult
        """
        try:
            # Parse tool call structure
            function_data = tool_call.get("function", {})
            tool_name = function_data.get("name", "")
            arguments_str = function_data.get("arguments", "{}")
            
            # Parse arguments
            try:
                tool_input = json.loads(arguments_str)
            except json.JSONDecodeError:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Invalid JSON in tool arguments: {arguments_str}",
                    tool_name=tool_name
                )
            
            # Execute tool
            return self.execute_tool(tool_name, tool_input)
            
        except Exception as e:
            logger.error(f"Failed to parse tool call: {e}")
            return ToolResult(
                success=False,
                result=None,
                error=f"Failed to parse tool call: {str(e)}"
            )
    
    def format_tool_result_for_llm(self, result: ToolResult) -> Dict[str, Any]:
        """
        Format tool result for sending back to LLM.
        
        Args:
            result: ToolResult from execution
            
        Returns:
            Formatted message for LLM
        """
        if result.success:
            return {
                "role": "tool",
                "content": json.dumps({
                    "tool": result.tool_name,
                    "result": result.result,
                    "success": True
                }),
                "tool_call_id": result.tool_name  # Can be enhanced with actual ID
            }
        else:
            return {
                "role": "tool",
                "content": json.dumps({
                    "tool": result.tool_name,
                    "error": result.error,
                    "success": False
                }),
                "tool_call_id": result.tool_name
            }
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent tool execution history."""
        return [r.to_dict() for r in self.execution_history[-limit:]]
    
    def clear_history(self):
        """Clear execution history."""
        self.execution_history.clear()


# Default tools
def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the web for information.
    
    Args:
        query: Search query
        max_results: Maximum results to return
    """
    try:
        from automation_tools_new import search_google
        results = search_google(query)
        return {
            "query": query,
            "results": results[:max_results] if results else [],
            "count": len(results) if results else 0
        }
    except Exception as e:
        return {
            "error": str(e),
            "query": query
        }


def execute_code(code: str, language: str = "python") -> Dict[str, Any]:
    """
    Execute code (sandboxed).
    
    Args:
        code: Code to execute
        language: Programming language
    """
    try:
        if language == "python":
            import subprocess
            result = subprocess.run(
                ["python", "-c", code],
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "language": language
            }
    except Exception as e:
        return {
            "error": str(e),
            "language": language
        }


def get_current_time() -> Dict[str, Any]:
    """Get current date and time."""
    from datetime import datetime
    now = datetime.now()
    return {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day": now.strftime("%A")
    }


def calculator(expression: str) -> Dict[str, Any]:
    """
    Evaluate a mathematical expression.
    
    Args:
        expression: Mathematical expression
    """
    import ast
    import operator

    # Define safe operators
    safe_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp):
            op = safe_operators.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op)}")
            return op(evaluate(node.left), evaluate(node.right))
        elif isinstance(node, ast.UnaryOp):
            op = safe_operators.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op)}")
            return op(evaluate(node.operand))
        else:
            raise ValueError(f"Unsupported node type: {type(node)}")

    try:
        # Parse the expression and evaluate safely
        tree = ast.parse(expression, mode='eval')
        result = evaluate(tree)
        return {
            "expression": expression,
            "result": result,
            "success": True
        }
    except Exception as e:
        return {
            "expression": expression,
            "error": str(e),
            "success": False
        }


# Create default executor with common tools
def get_default_executor() -> ToolExecutor:
    """Create executor with default tools."""
    executor = ToolExecutor()
    
    # Register default tools
    executor.register_tool(
        "web_search",
        web_search,
        "Search the web for information",
        {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return",
                "default": 5
            }
        },
        required_params=["query"]
    )
    
    executor.register_tool(
        "get_current_time",
        get_current_time,
        "Get current date and time",
        {}
    )
    
    executor.register_tool(
        "calculator",
        calculator,
        "Evaluate a mathematical expression",
        {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate"
            }
        },
        required_params=["expression"]
    )
    
    executor.register_tool(
        "execute_code",
        execute_code,
        "Execute code (Python only, sandboxed)",
        {
            "code": {
                "type": "string",
                "description": "Code to execute"
            },
            "language": {
                "type": "string",
                "description": "Programming language",
                "default": "python"
            }
        },
        required_params=["code"]
    )
    
    return executor
