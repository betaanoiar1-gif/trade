from evltrade.core import D, Instrument, OrderIntent, OrderType, Side
from evltrade.risk import PortfolioRiskController, RiskLimits
from evltrade.orchestrator import ExperimentCoordinator

def test_risk_kill_switch_and_limits():
    inst=Instrument("X"); intent=OrderIntent("s",inst,Side.BUY,D("1"),OrderType.MARKET)
    r=PortfolioRiskController(RiskLimits(max_order_notional=D("50")))
    assert r.check(intent,D("10"),D("100")).approved
    r.trip(); assert r.check(intent,D("10"),D("100")).reason=="kill_switch"

def test_coordinator_id_is_deterministic():
    a=ExperimentCoordinator.deterministic_id({"seed":42,"x":1}); b=ExperimentCoordinator.deterministic_id({"x":1,"seed":42}); assert a==b

def test_coordinator_completed_job():
    c=ExperimentCoordinator(1); jid=c.submit(lambda: 7); import time; time.sleep(.03); assert c.status(jid).result==7; c.shutdown()
