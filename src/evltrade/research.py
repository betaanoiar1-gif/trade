from dataclasses import dataclass
from decimal import Decimal
from statistics import mean,pstdev
@dataclass(frozen=True)
class Fitness:
 return_pct:float; sharpe:float; sortino:float; max_drawdown:float; stability:float; turnover:float; fees:float; complexity:float; novelty:float
def max_drawdown(equity):
 peak=None; worst=Decimal('0')
 for value in equity:
  peak=value if peak is None else max(peak,value)
  if peak: worst=max(worst,(peak-value)/peak)
 return worst
def sharpe(returns,annualization=252.0):
 if len(returns)<2:return 0.0
 sigma=pstdev(returns); return 0.0 if sigma==0 else mean(returns)/sigma*annualization**0.5
def sortino(returns,target=0.0,annualization=252.0):
 down=[min(0.0,r-target) for r in returns]; sigma=(sum(x*x for x in down)/len(down))**0.5 if down else 0.0
 return 0.0 if sigma==0 else (mean(returns)-target)/sigma*annualization**0.5
def complexity_score(node_count,depth,feature_count,parameter_count): return float(node_count+2*depth+feature_count+parameter_count)
