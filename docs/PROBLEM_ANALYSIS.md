# EVOLTRADE — PHASE 0: PROBLEM ANALYSIS

Date: 2026-09-10 · Status: draft for review

## 1. What we are building

EVOLTRADE is **not** a backtester, not a strategy generator, not a trading bot. It is an
**engineering and research platform** where:

- Markets can be simulated and replayed deterministically.
- Trading behaves as close to real trading as the data allows (order lifecycle, matching, fees,
  funding, margin, liquidation, latency, slippage, impact, queue position).
- A virtual account starts at exactly **$1,000.00** and is a real accounting entity (double-entry
  ledger, no phantom money).
- Orders flow through a strict pipeline:
  `Strategy → Order Intent → Risk → Broker → Matching → Fill → Accounting → Portfolio`.
- Strategies, portfolios, and execution policies **evolve**: mutation, crossover, selection,
  speciation, novelty, death, lineage.
- Synthetic exchanges can be created with explicit seeds.
- Every experiment is reproducible, immutable, and fully auditable (every number traces to an
  event).
- The core is free/open-source, contains **no AI/LLM**, and never assumes paid data or SaaS.

## 2. Decomposition of the problem

The ~27 named sub-problems group into **7 clusters**. Each cluster lists its purpose, hard
requirements (from the spec), dominant risks, and the design questions this phase must answer.

### Cluster 1 — SIMULATION & MARKET

Sub-problems: Market Simulation · Historical Replay · Synthetic Markets · Matching · Order Book ·
Queue Model · Latency · Slippage · Market Impact.

| Concern | Requirements (condensed) | Dominant risk | Design question |
|---|---|---|---|
| Market data tiers | Use real L2 when available; declare a synthetic model when not; never present synthetic as real | "Bad market reconstruction" trusted as truth | A declared **data-tier model** (T2/L2 → T1/L1+trades → T0/OHLCV) stamped on every result |
| Matching | Fill = result of a matching model over book state, **never** "candle touched price" | Unrealistic fills | Tiered matching models; depth consumption; price-time priority |
| Order book | Unified abstraction: levels, best bid/ask, spread, depth, consumption, estimated execution price | Book state drift | Single `OrderBook` interface with pluggable backends (reconstructed / synthetic) |
| Queue model | Queue position, trade consumption, partial/complete fill, no-fill, cancel, expire — all changeable | Invisible assumptions | Queue model as **plugin** (exact-FIFO on trade data, probabilistic otherwise, declared) |
| Latency | 6 independent layers (strategy compute, internal, network, broker, exchange, execution); deterministic + stochastic (seeded) modes | Wrong latency shape → wrong fills | Latency as event *scheduling* (time-shifted events), not post-hoc offsets |
| Slippage / impact | Pluggable: fixed, pct, spread, volatility, volume, book, latency-aware, custom; impact scales with size & liquidity | Cost underestimation | Both are **plugins over the same execution interface**, parameterized by book state |
| Replay | Pick a date, sequential events, no future revealed, 1x–100x, play/pause/step/jump-to-trade/jump-to-drawdown | Future leakage in the UI | Replay = re-broadcast of the **event log** of an immutable experiment; UI holds a mirror state |
| Synthetic markets | Seeded exchange: book, matching, liquidity agents, fees, latency, impact, regimes; optional | Over-assuming synthetic behavior | Synthetic exchange is a first-class **market adapter** (same interface as historical), guarded from historical runs |

### Cluster 2 — TRADING CORE

Sub-problems: Trading Engine · Brokerage · Portfolio · Accounting · Risk · Margin/Liquidation.

