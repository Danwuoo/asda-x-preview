from __future__ import annotations

import concurrent.futures
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from .dag_engine import (DAGFlowBuilder, ReplayManager, build_trace_id,
                       build_default_dag)
from .node_interface import list_registered_nodes
from .prompt_context import PromptContext, parse_input_context


class TaskSubmission(BaseModel):
    task_name: str
    input_context: Dict[str, Any]
    replay_mode: bool = False
    execution_params: Dict[str, Any] = {}


class TaskResult(BaseModel):
    trace_id: str
    status: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    dag_output: Optional[Dict[str, Any]] = None
    trace_summary: Optional[str] = None


class NodeStatus(BaseModel):
    nodes: list[str]


app = FastAPI()
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

from .replay_trace import ReplayWriter, ReplayReader

_tasks: Dict[str, TaskResult] = {}
_replay = ReplayManager(
    replay_writer=ReplayWriter(store="data/replays"),
    replay_reader=ReplayReader(store="data/replays"),
)


# def _run_dag(trace_id: str, task: TaskSubmission) -> None:
#     result = TaskResult(trace_id=trace_id, status="running")
#     _tasks[trace_id] = result
#     try:
#         # builder = build_default_dag()
#         # runner = builder.build_default_flow()
#         # replay_writer.init_trace(trace_id=trace_id, task_name=task.task_name)
#         # ctx = parse_input_context(task.input_context)
#         # output = runner.invoke(
#         #     {"raw_event": ctx.context_summary, "trace_id": trace_id}
#         # )
#         # replay_writer.finalize_trace()
#         # result.status = "completed"
#         # result.dag_output = output
#         # _replay.save(trace_id, {"input": task.dict(), "output": output})
#     except Exception as exc:  # pragma: no cover - background errors
#         result.status = "failed"
#         result.trace_summary = str(exc)
#     finally:
#         _tasks[trace_id] = result


def _run_dag(trace_id: str, task: TaskSubmission) -> None:
    """Helper to run DAG in the background."""
    result = TaskResult(trace_id=trace_id, status="running")
    _tasks[trace_id] = result
    try:
        _replay.replay_writer.init_trace(trace_id=trace_id, task_name=task.task_name)
        try:
            if task.task_name != "default_asda_flow":
                raise ValueError(f"Task '{task.task_name}' not found")
            # 1. Build the DAG
            builder = build_default_dag()
            runner = builder.build()

            # 2. Invoke the DAG
            output = runner.invoke(
                {"initial_input": task.input_context, "trace_id": trace_id}
            )

            # 3. Finalize the trace and update the result
            result.status = "completed"
            result.dag_output = output
            _replay.replay_writer.record_node_output(
                "__result__",
                task.input_context,
                result.dag_output,
                "1.0",
            )
        finally:
            _replay.replay_writer.finalize_trace()
    except Exception as exc:
        result.status = "failed"
        result.error = str(exc)
    finally:
        _tasks[trace_id] = result


@app.post("/run", response_model=TaskResult)
def run_task(
    task: TaskSubmission,
) -> TaskResult:
    trace_id = build_trace_id()
    result = TaskResult(trace_id=trace_id, status="running")
    _tasks[trace_id] = result
    executor.submit(_run_dag, trace_id, task)
    return result


@app.get("/status/{trace_id}", response_model=TaskResult)
def get_status(trace_id: str) -> TaskResult:
    return _tasks.get(
        trace_id, TaskResult(trace_id=trace_id, status="unknown")
    )


@app.get("/result/{trace_id}", response_model=TaskResult)
def get_result(trace_id: str) -> TaskResult:
    return _tasks.get(
        trace_id, TaskResult(trace_id=trace_id, status="unknown")
    )


@app.get("/nodes", response_model=NodeStatus)
def get_nodes() -> NodeStatus:
    return NodeStatus(nodes=list_registered_nodes())


@app.get("/replay/{trace_id}", response_model=TaskResult)
def replay(trace_id: str, background_tasks: BackgroundTasks) -> TaskResult:
    stored = _replay.replay_reader.load(trace_id)
    submission = TaskSubmission(
        task_name=stored.task_name,
        input_context=stored.executed_nodes[0].input,
    )
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
