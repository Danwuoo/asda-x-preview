import unittest
import uuid
from unittest.mock import MagicMock, patch

from src.core.dag_engine import (
    DAGFlowBuilder,
    DAGState,
    NodeWrapper,
    ContextInjector,
    ReplayManager,
    register_node,
    build_trace_id,
)
from src.core.prompt_context import PromptContext
from src.core.replay_trace import ReplayReader, ReplayWriter, TraceRecord, NodeExecutionTrace


class TestDAGEngine(unittest.TestCase):
    def test_build_trace_id(self):
        trace_id = build_trace_id()
        self.assertIsInstance(trace_id, str)
        self.assertEqual(len(trace_id), 36)  # UUID4 length

    def test_dag_state(self):
        state = DAGState(input_data={"key": "value"}, trace_id="test_trace")
        self.assertEqual(state.input_data, {"key": "value"})
        self.assertEqual(state.trace_id, "test_trace")
        self.assertFalse(state.is_replay)

    def test_dag_flow_builder(self):
        builder = DAGFlowBuilder()
        self.assertEqual(builder.name, "default_asda_flow")

        @register_node(builder, "test_node")
        def test_node(state: DAGState) -> DAGState:
            state.input_data["processed"] = True
            return state

        builder.set_entry_point("test_node")
        graph = builder.build()
        initial_state = {"input_data": {"key": "value"}, "trace_id": "test_trace"}
        final_state = graph.invoke(initial_state)
        self.assertTrue(final_state["input_data"]["processed"])

    def test_node_wrapper(self):
        mock_func = MagicMock(return_value=DAGState(input_data={"output": "processed"}))
        wrapper = NodeWrapper(mock_func, "test_node")
        initial_state = DAGState(input_data={"input": "raw"}, trace_id="test_trace")
        result_state = wrapper(initial_state)
        mock_func.assert_called_once_with(initial_state)
        self.assertEqual(result_state.input_data["output"], "processed")

    def test_context_injector(self):
        context = PromptContext(
            source_type="text",
            agent_id="test_agent",
            time= "2024-01-01T00:00:00",
            context_summary="Test context",
        )
        injector = ContextInjector(context)
        initial_state = DAGState(input_data={}, trace_id="test_trace")
        result_state = injector(initial_state)
        self.assertEqual(result_state.context, context)

    def test_replay_manager(self):
        mock_reader = MagicMock(spec=ReplayReader)
        mock_writer = MagicMock(spec=ReplayWriter)
        trace_id = "replay_trace_id"
        trace_record = TraceRecord(
            trace_id=trace_id,
            task_name="test_task",
            executed_nodes=[
                NodeExecutionTrace(
                    node_name="test_node",
                    version="v1.0",
                    input={"input": "raw"},
                    output={"output": "processed"},
                )
            ],
        )
        mock_reader.load.return_value = trace_record

        replay_manager = ReplayManager(mock_writer, mock_reader)
        builder = DAGFlowBuilder()

        @register_node(builder, "test_node")
        def test_node(state: DAGState) -> DAGState:
            # This should not be called in replay mode
            raise Exception("Node should not be executed")

        builder.set_entry_point("test_node")
        with patch("src.core.dag_engine.DAGFlowBuilder.build") as mock_build:
            mock_graph = MagicMock()
            mock_build.return_value = mock_graph
            mock_graph.invoke.return_value = {"input_data": {"output": "replayed"}}

            final_state = replay_manager.replay(trace_id, builder)

            mock_build.assert_called_once()
            self.assertTrue(mock_graph.invoke.call_args[0][0].is_replay)
            self.assertEqual(final_state["input_data"]["output"], "replayed")


if __name__ == "__main__":
    unittest.main()
