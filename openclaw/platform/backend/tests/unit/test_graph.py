"""Unit tests for DAG validation/topology."""
import pytest

from app.domain.workflow import Workflow, WorkflowEdge, WorkflowNode
from app.engine.graph import GraphError, topological_order, validate_dag


def _wf(edges):
    nodes = [WorkflowNode(id=i, type="trigger.manual" if i == "a" else "logic.merge")
             for i in ["a", "b", "c"]]
    return Workflow(name="t", nodes=nodes,
                    edges=[WorkflowEdge(source=s, target=t) for s, t in edges])


def test_topological_order_linear():
    order = topological_order(_wf([("a", "b"), ("b", "c")]))
    assert order.index("a") < order.index("b") < order.index("c")


def test_cycle_detected():
    with pytest.raises(GraphError):
        validate_dag(_wf([("a", "b"), ("b", "c"), ("c", "a")]))


def test_unknown_edge_target():
    wf = Workflow(name="t",
                  nodes=[WorkflowNode(id="a", type="trigger.manual")],
                  edges=[WorkflowEdge(source="a", target="ghost")])
    with pytest.raises(GraphError):
        validate_dag(wf)
