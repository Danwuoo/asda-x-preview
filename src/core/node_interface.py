"""Node Interface module for ASDA-X."""

from __future__ import annotations

import time
import uuid
from functools import wraps
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field

from .trace_logger import JSONLSink, TraceLogger, log_node_event
from .replay_trace import ReplayWriter


class NodeMeta(BaseModel):
    """Metadata for a DAG node."""

    name: str
    version: str
    tags: List[str] = Field(default_factory=list)
    trace_id: str
    timestamp: float


class BaseInputSchema(BaseModel):
    """Base fields for all node input schemas."""

    trace_id: Optional[str] = None
    context_id: Optional[str] = None
    timestamp: Optional[float] = None


class BaseOutputSchema(BaseModel):
    """Base fields for all node output schemas."""

    trace_id: Optional[str] = None
    context_id: Optional[str] = None
    timestamp: Optional[float] = None


InT = TypeVar("InT", bound=BaseInputSchema)
OutT = TypeVar("OutT", bound=BaseOutputSchema)


class NodeExecutionContext(Generic[InT, OutT]):
    """Helper for managing node execution context."""

    def __init__(self, trace_id: Optional[str] = None) -> None:
        self.trace_id = trace_id or str(uuid.uuid4())

    def build_meta(
        self, name: str, version: str, tags: Optional[List[str]] = None
    ) -> NodeMeta:
        return NodeMeta(
            name=name,
            version=version,
            tags=tags or [],
            trace_id=self.trace_id,
            timestamp=time.time(),
        )


# Node registry for optional lookup
_NODE_REGISTRY: Dict[str, Callable[..., Any]] = {}

# Default observability utilities used by nodes
default_logger = TraceLogger(JSONLSink("data/trace_events.jsonl"))


def register_node(name: str, func: Callable[..., Any]) -> None:
    """Register node by name."""
    _NODE_REGISTRY[name] = func


def list_registered_nodes() -> List[str]:
    return list(_NODE_REGISTRY.keys())


def asda_node(
    *,
    name: Optional[str] = None,
    version: str = "",
    tags: Optional[List[str]] = None,
    capture_io: bool = True,
    input_model: Optional[Type[InT]] = None,
    output_model: Optional[Type[OutT]] = None,
    replay_writer: Optional[ReplayWriter] = None,
) -> Callable[[Callable[[InT], OutT]], Callable[[InT], OutT]]:
    """Decorator to wrap a function as an ASDA node."""

    def decorator(func: Callable[[InT], OutT]) -> Callable[[InT], OutT]:
        node_name = name or func.__name__

        @wraps(func)
        def wrapper(data: InT) -> OutT:
            ctx = NodeExecutionContext(trace_id=data.trace_id)
            meta = ctx.build_meta(node_name, version, tags)
            if isinstance(data, BaseModel):
                payload = data.copy(
                    update={
                        "trace_id": meta.trace_id,
                        "timestamp": meta.timestamp,
                    }
                )
            else:
                payload = data
            if input_model is not None:
                payload = input_model.parse_obj(payload)
            with log_node_event(default_logger, node_name, version) as _:
                result = func(payload)
            if output_model is not None:
                result = output_model.parse_obj(result)
            if capture_io and isinstance(result, BaseModel):
                result = result.copy(
                    update={
                        "trace_id": meta.trace_id,
                        "timestamp": meta.timestamp,
                    }
                )
            if replay_writer:
                if getattr(replay_writer, "_current", None) is None:
                    replay_writer.init_trace()
                replay_writer.record_node_output(
                    node_name,
                    payload.dict() if isinstance(payload, BaseModel) else payload,
                    result.dict() if isinstance(result, BaseModel) else result,
                    version,
                )
            register_node(node_name, wrapper)
            return result

        return wrapper

    return decorator


__all__ = [
    "NodeMeta",
    "BaseInputSchema",
    "BaseOutputSchema",
    "NodeExecutionContext",
    "asda_node",
    "register_node",
    "list_registered_nodes",
    "default_logger",
    "replay_writer",
]
