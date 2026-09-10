from dataclasses import dataclass
from enum import Enum
from .core import MarketTick
class ReplaySpeed(str,Enum): X1='1x'; X2='2x'; X10='10x'; X50='50x'; X100='100x'
@dataclass
class ReplayCursor: index:int=0; paused:bool=True
class HistoricalReplay:
 def __init__(self,ticks:list[MarketTick]): self.ticks=ticks; self.cursor=ReplayCursor()
 def current(self): return self.ticks[self.cursor.index] if 0<=self.cursor.index<len(self.ticks) else None
 def step_event(self):
  tick=self.current()
  if tick is not None:self.cursor.index+=1
  return tick
 def jump_to_trade(self,ordinal): self.cursor.index=max(0,min(ordinal,len(self.ticks))); return self.current()
 def reset(self): self.cursor=ReplayCursor()
