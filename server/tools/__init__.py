"""
Tools package.
"""

from .registry import tool_registry, Tool
from .executor import tool_executor, execute_tool, ToolResult

# Import builtin tools to register them
from . import builtin

# Import enabled tool packs (extension-style modules)
from .packs import load_enabled_tool_packs

load_enabled_tool_packs()

__all__ = [
    "tool_registry",
    "Tool",
    "tool_executor",
    "execute_tool",
    "ToolResult",
]

# Convenience function
def list_tools():
    """List all registered tools."""
    return tool_registry.get_all_tools()
