from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import json
from typing import Iterable
from .core import MarketTick

@dataclass(frozen=True)
class DatasetManifest:
    dataset_id: str
    source: str
    version: str
    symbol: str
    timeframe: str
    timezone: str
    transformations: tuple[str,...] = ()
    quality: str = "unvalidated"
    content_hash: str = ""
    def canonical(self) -> str: return json.dumps(asdict(self),sort_keys=True,default=str,separators=(",",":"))

@dataclass(frozen=True)
class QualityIssue:
    kind: str
    index: int
    detail: str

class DataValidator:
    def validate_ticks(self, ticks: list[MarketTick]) -> list[QualityIssue]:
        issues=[]; seen=set(); prev=None
        for i,t in enumerate(ticks):
            if t.ts in seen: issues.append(QualityIssue("duplicate_timestamp",i,t.ts.isoformat()))
            seen.add(t.ts)
            if prev is not None and t.ts <= prev: issues.append(QualityIssue("non_increasing_timestamp",i,t.ts.isoformat()))
            if t.bid <= 0 or t.ask <= 0 or t.bid > t.ask: issues.append(QualityIssue("invalid_quote",i,"bid/ask"))
            if t.last <= 0: issues.append(QualityIssue("invalid_last",i,str(t.last)))
            if t.bid_size < 0 or t.ask_size < 0 or t.trade_size < 0: issues.append(QualityIssue("invalid_volume",i,"negative size"))
            prev=t.ts
        return issues
    def fingerprint(self,ticks: Iterable[MarketTick]) -> str:
        payload="\n".join(f"{t.ts.isoformat()}|{t.instrument.symbol}|{t.bid}|{t.ask}|{t.last}|{t.bid_size}|{t.ask_size}|{t.trade_size}" for t in ticks)
        return sha256(payload.encode()).hexdigest()

class LeakageGuard:
    @staticmethod
    def assert_monotonic(timestamps: list[datetime]):
        if any(b <= a for a,b in zip(timestamps,timestamps[1:])): raise ValueError("future/timestamp leakage detected")
    @staticmethod
    def causal_window(values: list[Decimal], end: int, width: int) -> list[Decimal]:
        start=max(0,end-width+1); return values[start:end+1]


def build_manifest(source: str, version: str, symbol: str, timeframe: str, timezone: str, ticks: list[MarketTick], transformations: tuple[str,...]=()) -> DatasetManifest:
    validator=DataValidator(); issues=validator.validate_ticks(ticks)
    quality="valid" if not issues else "invalid"
    return DatasetManifest(f"DS-{validator.fingerprint(ticks)[:12].upper()}",source,version,symbol,timeframe,timezone,transformations,quality,validator.fingerprint(ticks))
