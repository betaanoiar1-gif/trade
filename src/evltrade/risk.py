from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from .core import D, ZERO, OrderIntent

@dataclass(frozen=True)
class RiskLimits:
    max_position_notional: Decimal = D("1000")
    max_order_notional: Decimal = D("250")
    max_gross_exposure: Decimal = D("1000")
    max_leverage: Decimal = D("1")
    max_daily_loss: Decimal = D("100")
    max_drawdown: Decimal = D("0.20")
    max_asset_concentration: Decimal = D("1")
    max_strategy_concentration: Decimal = D("1")

@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reason: str
    requested_notional: Decimal = ZERO
    gross_exposure_after: Decimal = ZERO

class PortfolioRiskController:
    def __init__(self, limits: RiskLimits | None = None):
        self.limits = limits or RiskLimits()
        self.kill_switch = False

    def trip(self) -> None:
        self.kill_switch = True

    def reset(self) -> None:
        self.kill_switch = False

    def check(self, intent: OrderIntent, mark: Decimal, equity: Decimal, gross_exposure: Decimal = ZERO, daily_pnl: Decimal = ZERO, drawdown: Decimal = ZERO) -> RiskDecision:
        notional = abs(mark * intent.quantity)
        after = gross_exposure + notional
        if self.kill_switch:
            return RiskDecision(False, "kill_switch", notional, after)
        if intent.quantity <= ZERO:
            return RiskDecision(False, "quantity_must_be_positive", notional, after)
        if notional > self.limits.max_order_notional:
            return RiskDecision(False, "max_order_notional", notional, after)
        if equity <= ZERO:
            return RiskDecision(False, "non_positive_equity", notional, after)
        if after > equity * self.limits.max_leverage and not intent.reduce_only:
            return RiskDecision(False, "max_leverage", notional, after)
        if not intent.reduce_only and after > self.limits.max_gross_exposure:
            return RiskDecision(False, "max_gross_exposure", notional, after)
        if daily_pnl <= -abs(self.limits.max_daily_loss):
            return RiskDecision(False, "max_daily_loss", notional, after)
        if drawdown >= self.limits.max_drawdown and not intent.reduce_only:
            return RiskDecision(False, "max_drawdown", notional, after)
        return RiskDecision(True, "approved", notional, after)
