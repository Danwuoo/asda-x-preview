import asyncio
import json
from pathlib import Path
import sys
import types

# Provide a minimal jsonschema stub so imports succeed without the dependency.
jsonschema_stub = types.ModuleType("jsonschema")

class Draft7Validator:
    def __init__(self, schema):
        pass

    def iter_errors(self, playbook):
        return []


class ValidationError(Exception):
    pass


jsonschema_stub.Draft7Validator = Draft7Validator
jsonschema_stub.ValidationError = ValidationError
sys.modules.setdefault("jsonschema", jsonschema_stub)

from src.decision.prompt_builder import PromptBuilder
from src.decision.inference_engine import LLMInferenceEngine
from src.decision.agent_executor import LLMAgentExecutor, ExecutionContext
from src.inference.cit_controller import CITController, CITConfig
from src.decision.versioning.audit_logger import VersionedActionAudit
from src.decision.versioning.store import AuditStoreManager
from src.decision.soar.builder import PlaybookBuilder
from src.decision.soar.mapper import ActionParameterMapper
from src.decision.soar.versioning import VersionTagger
from src.inference.llm_agent import LLMModelRegistry, LLMAgent, PromptInput, PromptOutput
from src.execution.dispatcher import ActionDispatcher


class DummyModel:
    def __init__(self, reply: str) -> None:
        self.model_id = "dummy"
        self.reply = reply

    async def generate(self, prompt: PromptInput, stream: bool = False) -> PromptOutput:
        return PromptOutput(text=self.reply, model_id=self.model_id)


async def main() -> None:
    registry = LLMModelRegistry()
    registry.register("d", DummyModel('{"type": "echo", "msg": "hi"}'))
    agent = LLMAgent(registry, default_model_id="d")
    engine = LLMInferenceEngine(agent)
    cit = CITController(agent, config=CITConfig(threshold=0.5))
    builder = PromptBuilder()
    executor = LLMAgentExecutor(builder, engine, cit_controller=cit, version_id="v1")

    context = ExecutionContext(task_context={"query": "hi"}, session_id="sess1")
    output = await executor.execute(context)

    decision = {
        "name": "echo-task",
        "actions": [{"name": "echo", "ref": "sys.echo"}],
        "parameters": output.action_plan,
    }

    class SimpleSOARGenerator:
        def __init__(self, platform: str = "stackstorm") -> None:
            self.builder = PlaybookBuilder(platform)
            self.mapper = ActionParameterMapper()
            self.versioner = VersionTagger()

        def generate(self, decision: dict, template: str) -> dict:
            params = self.mapper.map_parameters(decision)
            context = {
                "name": decision.get("name", "generated-playbook"),
                "actions": decision.get("actions", []),
                "parameters": params,
            }
            pb = self.builder.build(template, context)
            return self.versioner.tag(pb)

    soar_gen = SimpleSOARGenerator()
    playbook = soar_gen.generate(decision, template="stackstorm.yaml.j2")

    out_dir = Path("integration/mock_outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "playbook.json", "w", encoding="utf-8") as f:
        json.dump(playbook, f, indent=2)

    store = AuditStoreManager(root=str(out_dir / "store"))
    auditor = VersionedActionAudit(store=store)
    version_id = auditor.record(decision)

    trace_path = Path("integration/trace_dag_export/trace.json")
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(auditor.tracer.to_dict(), f, indent=2)

    dispatcher = ActionDispatcher()
    dispatch_record = dispatcher.dispatch(
        decision_id=version_id,
        action_plan=decision,
        risk_level="low",
        action_type="echo",
        confidence=0.9,
        trace_id="tid1",
    )

    with open(out_dir / "dispatch.json", "w", encoding="utf-8") as f:
        json.dump(dispatch_record.model_dump(mode="json"), f, indent=2)

    print("Completed decision flow. Version:", version_id)


if __name__ == "__main__":
    asyncio.run(main())
