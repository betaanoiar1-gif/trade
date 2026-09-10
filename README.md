# EVOLTRADE

**Evolutionary Trading Laboratory**

EVOLTRADE is a research-first, deterministic, event-driven laboratory for realistic trading simulation and evolutionary discovery. It is not an LLM trading core, and live trading is disabled by default.

## Current platform

- Event-driven market/order/fill event log with deterministic digest
- Virtual broker and matching foundation with partial fills, L1/L2 book abstractions, queue consumption, fees, slippage, latency and market impact plugins
- Decimal-based $1,000 research portfolio with positions, equity, drawdown and double-entry-style accounting primitives
- Independent risk and margin primitives
- Strategy SDK plus a validated strategy IR/DSL covering logical/arithmetic/state/market conditions
- Evolution: mutation, crossover, structural genome hashing, Pareto front, novelty archive, diversity measurement, lineage tree, Alpha Cemetery and checkpoints
- Research Lab: walk-forward windows, robustness sweeps, Monte Carlo distributions, sensitivity grids, regime analysis and capacity sweeps
- Shared-capital tournaments and configurable adverse market modes
- Seeded Synthetic Exchange separated from historical deterministic replay
- Dataset manifests, fingerprints, quality validation and leakage guards
- SQLAlchemy persistence model for experiments, strategies, datasets, runs, portfolios, trades and lineage
- FastAPI/OpenAPI control plane with strategy, experiment, backtest, evolution, tournament, replay, portfolio, trade and SSE surfaces
- Next.js/TypeScript quant-style research UI with dashboard, population health, equity curve and research surfaces
- CLI: `data`, `backtest`, `evolve`, `tournament`, `replay`, `report`, `paper`, `synthetic`, `self-test`
- Docker + PostgreSQL local runtime

## Design constraints

The core remains free/open-source oriented, deterministic and auditable. External components are injected through explicit plugin protocols. Synthetic/co-evolutionary behavior must never silently alter historical deterministic results. Experiments are modeled as immutable records: changed assumptions create a new experiment identity.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
python -m evltrade.cli self-test
uvicorn apps.api.main:app --reload
```

For the database runtime:

```bash
docker compose up --build
```

## Research contract

The architecture explicitly guards against lookahead/future leakage, unrealistic candle-touch fills, duplicate fills, phantom money, uncontrolled convergence and misleading synthetic assumptions. See `docs/FAILURE_MODEL.md`, `docs/ARCHITECTURE_PROPOSAL.md`, and `docs/SPEC_COMPLIANCE.md`.
