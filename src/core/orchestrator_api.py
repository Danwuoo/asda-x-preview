from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from .dag_engine import DAGFlowBuilder, ReplayManager, build_trace_id
from .node_interface import (
    BaseInputSchema,
    BaseOutputSchema,
    asda_node,
    list_registered_nodes,
)


class TaskSubmission(BaseModel):
    task_name: str
    input_context: Dict[str, Any]
    replay_mode: bool = False
    execution_params: Dict[str, Any] = {}


class TaskResult(BaseModel):
    trace_id: str
    status: str
    dag_output: Optional[Dict[str, Any]] = None
    trace_summary: Optional[str] = None


class NodeStatus(BaseModel):
    nodes: list[str]


app = FastAPI()

_tasks: Dict[str, TaskResult] = {}
_replay = ReplayManager()


class RawEventIn(BaseInputSchema):
    raw_event: str


class ParsedOut(BaseOutputSchema):
    text: str


@asda_node(
    name="parse",
    version="1.0",
    input_model=RawEventIn,
    output_model=ParsedOut,
)
def parse_node(data: RawEventIn) -> ParsedOut:
    return ParsedOut(text=data.raw_event)


class UpperOut(BaseOutputSchema):
    text: str


@asda_node(
    name="upper",
    version="1.0",
    input_model=ParsedOut,
    output_model=UpperOut,
)
def upper_node(data: ParsedOut) -> UpperOut:
    return UpperOut(text=data.text.upper())


def build_default_dag() -> DAGFlowBuilder:
    builder = DAGFlowBuilder()
    builder.register(parse_node)
    builder.register(upper_node)
    return builder


def _run_dag(trace_id: str, task: TaskSubmission) -> None:
    result = TaskResult(trace_id=trace_id, status="running")
    _tasks[trace_id] = result
    try:
        builder = build_default_dag()
        runner = builder.build_default_flow()
        output = runner.invoke(
            {"raw_event": task.input_context.get("raw_event", "")}
        )
        result.status = "completed"
        result.dag_output = output
        _replay.save(trace_id, {"input": task.dict(), "output": output})
    except Exception as exc:  # pragma: no cover - background errors
        result.status = "failed"
        result.trace_summary = str(exc)
    finally:
        _tasks[trace_id] = result


@app.post("/run", response_model=TaskResult)
def run_task(
    task: TaskSubmission,
    background_tasks: BackgroundTasks,
) -> TaskResult:
    trace_id = build_trace_id()
    result = TaskResult(trace_id=trace_id, status="running")
    _tasks[trace_id] = result
    background_tasks.add_task(_run_dag, trace_id, task)
    return result


@app.get("/status/{trace_id}", response_model=TaskResult)
def get_status(trace_id: str) -> TaskResult:
    return _tasks.get(
        trace_id, TaskResult(trace_id=trace_id, status="unknown")
    )


@app.get("/result/{trace_id}", response_model=Dict[str, Any])
def get_result(trace_id: str) -> Dict[str, Any]:
    try:
        return _replay.load(trace_id)
    except FileNotFoundError:  # pragma: no cover - no result
        return {}


@app.get("/nodes", response_model=NodeStatus)
def get_nodes() -> NodeStatus:
    return NodeStatus(nodes=list_registered_nodes())


@app.get("/replay/{trace_id}", response_model=TaskResult)
def replay(trace_id: str, background_tasks: BackgroundTasks) -> TaskResult:
    stored = _replay.load(trace_id)
    submission = TaskSubmission.parse_obj(stored.get("input"))
    new_id = build_trace_id()
    result = TaskResult(trace_id=new_id, status="running")
    _tasks[new_id] = result
    background_tasks.add_task(_run_dag, new_id, submission)
    return result


@app.post("/test")
def test_endpoint(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"echo": data, "status": "ok"}


__all__ = [
    "app",
    "TaskSubmission",
    "TaskResult",
    "NodeStatus",
]
