from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from .core import D, ZERO

@dataclass(frozen=True)
class LedgerEntry:
    ts:str; debit:str; credit:str; amount:Decimal; reference:str; memo:str=''

@dataclass
class DoubleEntryLedger:
    entries:list[LedgerEntry]=field(default_factory=list); balances:dict[str,Decimal]=field(default_factory=dict)
    def post(self,ts,debit,credit,amount,reference,memo=''):
        amount=D(amount)
        if amount<ZERO: raise ValueError('ledger amount must be non-negative')
        if amount==ZERO:return
        self.entries.append(LedgerEntry(ts,debit,credit,amount,reference,memo)); self.balances[debit]=self.balances.get(debit,ZERO)+amount; self.balances[credit]=self.balances.get(credit,ZERO)-amount
    def balanced(self): return sum(self.balances.values(),ZERO)==ZERO
    def account_balance(self,account): return self.balances.get(account,ZERO)
    def reconcile(self,account_balance,expected,tolerance=D('0.00000001')): return abs(D(account_balance)-D(expected))<=tolerance

@dataclass
class MarginAccount:
    initial_margin_rate:Decimal=D('0'); maintenance_margin_rate:Decimal=D('0'); margin_used:Decimal=ZERO; warning_ratio:Decimal=D('0.8')
    def initial_required(self,notional): return max(ZERO,D(notional))*self.initial_margin_rate
    def maintenance_required(self,notional): return max(ZERO,D(notional))*self.maintenance_margin_rate
    def utilization(self,equity): return ZERO if D(equity)<=ZERO else self.margin_used/D(equity)
    def state(self,equity,notional):
        equity=D(equity); maintenance=self.maintenance_required(notional); util=self.utilization(equity)
        if equity<=maintenance:return 'liquidation'
        if util>=self.warning_ratio:return 'warning'
        return 'ok'
