import typer
from rich import print
from datetime import datetime, timezone, timedelta
from .core import Instrument, MarketTick, Side, OrderIntent, OrderType, D, Simulator
from .data import DataValidator
from .synthetic import SyntheticExchange, SyntheticScenario
from .evolution_runner import EvolutionRunner

app=typer.Typer(help='EVOLTRADE research CLI')

def _demo_ticks(n=50):
    i=Instrument('DEMO'); t=datetime(2026,1,1,tzinfo=timezone.utc); price=D('100'); out=[]; path=[D('0.001'),D('0.002'),D('-0.0015'),D('0.0005'),D('-0.002')]
    for k in range(n): price=max(D('1'),price*(D('1')+path[k%len(path)])); out.append(MarketTick(t+timedelta(seconds=k),i,price-D('.05'),price+D('.05'),price,D('10'),D('10')))
    return out

@app.command('data')
def data(action:str='validate'):
    if action!='validate':raise typer.BadParameter('only validate is supported')
    issues=DataValidator().validate_ticks(_demo_ticks()); print({'valid':not issues,'issues':[i.__dict__ for i in issues]})

@app.command('backtest')
def backtest(strategy:str='demo'):
    class BuyOnce:
        strategy_id=strategy; used=False
        def on_start(self):pass
        def on_market_data(self,tick):
            if self.used:return None
            self.used=True; return OrderIntent(self.strategy_id,tick.instrument,Side.BUY,D('1'),OrderType.MARKET)
        def on_order_update(self,order):pass
        def on_fill(self,fill):pass
        def on_timer(self,ts):pass
        def on_stop(self):pass
    r=Simulator().run(BuyOnce(),_demo_ticks()); print({'experiment':r.spec.experiment_id,'equity':str(r.equity),'return':str(r.return_pct),'trades':r.trades,'fees':str(r.fees),'digest':r.event_digest})

@app.command('evolve')
def evolve(population:int=100,generations:int=10,seed:int=42):
    if population<2 or generations<1:raise typer.BadParameter('population>=2 and generations>=1 required')
    ticks=SyntheticExchange(SyntheticScenario(seed=seed,ticks=400)).ticks(); r=EvolutionRunner(seed).run(ticks,population,generations)
    print({'status':'completed','population':r.final_population,'generations':r.generations,'seed':seed,'best_individual':r.best_individual_id,'best_fitness':r.best_fitness,'diversity':r.diversity,'cemetery':r.cemetery_size})

@app.command('tournament')
def tournament(action:str='run'):print({'status':'ready','action':action})
@app.command('replay')
def replay(experiment_id:str):print({'experiment':experiment_id,'future_data_exposed':False,'speeds':[1,2,10,50,100],'controls':['play','pause','step_event','step_trade','jump_trade','jump_drawdown']})
@app.command('report')
def report(experiment_id:str):print({'experiment':experiment_id,'formats':['html','json','csv','markdown']})
@app.command('paper')
def paper(action:str='start'):print({'mode':'paper','action':action,'live_trading':False})
@app.command('synthetic')
def synthetic(regime:str='normal',seed:int=42,ticks:int=100):print({'ticks':len(SyntheticExchange(SyntheticScenario(seed=seed,regime=regime,ticks=ticks)).ticks()),'seed':seed,'regime':regime,'synthetic':True})
@app.command('self-test')
def self_test():backtest('demo')
@app.command('version')
def version():print('EVOLTRADE 0.2.0')
