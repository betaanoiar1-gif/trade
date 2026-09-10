# EVOLTRADE Specification Compliance

This matrix maps the requested architecture to repository components. The platform is research/paper-only; live trading remains disabled by default.

| Area | Implementation | Status |
|---|---|---|
| Event-driven core | `src/evltrade/core.py` Event/EventLog/Simulator | implemented |
| Virtual capital | `Ledger`, `Portfolio`, Decimal accounting | implemented |
| Broker/order lifecycle | `core.py`, `execution.py` | implemented foundation |
| L2/order-book/queue | `execution.py` L2Book/BookLevel | implemented foundation |
| Latency | `execution.py` LatencyModel | implemented |
| Slippage/impact | `execution.py` policies | implemented |
| Risk | `core.py` RiskEngine | implemented foundation |
| Margin/liquidation | `accounting.py` MarginAccount | implemented foundation |
| Strategy SDK | `core.py` protocol | implemented |
| Strategy DSL/IR | `strategy.py` Node/StrategyDSL | implemented |
| Evolution operators | `evolution.py`, `core.py` | implemented |
| Pareto/novelty/niching | `evolution.py` | implemented foundation |
| Diversity pressure | `PopulationManager.diversity` | implemented foundation |
| Lineage/cemetery | `LineageStore`, `AlphaCemetery` | implemented |
| WFA/OOS | `research_lab.py` | implemented |
| Robustness | `research_lab.py` | implemented |
| Monte Carlo | `research_lab.py` | implemented |
| Counterfactual/sensitivity | `research_lab.py` | implemented foundation |
| Regime/capacity | `research_lab.py` | implemented foundation |
| Portfolio evolution | tournament/allocation primitives | implemented foundation |
| Shared-capital tournament | `tournament.py` | implemented |
| Execution evolution | execution policy representation | implemented foundation |
| Strategy competition | `tournament.py` modes | implemented |
| Co-evolution | module boundary reserved; must remain opt-in | interface |
| Synthetic exchange | `synthetic.py` | implemented |
| Historical replay | `core.py`, replay surface/API | implemented foundation |
| Counterfactual replay | API/research primitives | implemented foundation |
| Immutable experiments | SQLAlchemy `ExperimentRecord` + API | implemented |
| Dataset versioning/quality | `data.py` | implemented |
| Reproducibility | stable hashing/event digest + seeded models | implemented |
| Frontend | Next.js app with quant control-plane UI | implemented foundation |
| Realtime | SSE `/events` | implemented |
| PostgreSQL/Parquet-ready storage | SQLAlchemy + Arrow/DuckDB deps | configured |
| Worker orchestration | `orchestrator.py` | implemented |
| CLI | `src/evltrade/cli.py` | implemented |
| REST/OpenAPI | `apps/api/main.py` | implemented |
| Plugin system | `plugins.py` protocols/registry | implemented |
| Security defaults | environment-oriented design; live disabled | implemented baseline |
| Testing | unit/property/integration structure | expanded baseline |
| Performance | deterministic core separated for benchmarks | baseline; benchmark suite to expand |

## Non-negotiable invariants

1. Strategies emit order intents; they do not mutate cash, positions or PnL.
2. Accounting uses Decimal for monetary values.
3. Experiment records are immutable; changed assumptions create a new experiment identity.
4. Historical deterministic replay is isolated from optional synthetic/co-evolution modules.
5. Live trading is disabled by default.
6. Synthetic data and assumptions are explicitly labeled rather than presented as historical truth.
