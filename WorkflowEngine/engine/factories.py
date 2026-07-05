from typing import Dict, Any

from .models import ToolDefinition, AgentDefinition
from .loader import DataLoader
from core.base_tool import BaseTool
from core.base_agent import BaseAgent
import logging

logger = logging.getLogger(__name__)


class DummyTool(BaseTool):
    def __init__(self, definition: ToolDefinition):
        self.definition = definition

    def name(self) -> str:
        return self.definition.name

    def description(self) -> str:
        return self.definition.description

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # dummy behavior: echo input and add a marker
        logger.debug(f"Running tool {self.name()} with input {input_data}")
        output = {"tool_id": self.definition.id,
                  "result": f"processed by {self.name()}",
                  "input_snapshot": input_data}
        logger.debug(f"Tool {self.name()} output {output}")
        return output


class DummyAgent(BaseAgent):
    def __init__(self, definition: AgentDefinition, loader: DataLoader):
        self.definition = definition
        self.loader = loader
        # instantiate tools referenced by this agent
        self.tools = []
        for tid in definition.tools:
            tool_def = loader.get_tool(tid)
            self.tools.append(DummyTool(tool_def))

    def name(self) -> str:
        return self.definition.name

    def description(self) -> str:
        return self.definition.description

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # state is mutated and returned
        logger.debug(f"Agent {self.name()} starting with state {state}")
        # each tool is invoked sequentially
        for tool in self.tools:
            tool_input = {
                "workflow_state": state,
                "agent_properties": self.definition.properties,
            }
            tool_output = tool.run(tool_input)
            # store the result under state for traceability
            key = f"{self.definition.id}:{tool.definition.id}"
            state.setdefault("tool_results", {})[key] = tool_output
        logger.debug(f"Agent {self.name()} finished; state now {state}")
        return state


class AgentFactory:
    def __init__(self, loader: DataLoader):
        self.loader = loader
        self._cache: Dict[str, DummyAgent] = {}

    def get_agent(self, agent_id: str) -> DummyAgent:
        if agent_id not in self._cache:
            definition = self.loader.get_agent(agent_id)
            self._cache[agent_id] = DummyAgent(definition, self.loader)
        return self._cache[agent_id]


class ToolFactory:
    def __init__(self, loader: DataLoader):
        self.loader = loader
        self._cache: Dict[str, DummyTool] = {}

    def get_tool(self, tool_id: str) -> DummyTool:
        if tool_id not in self._cache:
            definition = self.loader.get_tool(tool_id)
            self._cache[tool_id] = DummyTool(definition)
        return self._cache[tool_id]
