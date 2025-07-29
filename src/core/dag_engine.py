from __future__ import annotations

import json
import os
import uuid
from typing import Any, Callable, Dict, List, Optional, Type

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field, ConfigDict
from src.core.node_interface import (
    asda_node,
    register_node as _register_node,
    list_registered_nodes as _list_registered_nodes,
)
from src.core.prompt_context import PromptContext
from src.core.replay_trace import ReplayReader, ReplayWriter, TraceRecord


class DAGState(BaseModel):
    """Represents the state of the DAG."""

    initial_input: Any = Field(default_factory=dict, alias="input_data")
    node_outputs: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[PromptContext] = None
    trace_id: str = ""
    is_replay: bool = False
    replay_data: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)


class DAGFlowBuilder:
    """Build and run a graph-based DAG flow."""

    def __init__(self, name: str = "default_asda_flow"):
        self.name = name
        self.workflow = StateGraph(DAGState)
        self.nodes: Dict[str, Callable] = {}

    def add_node(self, name: str, node: Callable):
        """Add a node to the graph."""
        self.workflow.add_node(name, node)
        self.nodes[name] = node

    def add_edge(self, start_node: str, end_node: str):
        """Add a directed edge between two nodes."""
        self.workflow.add_edge(start_node, end_node)

    def set_entry_point(self, node_name: str):
        """Set the entry point for the graph."""
        self.workflow.set_entry_point(node_name)

    def add_conditional_edge(
        self,
        start_node: str,
        condition: Callable[[DAGState], str],
        outcomes: Dict[str, str],
    ):
        """Add a conditional edge based on state."""
        self.workflow.add_conditional_edges(start_node, condition, outcomes)

    def build(self):
        """Compile the graph into a runnable workflow."""
        # By default, add an edge from the last added node to the end
        if self.nodes:
            last_node_name = list(self.nodes.keys())[-1]
            self.workflow.add_edge(last_node_name, END)
        return self.workflow.compile()


# NodeWrapper and register_node are deprecated in favor of the asda_node decorator.
# The `asda_node` decorator now handles all tracing, validation, and metadata.
# The DAGFlowBuilder now directly accepts the decorated node functions.

# Temporary shims for backwards compatibility with older tests that
# still import `register_node` and `list_registered_nodes` from this
# module. These simply re-export the implementations from
# `src.core.node_interface`.

def register_node(node_function: Callable[..., Any], name: Optional[str] = None) -> None:
    _register_node(node_function, name)


def list_registered_nodes() -> List[str]:
    return _list_registered_nodes()


class ContextInjector:
    """Injects context into the DAG state."""

    def __init__(self, context: PromptContext):
        self.context = context

    def __call__(self, state: DAGState) -> DAGState:
        """Injects the context into the state."""
        state.context = self.context
        return state


class ReplayManager:
    """Manages the replay of DAG traces."""

    def __init__(self, replay_writer: ReplayWriter, replay_reader: ReplayReader):
        self.replay_writer = replay_writer
        self.replay_reader = replay_reader

    def replay(self, trace_id: str, builder: DAGFlowBuilder) -> Dict[str, Any]:
        """Replays a given trace_id."""
        try:
            trace_record = self.replay_reader.load(trace_id)
        except FileNotFoundError:
            raise ValueError(f"Trace with ID '{trace_id}' not found.")

        initial_input = trace_record.executed_nodes[0].input
        replay_nodes = {
            node.node_name: node.output for node in trace_record.executed_nodes
        }

        # Create a new graph for replay
        replay_graph = builder.build()
        state = DAGState(
            input_data=initial_input,
            trace_id=trace_id,
            replay_nodes=replay_nodes,
            is_replay=True,
        )
        result_state = replay_graph.invoke(state)
        return {"replay_nodes": replay_nodes, "meta": result_state}


def start_node(state: DAGState) -> DAGState:
    """A starting node."""
    state.node_outputs["start"] = "start_node_output"
    return state


def context_injector_node(state: DAGState) -> DAGState:
    """A context injector node."""
    state.node_outputs["context_injector"] = "context_injector_node_output"
    return state


def processing_node(state: DAGState) -> DAGState:
    """A processing node."""
    state.node_outputs["processing"] = "processing_node_output"
    return state


def output_node(state: DAGState) -> DAGState:
    """An output node."""
    state.node_outputs["output"] = "output_node_output"
    return state



def _retriever_node(state: DAGState) -> DAGState:
    query = state.initial_input.get("query", "")
    state.node_outputs["retriever_node"] = {"documents": [f"Document for: {query}"]}
    state.initial_input = {"prompt": query}
    return state


def _llm_inference_node(state: DAGState) -> DAGState:
    prompt = state.initial_input.get("prompt", "")
    state.node_outputs["llm_inference_node"] = {"response": f"Response to: {prompt}"}
    state.initial_input = {"action": prompt}
    return state


def _executor_node(state: DAGState) -> DAGState:
    action = state.initial_input.get("action", "")
    state.node_outputs["executor_node"] = {"result": f"Executed: {action}"}
    return state

def build_default_dag() -> DAGFlowBuilder:
    """Build the default DAG."""
    builder = DAGFlowBuilder(name="default_asda_flow")
    builder.add_node("retriever_node", _retriever_node)
    builder.add_node("llm_inference_node", _llm_inference_node)
    builder.add_node("executor_node", _executor_node)
    builder.set_entry_point("retriever_node")
    builder.add_edge("retriever_node", "llm_inference_node")
    builder.add_edge("llm_inference_node", "executor_node")
    return builder


# Helper utils
def build_trace_id() -> str:
    """Generate a unique trace ID."""
    return str(uuid.uuid4())


def validate_io(node_func):
    """A decorator to validate node input and output schemas (conceptual)."""
    # This is a placeholder for a more complex implementation
    # that would use pydantic models to validate the input and output
    # of the node function.
    def wrapper(state: DAGState) -> DAGState:
        # Here you would add your validation logic
        # For example, checking if the input_data matches a certain schema
        result_state = node_func(state)
        # And then checking the result_state
        return result_state

    return wrapper
