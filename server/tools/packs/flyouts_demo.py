"""Demo flyout tool pack.

Enable with:
  ENABLED_TOOL_PACKS=flyouts_demo

Then the LLM can call `demo_flyout_card()` to open a flyout.
"""

from __future__ import annotations

from ..registry import tool_registry


@tool_registry.register(
    name="demo_flyout_card",
    description="DEMO: Show a simple info card in a flyout panel.",
    category="demo",
)
async def demo_flyout_card(
    title: str = "Flyout Demo",
    body: str = "This is a demo flyout tool pack.",
    flyout_type: str = "code",
) -> dict:
    """Return a structured tool result that triggers a flyout.

    Args:
        title: Card title
        body: Card content
        flyout_type: One of: browser, code, terminal
    """
    flyout_type = (flyout_type or "code").strip().lower()
    if flyout_type not in {"browser", "code", "terminal"}:
        flyout_type = "code"

    if flyout_type == "browser":
        content = "https://example.com"
    elif flyout_type == "terminal":
        content = f"$ echo '{title}'\n{body}"
    else:
        content = f"# {title}\n\n{body}\n"

    return {
        "text": f"Opening {title} in the {flyout_type} panel.",
        "flyout": {"type": flyout_type, "content": content},
    }
