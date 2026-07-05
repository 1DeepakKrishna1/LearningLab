from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ToolDefinition(BaseModel):
    id: str
    name: str
    description: str
    type: str
    properties: Dict[str, Any]
    icon: Optional[str]


class AgentDefinition(BaseModel):
    id: str
    name: str
    description: str
    type: str
    tools: List[str]
    properties: Dict[str, Any]
    icon: Optional[str]
    color: Optional[str]


class NodeData(BaseModel):
    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    tools: Optional[List[str]] = None
    toolConfigs: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


class Node(BaseModel):
    id: str
    node_kind: str
    agent_id: Optional[str]
    tool_id: Optional[str]
    position: Optional[Dict[str, Any]]
    data: NodeData


class Edge(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str]
    type: Optional[str]


class Workflow(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: Optional[str]
    nodes: List[Node]
    edges: List[Edge]
    created_at: Optional[str]
    updated_at: Optional[str]
    is_template: Optional[bool]
    tags: Optional[List[str]]
