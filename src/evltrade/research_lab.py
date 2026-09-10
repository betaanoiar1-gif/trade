from __future__ import annotations
from dataclasses import dataclass
import random, statistics
from typing import Callable, Sequence, Any

@dataclass(frozen=True)
class Window:
    train: tuple[int,int]; validation: tuple[int,int]; oos: tuple[int,int]

@dataclass(frozen=True)
class WFResult:
    windows: tuple[Window,...]; scores: tuple[float,...]

class WalkForward:
    def __init__(self,train:int,validation:int,oos:int,step:int,expanding:bool=False):
        if min(train,validation,oos,step)<=0: raise ValueError("window sizes must be positive")
        self.train,self.validation,self.oos,self.step,self.expanding=train,validation,oos,step,expanding
    def windows(self,n:int)->list[Window]:
        out=[]; start=0
        while start+self.train+self.validation+self.oos<=n:
            train_start=0 if self.expanding else start; train_end=start+self.train; val_end=train_end+self.validation; oos_end=val_end+self.oos
            out.append(Window((train_start,train_end),(train_end,val_end),(val_end,oos_end))); start+=self.step
        return out
    def evaluate(self,n:int,scorer:Callable[[tuple[int,int],tuple[int,int],tuple[int,int]],float])->WFResult:
        ws=self.windows(n); return WFResult(tuple(ws),tuple(scorer(w.train,w.validation,w.oos) for w in ws))

@dataclass(frozen=True)
class RobustnessResult:
    scenario:str; score:float; relative_change:float; stable:bool

class RobustnessLab:
    def sweep(self,baseline:float,scenarios:dict[str,float],tolerance:float=.20)->list[RobustnessResult]:
        out=[]
        for name,score in scenarios.items():
            rel=(score-baseline)/abs(baseline) if baseline else 0.0; out.append(RobustnessResult(name,score,rel,abs(rel)<=tolerance))
        return out
    def matrix(self,baseline:float,axes:dict[str,Sequence[float]],evaluator:Callable[[dict[str,float]],float],tolerance:float=.20)->list[dict[str,Any]]:
        rows=[]; keys=list(axes)
        def rec(i,current):
            if i==len(keys):
                score=evaluator(dict(current)); rel=(score-baseline)/abs(baseline) if baseline else 0.0; rows.append({**current,"score":score,"relative_change":rel,"stable":abs(rel)<=tolerance}); return
            k=keys[i]
            for v in axes[k]: current[k]=v; rec(i+1,current)
        rec(0,{}); return rows

@dataclass(frozen=True)
class MonteCarloSummary:
    mean:float; median:float; p05:float; p95:float; worst:float; best:float

class MonteCarloLab:
    def run(self,returns:Sequence[float],trials:int=1000,seed:int=42,execution_noise:float=0.0,slippage_noise:float=0.0,random_fills:bool=False)->MonteCarloSummary:
        if not returns or trials<=0: raise ValueError("returns must be non-empty and trials positive")
        rng=random.Random(seed); outcomes=[]
        for _ in range(trials):
            sample=list(returns); rng.shuffle(sample); eq=1.0
            for r in sample:
                fill=rng.uniform(.5,1.0) if random_fills else 1.0; noise=rng.gauss(0,execution_noise)+rng.gauss(0,slippage_noise); eq*=max(0.0,1+r*fill+noise)
            outcomes.append(eq-1)
        s=sorted(outcomes); q=lambda p:s[min(len(s)-1,max(0,int(p*(len(s)-1))))]
        return MonteCarloSummary(statistics.mean(s),statistics.median(s),q(.05),q(.95),s[0],s[-1])

class SensitivityLab:
    def grid(self,evaluator:Callable[[float,float,float,float],float],capitals,latencies,fees,liquidity):
        return [{"capital":c,"latency":l,"fee":f,"liquidity":liq,"score":evaluator(c,l,f,liq)} for c in capitals for l in latencies for f in fees for liq in liquidity]

class CounterfactualEngine:
    KEYS=("capital","fees","spread","slippage","latency","liquidity","leverage","execution_model")
    def run(self,base:dict[str,Any],changes:dict[str,Any],evaluator:Callable[[dict[str,Any]],Any]):
        scenario=dict(base); scenario.update(changes); return {"base":dict(base),"changes":dict(changes),"scenario":scenario,"result":evaluator(scenario)}

class RegimeLab:
    def classify(self,prices:Sequence[float],threshold:float=.02)->list[str]:
        if not prices:return []
        out=["unknown"]
        for a,b in zip(prices,prices[1:]):
            r=(b-a)/a if a else 0.0; out.append("up" if r>threshold else "down" if r<-threshold else "normal")
        return out
    def performance_by_regime(self,returns:Sequence[float],regimes:Sequence[str])->dict[str,float]:
        acc={}
        for r,x in zip(regimes,returns): acc.setdefault(r,[]).append(x)
        return {k:statistics.mean(v) for k,v in acc.items() if v}

class CapacityLab:
    CAPITALS=(1000,2500,5000,10000,50000,100000,1000000)
    def evaluate(self,base_return:float,impact_rate:float=.10):
        rows=[]
        for c in self.CAPITALS:
            ret=base_return/(1+impact_rate*max(0,c/10000-1)); rows.append({"capital":c,"return":ret,"degradation":base_return-ret,"liquidity_consumption":min(1.0,c/1000000)})
        return rows
