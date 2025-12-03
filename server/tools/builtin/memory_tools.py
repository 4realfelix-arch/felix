# server/tools/builtin/memory_tools.py
"""
Long-term memory tools using OpenMemory Python SDK.

These tools provide Felix with persistent memory across conversations.
Uses local SQLite storage with Ollama embeddings (no external backend needed).
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional
from openmemory import OpenMemory
from ..registry import tool_registry

logger = logging.getLogger(__name__)

# OpenMemory configuration
MEMORY_DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "memory.db"
MEMORY_DB_PATH.parent.mkdir(exist_ok=True)

# Lazy-loaded singleton
_memory: Optional[OpenMemory] = None


def _get_memory() -> OpenMemory:
    """Get or create the OpenMemory instance."""
    global _memory
    if _memory is None:
        _memory = OpenMemory(
            mode="local",
            path=str(MEMORY_DB_PATH),
            tier="smart",
            embeddings={
                "provider": "ollama",
                "ollama": {"url": "http://localhost:11434"},
                "model": "nomic-embed-text"
            }
        )
        logger.info("openmemory_initialized", path=str(MEMORY_DB_PATH))
    return _memory


@tool_registry.register(
    description="Remember something important. Store facts, preferences, personal details."
)
async def remember(content: str, tags: Optional[str] = None, importance: Optional[str] = "normal") -> str:
    """Store a memory."""
    try:
        tag_list = [t.strip() for t in tags.split(",")] if tags else []
        salience_map = {"low": 0.3, "normal": 0.5, "high": 0.8}
        salience = salience_map.get(importance, 0.5)
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: _get_memory().add(content, tags=tag_list, salience=salience)
        )
        
        mem_id = result.get("id", "unknown")[:8]
        sector = result.get("primarySector", "unknown")
        return f"Remembered: '{content}' ({sector}, ID: {mem_id})"
    except Exception as e:
        logger.error("memory_store_failed", error=str(e))
        return f"Failed to store memory: {str(e)}"


@tool_registry.register(
    description="Recall memories relevant to a topic or question."
)
async def recall(query: str, limit: Optional[int] = 5, min_relevance: Optional[float] = 0.3) -> str:
    """Search for relevant memories."""
    try:
        loop = asyncio.get_event_loop()
        memories = await loop.run_in_executor(
            None, lambda: _get_memory().query(query, k=min(limit, 20))
        )
        
        memories = [m for m in memories if m.get("score", 0) >= min_relevance]
        
        if not memories:
            return f"No memories found for: '{query}'"
        
        output_lines = [f"Found {len(memories)} memories:"]
        for i, mem in enumerate(memories, 1):
            content = mem.get("content", "")
            score = mem.get("score", 0)
            sectors = ", ".join(mem.get("sectors", []))
            mem_id = mem.get("id", "?")[:8]
            output_lines.append(f"\n{i}. [{sectors}] (score: {score:.2f}, id: {mem_id})")
            output_lines.append(f"   {content}")
        
        return "\n".join(output_lines)
    except Exception as e:
        logger.error("memory_recall_failed", error=str(e))
        return f"Failed to recall: {str(e)}"


@tool_registry.register(description="Forget a specific memory by its ID.")
async def forget(memory_id: str) -> str:
    """Delete a memory."""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: _get_memory().delete(memory_id))
        return f"Memory {memory_id[:8]} forgotten."
    except Exception as e:
        return f"Failed to forget: {str(e)}"


@tool_registry.register(description="Get memory system status and list stored memories.")
async def memory_status(sector: Optional[str] = None, limit: Optional[int] = 10) -> str:
    """Get memory status."""
    try:
        loop = asyncio.get_event_loop()
        memories = await loop.run_in_executor(
            None, lambda: _get_memory().getAll(limit=min(limit, 50), sector=sector)
        )
        
        output = ["📊 Memory System: Local SQLite + Ollama embeddings", f"   {len(memories)} memories\n"]
        
        if not memories:
            output.append("   (no memories stored)")
        else:
            for mem in memories[:limit]:
                content = mem.get("content", "")[:50]
                sectors = mem.get("sectors", [])
                s = sectors[0] if sectors else "?"
                mem_id = mem.get("id", "?")[:8]
                output.append(f"   • [{s}] {content}... (id: {mem_id})")
        
        return "\n".join(output)
    except Exception as e:
        return f"Failed to get status: {str(e)}"
