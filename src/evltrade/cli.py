import typer
from rich import print
from datetime import datetime, timezone, timedelta
from .core import Instrument, MarketTick, Side, OrderIntent, OrderType, D, Simulator
app=typer.Typer(help='EVOLTRADE research CLI')
@app.command('self-test')
def self_test():
 class BuyOnce:
  strategy_id='demo'; used=False
  def on_start(self): pass
  def on_market_data(self,tick):
   if self.used:return None
   self.used=True; return OrderIntent(self.strategy_id,tick.instrument,Side.BUY,D('1'),OrderType.MARKET)
  def on_order_update(self,order): pass
  def on_fill(self,fill): pass
  def on_timer(self,ts): pass
  def on_stop(self): pass
 i=Instrument('DEMO'); t=datetime(2026,1,1,tzinfo=timezone.utc); ticks=[MarketTick(t+timedelta(seconds=n),i,D('99.9'),D('100'),D('100'),D('10'),D('10')) for n in range(3)]
 r=Simulator().run(BuyOnce(),ticks); print({'equity':str(r.equity),'trades':r.trades,'fees':str(r.fees),'digest':r.event_digest})
@app.command('version')
def version(): print('EVOLTRADE 0.1.0')
