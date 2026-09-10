from __future__ import annotations
import asyncio, hashlib, json
from datetime import datetime, timezone
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from evltrade import __version__
from evltrade.core import D
from evltrade.storage import session_factory, ExperimentRecord

app=FastAPI(title="EVOLTRADE API",version=__version__,docs_url="/docs",openapi_url="/openapi.json")
STRATEGIES={}; RUNS={}; TOURNAMENTS={}

class ExperimentIn(BaseModel):
    dataset_id:str; strategy_id:str; genome_hash:str=""; seed:int=42; initial_capital:str=Field(default="1000.00"); assumptions:dict=Field(default_factory=dict)
class StrategyIn(BaseModel):
    name:str; genome:dict; description:str=""
class RunIn(BaseModel):
    strategy_ids:list[str]=Field(default_factory=list); dataset_id:str="synthetic"; population:int=100; generations:int=10; seed:int=42

@app.get("/health")
def health(): return {"status":"ok","version":__version__,"live_trading":False}
@app.get("/system")
def system(): return {"mode":"research","starting_capital":"1000.00","deterministic":True,"live_trading":False,"features":["evolution","replay","robustness","monte_carlo","synthetic_market"]}

@app.post("/strategies")
def create_strategy(req:StrategyIn):
    sid="STR-"+hashlib.sha256(json.dumps(req.model_dump(),sort_keys=True).encode()).hexdigest()[:12].upper()
    STRATEGIES.setdefault(sid,{"id":sid,**req.model_dump(),"version":1,"created_at":datetime.now(timezone.utc).isoformat()})
    return STRATEGIES[sid]
@app.get("/strategies/{strategy_id}")
def get_strategy(strategy_id:str):
    if strategy_id not in STRATEGIES: raise HTTPException(404,"strategy_not_found")
    return STRATEGIES[strategy_id]
@app.get("/strategies/{strategy_id}/lineage")
def lineage(strategy_id:str): return {"strategy_id":strategy_id,"parents":[],"children":[],"events":[]}

@app.post("/experiments")
def create_experiment(req:ExperimentIn):
    material=json.dumps(req.model_dump(),sort_keys=True); eid=f"EVL-{datetime.now(timezone.utc).year}-{hashlib.sha256(material.encode()).hexdigest()[:8].upper()}"
    Session=session_factory()
    with Session.begin() as s:
        if s.get(ExperimentRecord,eid): return {"id":eid,"immutable":True,"existing":True}
        s.add(ExperimentRecord(id=eid,dataset_id=req.dataset_id,strategy_id=req.strategy_id,engine_version=__version__,seed=req.seed,initial_capital=float(D(req.initial_capital)),immutable=True,created_at=datetime.now(timezone.utc).replace(tzinfo=None),assumptions_json=json.dumps(req.assumptions,sort_keys=True)))
    return {"id":eid,"immutable":True,"engine_version":__version__}
@app.get("/experiments/{experiment_id}")
def get_experiment(experiment_id:str):
    Session=session_factory()
    with Session() as s:
        row=s.get(ExperimentRecord,experiment_id)
        if not row: raise HTTPException(404,"experiment_not_found")
        return {"id":row.id,"dataset_id":row.dataset_id,"strategy_id":row.strategy_id,"seed":row.seed,"initial_capital":str(row.initial_capital),"immutable":row.immutable}

@app.post("/backtests")
def backtest(req:RunIn):
    rid="BT-"+hashlib.sha256(json.dumps(req.model_dump(),sort_keys=True).encode()).hexdigest()[:10].upper(); RUNS[rid]={"id":rid,"status":"queued","kind":"backtest",**req.model_dump()}; return RUNS[rid]
@app.post("/evolution/runs")
def evolution(req:RunIn):
    rid="EVO-"+hashlib.sha256(json.dumps(req.model_dump(),sort_keys=True).encode()).hexdigest()[:10].upper(); RUNS[rid]={"id":rid,"status":"queued","kind":"evolution","progress":0.0,**req.model_dump()}; return RUNS[rid]
@app.get("/evolution/runs/{run_id}")
def evolution_status(run_id:str): return RUNS.get(run_id,{"id":run_id,"status":"unknown"})
@app.post("/tournaments")
def tournament(req:RunIn):
    tid="TOUR-"+hashlib.sha256(json.dumps(req.model_dump(),sort_keys=True).encode()).hexdigest()[:10].upper(); TOURNAMENTS[tid]={"id":tid,"status":"queued",**req.model_dump()}; return TOURNAMENTS[tid]
@app.get("/tournaments/{tournament_id}")
def tournament_get(tournament_id:str): return TOURNAMENTS.get(tournament_id,{"id":tournament_id,"status":"unknown"})
@app.post("/replay")
def replay(payload:dict): return {"replay_id":"RPL-"+hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:12].upper(),"speed":payload.get("speed",1),"future_data_exposed":False}
@app.get("/portfolios/{portfolio_id}")
def portfolio(portfolio_id:str): return {"id":portfolio_id,"cash":"1000.00","equity":"1000.00","drawdown":"0","positions":[],"orders":[],"fees":"0","funding":"0","margin":"0"}
@app.get("/trades/{trade_id}")
def trade(trade_id:str): return {"id":trade_id,"status":"recorded"}

async def _events() -> AsyncGenerator[str,None]:
    for p in (0.0,0.25,0.5,0.75,1.0):
        yield f"data: {json.dumps({'progress':p})}\n\n"; await asyncio.sleep(0.01)
@app.get("/events")
async def events(): return StreamingResponse(_events(),media_type="text/event-stream",headers={"Cache-Control":"no-cache"})
