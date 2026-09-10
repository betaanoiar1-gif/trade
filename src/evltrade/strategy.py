from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from hashlib import sha256
import json
from typing import Any

@dataclass(frozen=True)
class Node:
    op: str
    args: tuple['Node',...]=()
    value: Any=None
    def to_dict(self): return {"op":self.op,"value":self.value,"args":[a.to_dict() for a in self.args]}
    def hash(self)->str: return sha256(json.dumps(self.to_dict(),sort_keys=True,default=str).encode()).hexdigest()
    @property
    def depth(self): return 1+max((a.depth for a in self.args),default=0)
    @property
    def nodes(self): return 1+sum(a.nodes for a in self.args)

class StrategyDSL:
    ALLOWED={"and","or","not","gt","lt","eq","add","sub","mul","div","const","feature","indicator","rolling","position","volatility","liquidity","time"}
    @classmethod
    def validate(cls,node:Node):
        if node.op not in cls.ALLOWED: raise ValueError(f"unsupported op: {node.op}")
        for arg in node.args: cls.validate(arg)
        return True
    @staticmethod
    def evaluate(node:Node, context:dict[str,Any]):
        op=node.op; vals=[StrategyDSL.evaluate(a,context) for a in node.args]
        if op=="const": return node.value
        if op in {"feature","indicator","position","volatility","liquidity","time"}: return context.get(str(node.value))
        if op=="and": return all(vals)
        if op=="or": return any(vals)
        if op=="not": return not vals[0]
        if op=="gt": return vals[0]>vals[1]
        if op=="lt": return vals[0]<vals[1]
        if op=="eq": return vals[0]==vals[1]
        if op=="add": return vals[0]+vals[1]
        if op=="sub": return vals[0]-vals[1]
        if op=="mul": return vals[0]*vals[1]
        if op=="div": return vals[0]/vals[1] if vals[1] else 0
        if op=="rolling": return context.get(f"rolling:{node.value}")
        raise ValueError(op)

@dataclass(frozen=True)
class StrategyGenome:
    entry: Node; exit: Node; position_size: Node|None=None; risk: dict[str,Decimal]=field(default_factory=dict); execution: dict[str,Any]=field(default_factory=dict); parameters: dict[str,Decimal]=field(default_factory=dict)
    def __post_init__(self): StrategyDSL.validate(self.entry); StrategyDSL.validate(self.exit)
    @property
    def hash(self): return sha256(json.dumps(self.to_dict(),sort_keys=True,default=str,separators=(",",":")).encode()).hexdigest()
    def to_dict(self): return {"entry":self.entry.to_dict(),"exit":self.exit.to_dict(),"position_size":self.position_size.to_dict() if self.position_size else None,"risk":self.risk,"execution":self.execution,"parameters":self.parameters}
    def complexity(self):
        roots=[self.entry,self.exit]+([self.position_size] if self.position_size else [])
        nodes=sum(r.nodes for r in roots if r); return {"depth":max(r.depth for r in roots if r),"nodes":nodes,"parameters":len(self.parameters),"features":sum(1 for r in roots if r for n in _walk(r) if n.op in {"feature","indicator"})}
    def behavior_descriptor(self, observations:list[dict[str,Any]])->tuple[float,...]:
        hits=sum(bool(StrategyDSL.evaluate(self.entry,o)) for o in observations); exits=sum(bool(StrategyDSL.evaluate(self.exit,o)) for o in observations)
        n=max(1,len(observations)); return (hits/n,exits/n,self.complexity()["nodes"])

def _walk(node:Node):
    yield node
    for child in node.args: yield from _walk(child)
