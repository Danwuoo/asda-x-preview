# src/core/node_interface.py

import inspect
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Generic, List, Literal, Optional, Type, TypeVar
import hashlib

from pydantic import BaseModel, Field, ValidationError

from src.core.global_logger import trace_logger
from src.core.trace_logger import TraceEvent, NodeStatus, log_node_execution

# 1. NodeMeta
class NodeMeta(BaseModel):
    """
    Represents the metadata of a node in the DAG.
    """
    node_name: str
    version: str
    tags: List[str] = Field(default_factory=list)
    replay_trace_id: Optional[str] = None
    runtime_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# 2. BaseInputSchema / BaseOutputSchema
class BaseInputSchema(BaseModel):
    """
    Base class for all node input schemas.
    """
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    context_tags: List[str] = Field(default_factory=list)

class BaseOutputSchema(BaseModel):
    """
    Base class for all node output schemas.
    """
    execution_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    node_meta: Optional[NodeMeta] = None

# 3. NodeExecutionContext
class NodeExecutionContext:
    """
    A helper class to manage the execution context of a node.
    """
    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc)

# 4. asda_node Decorator
InputSchema = TypeVar("InputSchema", bound=BaseInputSchema)
OutputSchema = TypeVar("OutputSchema", bound=BaseOutputSchema)

def asda_node(
    name: Optional[str] = None,
    version: str = "v1.0",
    tags: Optional[List[str]] = None,
    input_node: Optional[str] = None,
    capture_io: bool = True,
) -> Callable[..., Callable[..., Dict[str, Any]]]:
    """
    A decorator to wrap any function into a standardized, LangGraph-compatible DAG node.
    """
    def decorator(func: Callable[..., Any]) -> Callable[[Any], Dict[str, Any]]:
        node_name = name or func.__name__
        sig = inspect.signature(func)

        # --- Schema Extraction ---
        input_schema_type = next(
            (p.annotation for p in sig.parameters.values() if isinstance(p.annotation, type) and issubclass(p.annotation, BaseInputSchema)),
            None,
        )
        if not input_schema_type:
            raise TypeError(f"Node '{node_name}' must have an input parameter with a BaseInputSchema subclass annotation.")

        output_schema_type = sig.return_annotation
        if not (isinstance(output_schema_type, type) and issubclass(output_schema_type, BaseOutputSchema)):
            raise TypeError(f"Node '{node_name}' must have a return type annotation that is a BaseOutputSchema subclass.")

        @wraps(func)
        def wrapper(state: Any) -> Dict[str, Any]:
            # --- Replay Logic ---
            if state.is_replay and node_name in state.replay_data:
                return {"node_outputs": {**state.node_outputs, node_name: state.replay_data[node_name]}}

            # --- Input Preparation ---
            raw_input_data = state.initial_input if input_node is None else state.node_outputs.get(input_node)
            if raw_input_data is None:
                raise ValueError(f"Input for node '{node_name}' not found. Expected output from node '{input_node}'.")

            try:
                if isinstance(raw_input_data, dict):
                    input_schema = input_schema_type(**raw_input_data)
                elif isinstance(raw_input_data, BaseInputSchema):
                    input_schema = raw_input_data
                else: # Try to auto-assign to the first data field
                     data_field = next((f for f,v in input_schema_type.model_fields.items() if f not in BaseInputSchema.model_fields), None)
                     if data_field:
                         input_schema = input_schema_type(**{data_field: raw_input_data})
                     else:
                         raise TypeError(f"Cannot auto-assign input of type {type(raw_input_data)} to {input_schema_type.__name__}")

            except ValidationError as e:
                raise ValueError(f"Input validation failed for {node_name}: {e}") from e

            # --- Execution and Logging ---
            input_hash = hashlib.sha256(input_schema.model_dump_json().encode()).hexdigest() if capture_io else None
            with log_node_execution(
                logger=trace_logger,
                node_name=node_name,
                version=version,
                governance_tags=tags,
                input_hash=input_hash,
            ) as trace_event:
                # Set trace_id on the first node
                if state.trace_id == "":
                    state.trace_id = trace_event.trace_id
                input_schema.trace_id = state.trace_id

                output_data = func(input_schema)

                # --- Output Handling ---
                if isinstance(output_data, BaseOutputSchema):
                    output_schema = output_data
                else: # Auto-wrap raw output
                    data_field = next((f for f,v in output_schema_type.model_fields.items() if f not in BaseOutputSchema.model_fields), None)
                    if data_field:
                        output_schema = output_schema_type(**{data_field: output_data})
                    else:
                        raise TypeError(f"Cannot auto-assign output of type {type(output_data)} to {output_schema_type.__name__}")

                output_schema.node_meta = NodeMeta(
                    node_name=node_name, version=version, tags=tags or [],
                    replay_trace_id=state.trace_id,
                    runtime_timestamp=datetime.fromisoformat(trace_event.timestamp.isoformat()),
                )

                if capture_io:
                    output_hash = hashlib.sha256(output_schema.model_dump_json().encode()).hexdigest()
                    trace_event.output_hash = output_hash

                return {"node_outputs": {**state.node_outputs, node_name: output_schema}}

        return wrapper
    return decorator

# 5. register_node / list_registered_nodes
NODE_REGISTRY: Dict[str, Callable[..., Any]] = {}

def register_node(node_function: Callable[..., Any], name: Optional[str] = None) -> None:
    """
    Registers a node in the global registry.
    """
    node_name = name or node_function.__name__
    if node_name in NODE_REGISTRY:
        raise ValueError(f"Node with name '{node_name}' is already registered.")
    NODE_REGISTRY[node_name] = node_function

def list_registered_nodes() -> List[str]:
    """
    Returns a list of all registered node names.
    """
    return list(NODE_REGISTRY.keys())
