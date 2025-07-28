import unittest
from unittest.mock import MagicMock, patch

from langgraph.graph import StateGraph

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from langgraph.graph import StateGraph

from src.core.dag_engine import (
    DAGFlowBuilder,
    DAGState,
    register_node,
    ContextInjector,
    ReplayManager,
)
from src.core.prompt_context import PromptContext
from src.core.replay_trace import ReplayWriter, ReplayReader, TraceRecord, NodeExecutionTrace


class TestDAGEngine(unittest.TestCase):
    def test_dag_flow_builder(self):
        builder = DAGFlowBuilder()
        self.assertEqual(builder.name, "default_asda_flow")
        self.assertIsInstance(builder.workflow, StateGraph)

    def test_add_node(self):
        builder = DAGFlowBuilder()
        mock_node = MagicMock()
        builder.add_node("test_node", mock_node)
        self.assertIn("test_node", builder.nodes)
        self.assertEqual(builder.nodes["test_node"], mock_node)

    def test_register_node_decorator(self):
        builder = DAGFlowBuilder()

        @register_node(builder, name="test_node")
        def my_test_node(state: DAGState) -> DAGState:
            return state

        self.assertIn("test_node", builder.nodes)

    def test_context_injector(self):
        context = PromptContext(
            source_type="log",
            agent_id="test_agent",
            time=datetime.now(),
            context_summary="Test log message",
        )
        injector = ContextInjector(context)
        initial_state = DAGState(input_data={"key": "value"})
        new_state = injector.inject(initial_state)
        self.assertEqual(new_state.context, context)

    @patch("src.core.dag_engine.ReplayReader")
    def test_replay_manager(self, MockReplayReader):
        mock_reader = MockReplayReader.return_value
        mock_writer = MagicMock(spec=ReplayWriter)
        manager = ReplayManager(replay_writer=mock_writer, replay_reader=mock_reader)

        trace_id = "test_trace_123"
        trace_record = TraceRecord(
            trace_id=trace_id,
            task_name="test_task",
            executed_nodes=[
                NodeExecutionTrace(
                    node_name="start_node",
                    version="1.0",
                    input={"data": "initial"},
                    output={"data": "processed"},
                )
            ],
        )
        mock_reader.load.return_value = trace_record

        builder = DAGFlowBuilder()
        builder.add_node("start_node", lambda x: x)
        builder.set_entry_point("start_node")

        state = manager.replay(trace_id, builder)
        self.assertEqual(state["replay_nodes"]["start_node"]["data"], "processed")


if __name__ == "__main__":
    unittest.main()
