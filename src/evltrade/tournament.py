from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from .core import D, Individual

@dataclass(frozen=True)
class TournamentMode:
    name:str; spread_mult:Decimal=D("1"); liquidity_mult:Decimal=D("1"); latency_ms:int=0; fee_mult:Decimal=D("1")

MODES={
    "normal":TournamentMode("normal"),
    "volatile":TournamentMode("volatile",D("1.5"),D("1")),
    "crash":TournamentMode("crash",D("2"),D("0.5")),
    "low_liquidity":TournamentMode("low_liquidity",D("2"),D("0.25")),
    "wide_spread":TournamentMode("wide_spread",D("3"),D("0.75")),
    "high_latency":TournamentMode("high_latency",D("1"),D("1"),250),
    "cost_shock":TournamentMode("cost_shock",D("2"),D("0.75"),0,D("3")),
}

@dataclass
class TournamentResult:
    ranking:list[dict]=field(default_factory=list)
    allocations:dict[str,Decimal]=field(default_factory=dict)

class SharedCapitalTournament:
    def __init__(self,capital:Decimal=D("1000"),max_exposure:Decimal|None=None): self.capital=capital; self.max_exposure=max_exposure or capital
    def allocate(self, individuals:list[Individual], score_key="score")->dict[str,Decimal]:
        positives={i.individual_id:max(0.0,i.fitness.get(score_key,sum(i.fitness.values()))) for i in individuals}; total=sum(positives.values())
        if total<=0:return {i.individual_id:D("0") for i in individuals}
        return {k:self.capital*D(str(v/total)) for k,v in positives.items()}
    def rank(self,individuals:list[Individual])->TournamentResult:
        ranked=sorted(individuals,key=lambda x:sum(x.fitness.values()),reverse=True); alloc=self.allocate(ranked)
        rows=[]
        for n,i in enumerate(ranked,1): rows.append({"rank":n,"individual_id":i.individual_id,"fitness":i.fitness,"capital":str(alloc[i.individual_id])})
        return TournamentResult(rows,alloc)