| Concern | Requirements | Dominant risk | Design question |
|---|---|---|---|
| Engine | Event-driven core (not loops), all listed event types, traceable transitions | Non-determinism, untraceable state | Deterministic event scheduler with total order; event sourcing for audit |
| Virtual broker | Market/Limit/Stop/StopLimit/TP/Trailing/IOC/FOK/GTC/GTD/PostOnly/ReduceOnly; partial fills; rejections; expiry; precision; tick size; step size; min qty; min notional | Orders accepted that a real broker would reject | Broker = rule engine with structured **rejection reason codes**, enforced before matching |
| Accounting | Double-entry ledger for every financial operation; reconciliation; $1,000 real in the engine | Phantom money | Ledger is the **single source of truth** for money; Decimal-only; invariant checks |
| Portfolio | cash, reserved, available, positions, realized/unrealized PnL, fees, funding, margin, equity, drawdown, exposure | Wrong equity at any instant | Portfolio = *view* over ledger + positions; equity reconciled at checkpoints |
| Risk | Independent engine; max position/exposure/leverage/order/daily loss/drawdown/concentration; circuit breaker; kill switch; can reject orders | Risk bypassed or coupled to strategy | Risk sits **between intent and broker**; fail-closed; all decisions are events |
| Margin & liquidation | IM/MM, utilization, warnings, thresholds, full liquidation *process* (forced close + costs), not a price conditional | Liquidation as a toy flag | Liquidation = a multi-step stateful process producing forced orders through the normal pipeline |

### Cluster 3 — STRATEGY

Sub-problems: Strategy Framework · SDK · DSL/IR · Genome.

| Concern | Requirements | Dominant risk | Design question |
|---|---|---|---|
| SDK | `on_start/on_market_data/on_order_update/on_fill/on_timer/on_stop`; same strategy runs in Backtest/Replay/Paper/Live | Code drift between modes | **One engine, many adapters**: only the data source and order router change |
| Strategy isolation | Strategies may only emit **Order Intents**; never touch cash/positions/balance/PnL | Direct state mutation | The SDK context exposes read-only views + `submit_order_intent`; enforced by the type system |
| DSL / IR | Intermediate representation: logic, arithmetic, indicators, thresholds, rolling, time, position state, market state, volatility, liquidity, order-flow conditions | Un-evolvable code strategies | Strategies have a **dual representation**: (a) SDK code for humans, (b) **genome** (data AST) for evolution; both compile to the same IR execution form |
| Genome | Logic + indicators + parameters + entry/exit + sizing + risk + execution policy; content hash | Duplicate individuals | Canonical-JSON → sha256 → genome identity; dedupe at registration |

### Cluster 4 — EVOLUTION

Sub-problems: Evolution Engine · Population · Lineage · Strategy Cemetery · Portfolio Evolution ·
Execution Evolution · Co-Evolution · Tournaments.

| Concern | Requirements | Dominant risk | Design question |
|---|---|---|---|
| Engine | Mutation (parameter, subtree, structural, insertion, deletion, pruning), crossover, novelty, niching, speciation, diversity pressure, Pareto + survival selection | Overfitting to training window | Multi-objective Pareto selection + novelty search + WFA/OOS gates before "strength" claims |
| Population | Per generation: population, survivors, extinct, new, fitness distribution, diversity, novelty, complexity; checkpointing | Silent state loss on crash | Generation = **atomic unit** with full checkpoint (population + RNG states + archive) |
| Lineage | Parents, mutation, crossover, generation, genome hash, experiments, fitness, death, descendants; evolution tree | Lost provenance | Lineage DAG in DB; every individual links to its genome hash and experiment results |
| Cemetery | Failed strategies are never deleted: death reason, max DD, worst regime, execution failure, sensitivity, overfitting evidence, cost/latency sensitivity | Repeating the same mistakes | Death is a **classified, recorded, queryable** state; cemetery feeds resurrection |
| Portfolio evolution | Portfolio is a genome: strategy weights, cash weight, risk limits, selection | Portfolio hand-tuned forever | Allocator = evolvable genome evaluated by the same fitness machinery |
| Execution evolution | Genome chooses: market/limit/post-only/IOC/split/passive/aggressive/adaptive | Execution ignored in research | Execution policy is part of the genome and of the execution pipeline |
| Tournaments | Modes: normal, volatile, crash, low liquidity, wide spread, high latency, cost shock; plus **shared capital**: 100+ strategies, ONE $1,000 portfolio, capital allocation, risk control, correlation penalties | Single-regime winners | Tournament = experiment template over scenario presets + allocator genome |
| Co-evolution | Traders vs market makers vs liquidity providers vs adversaries; **optional**; must never affect the historical deterministic engine | Historical results contaminated | Hard guard: co-evolution config is **rejected** when the market adapter is historical; synthetic exchange only |

