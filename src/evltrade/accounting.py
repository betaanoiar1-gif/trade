from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from .core import D, Side, ZERO

@dataclass(frozen=True)
class LedgerEntry:
    ts: str
    debit: str
    credit: str
    amount: Decimal
    reference: str
    memo: str = ""

@dataclass
class DoubleEntryLedger:
    entries: list[LedgerEntry] = field(default_factory=list)
    balances: dict[str, Decimal] = field(default_factory=dict)
    def post(self, ts: str, debit: str, credit: str, amount: Decimal, reference: str, memo: str = ""):
        if amount < ZERO: raise ValueError("ledger amount must be non-negative")
        if amount == ZERO: return
        self.entries.append(LedgerEntry(ts,debit,credit,amount,reference,memo))
        self.balances[debit]=self.balances.get(debit,ZERO)+amount
        self.balances[credit]=self.balances.get(credit,ZERO)-amount
    def balanced(self) -> bool:
        return sum(self.balances.values(), ZERO) == ZERO
    def reconcile(self, external_cash: Decimal) -> bool:
        cash_delta = self.balances.get("cash", ZERO)
        return abs(cash_delta - external_cash) <= Decimal("0.00000001")

@dataclass
class MarginAccount:
    initial_margin_rate: Decimal = D("0")
    maintenance_margin_rate: Decimal = D("0")
    margin_used: Decimal = ZERO
    warning_ratio: Decimal = D("0.8")
    liquidation_ratio: Decimal = D("1")
    def initial_required(self, notional: Decimal) -> Decimal:
        return notional * self.initial_margin_rate
    def maintenance_required(self, notional: Decimal) -> Decimal:
        return notional * self.maintenance_margin_rate
    def utilization(self, equity: Decimal) -> Decimal:
        return ZERO if equity <= ZERO else self.margin_used / equity
    def check(self, equity: Decimal, notional: Decimal) -> str:
        maint=self.maintenance_required(notional)
        if equity <= maint: return "liquidation"
        if equity <= maint / max(self.liquidation_ratio, D("0.000001")): return "warning"
        return "ok"
