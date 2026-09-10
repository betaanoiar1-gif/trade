from __future__ import annotations
import csv, json
from io import StringIO
from pathlib import Path
from .core import ExperimentResult

class ExperimentReporter:
    @staticmethod
    def payload(result: ExperimentResult) -> dict:
        return {"experiment_id":result.spec.experiment_id,"dataset_id":result.spec.dataset_id,"strategy_id":result.spec.strategy_id,"genome_hash":result.spec.genome_hash,"engine_version":result.spec.engine_version,"seed":result.spec.seed,"initial_capital":str(result.spec.initial_capital),"equity":str(result.equity),"return_pct":str(result.return_pct),"max_drawdown":str(result.max_drawdown),"trades":result.trades,"fees":str(result.fees),"event_digest":result.event_digest,"assumptions":result.spec.assumptions}
    def json(self,result): return json.dumps(self.payload(result),sort_keys=True,indent=2,default=str)
    def markdown(self,result):
        p=self.payload(result); rows="\n".join(f"| {k} | {v} |" for k,v in p.items() if k!="assumptions")
        return "# EVOLTRADE Experiment Report\n\n| Metric | Value |\n|---|---|\n"+rows
    def csv(self,result):
        out=StringIO(); w=csv.writer(out); w.writerow(["metric","value"])
        for k,v in self.payload(result).items(): w.writerow([k,json.dumps(v,default=str) if isinstance(v,(dict,list)) else v])
        return out.getvalue()
    def write(self,result,directory):
        root=Path(directory); root.mkdir(parents=True,exist_ok=True); base=result.spec.experiment_id
        out={"json":root/f"{base}.json","md":root/f"{base}.md","csv":root/f"{base}.csv"}
        out["json"].write_text(self.json(result),encoding="utf-8"); out["md"].write_text(self.markdown(result),encoding="utf-8"); out["csv"].write_text(self.csv(result),encoding="utf-8")
        return out
