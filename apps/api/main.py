from __future__ import annotations
import asyncio, hashlib, json, os
from datetime import datetime, timezone
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from evltrade import __version__
from evltrade.core import D
from evltrade.storage import session_factory, ExperimentRecord, StrategyRecord, RunRecord, PortfolioRecord, TradeRecord, LineageRecord

app=FastAPI(title='EVOLTRADE API',version=__version__,docs_url='/docs',openapi_url='/openapi.json')
Session=session_factory()

class ExperimentIn(BaseModel):
    dataset_id:str; strategy_id:str; genome_hash:str=''; seed:int=42; initial_capital:str=Field(default='1000.00'); assumptions:dict=Field(default_factory=dict)
class StrategyIn(BaseModel):
    name:str; genome:dict; description:str=''
class RunIn(BaseModel):
    strategy_ids:list[str]=Field(default_factory=list); dataset_id:str='synthetic'; population:int=100; generations:int=10; seed:int=42
class PortfolioOut(BaseModel):
    id:str; cash:str; equity:str; drawdown:str

@app.get('/health')
def health(): return {'status':'ok','version':__version__,'live_trading':False}
@app.get('/system')
def system(): return {'mode':'research','starting_capital':'1000.00','deterministic':True,'live_trading':False,'database':os.getenv('DATABASE_URL','sqlite:///./evoltrade.db'),'features':['evolution','replay','robustness','monte_carlo','synthetic_market','sse']}

@app.post('/strategies')
def create_strategy(req:StrategyIn):
    sid='STR-'+hashlib.sha256(json.dumps(req.model_dump(),sort_keys=True,separators=(',',':')).encode()).hexdigest()[:12].upper(); now=datetime.now(timezone.utc).replace(tzinfo=None)
    with Session.begin() as s:
        row=s.get(StrategyRecord,sid)
        if row:return {'id':sid,'name':row.name,'version':row.version,'genome_hash':row.genome_hash}
        ghash=hashlib.sha256(json.dumps(req.genome,sort_keys=True,separators=(',',':')).encode()).hexdigest(); s.add(StrategyRecord(id=sid,name=req.name,version=1,genome_hash=ghash,genome_json=json.dumps({'genome':req.genome,'description':req.description},sort_keys=True),created_at=now))
    return {'id':sid,'name':req.name,'version':1,'genome_hash':ghash}

@app.get('/strategies/{strategy_id}')
def get_strategy(strategy_id:str):
    with Session() as s:
        row=s.get(StrategyRecord,strategy_id)
        if not row:raise HTTPException(404,'strategy_not_found')
        return {'id':row.id,'name':row.name,'version':row.version,'genome_hash':row.genome_hash,'genome':json.loads(row.genome_json)}

@app.get('/strategies/{strategy_id}/lineage')
def lineage(strategy_id:str):
    with Session() as s:
        rows=s.query(LineageRecord).filter(LineageRecord.child_id.like(f'{strategy_id}%')).all()
        return {'strategy_id':strategy_id,'nodes':[{'child_id':r.child_id,'parents':json.loads(r.parent_ids_json),'generation':r.generation,'operation':r.operation,'genome_hash':r.genome_hash} for r in rows]}

@app.post('/experiments')
def create_experiment(req:ExperimentIn):
    material=json.dumps(req.model_dump(),sort_keys=True,separators=(',',':')); eid=f"EVL-{datetime.now(timezone.utc).year}-{hashlib.sha256(material.encode()).hexdigest()[:8].upper()}"; now=datetime.now(timezone.utc).replace(tzinfo=None)
    with Session.begin() as s:
        if s.get(ExperimentRecord,eid):return {'id':eid,'immutable':True,'existing':True}
        s.add(ExperimentRecord(id=eid,dataset_id=req.dataset_id,strategy_id=req.strategy_id,engine_version=__version__,seed=req.seed,initial_capital=D(req.initial_capital),immutable=True,created_at=now,assumptions_json=json.dumps({**req.assumptions,'genome_hash':req.genome_hash},sort_keys=True)))
    return {'id':eid,'immutable':True,'engine_version':__version__}

