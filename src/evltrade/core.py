from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, getcontext
from enum import Enum
from hashlib import sha256
from typing import Any, Iterable, Protocol
import heapq, json, random, uuid
getcontext().prec = 28
ZERO=Decimal("0"); CENT=Decimal("0.01")
def D(v): return Decimal(str(v))
class Side(str,Enum): BUY="buy"; SELL="sell"
class OrderType(str,Enum): MARKET="market"; LIMIT="limit"; STOP="stop"; STOP_LIMIT="stop_limit"
class TimeInForce(str,Enum): IOC="ioc"; FOK="fok"; GTC="gtc"; GTD="gtd"
class EventType(str,Enum): MARKET="market"; ORDER_INTENT="order_intent"; ORDER_ACCEPTED="order_accepted"; ORDER_REJECTED="order_rejected"; ORDER_PARTIALLY_FILLED="order_partially_filled"; ORDER_FILLED="order_filled"
@dataclass(frozen=True)
class Instrument:
 symbol:str; quote:str="USD"; tick_size:Decimal=D("0.01"); quantity_step:Decimal=D("0.000001"); min_quantity:Decimal=D("0.000001"); min_notional:Decimal=D("1")
@dataclass(frozen=True)
class MarketTick:
 ts:datetime; instrument:Instrument; bid:Decimal; ask:Decimal; last:Decimal; bid_size:Decimal; ask_size:Decimal; trade_size:Decimal=ZERO
@dataclass(frozen=True)
class OrderIntent:
 strategy_id:str; instrument:Instrument; side:Side; quantity:Decimal; order_type:OrderType=OrderType.MARKET; limit_price:Decimal|None=None; stop_price:Decimal|None=None; time_in_force:TimeInForce=TimeInForce.GTC; reduce_only:bool=False; post_only:bool=False
@dataclass
class Order:
 id:str; intent:OrderIntent; created_at:datetime; status:str="new"; remaining:Decimal=field(init=False)
 def __post_init__(self): self.remaining=self.intent.quantity
@dataclass(frozen=True)
class Fill:
 order_id:str; ts:datetime; price:Decimal; quantity:Decimal; liquidity:str
@dataclass(frozen=True)
class Event:
 ts:datetime; type:EventType; payload:dict[str,Any]; sequence:int; event_id:str=field(default_factory=lambda:uuid.uuid4().hex)
class EventLog:
 def __init__(self): self._events=[]; self._sequence=0
 def append(self,ts,type_,payload): self._sequence+=1; e=Event(ts,type_,payload,self._sequence); self._events.append(e); return e
 def __iter__(self): return iter(self._events)
 def digest(self): return sha256("\n".join(json.dumps({"ts":e.ts.isoformat(),"type":e.type.value,"payload":e.payload,"sequence":e.sequence},sort_keys=True,default=str) for e in self._events).encode()).hexdigest()
class FeeModel(Protocol):
 def fee(self,price:Decimal,quantity:Decimal,liquidity:str)->Decimal: ...
@dataclass(frozen=True)
class PercentageFee:
 taker:Decimal=D("0.001"); maker:Decimal=D("0.0005")
 def fee(self,price,quantity,liquidity): return (price*quantity*(self.maker if liquidity=="maker" else self.taker)).quantize(CENT)
@dataclass(frozen=True)
class SlippageModel:
 bps:Decimal=D("0")
 def apply(self,price,side):
  move=price*self.bps/D("10000"); return price+move if side==Side.BUY else price-move
class OrderBook:
 def __init__(self): self.bids=[]; self.asks=[]; self._seq=0
 def add(self,order,price):
  self._seq+=1; row=(price,self._seq,order.id,order.remaining)
  heapq.heappush(self.bids,(-price,self._seq,order.id,order.remaining)) if order.intent.side==Side.BUY else heapq.heappush(self.asks,row)
 def best_bid(self): return -self.bids[0][0] if self.bids else None
 def best_ask(self): return self.asks[0][0] if self.asks else None
