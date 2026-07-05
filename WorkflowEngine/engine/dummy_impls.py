"""Concrete dummy classes for every agent and tool in dummy_data.json.
These classes exist primarily for documentation and inspection; the factory
in ``factories.py`` will instantiate ``DummyAgent``/``DummyTool`` instances
regardless of this file.  Having concrete classes means a user can import
``from engine.dummy_impls import DataIngestionAgent`` if desired.
"""

from typing import Dict, Any

from core.base_agent import BaseAgent
from core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)

# __all__ will be populated dynamically at import time
__all__ = []

# definitions extracted from the JSON at runtime; to avoid circular imports
# we defer the loader lookup until the class is instantiated.

from .loader import DataLoader

LOADER = DataLoader(__import__('pathlib').Path(__file__).parent.parent / 'dummy_data.json',
                    __import__('pathlib').Path(__file__).parent.parent / 'myworkflow.json')


class GenericDummyTool(BaseTool):
    def __init__(self, definition: Dict[str, Any]):
        self.definition = definition

    def name(self) -> str:
        return self.definition.get('name', 'unknown')

    def description(self) -> str:
        return self.definition.get('description', '')

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"{self.name()} (generic) running with {input_data}")
        return {"status": "ok", "input": input_data}


class GenericDummyAgent(BaseAgent):
    def __init__(self, definition: Dict[str, Any]):
        self.definition = definition
        self.tools = []
        for tid in definition.get('tools', []):
            tool_def = LOADER.get_tool(tid).dict()
            self.tools.append(GenericDummyTool(tool_def))

    def name(self) -> str:
        return self.definition.get('name', 'unknown')

    def description(self) -> str:
        return self.definition.get('description', '')

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"{self.name()} (generic) running with state {state}")
        for tool in self.tools:
            tool.run(state)
        return state


# create classes dynamically for each entity
for tool_def in LOADER.tool_definitions.values():
    class_name = tool_def.name.replace(' ', '') + 'Tool'
    cls = type(
        class_name,
        (GenericDummyTool,),
        {'__doc__': f"Dummy tool for {tool_def.name}", 'definition': tool_def}
    )
    globals()[class_name] = cls
    __all__.append(class_name)

for agent_def in LOADER.agent_definitions.values():
    class_name = agent_def.name.replace(' ', '') + 'Agent'
    cls = type(
        class_name,
        (GenericDummyAgent,),
        {'__doc__': f"Dummy agent for {agent_def.name}", 'definition': agent_def}
    )
    globals()[class_name] = cls
    __all__.append(class_name)
