from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RenderGraphNode:
    node_id: str
    kind: str
    inputs: list[str]=field(default_factory=list)
    settings: dict[str,Any]=field(default_factory=dict)


@dataclass(slots=True)
class RenderGraph:
    nodes: list[RenderGraphNode]=field(default_factory=list)

    def add(self,node_id:str,kind:str,*,inputs:list[str]|None=None,**settings:Any)->RenderGraphNode:
        node=RenderGraphNode(node_id,kind,list(inputs or []),dict(settings)); self.nodes.append(node); return node

    def to_dict(self)->dict[str,Any]: return {"nodes":[{"id":n.node_id,"kind":n.kind,"inputs":list(n.inputs),"settings":dict(n.settings)} for n in self.nodes]}