### Cluster 5 — RESEARCH LAB

Sub-problems: Research Lab · Robustness · Monte Carlo · Counterfactual · Sensitivity · Regime ·
Capacity.

| Concern | Requirements | Dominant risk | Design question |
|---|---|---|---|
| Robustness | Perturb: parameters, costs, spread, latency, slippage, liquidity, start date, regime | Fragile "winners" | Robustness = batch of **counterfactual experiments** (same spec, perturbed knobs) |
| Monte Carlo | Reshuffled trades, execution randomness, slippage/latency variation, random fills; distributions | Single-path illusion | Trade-level resampling over recorded fills (deterministic seed) |
| Counterfactual | Change capital/fees/spread/slippage/latency/liquidity/leverage/execution model → rerun same experiment | Unreproducible "what-if" | Experiment spec is a **hashable immutable object**; counterfactual = new spec with `parent_id` → new EVL id |
| Sensitivity | Maps: performance vs capital/latency/fees/slippage/liquidity | Blind spots | Grid/Sobol sweeps over spec knobs → surfaces rendered in UI |
| Regime | Regimes from **observable** data only; no causality claims without evidence; per-regime performance | Leaky regime labels | Regime detector = causal filters (rolling stats at time t only); regime series is a versioned dataset artifact |
| Capacity | Test $1K → $1M; show return degradation, slippage, impact, liquidity consumption | Scale fantasy | Capacity = scaled-capital reruns through the **same** impact model; degradation curve is a first-class result |
| Walk-forward | Rolling/expanding, configurable train/validation/OOS/step | In-sample worship | WFA = scheduled window experiments with strict data slicing; OOS only seen once |

### Cluster 6 — PRODUCT & INTERFACES

Sub-problems: Visualization · Frontend · Backend · CLI · API · Reports.

| Concern | Requirements | Dominant risk | Design question |
|---|---|---|---|
| Frontend | Professional quant-research UI (not a shallow dashboard): Dashboard, Portfolio, Strategy Lab, Evolution Lab (most important screen), Population Map, Evolution Tree, Genome View/Diff, Alpha Cemetery, Tournaments, Market Replay, Order Book, Trade Autopsy, Portfolio Autopsy, Experiment page, Reports, Live/Paper; dark-first design tokens; responsive desktop/tablet; keyboard-friendly | UI showing false precision; polling storms | ECharts + Lightweight Charts; SSE for progress, WS for replay; server-rendered numbers with declared precision; number formatting rules |
| Backend | FastAPI + Pydantic + SQLAlchemy + PostgreSQL (+ Redis when needed) — **after comparing alternatives**; OpenAPI-documented REST | Framework lock-in without evidence | Comparison done in ARCHITECTURE_PROPOSAL §18 (stack confirmed on merit, not habit) |
| CLI | `evoltrade data validate / backtest / evolve / tournament run / replay / report / paper start` | Research trapped behind UI | CLI and API are **peers**: same service layer underneath both |
| API | Logical endpoints for strategies/experiments/backtests/evolution/tournaments/portfolios/trades/replay | Ad-hoc surface | Resource-oriented design around immutable experiments and versioned strategies |
| Reports | HTML/JSON/CSV/Markdown (+PDF if sensible), exportable | Unreproducible reports | Report = **pure function of (EVL id, registry)**; the same id always yields the same report |
| Live/Paper | Connection state, market state, portfolio, orders, fills, latency, PnL, risk, kill switches; **Live disabled by default** | Accidental live trading | Live is a separate, explicitly-enabled, separately-audited module; default = disabled |

