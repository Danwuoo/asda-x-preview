from __future__ import annotations

import networkx as nx
from typing import Any, Dict


class ActionTraceLogger:
    """Maintain a DAG of decision versions."""

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_version(self, record: Dict[str, Any]) -> None:
        vid = record["version_id"]
        self.graph.add_node(vid, **record)
        parent = record.get("parent_version")
        if parent:
            self.graph.add_edge(parent, vid)

    def to_dict(self) -> Dict[str, Any]:
        return nx.node_link_data(self.graph)
