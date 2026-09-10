from dataclasses import dataclass,field
from .core import Genome,Individual,EvolutionEngine
@dataclass
class GenerationSnapshot:
 generation:int; population:list[Individual]=field(default_factory=list); survivors:list[str]=field(default_factory=list); extinct:list[str]=field(default_factory=list); novelty_archive:list[str]=field(default_factory=list); diversity:float=0.0
class PopulationManager:
 def __init__(self,seed=42): self.operator=EvolutionEngine(seed); self.generation=0; self.history=[]
 def breed(self,parents,size):
  out=[]
  if not parents:return out
  for i in range(size):
   a=parents[i%len(parents)]; b=parents[(i+1)%len(parents)]; g=self.operator.mutate(self.operator.crossover(a.genome,b.genome)); out.append(Individual(f'I{self.generation+1:04d}-{i:06d}',g,self.generation+1,[a.individual_id,b.individual_id]))
  self.generation+=1; return out
