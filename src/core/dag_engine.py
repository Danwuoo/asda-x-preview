"""Simple DAG Engine skeleton for ASDA-X."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Callable, Dict, List, Optional, Type

from pydantic import BaseModel


class NodeWrapper:
    """Wrap a callable node with basic validation and metadata."""

    def __init__(
        self,
        func: Callable[[Dict[str, Any]], Dict[str, Any]],
        *,
        name: str = "",
        version: str = "",
        input_model: Optional[Type[BaseModel]] = None,
        output_model: Optional[Type[BaseModel]] = None,
    ) -> None:
        self.func = func
        self.name = name
        self.version = version
        self.input_model = input_model
        self.output_model = output_model

    def __call__(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if self.input_model is not None:
            data = self.input_model(**data).dict()
        result = self.func(data)
        if self.output_model is not None:
            result = self.output_model(**result).dict()
        return result


def register_node(
    *,
    name: str = "",
    version: str = "",
    input_model: Optional[Type[BaseModel]] = None,
    output_model: Optional[Type[BaseModel]] = None,
) -> Callable[
    [Callable[[Dict[str, Any]], Dict[str, Any]]],
    Callable[[Dict[str, Any]], Dict[str, Any]],
]:
    """Decorator to register a node with metadata."""

    def decorator(func: Callable[[Dict[str, Any]], Dict[str, Any]]):
        wrapper = NodeWrapper(
            func,
            name=name,
            version=version,
            input_model=input_model,
            output_model=output_model,
        )

        def _wrapped(data: Dict[str, Any]) -> Dict[str, Any]:
            return wrapper(data)

        _wrapped.wrapper = wrapper  # type: ignore[attr-defined]
        return _wrapped

    return decorator


class ContextInjector:
    """Inject additional context into node input."""

    def inject(
        self, data: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        merged = data.copy()
        merged.update(context)
        return merged


class ReplayManager:
    """Manage saving and loading of DAG traces."""

    def __init__(self, store: str = "data/replay") -> None:
        self.store = store

    def _path(self, trace_id: str) -> str:
        return os.path.join(self.store, f"{trace_id}.json")

    def load(self, trace_id: str) -> Dict[str, Any]:
        path = self._path(trace_id)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, trace_id: str, data: Dict[str, Any]) -> None:
        os.makedirs(self.store, exist_ok=True)
        path = self._path(trace_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)


class DAGFlowBuilder:
    """Build and run a simple DAG flow."""

    def __init__(self) -> None:
        self.nodes: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []

    def register(
        self, node: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        self.nodes.append(node)

    def build_default_flow(self) -> "DAGFlowRunner":
        return DAGFlowRunner(self.nodes)


class DAGFlowRunner:
    """Execute a series of nodes sequentially."""

    def __init__(
        self, nodes: List[Callable[[Dict[str, Any]], Dict[str, Any]]]
    ) -> None:
        self.nodes = nodes
        self.trace_id = build_trace_id()

    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        data = inputs
        for node in self.nodes:
            data = node(data)
        return data


def build_trace_id() -> str:
    return str(uuid.uuid4())


__all__ = [
    "NodeWrapper",
    "register_node",
    "ContextInjector",
    "ReplayManager",
    "DAGFlowBuilder",
    "DAGFlowRunner",
    "build_trace_id",
]
