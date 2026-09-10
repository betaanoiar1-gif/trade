# EVOLTRADE Architecture Proposal

## Vision
Deterministic, event-driven evolutionary trading research platform with realistic execution, accounting, replay, robustness and auditable experiments.

## Chosen architecture
**Modular deterministic core + worker runtime.** Python owns domain/application contracts; performance-sensitive paths have replaceable interfaces for future Rust acceleration. Single-machine workers come before distributed orchestration.

## Layers
- Domain: instruments, orders, fills, positions, ledger, portfolio, genomes, experiments.
- Events: typed immutable transitions and deterministic event digest.
- Market: datasets, quality checks, historical replay, synthetic exchange.
- Execution: order book, queue, broker, fees, slippage, latency, market impact.
- Risk/accounting: independent risk policy and Decimal ledger.
- Strategy: SDK and IR; strategies emit intents and never mutate capital.
- Evolution: mutation, crossover, novelty, niching, speciation, Pareto selection, lineage and cemetery.
- Research: WFA, robustness, Monte Carlo, sensitivity, regimes, capacity, counterfactuals.
- Orchestration: immutable experiments, workers, checkpoints, cancellation and recovery.
- API/UI: FastAPI/OpenAPI + Next.js/TypeScript/ECharts.

## Integrity rules
Historical and synthetic sources are separated. Experiments identify dataset, genome, engine, broker/risk/execution assumptions and seed. The $1,000 starting capital is represented by an actual ledger/portfolio state, not a display-only value. Live trading is disabled by design.

## Alternatives
A monolithic Python app is simpler but couples domains. Microservices-first adds distributed-state complexity and weakens deterministic debugging. The selected architecture keeps domain boundaries strong while permitting later scale-out.
