from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from hashlib import sha256
import json, threading, time

@dataclass
class JobState:
    job_id:str; status:str="queued"; progress:float=0.0; result:object=None; error:str|None=None; started_at:float|None=None; finished_at:float|None=None

class CheckpointStore:
    def __init__(self): self.data={}; self.lock=threading.Lock()
    def save(self,key,payload):
        with self.lock:self.data[key]=json.loads(json.dumps(payload,default=str))
    def load(self,key):
        with self.lock:return self.data.get(key)

class ExperimentCoordinator:
    def __init__(self,workers:int=1): self.pool=ThreadPoolExecutor(max_workers=max(1,workers)); self.jobs={}; self.futures={}; self.checkpoints=CheckpointStore(); self.lock=threading.Lock()
    @staticmethod
    def deterministic_id(spec:dict)->str:
        canonical=json.dumps(spec,sort_keys=True,default=str,separators=(",",":")); return "EVL-"+sha256(canonical.encode()).hexdigest()[:8].upper()
    def submit(self,fn,*args,**kwargs)->str:
        job_id=self.deterministic_id({"fn":getattr(fn,"__name__","job"),"args":args,"kwargs":kwargs,"submitted":time.time_ns()}); self.jobs[job_id]=JobState(job_id,"running",0.0,started_at=time.time()); fut=self.pool.submit(fn,*args,**kwargs); self.futures[job_id]=fut; fut.add_done_callback(lambda f:self._done(job_id,f)); return job_id
    def _done(self,job_id,f:Future):
        s=self.jobs[job_id]; s.finished_at=time.time(); s.status="failed" if f.exception() else "completed"; s.error=str(f.exception()) if f.exception() else None; s.result=None if f.exception() else f.result(); s.progress=1.0
    def status(self,job_id): return self.jobs.get(job_id)
    def cancel(self,job_id):
        if job_id not in self.jobs:return False
        ok=self.futures[job_id].cancel()
        if ok:self.jobs[job_id].status="cancelled"; self.jobs[job_id].finished_at=time.time()
        return ok
    def shutdown(self): self.pool.shutdown(wait=False,cancel_futures=True)
