from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, List
import yaml

from pydantic import BaseModel

from ..inference_engine import LLMInferenceEngine
from .prompt_variation import PromptVariationGenerator
from .embedding import InstructionEmbedder
from .drift_evaluator import SemanticDriftEvaluator
from .reporter import ConsistencyReporter
from .trigger import RiskTriggerRouter


class CITConfig(BaseModel):
    embedding_threshold: float = 0.3
    max_variants: int = 2
    log_path: str = "data/replay/cit_decision.jsonl"

    @classmethod
    def from_yaml(cls, path: str) -> "CITConfig":
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        return cls()


class CITController:
    """Controller to evaluate semantic consistency across prompt variants."""

    def __init__(
        self,
        engine: LLMInferenceEngine,
        config: Optional[CITConfig] = None,
        variation_gen: Optional[PromptVariationGenerator] = None,
        embedder: Optional[InstructionEmbedder] = None,
        evaluator: Optional[SemanticDriftEvaluator] = None,
        reporter: Optional[ConsistencyReporter] = None,
        trigger: Optional[RiskTriggerRouter] = None,
    ) -> None:
        self.engine = engine
        self.config = config or CITConfig.from_yaml(
            "configs/decision/cit_config.yaml"
        )
        self.variation_gen = variation_gen or PromptVariationGenerator(
            "configs/decision/prompt_templates.yaml"
        )
        embedder = embedder or InstructionEmbedder()
        self.evaluator = evaluator or SemanticDriftEvaluator(embedder)
        self.reporter = reporter or ConsistencyReporter(self.config.log_path)
        self.trigger = trigger or RiskTriggerRouter(
            self.config.embedding_threshold
        )

    async def check(self, prompt: str, task_id: str) -> dict:
        variants = self.variation_gen.generate(
            prompt, self.config.max_variants
        )
        prompts: List[str] = [prompt] + variants
        outputs = []
        for p in prompts:
            result = await self.engine.infer(p)
            outputs.append(result.text)

        drift = self.evaluator.embedding_drift(outputs)
        action_sim = self.evaluator.action_similarity(outputs)

        status = (
            "drift_detected"
            if drift > self.config.embedding_threshold
            else "ok"
        )
        recommendation = self.trigger.handle(drift)
        report = {
            "original_prompt": prompt,
            "prompt_variants": variants,
            "embedding_drift_score": drift,
            "action_similarity_score": action_sim,
            "status": status,
            "recommendation": recommendation,
            "trace_id": (
                f"cit-{datetime.utcnow().strftime('%Y%m%d')}-{task_id}"
            ),
        }
        self.reporter.report(report)
        return report