@app.get('/experiments/{experiment_id}')
def get_experiment(experiment_id:str):
    with Session() as s:
        row=s.get(ExperimentRecord,experiment_id)
        if not row:raise HTTPException(404,'experiment_not_found')
        return {'id':row.id,'dataset_id':row.dataset_id,'strategy_id':row.strategy_id,'engine_version':row.engine_version,'seed':row.seed,'initial_capital':str(row.initial_capital),'immutable':row.immutable,'assumptions':json.loads(row.assumptions_json or '{}')}

@app.post('/backtests')
def backtest(req:RunIn):
    rid='BT-'+hashlib.sha256(json.dumps(req.model_dump(),sort_keys=True).encode()).hexdigest()[:10].upper(); now=datetime.now(timezone.utc).replace(tzinfo=None)
    with Session.begin() as s:s.merge(RunRecord(id=rid,kind='backtest',status='queued',progress=D('0'),seed=req.seed,created_at=now,config_json=json.dumps(req.model_dump(),sort_keys=True)))
    return {'id':rid,'status':'queued','kind':'backtest',**req.model_dump()}

@app.post('/evolution/runs')
def evolution(req:RunIn):
    rid='EVO-'+hashlib.sha256(json.dumps(req.model_dump(),sort_keys=True).encode()).hexdigest()[:10].upper(); now=datetime.now(timezone.utc).replace(tzinfo=None)
    with Session.begin() as s:s.merge(RunRecord(id=rid,kind='evolution',status='queued',progress=D('0'),seed=req.seed,created_at=now,config_json=json.dumps(req.model_dump(),sort_keys=True)))
    return {'id':rid,'status':'queued','kind':'evolution','progress':0.0,**req.model_dump()}

@app.get('/evolution/runs/{run_id}')
def evolution_status(run_id:str):
    with Session() as s:
        row=s.get(RunRecord,run_id)
        if not row:raise HTTPException(404,'run_not_found')
        return {'id':row.id,'kind':row.kind,'status':row.status,'progress':float(row.progress),'seed':row.seed,'config':json.loads(row.config_json or '{}')}

@app.post('/tournaments')
def tournament(req:RunIn):
    tid='TOUR-'+hashlib.sha256(json.dumps(req.model_dump(),sort_keys=True).encode()).hexdigest()[:10].upper(); now=datetime.now(timezone.utc).replace(tzinfo=None)
    with Session.begin() as s:s.merge(RunRecord(id=tid,kind='tournament',status='queued',progress=D('0'),seed=req.seed,created_at=now,config_json=json.dumps(req.model_dump(),sort_keys=True)))
    return {'id':tid,'status':'queued',**req.model_dump()}

@app.get('/tournaments/{tournament_id}')
def tournament_get(tournament_id:str):
    with Session() as s:
        row=s.get(RunRecord,tournament_id)
        if not row:raise HTTPException(404,'tournament_not_found')
        return {'id':row.id,'status':row.status,'config':json.loads(row.config_json or '{}')}

@app.post('/replay')
def replay(payload:dict): return {'replay_id':'RPL-'+hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:12].upper(),'speed':payload.get('speed',1),'future_data_exposed':False}

@app.get('/portfolios/{portfolio_id}',response_model=PortfolioOut)
def portfolio(portfolio_id:str):
    with Session() as s:
        row=s.get(PortfolioRecord,portfolio_id)
        if not row:return PortfolioOut(id=portfolio_id,cash='1000.00',equity='1000.00',drawdown='0')
        return PortfolioOut(id=row.id,cash=str(row.cash),equity=str(row.equity),drawdown=str(row.drawdown))

@app.get('/trades/{trade_id}')
def trade(trade_id:str):
    with Session() as s:
        row=s.get(TradeRecord,trade_id)
        if not row:raise HTTPException(404,'trade_not_found')
        return {'id':row.id,'experiment_id':row.experiment_id,'strategy_id':row.strategy_id,'symbol':row.symbol,'side':row.side,'price':str(row.price),'quantity':str(row.quantity),'fee':str(row.fee),'created_at':row.created_at.isoformat()}

async def _events()->AsyncGenerator[str,None]:
    for p in (0.0,0.25,0.5,0.75,1.0):
        yield 'data: '+json.dumps({'progress':p,'live_trading':False})+'\n\n'; await asyncio.sleep(.01)
@app.get('/events')
async def events():return StreamingResponse(_events(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
