"""Tool packs (extension-style tool modules).

A pack is an importable Python module under `server.tools.packs` that registers
one or more tools with `tool_registry` when imported.

Enabled packs are loaded from `Settings.enabled_tool_packs` (comma-separated).
"""

from __future__ import annotations

import importlib
import structlog

from ...config import settings

logger = structlog.get_logger(__name__)


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def load_enabled_tool_packs() -> list[str]:
    """Import enabled pack modules and return the successfully loaded names."""
    enabled = _parse_csv(getattr(settings, "enabled_tool_packs", ""))
    loaded: list[str] = []

    for pack_name in enabled:
        module_name = f"{__name__}.{pack_name}"
        try:
            importlib.import_module(module_name)
            loaded.append(pack_name)
            logger.info("tool_pack_loaded", pack=pack_name)
        except Exception as e:
            logger.warning("tool_pack_failed", pack=pack_name, error=str(e))

    return loaded
