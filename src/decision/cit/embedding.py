from __future__ import annotations


class InstructionEmbedder:
    """Simple token based embedder."""

    @staticmethod
    def embed(text: str) -> set[str]:
        return set(text.lower().split())