class MatchingEngine:
 def __init__(self,fees=None,slippage=None): self.fees=fees or PercentageFee(); self.slippage=slippage or SlippageModel()
 def execute(self,order,tick):
  if order.remaining<=ZERO:return []
  if order.intent.order_type==OrderType.LIMIT:
   lp=order.intent.limit_price
   if lp is None or (order.intent.side==Side.BUY and lp<tick.ask) or (order.intent.side==Side.SELL and lp>tick.bid): return []
  px=tick.ask if order.intent.side==Side.BUY else tick.bid; avail=tick.ask_size if order.intent.side==Side.BUY else tick.bid_size; qty=min(order.remaining,avail)
  if qty<=ZERO:return []
  return [Fill(order.id,tick.ts,self.slippage.apply(px,order.intent.side),qty,"taker" if order.intent.order_type==OrderType.MARKET else "maker")]
@dataclass
class Ledger:
 cash:Decimal=D("1000"); reserved_cash:Decimal=ZERO; realized_pnl:Decimal=ZERO; fees:Decimal=ZERO; entries:list=field(default_factory=list)
 def record_trade(self,side,price,qty,fee):
  gross=price*qty; self.cash += -gross if side==Side.BUY else gross; self.cash-=fee; self.fees+=fee; self.entries.append({"type":"trade","side":side.value,"gross":gross,"fee":fee})
@dataclass
class Position:
 quantity:Decimal=ZERO; avg_price:Decimal=ZERO; realized_pnl:Decimal=ZERO
 def apply(self,side,price,qty):
  signed=qty if side==Side.BUY else -qty
  if self.quantity==ZERO or (self.quantity>ZERO and signed>ZERO) or (self.quantity<ZERO and signed<ZERO):
   new=self.quantity+signed
   if new!=ZERO:self.avg_price=((abs(self.quantity)*self.avg_price)+(abs(signed)*price))/abs(new)
   self.quantity=new
  else:
   closing=min(abs(self.quantity),abs(signed)); self.realized_pnl+=closing*(price-self.avg_price if self.quantity>ZERO else self.avg_price-price); self.quantity+=signed
   if self.quantity!=ZERO:self.avg_price=price
@dataclass
class Portfolio:
 ledger:Ledger=field(default_factory=Ledger); positions:dict[str,Position]=field(default_factory=dict); equity:Decimal=D("1000"); peak_equity:Decimal=D("1000")
 def apply_fill(self,fill,intent,fee_model):
  fee=fee_model.fee(fill.price,fill.quantity,fill.liquidity); self.positions.setdefault(intent.instrument.symbol,Position()).apply(intent.side,fill.price,fill.quantity); self.ledger.record_trade(intent.side,fill.price,fill.quantity,fee); self.revalue({intent.instrument.symbol:fill.price})
 def revalue(self,marks):
  market_value=sum(marks.get(s,p.avg_price)*p.quantity for s,p in self.positions.items()); self.equity=self.ledger.cash+market_value; self.peak_equity=max(self.peak_equity,self.equity)
 @property
 def drawdown(self): return ZERO if self.peak_equity==ZERO else (self.peak_equity-self.equity)/self.peak_equity
class RiskEngine:
 def __init__(self,max_order_notional=D("1000"),max_exposure=D("1000")): self.max_order_notional=max_order_notional; self.max_exposure=max_exposure
 def approve(self,intent,mark,portfolio):
  notional=mark*intent.quantity
  if intent.quantity<=ZERO:return False,"quantity_must_be_positive"
  if intent.quantity<intent.instrument.min_quantity:return False,"minimum_quantity"
  if notional<intent.instrument.min_notional:return False,"minimum_notional"
  if notional>self.max_order_notional:return False,"max_order_notional"
  current=sum(abs(p.quantity*mark) for p in portfolio.positions.values())
  if current+notional>self.max_exposure and not intent.reduce_only:return False,"max_exposure"
  return True,"approved"
class Strategy(Protocol):
 strategy_id:str
 def on_start(self)->None: ...
 def on_market_data(self,tick:MarketTick)->OrderIntent|None: ...
 def on_order_update(self,order:Order)->None: ...
 def on_fill(self,fill:Fill)->None: ...
 def on_timer(self,ts:datetime)->None: ...
 def on_stop(self)->None: ...
