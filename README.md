# ASDA-X Preview

ASDA-X is an autonomous cybersecurity agent system aiming to replace SOC operations via a multi-layer modular architecture. This preview version implements the full closed-loop prototype from perception to governance, powered by the SEL Framework.

## Modules Overview

- **Core Layer**: LangGraph DAG orchestration of agent flow
- **LLM Inference**: Integration with watsonx.ai, Self-Refine, CIT Controller
- **Knowledge Retrieval**: RAG-based retrieval and attack graph reasoning
- **Decision Layer**: SOAR generation, policy trace, prompt injection guard
- **Learning**: Replay ➝ SEC generation ➝ continual fine-tuning
- **Governance**: ASGA audit system with drift & policy verification
- **Visualization**: Replay explorer, risk dashboard, KPI monitoring
- **Deployment**: Containerized CI/CD with ZeroMQ messaging bus
