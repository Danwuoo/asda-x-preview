from __future__ import annotations

import os
import yaml
from typing import Dict, List, Optional


class PromptVariationGenerator:
    """Generate semantically equivalent prompt variants."""

    def __init__(
        self,
        template_path: str | None = None,
        synonyms: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        self.synonyms = synonyms if synonyms is not None else {}
        if template_path and os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self.synonyms.update(data.get("synonyms", {}))

    def generate(self, prompt: str, num_variants: int = 2) -> List[str]:
        words = prompt.split()
        variants = []
        for _ in range(num_variants):
            new_words = []
            for w in words:
                lw = w.lower()
                if lw in self.synonyms:
                    repl = self.synonyms[lw][0]
                    if w.istitle():
                        repl = repl.capitalize()
                    new_words.append(repl)
                else:
                    new_words.append(w)
            variants.append(" ".join(new_words))
        return variants
