import os
import logging
from typing import Dict, Any, List

from .loader import DataLoader
from .factories import AgentFactory

import networkx as nx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()  # reads .env if present


class ExecutionLogger:
    def __init__(self):
        self.entries: List[Dict[str, Any]] = []

    def log(self, **kwargs):
        from datetime import datetime, timezone

        entry = {"timestamp": datetime.now(timezone.utc).isoformat()}
        entry.update(kwargs)
        self.entries.append(entry)
        logger.info(f"Execution log entry: {entry}")

    def get_all(self):
        return self.entries


class WorkflowExecutor:
    def __init__(self, loader: DataLoader):
        self.loader = loader
        self.agent_factory = AgentFactory(loader)
        self._strategy = os.getenv("WORKFLOW_EXECUTION_STRATEGY", "topological").lower()

    def _build_graph(self, workflow) -> nx.DiGraph:
        g = nx.DiGraph()
        # add nodes
        for node in workflow.nodes:
            g.add_node(node.id, agent_id=node.agent_id, data=node.data)
        # add edges
        for edge in workflow.edges:
            g.add_edge(edge.source, edge.target)
        return g

    def _get_execution_order(self, graph: nx.DiGraph) -> List[str]:
        # strategy flag may be "topological" or "langgraph" (case-insensitive)
        if self._strategy == "langgraph":
            logger.debug("Execution strategy set to langgraph; performing toposort via networkx as a placeholder")
            # langgraph has no documented simple topological API; use networkx under the hood
        try:
            order = list(nx.topological_sort(graph))
            logger.debug("Using networkx topological sort")
            return order
        except nx.NetworkXUnfeasible as e:
            logger.error("Graph contains cycles: %s", e)
            raise

    def execute(self, workflow_name: str, start_properties: Dict[str, Any]) -> Dict[str, Any]:
        wf = self.loader.get_workflow(workflow_name)
        graph = self._build_graph(wf)
        order = self._get_execution_order(graph)

        state: Dict[str, Any] = {"workflow_name": workflow_name, "start_properties": start_properties, "tool_results": {}, "node_states": {}}
        exec_log = ExecutionLogger()

        for node_id in order:
            node = next(n for n in wf.nodes if n.id == node_id)
            agent_id = node.agent_id
            if not agent_id:
                continue
            agent = self.agent_factory.get_agent(agent_id)
            exec_log.log(event="agent_start", node_id=node_id, agent=agent.name())
            result_state = agent.run(state)
            state["node_states"][node_id] = result_state.copy()
            exec_log.log(event="agent_end", node_id=node_id, agent=agent.name(), state_snapshot=result_state)

            # capture end agent properties if this node corresponds to the end type
            agent_def = self.loader.get_agent(agent_id)
            if agent_def.type == "end":
                # write snapshot of current state as end_properties
                state["end_properties"] = {**state.get("end_properties", {}), **result_state}

        # after execution, end properties already stored (may be empty)
        end_props = state.get("end_properties", {})
        if not end_props:
            # if workflow didn't include a dedicated end agent, use last node's snapshot
            if order:
                last_node = order[-1]
                end_props = state["node_states"].get(last_node, {})
                logger.debug("No explicit end agent; using last node state as end_properties")
        return {"end_properties": end_props, "state": state, "log": exec_log.get_all()}
