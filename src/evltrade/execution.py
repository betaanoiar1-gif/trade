from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import random
from .core import D, Fill, MarketTick, Order, OrderType, Side, TimeInForce, ZERO

class LatencyMode(str, Enum):
    DETERMINISTIC="deterministic"; STOCHASTIC="stochastic"

@dataclass(frozen=True)
class LatencyModel:
    strategy_ms:int=0; internal_ms:int=0; network_ms:int=0; broker_ms:int=0; exchange_ms:int=0; execution_ms:int=0
    mode:LatencyMode=LatencyMode.DETERMINISTIC; jitter_ms:int=0; seed:int=42
    def total_ms(self)->int:
        base=sum((self.strategy_ms,self.internal_ms,self.network_ms,self.broker_ms,self.exchange_ms,self.execution_ms))
        if self.mode==LatencyMode.STOCHASTIC and self.jitter_ms:return max(0,base+random.Random(self.seed).randint(-self.jitter_ms,self.jitter_ms))
        return base

@dataclass(frozen=True)
class SlippagePolicy:
    fixed_bps:Decimal=D("0"); spread_fraction:Decimal=D("0"); volatility_bps:Decimal=D("0")
    def price(self,tick:MarketTick,side:Side,qty:Decimal)->Decimal:
        mid=(tick.bid+tick.ask)/D("2"); spread=tick.ask-tick.bid; move=mid*self.fixed_bps/D("10000")+spread*self.spread_fraction+mid*self.volatility_bps/D("10000")
        return mid+move if side==Side.BUY else mid-move

@dataclass(frozen=True)
class ImpactModel:
    coefficient_bps:Decimal=D("0"); reference_liquidity:Decimal=D("1")
    def impact(self,price,qty):return ZERO if self.coefficient_bps<=ZERO or self.reference_liquidity<=ZERO else price*self.coefficient_bps*(qty/self.reference_liquidity)/D("10000")

@dataclass
class BookLevel:
    price:Decimal; quantity:Decimal; queue_ahead:Decimal=ZERO

@dataclass
class L2Book:
    bids:list[BookLevel]=field(default_factory=list); asks:list[BookLevel]=field(default_factory=list)
    def best_bid(self):return max(self.bids,key=lambda x:x.price,default=None)
    def best_ask(self):return min(self.asks,key=lambda x:x.price,default=None)
    def depth(self,side:Side):return list(self.bids if side==Side.BUY else self.asks)
    def available(self,side:Side,limit_price:Decimal|None=None)->Decimal:
        total=ZERO; levels=sorted(self.asks,key=lambda x:x.price) if side==Side.BUY else sorted(self.bids,key=lambda x:x.price,reverse=True)
        for lvl in levels:
            if limit_price is not None and ((side==Side.BUY and lvl.price>limit_price) or (side==Side.SELL and lvl.price<limit_price)):break
            total+=max(ZERO,lvl.quantity-lvl.queue_ahead)
        return total
    def consume(self,side:Side,qty:Decimal,limit_price:Decimal|None=None)->list[tuple[Decimal,Decimal]]:
        levels=sorted(self.asks,key=lambda x:x.price) if side==Side.BUY else sorted(self.bids,key=lambda x:x.price,reverse=True); remaining=qty; out=[]
        for lvl in levels:
            if remaining<=ZERO:break
            if limit_price is not None and ((side==Side.BUY and lvl.price>limit_price) or (side==Side.SELL and lvl.price<limit_price)):break
            take=min(remaining,max(ZERO,lvl.quantity-lvl.queue_ahead))
            if take>ZERO:lvl.quantity-=take; remaining-=take; out.append((lvl.price,take))
        return out

class ExecutionEngine:
    def __init__(self,slippage=None,impact=None,latency=None):self.slippage=slippage or SlippagePolicy(); self.impact=impact or ImpactModel(); self.latency=latency or LatencyModel()
    def execute(self,order:Order,tick:MarketTick,book:L2Book|None=None)->list[Fill]:
        if order.remaining<=ZERO:return []
        intent=order.intent
        if intent.expires_at and tick.ts>intent.expires_at:return []
        limit=intent.limit_price if intent.order_type in (OrderType.LIMIT,OrderType.STOP_LIMIT) else None
        if intent.post_only:
            crosses=intent.order_type==OrderType.MARKET or (limit is not None and ((intent.side==Side.BUY and limit>=tick.ask) or (intent.side==Side.SELL and limit<=tick.bid)))
            if crosses:return []
        if book:
            if intent.time_in_force==TimeInForce.FOK and book.available(intent.side,limit)<order.remaining:return []
            levels=book.consume(intent.side,order.remaining,limit); return [Fill(order.id,tick.ts,px+(self.impact.impact(px,q) if intent.side==Side.BUY else -self.impact.impact(px,q)),q,"taker" if intent.order_type==OrderType.MARKET else "maker") for px,q in levels]
        if limit is not None and ((intent.side==Side.BUY and limit<tick.ask) or (intent.side==Side.SELL and limit>tick.bid)):return []
        px=tick.ask if intent.side==Side.BUY else tick.bid; avail=tick.ask_size if intent.side==Side.BUY else tick.bid_size; qty=min(order.remaining,avail)
        if intent.time_in_force==TimeInForce.FOK and qty<order.remaining:return []
        if qty<=ZERO:return []
        base=self.slippage.price(tick,intent.side,qty) if intent.order_type==OrderType.MARKET else px; impact=self.impact.impact(base,qty)
        return [Fill(order.id,tick.ts,base+(impact if intent.side==Side.BUY else -impact),qty,"taker" if intent.order_type==OrderType.MARKET else "maker")]
