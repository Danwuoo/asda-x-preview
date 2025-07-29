# ASDA-X Preview

ASDA-X is an autonomous cybersecurity agent system aiming to replace SOC operations via a multi-layer modular architecture. This preview version implements the full closed-loop prototype from perception to governance, powered by the SEL Framework.

## Modules Overview

- **Core Layer**: LangGraph DAG orchestration of agent flow
- **LLM Inference**: Unified model registry with WatsonX/OpenLLM, consistency
  testing, self-refinement and output scoring modules. Feedback events are routed
  between components to enable closed-loop corrections.
- **Knowledge Retrieval**: RAG-based retrieval and attack graph reasoning
- **Decision Layer**: SOAR generation, policy trace, prompt injection guard
- **Learning**: Replay ➝ SEC generation ➝ continual fine-tuning
- **Governance**: ASGA audit system with drift & policy verification
- **Visualization**: Replay explorer, risk dashboard, KPI monitoring
- **Deployment**: Containerized CI/CD with ZeroMQ messaging bus

### Layer 2: LLM Inference Modules

The LLM layer orchestrates model calls and trace logging.

- `llm_agent.py` – unified interface to registered models
- `cit_controller.py` – runs semantic consistency checks
- `self_refiner.py` – iterative critique/rewrite cycle
- `output_scorer.py` – evaluate output quality and format
- `prompt_schema.py` – standardized prompt and output types
- `model_registry.py` – config-driven model registration
- `feedback_router.py` – dispatches feedback events
