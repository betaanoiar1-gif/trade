from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json, math
from .core import Genome, Individual, EvolutionEngine

@dataclass(frozen=True)
class Fitness:
    values: dict[str,float]
    def dominates(self, other:'Fitness')->bool:
        keys=set(self.values)|set(other.values); a=all(self.values.get(k,-math.inf)>=other.values.get(k,-math.inf) for k in keys); b=any(self.values.get(k,-math.inf)>other.values.get(k,-math.inf) for k in keys); return a and b

@dataclass
class DeathRecord:
    individual_id:str; generation:int; reason:str; metrics:dict[str,float]=field(default_factory=dict); evidence:dict[str,object]=field(default_factory=dict)

@dataclass
class GenerationSnapshot:
    generation:int; population:list[Individual]=field(default_factory=list); survivors:list[str]=field(default_factory=list); extinct:list[str]=field(default_factory=list); novelty_archive:list[str]=field(default_factory=list); diversity:float=0.0; average_fitness:float=0.0; complexity:float=0.0; pareto_front:list[str]=field(default_factory=list)

class NoveltyArchive:
    def __init__(self, max_size=500, k=10): self.max_size=max_size; self.k=k; self.items:dict[str,tuple[float,...]]={}
    def score(self, descriptor:tuple[float,...]):
        if not self.items:return 0.0
        ds=[self._dist(descriptor,d) for d in self.items.values()]; ds.sort(); return sum(ds[:min(self.k,len(ds))])/min(self.k,len(ds))
    @staticmethod
    def _dist(a,b): return math.sqrt(sum((float(x)-float(y))**2 for x,y in zip(a,b)))
    def add(self,key,descriptor): self.items[key]=descriptor; self.items=dict(sorted(self.items.items(), key=lambda kv:self.score(kv[1]), reverse=True)[:self.max_size])

class LineageStore:
    def __init__(self): self.parents={}; self.children={}; self.mutations={}
    def record(self,child:str,parents:list[str],operation:str):
        self.parents[child]=parents; self.mutations[child]=operation
        for p in parents:self.children.setdefault(p,[]).append(child)
    def tree(self,root):
        out=[]
        def walk(x,depth=0):
            out.append({"id":x,"depth":depth,"children":self.children.get(x,[])})
            for c in self.children.get(x,[]):walk(c,depth+1)
        walk(root); return out

class AlphaCemetery:
    def __init__(self): self.records:dict[str,DeathRecord]={}
    def bury(self,record:DeathRecord): self.records[record.individual_id]=record
    def get(self,individual_id): return self.records.get(individual_id)

class ParetoSelector:
    @staticmethod
    def front(individuals:list[Individual])->list[Individual]:
        out=[]
        for x in individuals:
            fx=Fitness(x.fitness)
            if not any(Fitness(y.fitness).dominates(fx) for y in individuals if y is not x): out.append(x)
        return out

class PopulationManager:
    def __init__(self,seed=42): self.operator=EvolutionEngine(seed); self.generation=0; self.history=[]; self.archive=NoveltyArchive(); self.lineage=LineageStore(); self.cemetery=AlphaCemetery()
    def diversity(self,population):
        hashes={i.genome.hash for i in population}; return len(hashes)/max(1,len(population))
    def select(self,population,size):
        front=ParetoSelector.front(population); remaining=[x for x in population if x not in front]; remaining.sort(key=lambda x:sum(x.fitness.values()),reverse=True)
        return (front+[x for x in remaining if x not in front])[:size]
    def breed(self,parents,size):
        out=[]
        if not parents:return out
        for i in range(size):
            a=parents[i%len(parents)]; b=parents[(i+1)%len(parents)]
            g=self.operator.mutate(self.operator.crossover(a.genome,b.genome)); child=Individual(f'I{self.generation+1:04d}-{i:06d}',g,self.generation+1,[a.individual_id,b.individual_id]); out.append(child); self.lineage.record(child.individual_id,child.parents,"crossover+mutation")
        self.generation+=1; return out
    def finalize_generation(self,population,survivors,death_reason="selection"):
        extinct=[x for x in population if x.individual_id not in {s.individual_id for s in survivors}]
        for x in extinct:self.cemetery.bury(DeathRecord(x.individual_id,x.generation,death_reason,x.fitness,{"genome_hash":x.genome.hash}))
        front=ParetoSelector.front(population)
        avg=sum(sum(i.fitness.values()) for i in population)/max(1,len(population))
        snap=GenerationSnapshot(self.generation,population,[x.individual_id for x in survivors],[x.individual_id for x in extinct],list(self.archive.items),self.diversity(population),avg, sum(i.genome.parameters.__len__() for i in population)/max(1,len(population)),[x.individual_id for x in front]); self.history.append(snap); return snap
    def checkpoint(self,path: str):
        Path(path).write_text(json.dumps({"generation":self.generation,"history":[asdict(x) for x in self.history],"cemetery":{k:asdict(v) for k,v in self.cemetery.records.items()}},default=str),encoding="utf-8")
    def resume(self,path: str):
        payload=json.loads(Path(path).read_text(encoding="utf-8")); self.generation=int(payload.get("generation",0))