@dataclass
class Genome:
 logic:dict[str,Any]; parameters:dict[str,Decimal]; risk:dict[str,Decimal]; execution:dict[str,Any]
 @property
 def hash(self): return sha256(json.dumps({"logic":self.logic,"parameters":self.parameters,"risk":self.risk,"execution":self.execution},sort_keys=True,default=str).encode()).hexdigest()
@dataclass
class Individual:
 individual_id:str; genome:Genome; generation:int; parents:list[str]=field(default_factory=list); fitness:dict[str,float]=field(default_factory=dict); alive:bool=True
class EvolutionEngine:
 def __init__(self,seed=42): self.rng=random.Random(seed)
 def mutate(self,genome,rate=D("0.2")):
  params=dict(genome.parameters)
  for k,v in params.items():
   if self.rng.random()<float(rate): params[k]=v*D(str(1+self.rng.uniform(-.1,.1)))
  return Genome(dict(genome.logic),params,dict(genome.risk),dict(genome.execution))
 def crossover(self,a,b):
  keys=sorted(set(a.parameters)|set(b.parameters)); params={k:(a.parameters[k] if self.rng.random()<.5 else b.parameters.get(k,a.parameters[k])) for k in keys}; return Genome({"left":a.logic,"right":b.logic,"operator":"and"},params,dict(a.risk),dict(a.execution))
@dataclass(frozen=True)
class ExperimentSpec:
 experiment_id:str; dataset_id:str; strategy_id:str; genome_hash:str; engine_version:str; seed:int; initial_capital:Decimal=D("1000"); assumptions:dict[str,Any]=field(default_factory=dict)
@dataclass(frozen=True)
class ExperimentResult:
 spec:ExperimentSpec; equity:Decimal; return_pct:Decimal; max_drawdown:Decimal; trades:int; fees:Decimal; event_digest:str
class Simulator:
 def __init__(self,capital=D("1000"),risk=None,matching=None): self.portfolio=Portfolio(ledger=Ledger(cash=capital),equity=capital,peak_equity=capital); self.risk=risk or RiskEngine(); self.matching=matching or MatchingEngine(); self.events=EventLog(); self.order_seq=0
 def run(self,strategy,ticks:list[MarketTick]):
  strategy.on_start(); trades=0
  dataset_id=sha256("\n".join(t.ts.isoformat() for t in ticks).encode()).hexdigest()
  for tick in ticks:
   self.events.append(tick.ts,EventType.MARKET,{"symbol":tick.instrument.symbol,"bid":str(tick.bid),"ask":str(tick.ask),"last":str(tick.last)})
   intent=strategy.on_market_data(tick)
   if intent is None: continue
   approved,reason=self.risk.approve(intent,tick.last,self.portfolio); self.events.append(tick.ts,EventType.ORDER_INTENT,{"strategy":intent.strategy_id,"reason":reason})
   if not approved:self.events.append(tick.ts,EventType.ORDER_REJECTED,{"reason":reason});continue
   self.order_seq+=1; order=Order(f"O{self.order_seq:08d}",intent,tick.ts); self.events.append(tick.ts,EventType.ORDER_ACCEPTED,{"order_id":order.id,"qty":str(intent.quantity)})
   for fill in self.matching.execute(order,tick):
    order.remaining-=fill.quantity; self.portfolio.apply_fill(fill,intent,self.matching.fees); trades+=1; self.events.append(fill.ts,EventType.ORDER_FILLED if order.remaining==ZERO else EventType.ORDER_PARTIALLY_FILLED,{"order_id":fill.order_id,"price":str(fill.price),"qty":str(fill.quantity)}); strategy.on_fill(fill)
  strategy.on_stop(); digest=self.events.digest(); spec=ExperimentSpec(f"EVL-{digest[:8].upper()}",dataset_id[:12],strategy.strategy_id,"", "0.1.0",42); return ExperimentResult(spec,self.portfolio.equity,(self.portfolio.equity-D("1000"))/D("1000"),self.portfolio.drawdown,trades,self.portfolio.ledger.fees,digest)
