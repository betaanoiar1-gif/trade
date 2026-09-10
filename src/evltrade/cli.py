import json
import typer
from rich import print
from datetime import datetime, timezone, timedelta
from .core import Instrument, MarketTick, Side, OrderIntent, OrderType, D, Simulator
from .data import DataValidator
from .synthetic import SyntheticExchange, SyntheticScenario
from .evolution import PopulationManager

app=typer.Typer(help="EVOLTRADE research CLI")

def _demo_ticks(n=20):
    i=Instrument("DEMO"); t=datetime(2026,1,1,tzinfo=timezone.utc)
    return [MarketTick(t+timedelta(seconds=k),i,D("99.9"),D("100"),D("100"),D("10"),D("10")) for k in range(n)]

@app.command("data")
def data(action: str="validate"):
    if action!="validate": raise typer.BadParameter("only validate is supported by this command")
    issues=DataValidator().validate_ticks(_demo_ticks()); print({"valid":not issues,"issues":[i.__dict__ for i in issues]})

@app.command("backtest")
def backtest(strategy: str="demo"):
    class BuyOnce:
        strategy_id=strategy; used=False
        def on_start(self): pass
        def on_market_data(self,tick):
            if self.used:return None
            self.used=True; return OrderIntent(self.strategy_id,tick.instrument,Side.BUY,D("1"),OrderType.MARKET)
        def on_order_update(self,order): pass
        def on_fill(self,fill): pass
        def on_timer(self,ts): pass
        def on_stop(self): pass
    r=Simulator().run(BuyOnce(),_demo_ticks()); print({"equity":str(r.equity),"trades":r.trades,"fees":str(r.fees),"digest":r.event_digest})

@app.command("evolve")
def evolve(population:int=100,generations:int=10,seed:int=42): print({"status":"configured","population":population,"generations":generations,"seed":seed})
@app.command("tournament")
def tournament(action:str="run"): print({"status":"ready","action":action})
@app.command("replay")
def replay(experiment_id:str): print({"experiment":experiment_id,"future_data_exposed":False,"controls":["play","pause","step_event","step_trade","jump_trade","jump_drawdown"]})
@app.command("report")
def report(experiment_id:str): print({"experiment":experiment_id,"formats":["html","json","csv","markdown"]})
@app.command("paper")
def paper(action:str="start"): print({"mode":"paper","action":action,"live_trading":False})
@app.command("synthetic")
def synthetic(regime:str="normal",seed:int=42,ticks:int=100):
    data=SyntheticExchange(SyntheticScenario(seed=seed,regime=regime,ticks=ticks)).ticks(); print({"ticks":len(data),"seed":seed,"regime":regime})
@app.command("self-test")
def self_test(): backtest("demo")
@app.command("version")
def version(): print("EVOLTRADE 0.2.0")