### Cluster 7 — PLATFORM & DATA

Sub-problems: Data Management · Deployment · Testing · Security.

| Concern | Requirements | Dominant risk | Design question |
|---|---|---|---|
| Data layer | Free public data, exchange APIs, user-provided datasets, local datasets, future provider plugins; versioning (source, version, symbol, timeframe, timezone, transformation history, quality); quality checks (duplicates, gaps, invalid OHLC, bad timestamps, bad volume, suspicious jumps) | Assuming all history is free; silent data corruption | Provider **plugins** + dataset **versioning** + ingestion **quality report** stored with the dataset |
| Deployment | Single machine + workers first; interfaces allowing future scale; no Kubernetes without real need | Premature platform complexity | Stateless workers + PG job table now; Celery/Valkey/Ray behind interfaces later |
| Testing | Full pyramid: unit, integration, regression, property-based, deterministic, accounting, broker, matching, replay, evolution, API, frontend, e2e, performance | Bias and accounting bugs ship silently | Property-based **invariants** (no phantom money, no double fill, fill ≤ qty, no double fee, position/ledger reconciliation, deterministic replay) as first-class suites |
| Performance benchmarks | events/sec, orders/sec, fills/sec (and: backtests/worker, memory, API p95) | Unknown cost per evolution generation | Benchmark suite pinned in CI; numbers recorded per release |
| Security | Secrets via env, never log keys, read-only default, live disabled, explicit enablement, kill switch, audit log | Credential leak; tampered history | Append-only **hash-chained audit log**; strategy code treated as untrusted (sandboxed workers) |

## 3. Cross-cutting concerns (bind every cluster)

1. **Determinism & reproducibility** — same dataset + strategy + engine + broker + seed ⇒ same
   result, bit-for-bit for money (Decimal) and event log, within declared tolerance for float
   quantities. This is a *global invariant*, not a feature.
2. **Auditability** — every state transition is an event; every metric is a function of events;
   every experiment is immutable and content-addressed.
3. **Anti-leakage** — the system must make lookahead *hard to express* (point-in-time views) and
   *easy to detect* (dedicated test suite).
4. **Accounting truth** — the ledger is the only place money exists. All views (UI, metrics) are
   derived and reconciled against it.
5. **Cost realism** — fees, funding, slippage, latency, and impact are never optional garnish;
   every result records which models were used.
6. **Declared assumptions** — every synthetic element (book reconstruction, queue position,
   regime labels, synthetic exchange) is stamped into the result metadata.
7. **Free core** — no paid API/SaaS/AI in the core; user-provided and free public data only by
   default; provider plugins for everything else.
8. **No AI/LLM in the core** — classical, inspectable, deterministic computation. (Optional
   research-only modules outside the core may explore ML later, and even then only as separate,
   clearly-labeled packages.)

## 4. Assumptions challenged (the described solution is not the final answer)

