from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterable
from .core import Individual

@dataclass(frozen=True)
class CoEvolutionRound:
    generation:int
    trader_scores:dict[str,float]
    market_maker_scores:dict[str,float]
    adversary_scores:dict[str,float]

class OptionalCoEvolution:
    """Opt-in adversarial sandbox. It never mutates historical replay state."""
    def __init__(self,seed:int=42): self.seed=seed; self.history:list[CoEvolutionRound]=[]
    def run(self,traders:Iterable[Individual],makers:Iterable[Individual],adversaries:Iterable[Individual],score:Callable[[Individual,Individual,Individual],float],generations:int=1):
        traders=list(traders); makers=list(makers); adversaries=list(adversaries); rounds=[]
        for g in range(generations):
            ts={t.individual_id:sum(score(t,m,a) for m in makers for a in adversaries) for t in traders}
            ms={m.individual_id:sum(score(t,m,a) for t in traders for a in adversaries) for m in makers}
            ass={a.individual_id:sum(-score(t,m,a) for t in traders for m in makers) for a in adversaries}
            rounds.append(CoEvolutionRound(g,ts,ms,ass))
        self.history.extend(rounds); return rounds
