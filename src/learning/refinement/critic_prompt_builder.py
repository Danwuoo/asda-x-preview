from __future__ import annotations

"""Utility to build prompts for critic models."""

from typing import Iterable, List, Optional


def build_prompt(
    draft: str,
    *,
    context: str = "",
    indicators: Optional[Iterable[str]] = None,
) -> str:
    """Assemble a review prompt from components."""
    parts: List[str] = []
    if context:
        parts.append(f"Context:\n{context}")
    parts.append(f"Output to review:\n{draft}")
    if indicators:
        lines = "\n".join(f"- {i}" for i in indicators)
        parts.append(f"Consider the following aspects:\n{lines}")
    return "\n\n".join(parts)


__all__ = ["build_prompt"]
