# EVOLTRADE Specification Compliance

This living gate maps the requested EVOLTRADE specification to code. `implemented` means executable code exists; `foundation` means primitives/interfaces exist but deeper integration remains; `configured` means the runtime/dependency is present. GitHub source has been inspected, but no claim of a green remote CI run is made because no workflow status is available.

| Area | Implementation | Status |
|---|---|---|
| Event-driven core | `src/evltrade/core.py` | implemented |
| Event taxonomy | `EventType` | implemented |
| $1,000 virtual capital | `Ledger` / `Portfolio` | implemented |
| Decimal accounting | core + SQLAlchemy Numeric | implemented |
| Double-entry ledger | `accounting.py` | implemented foundation |
| Broker/order lifecycle | core + execution | foundation |
| Market/limit/stop surface | `OrderType` / intent | foundation |
| IOC/FOK/GTC/GTD/Post-only/Reduce-only | core + execution | foundation |
| Partial fills / expiry / minimums | core + execution | foundation |
| L2 book + queue | `L2Book` / `BookLevel` | foundation |
| Latency | `LatencyModel` | implemented |
| Slippage / impact | execution models | implemented |
| Independent risk controller | `risk.py` | implemented |
| Margin / liquidation | `MarginAccount` | foundation |
| Strategy SDK | `Strategy` protocol | implemented |
| Strategy DSL / IR | `strategy.py` | implemented |
| Genome hashing | genome classes | implemented |
| Mutation / crossover | evolution engine | implemented |
| Structural mutation suite | evolution engine | foundation |
| Pareto selection | `ParetoSelector` | implemented |
| Novelty archive | `NoveltyArchive` | implemented |
| Niching/speciation | `Niching` | foundation |
| Diversity pressure | `PopulationManager.pressure` | implemented |
| Generational state | `GenerationSnapshot` | implemented |
| Lineage | `LineageStore` | implemented |
| Alpha Cemetery | `AlphaCemetery` | implemented |
| Checkpoint/resume | evolution + orchestrator | foundation |
| Walk-forward/OOS | `WalkForward` | implemented |
| Anti-leakage | `data.py` / tests | foundation |
| Robustness | `RobustnessLab` | implemented |
| Monte Carlo | `MonteCarloLab` | implemented |
| Counterfactual | `CounterfactualEngine` | implemented |
| Sensitivity | `SensitivityLab` | implemented |
| Regimes | `RegimeLab` | implemented |
| Capacity | `CapacityLab` | implemented |
| Portfolio evolution | tournament primitives | foundation |
| Shared-capital tournament | `tournament.py` | implemented |
| Execution evolution | execution fields | foundation |
| Competition stress modes | tournament modes | implemented |
| Optional co-evolution | `co_evolution.py` | implemented isolated sandbox |
| Synthetic exchange | `synthetic.py` | foundation |
| Historical replay | `replay.py` | foundation |
| Counterfactual replay | API/research primitives | foundation |
| Immutable experiments | storage + API | implemented |
| Dataset versioning | `data.py` | implemented |
| Dataset quality | `DataValidator` | implemented |
| Reproducibility | hashes + seeds | foundation |
| Reports | `reporting.py` | implemented |
| SSE realtime transport | API `/events` | foundation |
| PostgreSQL runtime | SQLAlchemy + Docker | configured |
| Arrow/DuckDB analytics | dependencies + data layer | configured |
| Worker orchestration | `orchestrator.py` | foundation |
| CLI | `cli.py` | foundation-to-executable |
| REST/OpenAPI | `apps/api/main.py` | implemented |
| Plugin interfaces | `plugins.py` | implemented |
| Security baseline | research-only/live-disabled/env config | implemented baseline |
| Quant frontend | Next.js/TypeScript | foundation |
| Remote CI | GitHub Actions | unavailable/not verified |
| Full frontend E2E | test suite | not yet verified |
| Full performance benchmark suite | benchmark package | not yet verified |

## Non-negotiable invariants

1. Strategies produce order intents and do not directly mutate portfolio cash/positions/PnL.
2. Monetary values are Decimal in the accounting/execution domain.
3. Experiments are immutable; changed assumptions produce new identities.
4. Historical deterministic replay is isolated from synthetic/co-evolutionary modules.
5. Live trading is disabled by default.
6. Synthetic data is explicitly labeled synthetic.
7. FOK checks liquidity before consuming an L2 book.
8. A fill cannot exceed the remaining order quantity.
9. Deterministic event digests exclude random UUIDs.
10. Environment/database secrets are not written into source code.

## Verification note

The latest GitHub `main` tree was inspected after the implementation updates and includes the verification script, expanded core/evolution/execution/research/orchestration layers, persistent API/storage changes, reporting, risk, and optional co-evolution. A remote GitHub Actions run is not available, so final runtime verification must be performed in an environment that can install dependencies and execute the repository checkout.
