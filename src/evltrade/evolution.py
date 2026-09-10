from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json, math
from .core import Genome, Individual, EvolutionEngine

@dataclass(frozen=True)
class Fitness:
    values: dict[str,float]
    directions: dict[str,int] = field(default_factory=dict)
    def dominates(self, other:'Fitness')->bool:
        keys=set(self.values)|set(other.values); better=False
        for k in keys:
            sign=self.directions.get(k,other.directions.get(k,1)); a=self.values.get(k,-math.inf)*sign; b=other.values.get(k,-math.inf)*sign
            if a<b:return False
            better |= a>b
        return better

@dataclass
class DeathRecord:
    individual_id:str; generation:int; reason:str; metrics:dict[str,float]=field(default_factory=dict); evidence:dict[str,object]=field(default_factory=dict)

@dataclass
class GenerationSnapshot:
    generation:int; population:list[Individual]=field(default_factory=list); survivors:list[str]=field(default_factory=list); extinct:list[str]=field(default_factory=list); novelty_archive:list[str]=field(default_factory=list); diversity:float=0.0; average_fitness:float=0.0; complexity:float=0.0; pareto_front:list[str]=field(default_factory=list); convergence_alert:bool=False; niches:dict[str,list[str]]=field(default_factory=dict)

class NoveltyArchive:
    def __init__(self,max_size=500,k=10): self.max_size=max_size; self.k=k; self.items={}
    @staticmethod
    def distance(a,b): return math.sqrt(sum((float(x)-float(y))**2 for x,y in zip(a,b)))
    def score(self,descriptor):
        if not self.items:return 0.0
        ds=sorted(self.distance(descriptor,d) for d in self.items.values()); n=min(self.k,len(ds)); return sum(ds[:n])/n
    def add(self,key,descriptor):
        self.items[key]=tuple(descriptor)
        self.items=dict(sorted(self.items.items(),key=lambda kv:self.score(kv[1]),reverse=True)[:self.max_size])

class LineageStore:
    def __init__(self): self.parents={}; self.children={}; self.operations={}
    def record(self,child,parents,operation):
        self.parents[child]=list(parents); self.operations[child]=operation
        for p in parents:self.children.setdefault(p,[]).append(child)
    def tree(self,root):
        out=[]
        def walk(x,depth=0):
            out.append({'id':x,'depth':depth,'parents':self.parents.get(x,[]),'children':self.children.get(x,[]),'operation':self.operations.get(x)})
            for c in self.children.get(x,[]):walk(c,depth+1)
        walk(root); return out

class AlphaCemetery:
    def __init__(self): self.records={}
    def bury(self,record): self.records[record.individual_id]=record
    def get(self,individual_id): return self.records.get(individual_id)

class ParetoSelector:
    @staticmethod
    def front(individuals):
        return [x for x in individuals if not any(Fitness(y.fitness).dominates(Fitness(x.fitness)) for y in individuals if y is not x)]

class Niching:
    def __init__(self,threshold=1.5): self.threshold=threshold
    def assign(self,population):
        niches={}; centers=[]
        for ind in population:
            d=tuple(ind.fitness.get(k,0.0) for k in sorted(ind.fitness))
            for idx,c in enumerate(centers):
                if self.distance(d,c)<=self.threshold:niches.setdefault(str(idx),[]).append(ind.individual_id); break
            else: centers.append(d); niches[str(len(centers)-1)]=[ind.individual_id]
        return niches
    @staticmethod
    def distance(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

class PopulationManager:
    def __init__(self,seed=42):
        self.operator=EvolutionEngine(seed); self.generation=0; self.history=[]; self.archive=NoveltyArchive(); self.lineage=LineageStore(); self.cemetery=AlphaCemetery(); self.niching=Niching()
    def diversity(self,population): return len({i.genome.hash for i in population})/max(1,len(population))
    def novelty(self,individual,descriptor):
        score=self.archive.score(descriptor); self.archive.add(individual.individual_id,descriptor); return score
    def pressure(self,population,threshold=.05): return self.diversity(population)<threshold
    def select(self,population,size):
        front=ParetoSelector.front(population); rest=[x for x in population if x not in front]; rest.sort(key=lambda x:sum(x.fitness.values()),reverse=True); return (front+rest)[:size]
    def breed(self,parents,size):
        out=[]
        if not parents:return out
        for i in range(size):
            a=parents[i%len(parents)]; b=parents[(i+1)%len(parents)]; g=self.operator.mutate(self.operator.crossover(a.genome,b.genome)); child=Individual(f'I{self.generation+1:04d}-{i:06d}',g,self.generation+1,[a.individual_id,b.individual_id]); out.append(child); self.lineage.record(child.individual_id,child.parents,'crossover+mutation')
        self.generation+=1; return out
    def finalize_generation(self,population,survivors,death_reason='selection'):
        survivor_ids={s.individual_id for s in survivors}; extinct=[x for x in population if x.individual_id not in survivor_ids]
        for x in extinct:self.cemetery.bury(DeathRecord(x.individual_id,x.generation,death_reason,x.fitness,{'genome_hash':x.genome.hash}))
        front=ParetoSelector.front(population); div=self.diversity(population); avg=sum(sum(i.fitness.values()) for i in population)/max(1,len(population)); complexity=sum(len(i.genome.parameters) for i in population)/max(1,len(population))
        snap=GenerationSnapshot(self.generation,population,[x.individual_id for x in survivors],[x.individual_id for x in extinct],list(self.archive.items),div,avg,complexity,[x.individual_id for x in front],div<.05,self.niching.assign(population)); self.history.append(snap); return snap
    def checkpoint(self,path):
        Path(path).write_text(json.dumps({'generation':self.generation,'history':[asdict(x) for x in self.history],'cemetery':{k:asdict(v) for k,v in self.cemetery.records.items()},'archive':self.archive.items,'lineage':{'parents':self.lineage.parents,'children':self.lineage.children,'operations':self.lineage.operations}},default=str,sort_keys=True),encoding='utf-8')
    def resume(self,path):
        p=json.loads(Path(path).read_text(encoding='utf-8')); self.generation=int(p.get('generation',0)); lin=p.get('lineage',{}); self.lineage.parents=lin.get('parents',{}); self.lineage.children=lin.get('children',{}); self.lineage.operations=lin.get('operations',{}); self.archive.items={k:tuple(v) for k,v in p.get('archive',{}).items()}
