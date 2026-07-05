"""DAG utilities: cycle detection and topological ordering."""
from __future__ import annotations

from ..domain.workflow import Workflow


class GraphError(ValueError):
    pass


def validate_dag(workflow: Workflow) -> None:
    """Raise GraphError if the workflow is not a valid DAG."""
    node_ids = {n.id for n in workflow.nodes}
    if not node_ids:
        raise GraphError("Workflow has no nodes.")
    for e in workflow.edges:
        if e.source not in node_ids:
            raise GraphError(f"Edge references unknown source '{e.source}'.")
        if e.target not in node_ids:
            raise GraphError(f"Edge references unknown target '{e.target}'.")
    # Cycle detection via topological sort.
    topological_order(workflow)


def topological_order(workflow: Workflow) -> list[str]:
    """Return node ids in topological order (Kahn's algorithm)."""
    indeg: dict[str, int] = {n.id: 0 for n in workflow.nodes}
    adj: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
    for e in workflow.edges:
        adj[e.source].append(e.target)
        indeg[e.target] += 1

    queue = [nid for nid, d in indeg.items() if d == 0]
    order: list[str] = []
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for nxt in adj[nid]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)

    if len(order) != len(workflow.nodes):
        raise GraphError("Workflow graph contains a cycle.")
    return order


def entry_nodes(workflow: Workflow) -> list[str]:
    """Nodes with no incoming edges (triggers / roots)."""
    targets = {e.target for e in workflow.edges}
    return [n.id for n in workflow.nodes if n.id not in targets]
