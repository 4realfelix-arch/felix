"""
Built-in tools package.
Import all tools to register them with the tool registry.
"""

from __future__ import annotations

import importlib


from ...config import settings


def _parse_csv(value: str) -> set[str]:
    return {item.strip() for item in (value or "").split(",") if item.strip()}


_DISABLED = _parse_csv(getattr(settings, "disabled_tool_modules", ""))


def _import_tool_module(module_name: str):
    if module_name in _DISABLED:
        return None
    return importlib.import_module(f"{__name__}.{module_name}")


# Core tool modules (expected to have no optional deps)
datetime_tools = _import_tool_module("datetime_tools")
weather_tools = _import_tool_module("weather_tools")
web_tools = _import_tool_module("web_tools")
system_tools = _import_tool_module("system_tools")
knowledge_tools = _import_tool_module("knowledge_tools")
help_tools = _import_tool_module("help_tools")
onboarding_tools = _import_tool_module("onboarding_tools")
image_tools = _import_tool_module("image_tools")


# Optional-dependency modules
try:
    memory_tools = _import_tool_module("memory_tools")
except ModuleNotFoundError as e:
    if getattr(e, "name", None) != "openmemory":
        raise
    memory_tools = None

try:
    music_tools = _import_tool_module("music_tools")
except ModuleNotFoundError as e:
    if getattr(e, "name", None) != "mpd":
        raise
    music_tools = None

__all__ = [
    "datetime_tools",
    "weather_tools", 
    "web_tools",
    "system_tools",
    "knowledge_tools",
    "help_tools",
    "memory_tools",
    "music_tools",
    "onboarding_tools",
    "image_tools",
]
