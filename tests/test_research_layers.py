from datetime import datetime, timezone, timedelta
from decimal import Decimal
from evltrade.core import D, Instrument, MarketTick
from evltrade.data import DataValidator, LeakageGuard, build_manifest
from evltrade.execution import LatencyModel, LatencyMode, L2Book, BookLevel
from evltrade.research_lab import WalkForward, MonteCarloLab
from evltrade.synthetic import SyntheticExchange, SyntheticScenario

def ticks(n=5):
    i=Instrument('X'); t=datetime(2026,1,1,tzinfo=timezone.utc)
    return [MarketTick(t+timedelta(seconds=k),i,D('99'),D('101'),D('100'),D('10'),D('10')) for k in range(n)]

def test_dataset_manifest_and_quality():
    ts=ticks(); v=DataValidator(); assert v.validate_ticks(ts)==[]; m=build_manifest('test','1','X','1s','UTC',ts); assert m.quality=='valid' and m.content_hash

def test_leakage_guard():
    LeakageGuard.assert_monotonic([x.ts for x in ticks()])

def test_latency_is_seeded_and_l2_depth_is_consumable():
    l=LatencyModel(strategy_ms=5,network_ms=10,mode=LatencyMode.STOCHASTIC,jitter_ms=3,seed=7); assert l.total_ms()==l.total_ms()
    b=L2Book([BookLevel(D('99'),D('2'))],[BookLevel(D('101'),D('2'))]); assert b.consume('buy' if False else __import__('evltrade.core',fromlist=['Side']).Side.BUY,D('1'))

def test_walk_forward_windows_do_not_overlap_future():
    ws=WalkForward(10,5,5,5).windows(30); assert ws and all(a.oos[0]>=a.validation[1] for a in ws)

def test_monte_carlo_reproducible():
    x=MonteCarloLab().run([0.01,-0.005,0.002],trials=100,seed=42); y=MonteCarloLab().run([0.01,-0.005,0.002],trials=100,seed=42); assert x==y

def test_synthetic_reproducible():
    a=SyntheticExchange(SyntheticScenario(seed=42,ticks=10)).ticks(); b=SyntheticExchange(SyntheticScenario(seed=42,ticks=10)).ticks(); assert [(x.last,x.bid,x.ask) for x in a]==[(x.last,x.bid,x.ask) for x in b]
