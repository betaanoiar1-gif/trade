from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import random
from .core import D, Fill, Instrument, MarketTick, Order, OrderType, Side, TimeInForce, ZERO

class LatencyMode(str, Enum): DETERMINISTIC = "deterministic"; STOCHASTIC = "stochastic"

@dataclass(frozen=True)
class LatencyModel:
    strategy_ms: int = 0; internal_ms: int = 0; network_ms: int = 0; broker_ms: int = 0; exchange_ms: int = 0; execution_ms: int = 0
    mode: LatencyMode = LatencyMode.DETERMINISTIC; jitter_ms: int = 0; seed: int = 42
    def total_ms(self) -> int:
        base = sum((self.strategy_ms,self.internal_ms,self.network_ms,self.broker_ms,self.exchange_ms,self.execution_ms))
        if self.mode == LatencyMode.STOCHASTIC and self.jitter_ms:
            return max(0, base + random.Random(self.seed).randint(-self.jitter_ms, self.jitter_ms))
        return base

@dataclass(frozen=True)
class SlippagePolicy:
    fixed_bps: Decimal = D("0")
    spread_fraction: Decimal = D("0")
    volatility_bps: Decimal = D("0")
    def price(self, tick: MarketTick, side: Side, qty: Decimal) -> Decimal:
        mid = (tick.bid + tick.ask) / D("2")
        spread_component = (tick.ask-tick.bid) * self.spread_fraction / D("1")
        vol_component = mid * self.volatility_bps / D("10000")
        fixed = mid * self.fixed_bps / D("10000")
        move = fixed + spread_component + vol_component
        return mid + move if side == Side.BUY else mid - move

@dataclass(frozen=True)
class ImpactModel:
    coefficient_bps: Decimal = D("0")
    reference_liquidity: Decimal = D("1")
    def impact(self, price: Decimal, qty: Decimal) -> Decimal:
        if self.coefficient_bps <= ZERO or self.reference_liquidity <= ZERO: return ZERO
        participation = qty / self.reference_liquidity
        return price * self.coefficient_bps * participation / D("10000")

@dataclass
class BookLevel:
    price: Decimal
    quantity: Decimal
    queue_ahead: Decimal = ZERO

@dataclass
class L2Book:
    bids: list[BookLevel] = field(default_factory=list)
    asks: list[BookLevel] = field(default_factory=list)
    def best_bid(self): return max(self.bids, key=lambda x:x.price, default=None)
    def best_ask(self): return min(self.asks, key=lambda x:x.price, default=None)
    def depth(self, side: Side): return list(self.bids if side == Side.BUY else self.asks)
    def consume(self, side: Side, qty: Decimal) -> list[tuple[Decimal,Decimal]]:
        levels = sorted(self.depth(side), key=lambda x: x.price, reverse=side==Side.SELL)
        out=[]; remaining=qty
        for lvl in levels:
            if remaining<=ZERO: break
            take=min(remaining,lvl.quantity); lvl.quantity-=take; remaining-=take; out.append((lvl.price,take))
        return out

class ExecutionEngine:
    def __init__(self, slippage=None, impact=None, latency=None):
        self.slippage=slippage or SlippagePolicy(); self.impact=impact or ImpactModel(); self.latency=latency or LatencyModel()
    def execute(self, order: Order, tick: MarketTick, book: L2Book|None=None) -> list[Fill]:
        if order.remaining<=ZERO: return []
        if order.intent.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT):
            p=order.intent.limit_price
            if p is None: return []
            if order.intent.side==Side.BUY and p<tick.ask: return []
            if order.intent.side==Side.SELL and p>tick.bid: return []
        if order.intent.post_only and order.intent.order_type==OrderType.MARKET: return []
        if book:
            levels=book.consume(order.intent.side, order.remaining)
            if not levels: return []
            fills=[]
            for px,qty in levels:
                impact=self.impact.impact(px,qty)
                exec_px=px+(impact if order.intent.side==Side.BUY else -impact)
                fills.append(Fill(order.id,tick.ts,exec_px,qty,"maker" if order.intent.order_type==OrderType.LIMIT else "taker"))
            return fills
        px=tick.ask if order.intent.side==Side.BUY else tick.bid
        avail=tick.ask_size if order.intent.side==Side.BUY else tick.bid_size
        qty=min(order.remaining,avail)
        if qty<=ZERO: return []
        base=self.slippage.price(tick,order.intent.side,qty) if order.intent.order_type==OrderType.MARKET else px
        imp=self.impact.impact(base,qty)
        return [Fill(order.id,tick.ts,base+(imp if order.intent.side==Side.BUY else -imp),qty,"taker" if order.intent.order_type==OrderType.MARKET else "maker")]
