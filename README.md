# EVOLTRADE

**Evolutionary Trading Laboratory**

EVOLTRADE is a research-first, deterministic, event-driven laboratory for realistic trading simulation and evolutionary discovery. It is not an LLM trading core, and live trading is disabled by default.

## Current platform

- Event-driven market/order/fill event log with deterministic digest
- Virtual broker and matching foundation with partial fills, L1/L2 book abstractions, queue consumption, fees, slippage, latency and market-impact models
- Decimal-based $1,000 research portfolio with positions, equity, drawdown and double-entry accounting primitives
- Independent risk controller, kill switch and margin primitives
- Strategy SDK plus validated Strategy IR/DSL covering logical, arithmetic, state, market, volatility and liquidity conditions
- Evolution with mutation/crossover, Pareto selection, novelty archive, diversity pressure, configurable niching, lineage, Alpha Cemetery and checkpoints
- Simulation-backed `EvolutionRunner` so candidate fitness can come from actual deterministic trading simulations rather than only synthetic fitness values
- Research Lab with walk-forward/OOS windows, robustness, Monte Carlo, counterfactual, sensitivity, regime and capacity analysis
- Shared-capital tournament primitives and adverse-market modes
- Optional isolated co-evolution sandbox
- Seeded Synthetic Exchange separated from historical deterministic replay
- Dataset manifests, fingerprints, quality validation and leakage guards
- SQLAlchemy persistence for experiments, strategies, datasets, runs, portfolios, trades and lineage; PostgreSQL supported through `DATABASE_URL`
- FastAPI/OpenAPI control plane with persistent strategy/run records and SSE event transport
- Next.js/TypeScript quant-style research UI; dashboard metrics are explicitly marked as a seeded demo snapshot until connected to live API state
- CLI: `data`, `backtest`, `evolve`, `tournament`, `replay`, `report`, `paper`, `synthetic`, `self-test`
- Docker + PostgreSQL local runtime

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
python scripts/verify_core.py
python -m evltrade.cli evolve --population 100 --generations 10 --seed 42
uvicorn apps.api.main:app --reload
```

For PostgreSQL runtime:

```bash
docker compose up --build
```

## Research contract

The system is explicitly designed to guard against lookahead/future leakage, unrealistic candle-touch fills, destructive FOK handling, duplicate fills, phantom money, uncontrolled convergence and misleading synthetic assumptions. Historical deterministic replay is isolated from synthetic/co-evolutionary modules, experiments are immutable, and live trading remains disabled by default.

See `docs/FAILURE_MODEL.md`, `docs/ARCHITECTURE_PROPOSAL.md`, `docs/EVOLUTION_MODEL.md`, and `docs/SPEC_COMPLIANCE.md`.

## Verification note

The repository structure and source files have been inspected on GitHub after the current implementation pass. A complete local/remote green CI result is not claimed because the current execution environment could not clone the public repository and the repository has no available workflow status for this revision.
