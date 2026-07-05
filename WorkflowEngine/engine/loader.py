import json
from pathlib import Path
from typing import Dict, List

from .models import ToolDefinition, AgentDefinition, Workflow


class DataLoader:
    def __init__(self, tools_path: Path, workflows_path: Path):
        self.tools_path = tools_path
        self.workflows_path = workflows_path
        self.tool_definitions: Dict[str, ToolDefinition] = {}
        self.agent_definitions: Dict[str, AgentDefinition] = {}
        self.workflows: Dict[str, Workflow] = {}
        self._load_tools_and_agents()
        self._load_workflows()

    def _load_tools_and_agents(self):
        data = json.loads(self.tools_path.read_text())
        # dummy_data.json contains separate lists for tools and agents
        for tool in data.get("tools", []):
            td = ToolDefinition(**tool)
            self.tool_definitions[td.id] = td
        for agent in data.get("agents", []):
            ad = AgentDefinition(**agent)
            self.agent_definitions[ad.id] = ad

    def _load_workflows(self):
        raw = json.loads(self.workflows_path.read_text())
        # myworkflow.json is a list of workflows
        for wf in raw:
            workflow = Workflow(**wf)
            self.workflows[workflow.name] = workflow

    def get_tool(self, tool_id: str) -> ToolDefinition:
        return self.tool_definitions[tool_id]

    def get_agent(self, agent_id: str) -> AgentDefinition:
        return self.agent_definitions[agent_id]

    def get_workflow(self, name: str) -> Workflow:
        return self.workflows[name]
