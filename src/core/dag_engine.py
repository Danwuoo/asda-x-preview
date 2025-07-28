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

    input_data: Any
    context: Optional[PromptContext] = None
    trace_id: str = ""
    replay_nodes: Dict[str, Any] = {}

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
        self.workflow.add_edge(list(self.nodes.keys())[-1], END)
        return self.workflow.compile()


class ContextInjector:
    """Injects context into the DAG state."""

    def __init__(self, context: PromptContext):
        self.context = context

    def inject(self, state: DAGState) -> DAGState:
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
        trace_record = self.replay_reader.load(trace_id)
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
        )
        return replay_graph.invoke(state)


# Helper utils
def build_trace_id() -> str:
    """Generate a unique trace ID."""
    return str(uuid.uuid4())


def register_node(
    builder: DAGFlowBuilder, name: str, version: str = "v1.0", tags: List[str] = None
):
    """Decorator to register a function as a DAG node."""

    def decorator(func: Callable[[DAGState], DAGState]):
        @asda_node(name=name, version=version, tags=tags or [])
        def wrapper(state: DAGState) -> DAGState:
            # If in replay mode, use the stored output
            if name in state.replay_nodes:
                return state.replay_nodes[name]
            return func(state)

        builder.add_node(name, wrapper)
        return wrapper

    return decorator
