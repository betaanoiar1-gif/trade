from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import random
from .core import D, Instrument, MarketTick, ZERO
from .execution import L2Book, BookLevel

@dataclass(frozen=True)
class SyntheticScenario:
    seed:int=42; start_price:Decimal=D("100"); spread_bps:Decimal=D("5"); volatility:Decimal=D("0.001"); liquidity:Decimal=D("100"); ticks:int=1000; regime:str="normal"

class SyntheticExchange:
    def __init__(self, scenario:SyntheticScenario=None): self.scenario=scenario or SyntheticScenario(); self.rng=random.Random(self.scenario.seed)
    def ticks(self,instrument=None):
        instrument=instrument or Instrument("SYNTH/USD",tick_size=D("0.01")); price=self.scenario.start_price; ts=datetime(2026,1,1,tzinfo=timezone.utc); out=[]
        mult={"crash":-0.003,"volatile":0.0,"low_liquidity":0.0}.get(self.scenario.regime,0.0001)
        for _ in range(self.scenario.ticks):
            ret=self.rng.gauss(mult,float(self.scenario.volatility)); price=max(D("0.01"),price*D(str(1+ret))); spread=price*self.scenario.spread_bps/D("10000"); liq=self.scenario.liquidity*(D("0.25") if self.scenario.regime=="low_liquidity" else D("1")); out.append(MarketTick(ts,instrument,price-spread/2,price+spread/2,price,liq,liq,D(str(abs(ret)*float(liq))))); ts+=timedelta(seconds=1)
        return out
    def book(self,price:Decimal)->L2Book:
        b=[]; a=[]
        for i in range(1,6):
            size=self.scenario.liquidity/D(str(i)); b.append(BookLevel(price-D(str(i)),size)); a.append(BookLevel(price+D(str(i)),size))
        return L2Book(b,a)