| # | Common assumption | Challenge | EVOLTRADE position |
|---|---|---|---|
| A1 | "A strategy is a Python class" | Evolvable units must be **data** (genome), not code, to be mutated, hashed, deduped, serialized, and diffed at population scale | **Dual representation**: SDK code for humans + genome (AST) for evolution; both compile to one IR execution form. Code strategies can be *captured* into genomes (parameter extraction) to enter evolution |
| A2 | "Backtest, replay, paper, live are four systems" | Four systems ⇒ four bug surfaces and divergent behavior | **One engine, many adapters**: historical source, replay source, synthetic exchange, (future) live adapter. Same scheduler, same broker, same ledger |
| A3 | "Candle touched price ⇒ fill" | Fills depend on book depth, queue position, latency, and impact | Tiered **matching models** (T2 real L2 / T1 L1+trades / T0 declared synthetic); candle-touch is a flagged, non-default, "unreliable" model only |
| A4 | "Fitness = profit" | Profit-only fitness → overfit, fragile, convergent populations | **Multi-objective Pareto** fitness (risk-adjusted, stability, OOS, turnover, capacity, complexity, novelty, correlation) + novelty search + diversity pressure |
| A5 | "Buy the best existing backtester" | Every candidate is GPL/AGPL/frozen/common-clause or US-equity-centric (see OSS survey) | **Build the thin core** (engine + broker + ledger are the differentiators); **borrow architectures** from NautilusTrader/LEAN/Hummingbot; reject most incumbents for licensing or fit |
| A6 | "PostgreSQL for everything" | Tick/event volumes don't belong in row-store hot paths | **PostgreSQL** (metadata, lineage, registry, audit) + **Parquet/Arrow** (events, ticks, results) + **DuckDB** (analytical queries over Parquet) |
| A7 | "Microservices + Kafka from day one" | Ops burden and non-determinism before there is scale | **Modular monolith + worker pool** (Architecture C), with interfaces that make distribution a later swap, not a rewrite |
| A8 | "The UI polls for results" | Polling is wasteful and laggy for long evolutions | **SSE** for progress/state streams, **WebSocket** for replay sessions and (future) live order control |
| A9 | "Niche labels are fixed categories" | Fixed labels force the population into arbitrary buckets | **Dynamic speciation**: cluster behavior descriptors per generation; species/niches are *computed*, re-forming as needed |
| A10 | "Regime = anything we can label" | Ex-post labels leak future information into research | **Causal-only regime detector** (rolling, at-time-t features); per-regime performance reported post-hoc, never fed back as input during the run |
| A11 | "Redis is free" | Redis ≥ 7.4 is SSPL/RSALv2 (source-available, not OSI OSS) | **Valkey** (BSD-3, Linux Foundation) when a broker/cache is needed — and no broker at all in Phase 1 |
| A12 | "Live trading is just another mode" | Live adds credentials, latency reality, and catastrophic risk | Live is a **separate module**, disabled by default, explicitly enabled, with its own kill switches and audit; paper mode is the default "realistic" mode |
| A13 | "More indicators = better strategies" | Complexity must be paid for | **Complexity penalty** as a fitness objective (tree depth, node count, feature count, parameter count) + parsimony reporting |
| A14 | "One RNG, one seed" | Shared RNG streams couple components and break partial reproducibility | **Derived seeds**: master seed → independent streams (market/synthetic, execution, evolution) via a stable KDF, each stream state checkpointable |

## 5. Non-goals (v1)

- Real live trading (module exists as a disabled stub; enablement is a later, separate decision).
- Multi-tenant SaaS, billing, SSO (single-organization deployment with local auth + API keys).
- Mobile-first UI (desktop/tablet quant UI; phones get read-only degradation).
- Options/futures derivatives pricing (perpetual futures funding model supported for crypto;
  other derivatives later).
- Kubernetes, multi-region, GPU clusters (interfaces reserved, deployment = Docker Compose).
- ML/LLM anywhere in the deterministic core (explicitly out by policy; optional research
  side-packages may exist later, clearly separated).

## 6. Success criteria for Phase 0 (this phase)

1. Problem decomposed and assumptions challenged (this document).
2. Ecosystem surveyed with **verified** licenses and activity (OSS_SURVEY + THIRD_PARTY).
3. ≥3 architectures compared on 9 axes, one chosen and justified (proposal §6).
4. Failure model complete with prevention-by-design and tests named (FAILURE_MODEL).
5. Domain model with all required objects and relations (DOMAIN_MODEL).
6. Full ARCHITECTURE_PROPOSAL covering all mandated sections + requirements traceability
   for all 87 spec items.
7. Roadmap with exit criteria per phase; open decisions listed for stakeholder approval.
