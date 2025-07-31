import os
import sys

CURRENT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.decision.versioning import (
    VersionIDGenerator,
    DecisionDiffer,
    AuditStoreManager,
    VersionedActionAudit,
)


def test_version_id_uniqueness():
    gen = VersionIDGenerator()
    d1 = gen.generate({"a": 1})
    d2 = gen.generate({"a": 1})
    assert d1 != d2


def test_decision_differ():
    diff = DecisionDiffer().compare({"a": 1}, {"a": 2})
    assert "values_changed" in diff


def test_store_round_trip(tmp_path):
    store = AuditStoreManager(root=str(tmp_path))
    store.save("v1", {"foo": 1})
    assert store.load("v1") == {"foo": 1}


def test_trace_logger_and_audit(tmp_path):
    store = AuditStoreManager(root=str(tmp_path))
    audit = VersionedActionAudit(store=store)
    v1 = audit.record({"act": "a"})
    v2 = audit.record({"act": "b"})
    graph = audit.tracer.graph
    assert graph.has_edge(v1, v2)
