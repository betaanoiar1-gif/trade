# EVOLTRADE

**Evolutionary Trading Laboratory**

A deterministic, event-driven research platform for realistic trading simulation, evolutionary strategy research, portfolio/execution evolution, historical replay, robustness analysis and auditable experiments.

## Implemented foundation
- Event log with deterministic digest
- Market tick, order intent, order, fill and order-book primitives
- Risk -> matching -> fill -> Decimal accounting -> portfolio flow
- L1 liquidity constraints, limit/market orders, fees and slippage interfaces
- $1,000 default research capital
- Strategy SDK lifecycle
- Genome hashing, mutation and crossover
- Population/lineage primitives
- Fitness metrics: return, Sharpe, Sortino, drawdown, complexity
- Historical replay cursor
- Immutable experiment storage and FastAPI control plane
- CLI self-test and deterministic tests
- Research-only mode; live trading disabled

## Run
```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
python -m evltrade.cli self-test
uvicorn apps.api.main:app --reload
```

See `docs/ARCHITECTURE_PROPOSAL.md` and `docs/FAILURE_MODEL.md`.
