from __future__ import annotations

import json
import os
import uuid
from typing import Any, Callable, Dict, List, Optional, Type

from langchain_core.pydantic_v1 import BaseModel
from langgraph.graph import END, StateGraph

from src.core.node_interface import asda_node
from src.core.prompt_context import PromptContext
from src.core.replay_trace import ReplayReader, ReplayWriter, TraceRecord


class DAGState(BaseModel):
    """Represents the state of the DAG."""

    initial_input: Any
    node_outputs: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[PromptContext] = None
    trace_id: str = ""
    is_replay: bool = False
    replay_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


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

    def build_default_flow(self):
        """Build a default DAG flow for demonstration."""
        self.set_entry_point("start")
        self.add_edge("start", "context_injector")
        self.add_edge("context_injector", "processing_node")
        self.add_edge("processing_node", "output_node")
        return self.build()


# NodeWrapper and register_node are deprecated in favor of the asda_node decorator.
# The `asda_node` decorator now handles all tracing, validation, and metadata.
# The DAGFlowBuilder now directly accepts the decorated node functions.


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

    def replay(self, trace_id: str, builder: DAGFlowBuilder) -> DAGState:
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
        return replay_graph.invoke(state)


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
