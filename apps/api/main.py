from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,Field
from evltrade import __version__
from evltrade.core import D
from evltrade.storage import session_factory
from datetime import datetime,timezone
app=FastAPI(title='EVOLTRADE API',version=__version__,docs_url='/docs')
class ExperimentIn(BaseModel):
 dataset_id:str; strategy_id:str; genome_hash:str=''; seed:int=42; initial_capital:str=Field(default='1000.00'); assumptions:dict=Field(default_factory=dict)
@app.get('/health')
def health(): return {'status':'ok','version':__version__,'live_trading':False}
@app.get('/system')
def system(): return {'mode':'research','starting_capital':'1000.00','deterministic':True,'live_trading':False}
@app.post('/experiments')
def create_experiment(req:ExperimentIn):
 import hashlib,json
 from evltrade.storage import ExperimentRecord
 material=json.dumps(req.model_dump(),sort_keys=True); eid=f'EVL-{datetime.now(timezone.utc).year}-{hashlib.sha256(material.encode()).hexdigest()[:8].upper()}'
 Session=session_factory()
 with Session.begin() as s:
  if s.get(ExperimentRecord,eid): return {'id':eid,'immutable':True,'existing':True}
  s.add(ExperimentRecord(id=eid,dataset_id=req.dataset_id,strategy_id=req.strategy_id,engine_version=__version__,seed=req.seed,initial_capital=float(D(req.initial_capital)),immutable=True,created_at=datetime.now(timezone.utc).replace(tzinfo=None),assumptions_json=json.dumps(req.assumptions,sort_keys=True)))
 return {'id':eid,'immutable':True,'engine_version':__version__}
@app.get('/experiments/{experiment_id}')
def get_experiment(experiment_id:str):
 from evltrade.storage import ExperimentRecord
 Session=session_factory()
 with Session() as s:
  row=s.get(ExperimentRecord,experiment_id)
  if not row: raise HTTPException(404,'experiment_not_found')
  return {'id':row.id,'dataset_id':row.dataset_id,'strategy_id':row.strategy_id,'seed':row.seed,'initial_capital':str(row.initial_capital),'immutable':row.immutable}
