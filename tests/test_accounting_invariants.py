from decimal import Decimal
from evltrade.core import D, Instrument, Ledger, Order, OrderIntent, OrderType, Side
from evltrade.execution import ExecutionEngine, SlippagePolicy, ImpactModel
from datetime import datetime, timezone
from evltrade.core import MarketTick

def test_ledger_is_balanced_after_double_entry():
    ledger=__import__('evltrade.accounting',fromlist=['DoubleEntryLedger']).DoubleEntryLedger()
    ledger.post('2026-01-01T00:00:00Z','asset','cash',D('100'),'T1','buy')
    ledger.post('2026-01-01T00:00:00Z','cash','asset',D('100'),'T2','reverse')
    assert ledger.balanced()

def test_fill_quantity_never_exceeds_remaining():
    inst=Instrument('X'); intent=OrderIntent('S',inst,Side.BUY,D('4'),OrderType.MARKET); order=Order('O1',intent,datetime.now(timezone.utc))
    tick=MarketTick(datetime.now(timezone.utc),inst,D('99'),D('101'),D('100'),D('1'),D('2'))
    fills=ExecutionEngine(slippage=SlippagePolicy(),impact=ImpactModel()).execute(order,tick)
    assert sum(f.quantity for f in fills) <= order.remaining

def test_decimal_money_has_exact_decimal_type():
    l=Ledger(); assert isinstance(l.cash,Decimal)
