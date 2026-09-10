from __future__ import annotations
from dataclasses import dataclass, asdict
from decimal import Decimal
import random, statistics
from typing import Callable, Sequence

@dataclass(frozen=True)
class Window:
    train: tuple[int,int]; validation: tuple[int,int]; oos: tuple[int,int]

@dataclass(frozen=True)
class WFResult:
    windows: tuple[Window,...]
    scores: tuple[float,...]

class WalkForward:
    def __init__(self, train: int, validation: int, oos: int, step: int, expanding: bool=False):
        self.train=train; self.validation=validation; self.oos=oos; self.step=step; self.expanding=expanding
    def windows(self,n:int)->list[Window]:
        out=[]; start=0
        while start+self.train+self.validation+self.oos<=n:
            train_start=0 if self.expanding else start
            out.append(Window((train_start,start+self.train),(start+self.train,start+self.train+self.validation),(start+self.train+self.validation,start+self.train+self.validation+self.oos)))
            start+=self.step
        return out

@dataclass(frozen=True)
class RobustnessResult:
    scenario: str; score: float; relative_change: float

class RobustnessLab:
    def sweep(self, baseline: float, scenarios: dict[str,float], tolerance: float=0.20)->list[RobustnessResult]:
        return [RobustnessResult(k,v,(v-baseline)/baseline if baseline else 0.0) for k,v in scenarios.items()]
    def stable(self, result: RobustnessResult, tolerance: float=0.20)->bool: return abs(result.relative_change)<=tolerance

@dataclass(frozen=True)
class MonteCarloSummary:
    mean: float; median: float; p05: float; p95: float; worst: float; best: float

class MonteCarloLab:
    def run(self, returns: Sequence[float], trials: int=1000, seed: int=42, execution_noise: float=0.0)->MonteCarloSummary:
        if not returns: raise ValueError("returns cannot be empty")
        rng=random.Random(seed); outcomes=[]
        for _ in range(trials):
            sample=list(returns); rng.shuffle(sample); eq=1.0
            for r in sample: eq*=1.0+r+rng.gauss(0,execution_noise)
            outcomes.append(eq-1.0)
        s=sorted(outcomes)
        q=lambda p:s[min(len(s)-1,max(0,int(p*(len(s)-1))))]
        return MonteCarloSummary(statistics.mean(s),statistics.median(s),q(.05),q(.95),s[0],s[-1])

class SensitivityLab:
    def grid(self, evaluator: Callable[[float,float,float,float],float], capitals, latencies, fees, liquidity):
        rows=[]
        for c in capitals:
            for l in latencies:
                for f in fees:
                    for liq in liquidity: rows.append({"capital":c,"latency":l,"fee":f,"liquidity":liq,"score":evaluator(c,l,f,liq)})
        return rows

class RegimeLab:
    def classify(self, prices: Sequence[float], volatility_threshold: float=0.02)->list[str]:
        if not prices: return []
        out=["unknown"]
        for a,b in zip(prices,prices[1:]):
            ret=(b-a)/a if a else 0
            out.append("up" if ret>volatility_threshold else "down" if ret<-volatility_threshold else "normal")
        return out
    def performance_by_regime(self, returns: Sequence[float], regimes: Sequence[str])->dict[str,float]:
        acc={}
        for r,x in zip(regimes,returns): acc.setdefault(r,[]).append(x)
        return {k:statistics.mean(v) for k,v in acc.items() if v}

class CapacityLab:
    CAPITALS=(1000,2500,5000,10000,50000,100000,1000000)
    def evaluate(self, base_return: float, impact_rate: float=0.10):
        return [{"capital":c,"return":base_return/(1+impact_rate*max(0,c/10000-1))} for c in self.CAPITALS]
