from datetime import datetime,timezone,timedelta
from decimal import Decimal
from evltrade.core import Instrument,MarketTick,Side,OrderIntent,OrderType,Simulator,D,PercentageFee
class OneBuy:
 strategy_id='s1'; used=False
 def on_start(self): pass
 def on_market_data(self,tick):
  if self.used:return None
  self.used=True; return OrderIntent(self.strategy_id,tick.instrument,Side.BUY,D('1'),OrderType.MARKET)
 def on_order_update(self,order): pass
 def on_fill(self,fill): pass
 def on_timer(self,ts): pass
 def on_stop(self): pass
def ticks():
 t=datetime(2026,1,1,tzinfo=timezone.utc); i=Instrument('BTC',min_notional=D('1'))
 return [MarketTick(t+timedelta(seconds=n),i,D('99'),D('100'),D('100'),D('5'),D('5')) for n in range(3)]
def test_capital_and_fee_reconciliation():
 r=Simulator().run(OneBuy(),ticks()); assert r.trades==1; assert r.fees==D('0.10'); assert r.equity<=D('1000')
def test_deterministic_event_digest():
 a=Simulator().run(OneBuy(),ticks()); b=Simulator().run(OneBuy(),ticks()); assert a.event_digest==b.event_digest
def test_fee_model(): assert PercentageFee().fee(D('100'),D('1'),'taker')==Decimal('0.10')
