import argparse
import json
from rich.console import Console
from rich.table import Table
from src.core.replay_trace import ReplayReader

def show_trace(trace_id: str):
    """
    Displays a formatted summary of a given trace ID.
    """
    console = Console()
    try:
        reader = ReplayReader(store="data/replays")
        trace = reader.load(trace_id)
    except FileNotFoundError:
        console.print(f"[bold red]Error: Trace ID '{trace_id}' not found.[/bold red]")
        return

    console.print(f"[bold]Trace Summary for {trace.trace_id}[/bold]")
    console.print(f"Task: {trace.task_name}")
    console.print(f"Status: {'Completed' if trace.end_time else 'In-progress'}")
    console.print(f"Start Time: {trace.start_time.isoformat()}")
    if trace.end_time:
        console.print(f"End Time: {trace.end_time.isoformat()}")
        duration = (trace.end_time - trace.start_time).total_seconds()
        console.print(f"Duration: {duration:.2f}s")

    table = Table(title="Executed Nodes")
    table.add_column("Node Name", style="cyan")
    table.add_column("Version", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Runtime (ms)", style="yellow")
    table.add_column("Input", no_wrap=False)
    table.add_column("Output", no_wrap=False)

    for node in trace.executed_nodes:
        input_str = json.dumps(node.input, indent=2)
        output_str = json.dumps(node.output, indent=2) if node.output else "N/A"
        table.add_row(
            node.node_name,
            node.version,
            node.status,
            f"{node.runtime_ms:.2f}" if node.runtime_ms is not None else "N/A",
            input_str,
            output_str,
        )

    console.print(table)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View a summary of a trace.")
    parser.add_argument("trace_id", type=str, help="The ID of the trace to view.")
    args = parser.parse_args()
    show_trace(args.trace_id)
