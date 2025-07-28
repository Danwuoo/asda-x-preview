"""Simple DAG Engine skeleton."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Callable, Optional

from pydantic import BaseModel

from .prompt_context import PromptContext
from .trace_logger import log_trace
from .replay_trace import ReplayTrace


# Helper utils

def build_trace_id() -> str:
    """Generate a unique trace id."""
    return str(uuid.uuid4())


def validate_io(value: Any, schema: Optional[type[BaseModel]]) -> Any:
    """Validate value against a pydantic schema if provided."""
    if schema is None:
        return value
    if isinstance(value, schema):
        return value
    return schema.model_validate(value)


class NodeWrapper:
    """Wrap a node function with tracing and validation."""

    def __init__(
        self,
        func: Callable[..., Any],
        name: str,
        version: str,
        input_model: Optional[type[BaseModel]] = None,
        output_model: Optional[type[BaseModel]] = None,
    ) -> None:
        self.func = func
        self.name = name
        self.version = version
        self.input_model = input_model
        self.output_model = output_model

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        log_trace("node_start", node=self.name, version=self.version)
        if args:
            args = (validate_io(args[0], self.input_model),) + args[1:]
        result = self.func(*args, **kwargs)
        result = validate_io(result, self.output_model)
        log_trace("node_end", node=self.name, version=self.version)
        return result


def register_node(
    name: str,
    version: str,
    input_model: Optional[type[BaseModel]] = None,
    output_model: Optional[type[BaseModel]] = None,
) -> Callable[[Callable[..., Any]], NodeWrapper]:
    """Decorator to register a node."""

    def decorator(func: Callable[..., Any]) -> NodeWrapper:
        return NodeWrapper(func, name, version, input_model, output_model)

    return decorator


class ContextInjector:
    """Inject context information into data."""

    def __init__(self, context: Optional[PromptContext] = None) -> None:
        self.context = context or PromptContext()

    def inject(self, data: dict[str, Any]) -> dict[str, Any]:
        result = dict(data)
        result.setdefault("context_id", self.context.context_id)
        return result


class ReplayManager:
    """Manage replay traces."""

    def __init__(self, storage_path: str = "data/replay") -> None:
        self.storage_path = storage_path

    def load(self, trace_id: str) -> ReplayTrace:
        return ReplayTrace(trace_id)

    def replay(self, trace: ReplayTrace) -> ReplayTrace:
        log_trace("replay", trace_id=trace.trace_id)
        return trace


class DAGFlowBuilder:
    """Construct and execute a simple DAG flow."""

    def __init__(self) -> None:
        self.trace_id = build_trace_id()
        self.nodes: list[NodeWrapper] = []

    def add_node(self, node: NodeWrapper) -> "DAGFlowBuilder":
        self.nodes.append(node)
        return self

    def build_default_flow(self) -> Callable[[Any], Any]:
        async def flow(inputs: Any) -> Any:
            data = inputs
            for node in self.nodes:
                if asyncio.iscoroutinefunction(node.func):
                    data = await node(data)
                else:
                    data = node(data)
            return data

        return flow
