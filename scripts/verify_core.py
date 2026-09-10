from __future__ import annotations
from datetime import datetime, timedelta, timezone
from evltrade.core import D, Instrument, MarketTick, OrderIntent, OrderType, Side, Simulator
from evltrade.data import DataValidator, LeakageGuard
from evltrade.evolution import PopulationManager
from evltrade.risk import PortfolioRiskController
from evltrade.synthetic import SyntheticExchange, SyntheticScenario

class BuyOnce:
    strategy_id='verify'
    used=False
    def on_start(self): pass
    def on_market_data(self,tick):
        if self.used:return None
        self.used=True; return OrderIntent(self.strategy_id,tick.instrument,Side.BUY,D('1'),OrderType.MARKET)
    def on_order_update(self,order): pass
    def on_fill(self,fill): pass
    def on_timer(self,ts): pass
    def on_stop(self): pass

def main():
    inst=Instrument('VERIFY'); start=datetime(2026,1,1,tzinfo=timezone.utc)
    ticks=[MarketTick(start+timedelta(seconds=i),inst,D('99.9'),D('100.1'),D('100'),D('10'),D('10')) for i in range(8)]
    assert not DataValidator().validate_ticks(ticks); LeakageGuard.assert_monotonic([t.ts for t in ticks])
    a=Simulator().run(BuyOnce(),ticks); b=Simulator().run(BuyOnce(),ticks)
    assert a.event_digest==b.event_digest and a.trades==1 and a.fees==D('0.10')
    assert PortfolioRiskController().check(OrderIntent('s',inst,Side.BUY,D('1')),D('100'),D('1000')).approved
    syn_a=SyntheticExchange(SyntheticScenario(seed=42,ticks=8)).ticks(); syn_b=SyntheticExchange(SyntheticScenario(seed=42,ticks=8)).ticks(); assert [(x.last,x.bid,x.ask) for x in syn_a]==[(x.last,x.bid,x.ask) for x in syn_b]
    pm=PopulationManager(42); assert pm.pressure([])
    print('EVOLTRADE core verification: PASS')

if __name__=='__main__': main()
