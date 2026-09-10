from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from .core import D, Genome, Individual, MarketTick, OrderIntent, OrderType, Side, Simulator
from .evolution import PopulationManager

class ThresholdMomentumStrategy:
    def __init__(self, strategy_id:str, genome:Genome): self.strategy_id=strategy_id; self.genome=genome; self.position=D('0'); self.prev=None
    def on_start(self): self.position=D('0'); self.prev=None
    def on_market_data(self,tick:MarketTick):
        if self.prev is None:self.prev=tick.last; return None
        ret=(tick.last-self.prev)/self.prev if self.prev else D('0'); self.prev=tick.last
        threshold=self.genome.parameters.get('entry_threshold',D('0.001')); exit_threshold=self.genome.parameters.get('exit_threshold',D('-0.001')); qty=self.genome.parameters.get('quantity',D('1'))
        if self.position==0 and ret>=threshold:return OrderIntent(self.strategy_id,tick.instrument,Side.BUY,qty,OrderType.MARKET)
        if self.position>0 and ret<=exit_threshold:return OrderIntent(self.strategy_id,tick.instrument,Side.SELL,self.position,OrderType.MARKET,reduce_only=True)
        return None
    def on_order_update(self,order): pass
    def on_fill(self,fill): self.position += fill.quantity if self.position==0 else -fill.quantity
    def on_timer(self,ts): pass
    def on_stop(self): pass

@dataclass(frozen=True)
class EvolutionRunResult:
    generations:int; final_population:int; best_individual_id:str; best_fitness:dict[str,float]; diversity:float; cemetery_size:int

class EvolutionRunner:
    def __init__(self,seed:int=42): self.manager=PopulationManager(seed); self.seed=seed
    def evaluate(self,individual:Individual,ticks:list[MarketTick])->dict[str,float]:
        result=Simulator().run(ThresholdMomentumStrategy(individual.individual_id,individual.genome),ticks); ret=float(result.return_pct); dd=float(result.max_drawdown); fees=float(result.fees)
        return {'return':ret,'stability':max(0.0,1.0-dd),'cost_efficiency':max(0.0,1.0-fees/1000.0),'complexity':-float(len(individual.genome.parameters)),'trades':float(result.trades),'experiment_digest':result.event_digest}
    def run(self,ticks:list[MarketTick],population_size:int=100,generations:int=10,genome_factory:Callable[[int],Genome]|None=None)->EvolutionRunResult:
        if population_size<2 or generations<1:raise ValueError('population_size>=2 and generations>=1 required')
        factory=genome_factory or (lambda i:Genome({'entry':'momentum','exit':'momentum'},{'entry_threshold':D(str(0.0005+(i%11)*0.0002)),'exit_threshold':D('-0.001'),'quantity':D('1')},{'max_risk':D('.02')},{'type':'market'}))
        pop=[Individual(f'I0000-{i:06d}',factory(i),0,[]) for i in range(population_size)]
        for _ in range(generations):
            for ind in pop:
                ind.fitness=self.evaluate(ind,ticks); manager_descriptor=(ind.fitness['return'],ind.fitness['stability'],ind.fitness['complexity'],ind.fitness['trades']); self.manager.novelty(ind,manager_descriptor)
            survivors=self.manager.select(pop,max(2,population_size//5)); self.manager.finalize_generation(pop,survivors); pop=self.manager.breed(survivors,population_size)
        for ind in pop:ind.fitness=self.evaluate(ind,ticks)
        best=max(pop,key=lambda x:(x.fitness.get('return',-1e9),x.fitness.get('stability',0)))
        return EvolutionRunResult(generations,len(pop),best.individual_id,best.fitness,self.manager.diversity(pop),len(self.manager.cemetery.records))
