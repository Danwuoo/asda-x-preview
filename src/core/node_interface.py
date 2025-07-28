# src/core/node_interface.py

import inspect
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Generic, List, Literal, Optional, Type, TypeVar
import hashlib

from pydantic import BaseModel, Field, ValidationError

from src.core.trace_logger import TraceLogger, JSONLSink, TraceEvent

# Initialize a default trace logger
# In a real application, this might be configured via a config file
trace_logger = TraceLogger(sink=JSONLSink(path="data/trace_events.jsonl"))

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
    capture_io: bool = True,
) -> Callable[..., Callable[..., OutputSchema]]:
    """
    A decorator to wrap any function into a standardized DAG node.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., OutputSchema]:
        node_name = name or func.__name__
        sig = inspect.signature(func)

        # Extract and validate input schema from function signature
        input_schema_type: Optional[Type[BaseInputSchema]] = None
        for param in sig.parameters.values():
            if param.annotation is not inspect.Parameter.empty and isinstance(param.annotation, type) and issubclass(param.annotation, BaseInputSchema):
                input_schema_type = param.annotation
                break

        if not input_schema_type:
            raise TypeError(f"Node '{node_name}' must have an input parameter annotated with a subclass of BaseInputSchema.")

        # Extract and validate output schema from function signature
        output_schema_type: Type[BaseOutputSchema] = sig.return_annotation
        if not (isinstance(output_schema_type, type) and issubclass(output_schema_type, BaseOutputSchema)):
             raise TypeError(f"Node '{node_name}' must have a return type annotation that is a subclass of BaseOutputSchema.")

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> OutputSchema:
            start_time = datetime.now(timezone.utc)
            input_schema = None
            error_msg = None
            output_schema = None
            status = "success"

            try:
                # Create and validate input schema
                input_data = args[0] if args else kwargs
                if isinstance(input_data, dict):
                    input_schema = input_schema_type(**input_data)
                elif isinstance(input_data, BaseInputSchema):
                    input_schema = input_data
                else:
                    raise TypeError(f"Invalid input type for node '{node_name}'. Expected a dictionary or BaseInputSchema subclass.")

                # Execute the node's core logic
                output_data = func(input_schema)

                # Create and validate output schema
                if isinstance(output_data, dict):
                    output_schema = output_schema_type(**output_data)
                elif isinstance(output_data, BaseOutputSchema):
                    output_schema = output_data
                else:
                    output_fields = output_schema_type.model_fields
                    base_fields = BaseOutputSchema.model_fields.keys()
                    target_field = next((f for f in output_fields if f not in base_fields), None)
                    if target_field:
                        output_schema = output_schema_type(**{target_field: output_data})
                    else:
                        raise TypeError(f"Cannot automatically assign output of type {type(output_data)} to any field in {output_schema_type.__name__}.")

            except ValidationError as e:
                status = "validation_error"
                error_msg = str(e)
                raise
            except Exception as e:
                status = "execution_error"
                error_msg = str(e)
                raise

            finally:
                if capture_io:
                    runtime_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    input_hash = hashlib.sha256(input_schema.model_dump_json().encode()).hexdigest() if input_schema else None
                    output_hash = hashlib.sha256(output_schema.model_dump_json().encode()).hexdigest() if output_schema else None

                    trace_event = TraceEvent(
                        trace_id=input_schema.trace_id if input_schema else str(uuid.uuid4()),
                        node_name=node_name,
                        version=version,
                        input_hash=input_hash,
                        output_hash=output_hash,
                        runtime_ms=runtime_ms,
                        status=status,
                        error_msg=error_msg,
                        governance_tags=",".join(tags or []),
                    )
                    trace_logger.log(trace_event)

            # Attach metadata to the final output
            if output_schema:
                output_schema.node_meta = NodeMeta(
                    node_name=node_name,
                    version=version,
                    tags=tags or [],
                    replay_trace_id=input_schema.trace_id if input_schema else None,
                    runtime_timestamp=start_time,
                )

            return output_schema

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
