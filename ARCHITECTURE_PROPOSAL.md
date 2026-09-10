# EVOLTRADE — ARCHITECTURE PROPOSAL

**Project:** EVOLTRADE — Evolutionary Trading Laboratory
**Phase:** 0 — Discovery & Architectural Research
**Date:** 2026-09-10 · **Status:** draft for stakeholder approval
**Companion docs:** [THIRD_PARTY.md](THIRD_PARTY.md) · [FAILURE_MODEL.md](FAILURE_MODEL.md) · [DOMAIN_MODEL.md](DOMAIN_MODEL.md) · [docs/PROBLEM_ANALYSIS.md](docs/PROBLEM_ANALYSIS.md) · [docs/OSS_SURVEY.md](docs/OSS_SURVEY.md)

> **Nothing in this proposal is implemented yet.** This is the design contract. Code starts only
> after this document is approved and the open decisions (§27) are resolved.

---

## 1. Executive summary

EVOLTRADE is a professional platform for trading simulation, experimentation, and evolutionary
research. Its defining engineering property is that **every number is traceable to an event, every
experiment is immutable and reproducible, and every assumption is declared**.

Key decisions (details in the referenced sections):

1. **Architecture C — Modular monolith + event-sourced simulation core + stateless worker pool**
   (§6). Not a backtester wrapper, not microservices. One deterministic engine, many adapters.
2. **One engine, many adapters** (§7): the identical scheduler/broker/ledger runs historical
   replay, replay-UI, synthetic exchanges, and (future, disabled) live. No parallel code paths.
3. **Strategies are data** (§12): dual representation — a Python SDK for humans and a **genome**
   (causal AST) for evolution. Both compile to one IR execution form; the genome is the evolvable
   unit (hashable, mutable, diffable).
4. **The ledger is the truth** (§14): double-entry, `Decimal`-only money, a single balanced
   journal per financial operation, reconciliation at checkpoints. The default account opens with
   exactly **$1,000.00** as a real opening journal entry. No money setter exists anywhere.
5. **Strict order pipeline** (§7, §15):
   `Strategy → Order Intent → Risk → Broker → Matching → Fill → Accounting → Portfolio`.
   Strategies can only emit intents. Risk can reject. The broker validates precision/TIF/minima.
   Matching consumes real or *declared-synthetic* book depth — never "candle touched price".
6. **Evolution is a first-class axis** (§13): mutation/crossover/structural operators, Pareto
   multi-objective selection, novelty search with an archive, dynamic speciation, diversity
   pressure with a 0.95 convergence threshold, complexity penalty, lineage DAG, Alpha Cemetery,
   checkpoint/resume, portfolio-evolution and execution-evolution genomes, optional co-evolution
   (synthetic-only, hard-guarded).
7. **Free core, no AI** (§24): permissive-licensed dependencies only (verified 2026-09-10, see
   THIRD_PARTY.md); Valkey instead of Redis (license change); no LLM anywhere in the core.
8. **Stack** (§17, §18): Python 3.12 core; PostgreSQL (metadata) + Parquet/Arrow (events/ticks) +
   DuckDB (analytics); FastAPI + Pydantic + SSE/WS; Next.js + TypeScript + Tailwind + ECharts +
   Lightweight Charts; Typer/Rich CLI; Docker Compose deployment.

---

## 2. Vision

A **laboratory** in the strict sense: a place where trading hypotheses are *experiments* —
falsifiable, reproducible, auditable, and subject to the controls (costs, latency, impact,
regimes, OOS) that reality imposes. Unlike a backtester (one strategy, one window, one number)
or a bot (one strategy, live only), EVOLTRADE runs **populations of evolvable strategies against
deterministic market simulations**, with a real $1,000 accounting core, and answers questions
like:

- *Does this strategy survive costs, latency, and other regimes — or is it a training-window artifact?*
- *How does performance degrade as capital grows from $1K to $1M?*
- *What would have happened with 2× fees or a passive (post-only) execution policy?*
- *Which lineages are structurally different, and which died — and why?*
- *Can a portfolio allocator evolve that beats any single strategy under one shared $1,000?*

The laboratory must be **honest by construction**: it must make it *hard to express* a lookahead,
*impossible to produce* phantom money, and *obvious* when a result rests on a synthetic
assumption.

## 3. Core principles

| # | Principle | Consequence in the design |
|---|---|---|
| P1 | **Determinism & reproducibility first** | Event-sourced core, total event order, seeded RNG streams, content-hashed specs/datasets, golden experiments in CI. Same inputs ⇒ identical event-log hash (§19, §25) |
| P2 | **Money is sacred** | Ledger = single source of truth; Decimal-only; balanced journals; reconciliation; no setters. The 8 invariants of FAILURE_MODEL §ledger |
| P3 | **Strategies never touch money** | SDK context exposes read-only views + `submit_order_intent` only; enforced by types + static analysis rule |
| P4 | **One engine, many adapters** | Historical / replay / synthetic / (live) are market *adapters*; scheduler, broker, matching, ledger, risk are shared, single implementations |
| P5 | **Strategies are data** | Genome (canonical JSON AST) is the evolvable unit; SDK code is an authoring surface; both compile to one IR |
| P6 | **Declared assumptions** | Data tier (T2/T1/T0), queue model, latency model, slippage/impact models, regime detector are stamps on every spec and every report |
| P7 | **Free core** | Permissive licenses only in core; no paid API/SaaS in the core path; user-provided data and free public data by default (THIRD_PARTY.md) |
| P8 | **No AI/LLM in the core** | Classical, inspectable, deterministic computation; optional research side-packages later, clearly separated and non-core |
| P9 | **Auditability** | Every state transition is an event; every metric = f(events); experiments immutable; hash-chained audit log; reports = pure function of an EVL id |
| P10 | **Fail closed, fail loud** | Risk rejects on error; data quality fails closed; integrity violation ⇒ run INVALID + event, never silent; no "degraded" metric without a visible flag |
| P11 | **Replaceable periphery** | Everything environment-shaped is a plugin with a versioned interface (data, fees, slippage, latency, impact, queue, matching tier, fitness, operators, allocator, exchange) |
| P12 | **Boring deployment, real interfaces** | Single machine + worker pool first; distribution is a later swap behind `WorkerPool`/`JobQueue` interfaces, not a rewrite |

## 4. Scope & non-goals (v1)

See [PROBLEM_ANALYSIS §5](docs/PROBLEM_ANALYSIS.md#5-non-goals-v1). In short: no real live
trading (disabled module), no K8s, no multi-tenant SaaS, no mobile-first, no ML in the core.

## 5. Problem analysis (summary)

Full decomposition: [PROBLEM_ANALYSIS.md](docs/PROBLEM_ANALYSIS.md) — 7 clusters (Simulation &
Market, Trading Core, Strategy, Evolution, Research Lab, Product & Interfaces, Platform & Data),
each with requirements, risks, and design questions; plus 14 challenged assumptions
(e.g. "strategy = code", "backtest/replay/paper/live = 4 systems", "Redis is free", "fitness =
profit"). The architecture below is the answer to those questions.

## 6. Architecture options (≥3, compared, one chosen)

### Option A — Monolithic in-process ("one FastAPI process does everything")

Everything (engine + API + workers) in one Python process; simulations run in threads or
blocking calls from request handlers; state in memory + PostgreSQL.

- **Correctness:** high (one code path)
- **Performance:** poor at scale — GIL serializes evolution; long simulations block/timeout API; no horizontal scale
- **Complexity:** low initially
- **Extensibility:** medium (plugins work, but UI latency couples to simulation cost)
- **Maintainability:** medium (module boundaries blur under one process)
- **Determinism:** high
- **Scalability:** none beyond one big machine; CPU-bound evolution cannot use >1 core effectively
- **Development effort:** lowest
- **Dependency risk:** low
- **Verdict:** fails the core use case — 5000-individual × 100-generation evolution is
  CPU-bound parallel work; a UI-coupled monolith cannot do it.

### Option B — Event-driven microservices (many services + message bus)

Separate services: market-data-svc, engine-svc (per simulation), broker-svc, portfolio-svc,
evolution-svc, api-svc, ui; Kafka/Redis Streams between them.

- **Correctness:** medium — state split across services; money lives in multiple services
- **Performance:** high ceiling, high floor cost (network hops in the hot loop)
- **Complexity:** very high (deployment, schema evolution, distributed transactions)
- **Extensibility:** high
- **Maintainability:** low for a small team (ops burden dominates)
- **Determinism:** **hard** — cross-service clocks and async delivery fight P1; proving
  bit-identical replays across a network is a research problem
- **Scalability:** high
- **Development effort:** highest
- **Dependency risk:** high (broker infra in the critical path)
- **Verdict:** premature. Distribution is a *scaling* concern; determinism is a *correctness*
  concern. Putting the message bus inside the deterministic core is backwards. Keep the
  *interfaces* that make B reachable later (stateless workers, job queue, event contract).

### Option C — Modular monolith + event-sourced simulation core + stateless worker pool *(CHOSEN)*

One deployable application (FastAPI) + shared core libraries, **and** worker processes that
execute experiments. The simulation core is an in-process deterministic event machine (one
process per experiment run ⇒ no intra-experiment parallelism ⇒ determinism by construction).
Workers are stateless: they pull jobs (PG job table + advisory locks in v1), execute, and write
artifacts (Parquet + hashes). The API exposes REST + SSE/WS. PostgreSQL holds metadata, the
registry, and queryable mirrors; Parquet/Arrow hold events/ticks/results (system of record);
DuckDB queries them.

- **Correctness:** high — single-process engine, event sourcing, ledger invariants, content addressing
- **Performance:** high for the real workload — embarrassingly parallel *across* individuals/runs (process pool, no GIL limit), zero-copy Arrow, DuckDB analytics; hot loop stays in-process
- **Complexity:** medium — clear module boundaries enforced by imports (core never imports services)
- **Extensibility:** high — plugins per P11; `WorkerPool`/`JobQueue` interfaces make Celery/Valkey (Phase 2) and Ray (Phase 3) drop-in
- **Maintainability:** high for a small team — one deployment unit to think about, Docker Compose
- **Determinism:** **highest of the three** — deterministic by construction inside a run; cross-run via seeds + hashes
- **Scalability:** good path: more workers → same job table → Celery/Valkey → Ray; UI/API stateless behind LB
- **Development effort:** medium
- **Dependency risk:** low (PG + files; Valkey only from Phase 2)

### Comparison matrix

| Axis (weight) | A: Monolith | B: Microservices | **C: Chosen** |
|---|---|---|---|
| Correctness (★★★) | High | Medium | **High** |
| Performance (★★★) | Low at scale | High ceiling / high floor | **High for real workload** |
| Complexity (★★) | Low | Very high | **Medium** |
| Extensibility (★★) | Medium | High | **High** |
| Maintainability (★★) | Medium | Low | **High** |
| Determinism (★★★) | High | **Hard** | **By construction** |
| Scalability (★★) | None | High | **Phased path** |
| Dev effort (★) | Lowest | Highest | **Medium** |
| Dependency risk (★) | Low | High | **Low** |

**Why C wins:** the project's hardest requirements — determinism, auditable money, reproducible
experiments — are *process-local* properties. C makes them structural (one process per run),
while the part that actually scales (population evolution = many independent runs) is exactly
the embarrassingly parallel part C parallelizes for free. B buys scalability we don't need yet,
at the cost of the property we cannot afford to lose. A cannot deliver the core use case.

**Sub-decision (recorded):** the simulation core is **pure Python 3.12 in Phase 1–3** with a
stable internal `SimulationCore` interface. If benchmarks (§23) show the Python hot loop
binding the evolution throughput budget, Phase 4 adds an **optional Rust core (PyO3)** behind
that interface — same event contract, same determinism rules, golden tests must pass unchanged.
We do *not* start in Rust: the differentiators are the ledger, the evolution machinery, and the
registry — all better developed first in Python, with the hot loop isolated for later
replacement (numba is the interim lever).

## 7. System architecture (Option C, detailed)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                INTERFACES                                        │
│  Web UI (Next.js/TS)          CLI (Typer/Rich/Textual)         REST + OpenAPI    │
│  ECharts + LW-Charts          evoltrade data|backtest|evolve   SSE (progress)    │
│  SSE client, WS client        |tournament|replay|report|paper   WS (replay/live) │
└──────────────┬───────────────────────┬──────────────────────────────┬────────────┘
               │  HTTP / SSE / WS      │  same service layer          │
┌──────────────┴───────────────────────┴──────────────────────────────┴────────────┐
│                         SERVICES LAYER  (FastAPI app, stateless)                 │
│  Strategy Svc │ Experiment Svc │ Evolution Coordinator │ Replay Svc              │
│  Research Svc (robustness·MC·counterfactual·sensitivity·regime·capacity·WFA)     │
│  Dataset Svc  │ Report Svc     │ Live Svc (DISABLED by default) │ Audit/Admin    │
│  ───────────────────────────────────────────────────────────────────────────────  │
│  JOB SYSTEM: PG jobs table + advisory locks · worker pool (processes)            │
│  [Phase 2: Celery + Valkey]  [Phase 3: Ray farm]   — behind WorkerPool/JobQueue  │
└──────────────┬───────────────────────────────────────────────────────────────────┘
               │ in-process (one engine instance per RUN)
┌──────────────┴───────────────────────────────────────────────────────────────────┐
│                         RESEARCH DOMAIN (pure, deterministic Python)             │
│  Fitness/Selection (Pareto) │ Novelty Archive │ Speciation │ Diversity Monitor   │
│  Complexity Penalty │ WFA Planner │ Robustness │ MonteCarlo │ Counterfactual     │
│  Sensitivity │ Regime (causal) │ Capacity │ Tournaments │ Allocator (port. evo)  │
│  Execution Evolution │ Co-Evolution module (synthetic-only, guarded)             │
├──────────────────────────────────────────────────────────────────────────────────┤
│                         SIMULATION CORE  (the heart — P1/P2/P3 live here)        │
│  Event Scheduler (total order (sim_ts, seq)) │ SimulationClock │ RNG KDF (seeded)│
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ MARKET ADAPTERS│  │ VIRTUAL BROKER │  │ MATCHING ENGINE  │  │ ACCOUNTING    │ │
│  │ historical     │→ │ rules: TIF,    │→ │ OrderBook        │→ │ Ledger (Dec.) │ │
│  │ replay         │  │ precision, min │  │ queue-model plug │  │ + Portfolio   │ │
│  │ synthetic      │  │ notional, TIF  │  │ + latency layers │  │ + RISK ENGINE │ │
│  │ (co-ev: guarded)│ │ reject reasons │  │ + slippage/impact│  │ (independent) │ │
│  └────────────────┘  └────────────────┘  │ + fee/funding    │  └───────────────┘ │
│                                          └──────────────────┘                    │
│  Event Log writer (Parquet segments + checksums) · Checkpoints · Invariant checks│
├──────────────────────────────────────────────────────────────────────────────────┤
│                                DATA LAYER                                        │
│  Providers (plugins): ccxt · yfinance · user CSV/Parquet · exchange APIs (keys)  │
│  Ingest → Validate (pandera + stats) → Version (content hash) → Quality report   │
│  Storage: PostgreSQL (metadata/registry/audit/mirrors) + Parquet/Arrow (events,  │
│            ticks, results — system of record) + DuckDB (analytical queries)      │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Components (responsibility + key invariant)

| Component | Responsibility | Key invariant / note |
|---|---|---|
| **Event Scheduler** | Total-ordered event dispatch; latency = scheduled future events; deterministic tie-break | Order `(sim_ts, seq)`; no wall clock; one process per run |
| **SimulationClock** | Advances only on events; exposes sim time; watermark for anti-leakage | Time is data, never `time.time()` |
| **RNG KDF** | Master seed → independent streams (market/synthetic, execution, evolution); per-stream state for checkpoints | All stochastic draws go through a named stream |
| **Market Adapters** | historical (Parquet), replay (event log), synthetic (seeded exchange) | Same interface; co-ev config rejected on historical (guard) |
| **Virtual Broker** | Accept/reject/hold orders; TIF semantics; precision/tick/step/mins; order state machine | Structured reject reason codes; fail-closed |
| **Matching Engine + OrderBook** | Fill determination from book state per tier (T2/T1/T0); depth consumption; partial fills | Fill = book consumption, never candle-touch; per-order Σfills ≤ qty |
| **Queue Model (plugin)** | Queue position + consumption assumptions | Named + stamped; exact-FIFO on trade data, declared otherwise |
| **Latency Layers** | 6 independent layers; deterministic (fixed) or stochastic (seeded dist) | Per-trade latency budget recorded (autopsy) |
| **Slippage / Impact plugins** | Price adjustment models | Mandatory in pipeline; recorded per fill |
| **Fee/Funding models** | One fee journal per fill; funding on position × rate at timestamps | Fee total == independent recomputation |
| **Accounting Ledger** | Double-entry, Decimal, balanced journals, reconciliation | The only place money exists |
| **Risk Engine** | Pre-trade gates, monitors, circuit breaker, kill switches | Independent of strategy; fail-closed; every decision evented |
| **Portfolio Views** | Equity/drawdown/exposure/margin/attribution over ledger + positions | Reconciled at checkpoints; causal drawdown |
| **Strategy Runtime** | Runs compiled strategies (SDK or genome) against the event stream | Read-only views + intents only |
| **Research Domain** | All §5-research functions; plans batches of Experiments | Outputs are Experiments (immutable), not ad-hoc numbers |
| **Experiment Registry** | EVL ids, immutable specs/results, counterfactual chains | No UPDATE/DELETE; content-addressed |
| **Replay Service** | Streams event logs to UI with pacing/jump; self-heal re-broadcast | No event beyond cursor; state hash checkpoints |
| **Report Service** | Pure function of (EVL id, registry) → HTML/JSON/CSV/MD(/PDF) | Same id ⇒ same bytes (modulo generator version stamp) |
| **Job System** | Queue, assign, progress, retry, cancel, checkpoint/resume | Stateless workers; advisory locks (v1) |
| **Audit Service** | Hash-chained append-only log | Chain verifiable; no gaps |

## 8. Data flow

### 8.1 Ingestion

```
provider plugin (ccxt | yfinance | user file | exchange API)
   → raw fetch (declared params) → raw Parquet (immutable, hash)
   → VALIDATE: schema (pandera) + statistics (gaps, jumps, OHLC validity, ts monotonicity, volume)
   → quality report JSON (stored with version)
   → DATASET_VERSION READY (content hash; symbols, range, timeframe, tz, tier, transform history)
   → optional: precompute causal indicators → indicators cache (part of version artifact)
```
Rejected data is quarantined (REJECTED status, reviewable override kept as an audited flag).

### 8.2 Experiment execution

```
spec (canonical JSON) ── spec_hash
   → validate (dataset READY + hashes, engine version, seeds)
   → job QUEUED → worker picks up (re-verify input hashes)
   → per-run: load market adapter window + dataset versions
              compile strategy (genome → IR, cached by genome_hash)
              instantiate engine (scheduler, clock, RNG streams, broker, risk, ledger)
   → RUN: events flow (§9) → EventLog segments (Parquet + checksums)
              checkpoints (portfolio, positions, ledger mirror, book state)
   → finalize: final reconciliation (all 8 invariants) → metrics (registry-defined)
              → results artifacts (curves, trades, attribution, assumptions)
   → registry: COMPLETED + result_hash   (or FAILED / INVALID + reason)
```

### 8.3 Research flow (counterfactuals, robustness, MC, sensitivity, capacity, WFA, tournaments)

All are **spec transformations**: take an Experiment spec, mutate only the declared knobs
(fees ×2, latency +50%, capital ×5, execution model swap, window shift, …), create child
Experiments (`parent_id`), batch them as a job group, aggregate into a report bound to the
parent. The original is never modified.

### 8.4 Replay flow

```
Experiment event log (Parquet + jump index: trade→offset, drawdown→offset)
   → ReplaySession (WS) → paced batches at speed s ∈ {1,2,10,50,100}x
   → UI reducer (same schema) → charts/state
   → commands: play/pause/step event/step trade/jump trade/jump drawdown/seek
   → periodic state-hash check vs server (self-heal by re-broadcast)
```

## 9. Event flow

### 9.1 Event taxonomy

| Group | Events |
|---|---|
| Market | `TICK` · `QUOTE` · `TRADE` · `BAR_CLOSED` · `BOOK_SNAPSHOT` · `BOOK_UPDATE` · `BOOK_DEGRADED` · `BOOK_RESYNC` · `SYNTHETIC_SEED` |
| Time | `TIMER` · `SCHEDULED_DELAY` (latency) · `SESSION_START` · `SESSION_END` |
| Strategy | `SIGNAL` (audit-only: what fired, why) · `ORDER_INTENT` |
| Order lifecycle | `ORDER_SUBMITTED` · `ORDER_ACCEPTED` · `ORDER_REJECTED` · `ORDER_STOP_TRIGGERED` · `ORDER_PARTIALLY_FILLED` · `ORDER_FILLED` · `ORDER_CANCELLED` · `ORDER_EXPIRED` |
| Execution | `FILL` · `FEE` · `FUNDING_ACCRUAL` · `EXECUTION_RECORD` (policy → orders trace) |
| Position/Financial | `POSITION_OPENED` · `POSITION_UPDATED` · `POSITION_CLOSED` · `POSITION_LIQUIDATED` · `MARGIN_RESERVE` · `MARGIN_RELEASE` · `MARGIN_WARNING` · `LIQUIDATION_START` · `LIQUIDATION_COMPLETE` |
| Portfolio | `PORTFOLIO_SNAPSHOT` · `DRAWDOWN_EVENT` · `KILL_SWITCH_TRIPPED` · `KILL_SWITCH_RESET` |
| Risk | `RISK_DECISION` (accept/reject/kill + checks) · `CIRCUIT_BREAKER_TRIPPED` |
| System | `RUN_STARTED` · `RUN_COMPLETED` · `RUN_FAILED` · `CHECKPOINT` · `ENGINE_INTEGRITY_VIOLATION` · `ANTI_LEAKAGE_VIOLATION` |

### 9.2 Envelope & ordering

```
Event { event_id: ULID, experiment_id: EVL-…, run_id, sim_ts_ns: i64 (UTC),
        seq: i64, source: component_id, type: EventType, payload: msgspec struct }
```

- **Total order:** `(sim_ts_ns, seq)`; `seq` assigned by the scheduler in dispatch order —
  deterministic given the same event set. Ties on sim_ts are impossible by construction
  (scheduler assigns seq before any consumer sees the event).
- **Latency** = scheduling the downstream event at `sim_ts + delay` (`SCHEDULED_DELAY` markers
  carry the per-layer budget). Nothing "waits" on a wall clock.
- **No future event is dispatched before its sim_ts** (the scheduler is a priority queue over
  sim_ts). This is the mechanical backbone of anti-leakage (I-8): a consumer at sim time t
  has only ever seen events ≤ t.

### 9.3 Sequence: a BUY order (trade autopsy trace)

```
bar closed ──► strategy.on_market_data
                └─ (read-only views, watermark = t) ─► SIGNAL {rule=entry, features=…}
                └─► ORDER_INTENT {side=BUY, qty=⌊0.5×available/atmp⌋, policy=passive}
                      └─► RISK_DECISION {checks:[exposure ✔, daily-loss ✔, order-limit ✔] → ACCEPT}
                      └─► broker.validate {tick grid ✔, min notional ✔, TIF=GTC ✔} → ORDER_SUBMITTED
                      └─► ORDER_ACCEPTED
                      └─► [latency: network 8ms + broker 2ms + exchange 5ms → SCHEDULED_DELAY events]
                      └─► matching @ t+15ms: book tier T1, depth 0.42 @ bid+1 tick
                           queue_model=probabilistic(v0.3) → partial fill 0.30/0.50
                      └─► FILL {price, qty, latency_budget{…}, impact 1.2bps, slippage 0.8bps}
                      └─► FEE {fee_model=bps_v1, amount ₤} ─► journal (CASH→FEES)
                      └─► POSITION_UPDATED {qty 0.30, avg_cost} ─► journal (CASH→POSITION)
                      └─► ORDER_PARTIALLY_FILLED
                      └─► PORTFOLIO_SNAPSHOT {equity, available, exposure, …}
                      └─► strategy.on_order_update / on_fill (read-only + intents only)
```
**Trade Autopsy UI** = this exact chain, fetched by `order_id`/`fill_id` from the event log —
every latency layer, every check, every journal entry. There is no second story.

## 10. Domain model (summary)

Full model with mermaid diagrams, state machines, and cardinalities: [DOMAIN_MODEL.md](DOMAIN_MODEL.md).
Object groups: **Market** (Instrument, Tick/Quote/Trade, OrderBook) · **Execution** (Order,
Execution, Fill, Fee, FundingAccrual, RiskDecision, KillSwitchState) · **Financial** (Account,
Portfolio, Position, LedgerEntry, PortfolioSnapshot) · **Strategy** (Strategy, StrategyGenome,
ExecutionPolicy) · **Evolution** (Individual, Population, Generation, EvolutionRun, LineageEdge,
DeathRecord, NoveltyArchive, FitnessMetric, Tournament) · **Experiment** (DatasetVersion,
Experiment, Run, Result, EventLog, ReplaySession, WalkForwardPlan, studies, Regime, Scenario) ·
**Platform** (RiskPolicy, AuditEntry).

## 11. Database design

**Principle:** PostgreSQL = metadata, registry, audit, and *queryable mirrors*.
Parquet/Arrow = **system of record** for high-volume artifacts (events, ticks, trades, curves).
The PG mirror of high-volume tables is **rebuildable from Parquet** (it is an index, not the
truth) — corruption of PG is recoverable; corruption of Parquet is detected by checksums and is
an incident.

### 11.1 PostgreSQL tables (core)

| Table | Key columns | Notes |
|---|---|---|
| `users` / `api_keys` | id, email/handle, key_hash (argon2), scopes, created | local auth + scoped keys |
| `instruments` | id, symbol, asset_class, venue, tick_size ₤, step_size ₤, min_qty ₤, min_notional ₤, precision, margin_profile | registry of tradable things |
| `datasets` / `dataset_versions` | id, source, version, symbols[], range, timeframe, tz, tier, content_hash, quality_report jsonb, universe_mode, status | immutable after READY |
| `strategies` / `strategy_versions` | id, name, version, representation, genome_hash, state, source_ref | immutable once PUBLISHED |
| `genomes` | genome_hash (PK), canonical_json, size metrics (nodes/depth/params/features) | content-addressed |
| `individuals` | id, genome_hash, evolution_run_id, birth_gen, status, species_id, novelty, complexity, fitness jsonb | one row per individual |
| `lineage_edges` | parent_id, child_id, op_type, generation | the evolution DAG |
| `death_records` | individual_id, reason, max_dd ₤, worst_regime, sensitivities jsonb, overfit_evidence jsonb, age | the cemetery (append-only) |
| `novelty_archives` | run_id, entry (descriptor vector, genome_hash, gen) | per run |
| `populations` / `generations` | run_id, index, counts, diversity jsonb, checkpoint_ref | checkpoint manifest |
| `evolution_runs` | id, experiment_id, config jsonb, status, progress jsonb | coordinator state |
| `tournaments` / `tournament_entries` | id, mode, capital ₤, allocator_genome_hash / individual_id, allocation ₤, rank, robustness_passed | shared-capital mode |
| `scenarios` | id, name, preset jsonb | named mode presets |
| `experiments` | **evl_id PK (EVL-YYYY-XXXXXXXX)**, spec jsonb, spec_hash, status, parent_id, result_hash, engine_version, dataset_version_hash, created_by, ts | **IMMUTABLE** (trigger: no UPDATE/DELETE) |
| `runs` | id, experiment_id, role, worker_id, seed_stream, status, progress, resource_usage | worker bookkeeping |
| `results` | id, experiment_id, run_id, metrics jsonb, curves_ref, trades_ref, assumptions jsonb, hash | content-addressed refs |
| `regime_series` | id, dataset_version, detector, ref | derived artifact |
| `audit_entries` | id, actor, action, target, before_hash, after_hash, ts, prev_hash, entry_hash | hash chain |
| `jobs` | id, kind, experiment/run ref, status, worker_id, attempts, heartbeat, progress, ts×3 | v1 job queue |
| `kill_switches` | scope, state, rule, tripped_by, ts | |
| **Mirrors (rebuildable)**: `orders`, `fills`, `fees`, `positions`, `portfolio_snapshots`, `ledger_entries` | experiment_id partition key + natural keys | partitioned by experiment; refresh job rebuilds from Parquet; API reads here |

### 11.2 Parquet/Arrow layout (system of record)

```
datastore/
  datasets/{dataset_id}/{version}/
    raw/*.parquet            # immutable raw (per symbol/segment)
    quality.json             # quality report
    manifest.json            # per-file sha256, schema, counts
  indicators/{dataset_version_hash}/{indicator_key}.parquet   # causal, precomputed
  experiments/{evl}/
    spec.{hash}.json         # the spec, named by its hash
    events/seg-000001.parquet … + manifest.json (checksums) + index.json
                             # index.json: trade_id→offset, drawdown_events→offset
    results/metrics.json  curves.parquet  trades.parquet  attribution.parquet
    results/assumptions.json        # declared models & tiers (mandatory)
    checkpoints/gen-{n}.parquet     # evolution runs (population+RNG+archive)
```

### 11.3 ID scheme

- ULIDs (time-ordered) for all entities; `EVL-YYYY-XXXXXXXX` for experiments (PG sequence,
  year-scoped, allocated atomically at spec submission); genome identity = sha256.

## 12. Strategy model

### 12.1 Dual representation

| Surface | Form | Audience | Evolvable? |
|---|---|---|---|
| **SDK strategy** | Python class: `on_start/on_market_data/on_order_update/on_fill/on_timer/on_stop` | humans | indirectly (via *capture*) |
| **Genome strategy** | Canonical-JSON AST (logic trees + sizing + risk overrides + execution policy) | the evolution engine | **yes — it is the genome** |

Both compile to the **same IR execution form** and run in the **same runtime** in
Backtest / Replay / Paper / (future) Live — the mode changes only the market adapter and order
router (P4). **Capture**: a finished SDK strategy can be analyzed (its emitted signals are
recorded with feature attribution) and, where its logic is expressible in the IR, converted to a
genome (parameter extraction) to enter evolution; capture reports are stored with the strategy.

### 12.2 IR grammar (Strategy DSL)

```
genome       := { logic:{entry: expr, exit: expr, size?: expr, timing?: expr},
                  position_sizing: Sizing, risk_overrides: Risk, execution_policy: Exec }
expr         := expr AND expr | expr OR expr | NOT expr | comparison
comparison   := term OP term          # OP ∈ {>, <, >=, <=, ==, !=}
cross        := CROSS_ABOVE(a,b) | CROSS_BELOW(a,b)
term         := indicator | literal | PARAM(name) | TIME(...) | STATE(...) | ROLL(w, expr) | ARITH(expr,expr)
indicator    := SMA | EMA | RSI | ATR | BBANDS | OBV | VWAP | REALIZED_VOL | SPREAD
               | VOLUME_Z | RET_1 | REGIME_FLAG | …            # all causal, pre-windowed
TIME         := BAR_IDX | HOUR | MINUTE
STATE        := IN_POSITION | POS_PNL | PORTFOLIO_DRAWDOWN
ROLL(w, x)   := rolling statistic over the closed causal window [t-w+1 .. t]   # no centering exists
```

**Causality is grammatical**: no operator in the grammar can reference t+k. The IR validator
also enforces structural caps (max depth, max nodes, max params, max distinct features) →
feeds the complexity penalty and rejects runaway genomes (F5.7).

### 12.3 Compilation & execution

`genome_hash` → cached compile: (1) validate IR; (2) build **indicator precompute plan** —
indicators are dataset-level artifacts (cached under dataset version + param hash, so a
population sharing a dataset pays once); (3) emit a per-bar evaluation closure (pure Python;
numba-compiled variant behind the same interface if benchmarked faster); (4) wrap with sizing,
risk overrides, and execution policy → StrategyRuntime.
Per bar: `views(read-only) → signals → sizing → OrderIntents`. The runtime **cannot** write any
accounting state — it has no such API (P3, I-1).

## 13. Evolution model

### 13.1 Operators (plugins, all on the genome AST)

| Operator | Effect |
|---|---|
| parameter mutation | jitter PARAM values within declared ranges (Gaussian/uniform, seeded) |
| subtree mutation | replace a random subtree with a fresh causal expression (size-capped) |
| structural mutation | swap entry/exit subtrees; change comparison operator; rewire a node |
| insertion | insert a new condition (AND/OR) around an existing node |
| deletion | remove a redundant branch (simplification) |
| pruning | remove a terminal leaf + collapse |
| crossover | one/two-point subtree exchange between two parents |
| sizing/risk/exec mutation | parameterize the non-logic blocks (position sizing, risk overrides, **execution policy** — execution evolution, §15.6) |

All operators: (a) produce a valid IR (validator re-runs; invalid child ⇒ retry ≤ N ⇒ parent
clone), (b) are recorded as `ops[]` on the child (genome diff = added/removed/changed,
mutation/crossover — drives the Genome Diff UI), (c) draw from the `evo` RNG stream only.

### 13.2 Fitness (multi-objective, Pareto)

```
f(individual) = [ return_net↑, sharpe↑, sortino↑, max_drawdown↓,
                  oos_stability↑ = min(0, oos_return/is_return),
                  turnover↓, cost_drag↓, execution_sensitivity↓,
                  capacity↑, complexity↓, novelty↑, correlation↓ ]
```
- Selection: **fast non-dominated sort + crowding** (NSGA-II-style) over the configured subset;
  default includes risk, OOS, complexity, and novelty — profit alone is *not* the selection basis (F5.6).
- **Novelty-driven slots**: a configurable fraction (default 5%) of offspring slots are filled by
  top-novelty individuals regardless of fitness — search for *structurally and behaviorally*
  different strategies, not just fitter ones.
- **OOS/WFA gate**: an individual's "strength" (promotion to reports/tournaments) requires
  passing the Walk-Forward gate; IS-only excellence is recorded as overfitting evidence.

### 13.3 Novelty search & archive

- **Behavior descriptor** (normalized, from *recorded trade/signal events* — not from raw
  returns): entry rate by regime (k buckets), avg holding bars, buy/sell ratio, avg order
  notional, turnover, volatility sensitivity, spread sensitivity, drawdown profile (5 buckets),
  signal density.
- **Archive**: per-run list of (descriptor, genome_hash); capacity-capped with
  similarity-based eviction; `novelty(x) = mean distance to k nearest` (k=10 default).
- Duplicates (genome hash) never enter the population (F5.8); near-duplicates (novelty < ε) are
  recorded as `DUPLICATE` deaths.

### 13.4 Diversity pressure & convergence (the 95% rule)

Per generation the monitor computes: cluster ratio (largest cluster on descriptors),
effective population size `Hp = 1/Σp_i²`, novelty distribution. If **cluster ratio > 0.95**
(default, configurable) ⇒ `CONVERGENCE` event + automatic actions (configurable set):
1. mutation-rate boost (×2, geometric decay),
2. novelty slots raised (5% → 10%),
3. **resurrection**: sample dead individuals with high peak fitness (from the cemetery),
   re-mutate them into the next generation (`op=RESURRECTION`),
4. speciation pressure (tighter cluster threshold).
All actions are evented and visible in the Evolution Lab — the system *announces* when the
population is collapsing and what it did about it.

### 13.5 Niching & speciation (dynamic, not fixed)

Species are **computed each generation** by threshold agglomeration on behavior descriptors
(scipy hierarchy, seeded/tie-broken deterministically). Species ids exist only within the
generation; lineage stores (species_id, params) at the time. Per-species selection (fitness
sharing) keeps niches alive; no fixed taxonomy is ever assumed (A9).

### 13.6 Population lifecycle (one generation, atomic)

```
load (population, archive, RNG states)  →  evaluate unevaluated individuals (parallel Experiments)
→ fitness/novelty/complexity/descriptors  →  convergence & diversity monitor (adjust operators)
→ speciation  →  selection (Pareto + crowding + novelty slots)
→ variation (crossover + mutation, evo-RNG)  →  dedupe (genome hash)  →  register births
→ classify deaths → DeathRecords  →  update archive  →  ATOMIC CHECKPOINT
→ progress event (SSE)
```
Checkpoint content: population, all RNG stream states, archive, best-so-far, generation index.
Resume after crash ⇒ **bit-identical continuation** (determinism makes re-execution safe; F6.2).

### 13.7 Lineage, cemetery, parallelism

- **Lineage**: DAG of individuals (parents, ops, generation, genome hash, experiments, fitness,
  death/descendants) — the Evolution Tree UI; query: any individual ⇒ full ancestry +
  descendants + per-generation fitness.
- **Alpha Cemetery**: every death is a classified DeathRecord (reason taxonomy, max DD, worst
  regime, cost/latency/spread sensitivity, overfitting evidence). The cemetery is queryable,
  feeds resurrection, and is never purged.
- **Parallelism**: Evolution Coordinator (in the API process) decomposes generations into
  individual-evaluation jobs; **Simulation Workers** (process pool, v1) execute them; a Result
  Aggregator assembles the generation. Unit of parallelism = *individual* (independent ⇒
  determinism preserved). Checkpoint/resume/cancel/progress/failure-recovery per §13.6.

### 13.8 Portfolio evolution, shared-capital tournaments, execution evolution, co-evolution

- **Portfolio = genome**: allocator genome = {strategy weights (over population members), cash
  weight, risk limits, selection rule}. Evaluated by the same fitness machinery on the same
  $1,000 account; rebalance cycle is part of the genome. Baseline comparison: a non-evolved
  cvxpy/constrained allocation must be reported alongside (otherwise the result is uninterpretable).
- **Shared-capital tournament**: N strategies (100+) compete for ONE $1,000 portfolio: per-cycle
  capital allocation by the allocator, per-strategy risk sub-limits, exposure control, and a
  **correlation penalty** in allocation. Tournament modes = scenario presets: normal, volatile,
  crash, low liquidity, wide spread, high latency, cost shock.
- **Execution evolution**: the execution-policy block of the genome (order-type preference,
  passive/aggressive/adaptive, split count, post-only, TP/SL distances) evolves alongside logic.
- **Co-evolution (optional module)**: trader population vs market-maker / liquidity-provider /
  adversarial populations — **only against the synthetic exchange**. Hard scheduler guard:
  co-ev config + historical adapter ⇒ run rejected (`CONFIG_GUARD`). Co-ev results are always
  stamped `synthetic=coev` and never mixed into historical rankings (F6.8).

## 14. Portfolio model

### 14.1 The account

Default official account: **opening balance 1,000.00 USD**, created by exactly one opening
journal entry (`EQUITY_OPENING → CASH`, reason `OPENING`). Contents (all ledger-derived views):
`cash ₤`, `reserved_cash ₤` (margin), `available_cash ₤`, positions, `realized_pnl ₤`,
`unrealized_pnl ₤` (marks), `fees ₤`, `funding ₤`, `margin {used, required, utilization} ₤`,
`equity ₤`, `drawdown ₤` (causal HWM), `exposure ₤`, per-strategy attribution.

### 14.2 Double-entry ledger (detail)

Account set: `CASH`, `CASH_RESERVE`, `POSITION:{symbol}` (per position), `FEES`, `FUNDING`,
`LIQ_COSTS`, `EQUITY_REALIZED`, `EQUITY_UNREALIZED` (mark account), `EQUITY_OPENING`.
Each financial operation = **one journal** = list of (account, amount ₤) with Σ = 0 (writer
cannot express Σ≠0), tagged with `reason_code` from a closed set and the causing `ref_event_id`.
Operations: OPEN, CLOSE, FEE, FUNDING, MARGIN_RESERVE/RELEASE, LIQUIDATION, SETTLE, OPENING,
MARK (mark-to-market, throttled: per bar or per tick, configurable; forced on close).

**Reconciliation** (always on): per-write balance check; per-checkpoint:
(1) `CASH + CASH_RESERVE + Σ POSITION(marked) = equity`;
(2) `Σ signed fills = position qty` (recomputed, not trusted incrementally);
(3) fee total == FeeModel recomputation; (4) funding == rate series × positions;
(5) `EQUITY_REALIZED` == Σ(close proceeds − open cost − allocated fees).
Any drift ⇒ `ENGINE_INTEGRITY_VIOLATION` ⇒ run `INVALID` (loud, audited — never silent).

### 14.3 Margin & liquidation (a process, not a flag)

When leverage is enabled per instrument profile: `initial margin %`, `maintenance margin %`,
utilization, warning threshold (default 80% utilization), liquidation threshold (maintenance
breach). On **every mark update**:

```
1. margin_ratio = (equity − margin_required) / margin_required
2. ratio < warn          → MARGIN_WARNING (event, portfolio state flagged)
3. ratio < maintenance   → LIQUIDATION_START:
     shortfall = margin_required·(1+buffer) − equity
     forced MARKET orders generated per position (size covers shortfall; capped per cascade)
     forced orders are FORCED (user-cancellable = false) and enter the NORMAL pipeline:
     broker → matching (with impact) → fills → FEE (incl. liquidation penalty) → ledger
4. settle cascade: if still short after a cascade (max N) → forced settlement at floor,
     residual booked to LIQ_COSTS
5. LIQUIDATION_COMPLETE {full chain ref} — the Trade Autopsy can replay the entire chain
6. position state = LIQUIDATED; re-entry barred until fully settled
```
There is no "price < X ⇒ close" shortcut anywhere in the core.

### 14.4 Funding (crypto perps)

Rate series is a **dataset artifact** (declared source, e.g. exchange-published); accrual at
funding timestamps: `position_qty × rate`, signed by side; one ledger entry per accrual
(`FUNDING`), reconciled (§14.2-4). Spot/equity modes: funding disabled, optional interest
config.

## 15. Execution model

### 15.1 Order types & TIF (virtual broker)

Types: Market, Limit, Stop, Stop Limit, Take Profit, Trailing Stop (parent + managed child).
TIF: GTC, GTD, IOC, FOK. Flags: Post-Only, Reduce-Only, (internal) Forced.
Broker rules (per instrument): tick size, step size, min qty, min notional, price/qty precision.
Every rejection carries a structured reason code: `RISK_*`, `PREC_*`, `NOTIONAL_*`, `BALANCE_*`,
`LIQ_*`, `DUP_*`, `STATE_*`, `TIF_*` — the UI shows the exact failing rule.
Stop/StopLimit/Trailing: armed in the broker; trigger ⇒ child order spawned (evented);
Trailing re-arms per fill/mark per policy (evented).

### 15.2 Matching tiers (declared, never silent)

| Tier | Input | Model |
|---|---|---|
| **T2** | real L2 book data | book reconstruction (seq-tracked, gap ⇒ DEGRADED + resync); price-time priority; **depth consumption** fills; queue model = exact-FIFO (from trade flow) |
| **T1** | L1 (bid/ask) + trades | top-of-book + spread model; depth estimated from trade flow + declared curve; queue model = probabilistic (named plugin) |
| **T0** | OHLCV only | **synthetic book**: volatility-scaled spread, participation depth, sqrt-impact; always stamped `synthetic` |

`fill_model=candle_touch` exists only as a flagged `UNRELIABLE` variant (excluded from
rankings, labeled in every output). **Every fill records** its tier + queue model + book
snapshot ref, so any fill can be re-explained (F1.4, F3.1, F3.7).

### 15.3 Queue model (plugin)

`exact_fifo` (needs trade-level consumption data) / `probabilistic` (fill probability from
queue position proxy, seeded) / `conservative` (assumes worst position). Name + parameters in
the spec; swap = counterfactual.

### 15.4 Latency (6 independent layers)

`strategy_compute` · `internal` · `network` · `broker` · `exchange` · `execution`.
Each layer: **deterministic mode** (fixed ms from config) or **stochastic mode** (distribution:
fixed mean/σ, lognormal, mixture — seeded from the `exec` stream, parameters in the spec).
Per-order latency budget is the sum of layer draws; recorded per fill (autopsy shows the
breakdown). Validation at config time: supports ≥ 0, declared moments.

### 15.5 Slippage & market impact (mandatory plugins)

Slippage: `fixed` · `pct` · `spread_based` (half-spread + adverse) · `volatility_based` ·
`volume_based` (participation) · `order_book_based` (depth) · `latency_aware` (stale-quote
penalty) · `custom`.
Impact: `fixed_bps` · `volume_sensitive` (sqrt law: `impact ≈ σ·√(Q/ADV)`) · `participation`
(cap Q as fraction of bar volume; excess ⇒ queue or skip, declared) · `order_book_consumption`
· `custom`. Impact depends on **trade size and liquidity** (book depth / ADV), recorded as
`impact_bps` per fill; the capacity engine (§16.6) is just this mechanism at scale.

### 15.6 Execution policy (evolvable)

The policy block decides *how* an intent becomes orders: order-type preference, passive vs
aggressive timing (post-only until touched, then market), split count (iceberg), TP/SL/trailing
placement, reduce-only exits. The **Execution Engine** implements it as events
(`EXECUTION_RECORD` per intent→orders trace). Because it is a genome block, **execution itself
evolves** — a passive-execution variant of a winning logic is a first-class discovery.

## 16. Research lab

| Lab | Mechanism | Output |
|---|---|---|
| **Walk-Forward** | rolling/expanding windows; configurable train/validation/OOS/step; strict slices (no overlap); each window = Experiments | per-individual IS/OOS/WFA table; OOS-seen-once discipline; promotion gate |
| **Robustness** | batch of counterfactuals: parameter perturb, cost×2, spread widen, latency +50%, slippage up, liquidity down, start-date shift, regime shift | pass/fail per perturbation + stability score; mandatory for "strong" |
| **Monte Carlo** | trade-sequence reshuffle; execution randomness; slippage/latency variation; random fills — all seeded | distributions (return, DD, ruin probability); percentile reports |
| **Counterfactual** | spec mutation on declared knobs (capital, fees, spread, slippage, latency, liquidity, leverage, execution model) → child Experiments | A/B diff: metric deltas, overlaid curves; parent id on child |
| **Sensitivity** | grid/Sobol sweeps over knobs (capital/latency/fees/slippage/liquidity) | sensitivity maps (surfaces) in UI |
| **Regime** | causal detector (rolling realized-vol quantile, trend slope, liquidity) → versioned regime series; per-regime performance post-hoc | regime table + regime-conditioned curves; detector is data (observable-only, no labels fed into runs) |
| **Capacity** | reruns at $1K/$2.5K/$5K/$10K/$50K/$100K/$1M through the **same** impact/liquidity models | degradation curve; capacity ceiling (capital at −50% return); slippage/impact/liquidity-consumption breakdown |
| **Tournaments** | scenario presets × populations; shared-capital mode (allocator genome, $1,000, correlation penalty) | ranking (equity, DD, survival, capital efficiency, risk, robustness); every entry opens to its full experiment |

All lab outputs are **Experiments** (immutable, EVL-id'd, parent-linked) — nothing in the lab
ever produces a number that cannot be re-run.

## 17. Frontend architecture

**Stack (decided after comparison — see OSS_SURVEY §9):**
Next.js 16 (App Router; RSC for data-dense initial states) · TypeScript · Tailwind 4 (design
tokens) · shadcn/ui (owned, accessible primitives) · TanStack Query (server state) + TanStack
Table (grids) · Zustand (client state) · **Apache ECharts** (analytics: equity, drawdown, Pareto
fronts, population maps 2D/3D, evolution tree graph, sensitivity surfaces) · **Lightweight
Charts** (replay: candles, trades, bid/ask, book-depth markers, strategy-signal markers) ·
EventSource (SSE) + WebSocket clients · Vitest/RTL/Playwright.
**Why not Plotly:** bundle weight and interaction cost on 100k+ point datasets; ECharts canvas
rendering + sampling handles the density this UI demands. **Why Next.js over SPA:** replay and
experiment pages stream large initial datasets — RSC + streaming is the right tool; the app stays
client-capable where interactivity is king.

### 17.1 Information architecture (pages)

| Page | Contents |
|---|---|
| **Dashboard** | total equity, starting capital, active strategies, active experiments, current generation, population health (diversity/convergence), portfolio PnL, drawdown, running simulations (live progress bars), system health (workers, data quality flags, queue depth) |
| **Portfolio** | equity curve, drawdown, cash/available, exposure, positions (table), orders (live table), PnL, fees, funding, margin utilization, kill-switch states |
| **Strategy Lab** | create/edit (SDK or genome), run backtest/replay, duplicate, version, view genome (visual), view metrics; compile-check with causality/size diagnostics |
| **Evolution Lab** *(the flagship)* | current generation, population table, survivors/deaths feed, best individuals, **Pareto frontier** (interactive scatter, selectable), novelty distribution, diversity panel (cluster ratio, Hp, convergence alerts), avg fitness, complexity distribution, evolution speed (individuals/min), actions (pause/resume/cancel/checkpoint) |
| **Population Map** | 2D/3D scatter of the population by (fitness, novelty, complexity, behavior dimensions — selectable axes); hover ⇒ individual; click ⇒ genome |
| **Evolution Tree** | interactive lineage DAG (ECharts graph); click individual ⇒ genome, parents, children, mutation list, experiments, metrics, death/survival state |
| **Genome View / Diff** | visual genome grouped as Entry / Exit / Risk / Position Size / Execution / Features / Parameters (tree rendering, not raw JSON); **diff**: parent vs child — added/removed/changed, mutation vs crossover highlighted |
| **Alpha Cemetery** | strategy, age (generations survived), peak fitness, death reason (taxonomy chips), failure regime, sensitivity profile; filters; resurrect action |
| **Tournaments** | ranking table (equity, DD, survival, capital efficiency, risk, robustness), mode badge, shared-capital allocation view; open any strategy |
| **Market Replay** *(strongest screen)* | candles + trades + bid/ask + order book + strategy signals + orders + fills + portfolio state + PnL, synced timeline; transport controls: play/pause, 1x/2x/10x/50x/100x, step event, step trade, jump to trade, jump to drawdown, seek |
| **Order Book UI** | bid/ask ladder, spread, depth histogram, recent trades, **strategy order markers** (resting/partial/filled), book state chip (OK/DEGRADED/SYNTHETIC) |
| **Trade Autopsy** | per trade: Signal → Order → Broker → Latency (layer breakdown) → Exchange → Fill → Fee → Position → Exit, with journal entries; one view, the event chain |
| **Portfolio Autopsy** | at a drawdown point: contribution by strategy / asset / leverage / execution / fees / funding / correlation |
| **Experiment page** | Summary, Metrics, Trades, Execution, Robustness, Walk-Forward, Monte Carlo, Sensitivity, Capacity, Regimes, Lineage, **Assumptions** (the declared-models stamp) |
| **Reports** | export HTML / JSON / CSV / Markdown (+ PDF optional); report = pure function of EVL id |
| **Live/Paper** | connection state, market state, portfolio, orders, fills, latency, PnL, risk, kill switches — **Live = DISABLED BY DEFAULT** (paper is the default mode) |

### 17.2 Realtime & interaction

- **SSE** for all one-way streams: `/experiments/{id}/stream` (status, progress, results
  arriving), `/evolution/{id}/stream` (per-generation progress + population-health ticks),
  `/live/stream` (paper/live state). Auto-reconnect with `Last-Event-ID`; server replays missed
  events from the log.
- **WebSocket** for bidirectional: replay sessions (commands in §8.4) and (future) live order
  control. No polling anywhere except liveness heartbeats.
- **Shared domain schema**: Python event structs → codegen'd TypeScript (`domain-events`
  package) so the UI reducer and the engine consume the same types (F6.3).
- **Design system (tokens, dark-first)**: semantic colors (`up/down/neutral/warning/critical`
  with color-blind-safe pairs), 8pt spacing scale, 12–13px base, **tabular numerals** for all
  financial figures, declared precision per metric type (money 2dp, ratios 4dp, rates %2dp),
  `~`/estimated chip on any T0/queue-estimated quantity (F6.6), keyboard map (`g`+key
  navigation, `space` play/pause, `←/→` step, `t` trade jump, `d` drawdown jump, `/` command
  palette, `k` kill-switch guard), responsive desktop/tablet.

## 18. Backend architecture

**Stack (confirmed after comparison — OSS_SURVEY §8):** FastAPI + Pydantic v2 (schemas
shared/codegen'd with the core) + SQLAlchemy 2 (MIT) + Alembic + PostgreSQL 16 (+Valkey from
Phase 2) + Uvicorn/uvloop + structlog + orjson/msgspec.
*Alternatives rejected:* Django/DRF (heavier, weaker native async/typing integration for an
event-heavy core), Flask (less structure), Go services (splits the backend from the Python core),
NestJS (same split). The winning criterion was **schema sharing between core and API** —
Pydantic models describe both; codegen produces the TS side.

### 18.1 Service layout (in the API process)

`routers` (thin, OpenAPI-documented) → `services` (domain logic) → `repositories`
(PG + datastore access) → `job system`. Workers are a **separate command of the same
distribution** (`evoltrade worker`): strategy execution happens in **sandboxed subprocesses**
(F7.1) inside workers; the engine instance is per-run (P1).

### 18.2 Job system

`jobs` table (PG) + advisory locks (v1) → push mode via Valkey pub/sub (Phase 2).
Kinds: `BACKTEST`, `WALK_FORWARD`, `EVOLUTION_GEN`, `ROBUSTNESS`, `MONTE_CARLO`,
`SENSITIVITY`, `CAPACITY`, `TOURNAMENT`, `DATASET_INGEST`, `DATASET_VALIDATE`, `REPORT`,
`MIRROR_REFRESH`. Lifecycle: PENDING → QUEUED → RUNNING (heartbeat) → DONE/FAILED/CANCELLED;
retry ≤ N with backoff; progress = (fraction, generation, individual) → SSE. Cancellation is
cooperative at generation/checkpoint boundaries (determinism-safe).

### 18.3 API surface (representative; OpenAPI auto-generated with examples)

```
POST   /strategies                     (create: SDK code ref or genome)
GET    /strategies/{id}   /strategies/{id}/lineage   /strategies/{id}/genome
GET    /strategies/{a}/diff/{b}        (genome diff)
POST   /experiments                    (spec → EVL id, 202)
GET    /experiments/{id}               (status, metrics summary, assumptions)
GET    /experiments/{id}/events        (event log paging; offsets for replay)
GET    /experiments/{id}/trades        (mirror, paginated)
GET    /trades/{id}                    (autopsy: full event chain)
POST   /backtests                      (single-strategy backtest job)
POST   /evolution/runs                 (population, generations, objectives, seed)
GET    /evolution/runs/{id}/generation/{n}
POST   /tournaments                    (mode, participants, allocator)
GET    /portfolios/{id}   /portfolios/{id}/snapshots/{ts}
POST   /replay                         (open replay session → WS url)
GET    /datasets  /datasets/{id}/versions/{v}/quality
POST   /datasets/ingest                (provider ref or upload)
GET    /experiments/{id}/reports/{fmt} (html|json|csv|md|pdf)
GET    /live/status                    (DISABLED unless explicitly enabled)
GET    /admin/audit  /admin/health     (audit chain, system health)
WS     /replay/sessions/{id}           (pacing + commands)
SSE    /experiments/{id}/stream  /evolution/{id}/stream  /live/stream
```

Auth: local users (argon2) + scoped API keys (read-only default; write requires scope);
rate limiting; all mutations audit-logged.

## 19. Plugin architecture

**Replaceable categories (versioned interfaces + Pydantic config schemas):**
`DataProvider` · `FeeModel` · `SlippageModel` · `LatencyModel` · `ImpactModel` · `QueueModel` ·
`MatchingModel` (per tier) · `FitnessEvaluator` · `MutationOperator` · `CrossoverOperator` ·
`SelectionPolicy` · `PortfolioAllocator` · `ExchangeAdapter` (live — disabled) · `ReportExporter`.

- **Discovery:** built-in registry + Python entry points (`evoltrade.plugins.<category>`);
  plugins are separate distributions; core distributions ship no GPL/AGPL plugin.
- **Loading:** plugins load **only in worker processes** (never the API process); plugin API is
  semver-versioned; config is validated against the schema before a run starts (bad config ⇒
  job rejected, not a mid-run crash).
- **Isolation:** strategy code (the most untrusted input) runs a level deeper — sandboxed
  subprocesses with rlimits and no network (§22).
- **Declarations:** every plugin records `name@version` + params into the experiment spec ⇒
  any result states exactly which models produced it (P6).

## 20. Testing architecture

| Layer | Tools | Suites (named) |
|---|---|---|
| Unit | pytest | broker TIF matrix; matching per tier; ledger ops; genome IR validator; fee/funding math; queue models; latency validation; regime causality; formatters |
| **Property (invariants)** | Hypothesis | **I-1..I-8** (FAILURE_MODEL): no phantom money, no double fill, fill ≤ qty, no fee twice, position & ledger reconciliation, deterministic replay, point-in-time; fuzzed strategies + markets |
| Anti-leakage | pytest + [P] | truncation-equivalence (results on data[:T] == full run restricted ≤T); tail-perturbation (mutating data after T leaves ≤T unchanged); lookahead probe abort; repainter detector; bar-closed discipline |
| Integration | pytest (compose) | full pipeline scenario (intent→…→portfolio) per order type; liquidation chain; counterfactual A/B; WFA slicing; replay parity (UI hash == server hash); sandbox kills (F7.1) |
| Regression | pytest + golden | **5 golden experiments** pinned (spec+dataset ⇒ event-log hash + metrics JSON); re-baseline only via changelog entry (F6.5) |
| Determinism | pytest (2 processes) | same spec, separate processes ⇒ identical event-log hash; RNG stream checkpoint/resume identity |
| Accounting | pytest | opening entry $1,000.00; 1e6-op Decimal drift; reconciliation fuzz |
| API | pytest + httpx | OpenAPI contract; auth negative; immutability (UPDATE blocked); SSE/WS flows |
| Frontend | Vitest + RTL + Playwright | reducers vs shared schema; precision formatting; replay transport; e2e golden page |
| Performance | pytest-benchmark + vegeta | events/s, orders/s, **fills/s**, backtests/worker, memory/run, API p95, SSE latency, replay 100×; CI baselines with regression alerts |
| E2E | Playwright + compose | CLI `evoltrade evolve` → Evolution Lab → cemetery → report export round-trip |

**Test data:** (a) seeded synthetic T0 reference dataset (generated by the synthetic exchange —
deterministic), (b) a real free dataset via ccxt (e.g. a major crypto pair, public history),
(c) a real free equity dataset via yfinance — the golden suite runs on all three tiers so tier
behavior is always covered.

## 21. Deployment architecture

**v1 — single machine, Docker Compose:**

```
services: web (Next.js) · api (FastAPI) · worker (N=CPU-1 processes, sandbox children)
          · postgres:16 · [valkey (Phase 2)] · [grafana (optional, standalone)]
volumes:  pgdata · datastore (Parquet tree)
env:      EVOLTRADE_* (secrets); no secrets in images; .env file outside the image
```

- Migrations run at api start (Alembic, idempotent); datastore integrity check on worker start.
- Backups: nightly `pg_dump` + datastore manifest (hashes) + audit chain export; restore test
  quarterly (the audit chain + content hashes make restoration verifiable).
- **Scale path (interfaces already exist):** workers → Celery+Valkey (Phase 2, same job
  contract) → Ray farm (Phase 3, evolution farm; coordinator API unchanged); API/web stateless
  behind LB; PG read replicas if the mirror queries grow. **No Kubernetes until a real need
  appears** (spec §79) — Compose + 2 machines covers a research lab comfortably.
- Monitoring: Prometheus `/metrics` (queue depth, events/s, worker heartbeats, datastore IO),
  OpenTelemetry traces (job → run → event batch), structured JSON logs (redacting), health
  endpoints; the Dashboard "system health" panel reads the same metrics.

## 22. Security model

| Threat | Control |
|---|---|
| Strategy code is untrusted (infinite loops, forks, huge alloc, path tricks) | **Sandboxed subprocess**: CPU-time + memory rlimits, no network (disabled at OS level in v1), read-only FS except per-run scratch, separate uid; kill on breach ⇒ `TIMEOUT`/`RESOURCE` death reason; host unaffected (fuzz-tested, F7.1) |
| Secret leakage (exchange keys) | Secrets only via environment; logging redaction filter; keys never stored in DB/reports (only provider ref + hashed credential handle); CI log-scan for key patterns |
| Tampered history | Immutable experiments (DB trigger) + content-addressed artifacts + **hash-chained audit log** + daily integrity re-hash (F6.4, F7.5) |
| Unauthenticated mutation / abuse | Local auth + scoped API keys (read-only default), rate limiting, audit on every mutation |
| **Accidental live trading** | Live module absent by default: no adapter, no config, no endpoint; enablement = explicit command with risk acknowledgment + separate key + per-scope kill switches + audit; **paper is the default "realistic" mode** (F7.3) |
| Supply chain | pinned lockfile, hash-verified wheels, SCA scan in CI, THIRD_PARTY.md review gate for any new dependency |
| Data privacy (user datasets) | datasets namespaced + quality-gated; provenance on every experiment; no external transmission of user data by the core (providers pull, never push) |
| Kill switches | GLOBAL / PORTFOLIO / STRATEGY / INSTRUMENT scopes; manual or auto (circuit breaker); trip ⇒ only reduce-only/forced orders; reset audited; visible on Dashboard + Live UI |

## 23. Performance strategy

**Targets (v1, single 8-core machine, consumer-grade; measured, not hoped):**

| Metric | Target (v1) | Notes |
|---|---|---|
| Event throughput (engine, OHLCV) | ≥ 100k events/s/worker | pure Python; Rust core (Phase 4) aims ≥ 1M |
| Matching ops | ≥ 50k orders/s/worker (T0/T1) | T2 benchmarked per dataset |
| Backtest: 100k bars, 1 genome | < 1 s | indicators precomputed/cached |
| Backtest: 1M ticks, 1 genome | < 30 s | T1 |
| Evolution throughput | ≥ 200 strategy-backtests/s aggregate (8 workers) | ⇒ 500 ind × 100 gen × 10k bars ≈ 20–40 min |
| API read p95 | < 50 ms | mirror queries (DuckDB over Parquet for heavy) |
| SSE lag | < 200 ms | |
| Replay | 100× of 100k events stable | |
| Memory per run | ≤ 512 MB (capped; OOM ⇒ FAILED, not host risk) | |

**Techniques:** process-level parallelism (GIL irrelevant across runs); Arrow zero-copy between
data layers; indicator precomputation cached by (dataset_version, params) hash; DuckDB for
aggregations; msgspec/orjson for event I/O; uvloop for the API; event batching to Parquet
(segments, zstd); per-worker memory caps; numba for the per-bar evaluation closure if benchmarked
faster (same interface); optional **fast pre-screening tier** (vectorized, declared as
*screening-only* — promotion to "real" results requires the event-driven engine, echoing the
industry lesson that vectorized sweeps overstate reality).
**Measurement:** benchmarks are CI jobs with stored baselines + regression alerts; every release
notes its numbers. Benchmarks also define the trigger for the optional Rust core (P12).

## 24. Licensing strategy

- **Core (engine, broker, ledger, evolution, research, registry, API, CLI, web): Apache-2.0**
  (recommended; MIT acceptable — decision needed, §27). Rationale: permissive (usable
  everywhere) + explicit patent grant (important for a trading/execution codebase) + compatible
  with the entire chosen dependency set.
- **Third-party:** as registered in [THIRD_PARTY.md](THIRD_PARTY.md) — permissive only in-core;
  GPL/AGPL never in-process (optional standalone processes only, e.g. Grafana); source-available
  (SSPL/RSALv2/Commons Clause) and SaaS never; NOTICE file generated from the register.
- **Plugins:** may carry their own permissive or copyleft licenses; the core must not *require*
  any plugin; copyleft plugins are user-installed, clearly labeled, and excluded from
  core distributions.
- **User data:** stays the user's; the platform never redistributes user datasets; provider
  terms (ccxt exchanges, Yahoo, optional paid feeds) remain the user's responsibility and are
  surfaced in the dataset provenance record.
- **Data & models:** reference datasets (synthetic + fetched samples) ship with provenance
  (source, license, fetch params); fetched data is reproducible but *not* a license to
  redistribute the source data.

## 25. Experiment registry & reproducibility contract

**EVL-YYYY-XXXXXXXX** — allocated atomically (PG sequence, year-scoped) at spec submission.
The **spec** (canonical JSON, hash-named file + PG row) fixes everything:

```json
{
  "schema_version": 1,
  "experiment_id": "EVL-2026-00000123",
  "parent_id": null,
  "capital": "1000.00", "currency": "USD",
  "dataset": {"version_id": "…", "content_hash": "sha256:…", "symbols": ["BTC/USDT"],
               "range": ["2024-01-01T00:00:00Z", "2024-06-30T00:00:00Z"], "tier": "T1"},
  "strategy": {"representation": "GENOME", "genome_hash": "sha256:…"},
  "engine": {"version": "git:abc123…", "precision": "decimal-28"},
  "broker": {"fee_model": "bps@1", "fee_params": {"taker": "0.001"}},
  "execution": {"slippage": "spread_based@1", "latency": {"network": {"mode": "stochastic",
     "dist": "lognormal", "params": {"mu": -4.2, "sigma": 0.8}}, "exchange": {"mode": "deterministic", "ms": 5}},
     "impact": "volume_sensitive@1", "queue_model": "probabilistic@1", "fill_model": "tier_default"},
  "risk": {"policy_id": "default-conservative"},
  "portfolio": {"leverage": false, "margin_profile": "spot"},
  "seed": {"master": 42, "streams": {"market": "sha256:…", "exec": "sha256:…", "evo": "sha256:…"}}
}
```

**Contract:**
1. `spec_hash = sha256(canonical_json(spec))`; stored spec is content-addressed
   (`spec.{hash}.json`).
2. **Immutability**: no UPDATE/DELETE on experiments (DB trigger); any change ⇒ new experiment
   with `parent_id` (that's the counterfactual lineage, not an edit).
3. **Reproducibility**: same `(spec_hash, dataset content_hash, engine git sha, seed)` ⇒
   identical event-log hash and metrics — enforced by the determinism test and the golden set
   (I-7). Money is bit-identical (Decimal); float metrics within declared tolerance
   (relative 1e-9) — and the tolerance itself is stamped in the report.
4. **Auditability**: every result page links `engine_version`, `dataset_version_hash`,
   `spec_hash`, `result_hash`, and the **Assumptions** stamp (models + tiers used).
5. **Reports are pure**: `report = f(evl_id, registry, generator_version)` — the same id always
   yields the same report bytes.

## 26. Roadmap (with exit criteria)

| Phase | Name | Scope | Exit criteria |
|---|---|---|---|
| **0** | Discovery & Architecture *(this doc)* | analysis, survey, proposal, approval | proposal approved; §27 decisions recorded |
| **1** | Vertical Slice (MVP core) | data layer (user files + ccxt + yfinance, validation, versioning, quality); engine core (scheduler, clock, RNG, events); OrderBook + matching T0/T1; Virtual Broker (all types/TIF); Decimal ledger + reconciliation + $1,000 opening; Risk Engine (core limits + kill switch); Portfolio views; SDK + Genome v1 (entry/exit, sizing, basic exec policy); backtest (CLI + API); Experiment Registry (EVL, immutable, spec hash); **test suites: determinism, ledger invariants, anti-leakage, golden×3**; minimal API + SSE; minimal Web (Dashboard: equity curve, experiments, system health) | a reproducible backtest with full audit trail; all invariants green in CI; golden suite pinned; $1,000 ledger exact to the cent |
| **2** | Evolution Engine | operators (all §13.1), Pareto selection + fitness vector, novelty archive, diversity/convergence (0.95), dynamic speciation, complexity penalty, checkpoints/resume, lineage, **Alpha Cemetery**, WFA gate; `evoltrade evolve`; **Evolution Lab UI** (lab, population map, evolution tree, genome view/diff, cemetery UI) | 500×20 generations end-to-end, reproducible (hash), convergence demo triggers and recovers; kill/resume = identical result |
| **3** | Research Lab | robustness, Monte Carlo, counterfactual, sensitivity, regime, capacity, tournaments (all modes + shared capital + allocator genome), execution evolution; **Trade/Portfolio Autopsy**, **Replay UI (full)**, **Experiment page (full)**, Reports (HTML/JSON/CSV/MD + PDF optional), Order Book UI | every Experiment page renders all sections for 10 sample EVLs; counterfactual A/B reproducible; capacity curve monotone under impact |
| **4** | Market Realism | matching T2 (real L2) + book reconstruction + exact-FIFO queue; advanced latency (mixtures, session patterns); synthetic exchange (agent-based, seeded, stylized-fact validated a la ABIDES); co-evolution module (guarded); ArcticDB evaluation for tick storage | T2 replay parity tests vs reference book; synthetic exchange reproduces ≥ 8 stylized facts; co-ev guard negative test green |
| **5** | Scale & Paper/Live-adjacent | distributed workers (Celery+Valkey → Ray); paper mode (exchange adapters, user keys, sandboxed credentials); optional Rust core (if benchmarks demand); multi-user/SSO; K8s only on real need | 5000×100 evolution farm on 2 machines; paper session parity with backtest on identical data window |
| — | Live trading | separate module, separate review, explicit enablement, own kill switches & audit | out of scope until Phase 5 is proven; **disabled by default, always** |

## 27. Open decisions (need stakeholder sign-off)

| # | Decision | Recommendation |
|---|---|---|
| D1 | Core language/shape | Python 3.12 core + optional Rust core later (Phase 4) behind `SimulationCore` — confirm |
| D2 | Core license | **Apache-2.0** (vs MIT) — choose |
| D3 | Primary reference data for golden tests | crypto via ccxt (public, free, 24/7, funding model fits margin labs) as **tier-1 reference**; equities via yfinance as secondary — confirm (affects first datasets) |
| D4 | Account instrument universe for v1 | crypto perpetuals + spot (funding/margin labs) vs equities (yfinance) vs both — recommend **both**, crypto first |
| D5 | UI language | English-first in v1; Arabic/RTL as a later i18n layer — confirm |
| D6 | PDF reports | optional in v1 via WeasyPrint (BSD-3) — confirm need |
| D7 | Monorepo layout | single repo: `src/evoltrade/…` (core+services+cli) + `web/` (Next.js) + `docs/` — confirm |
| D8 | The user's spec message appears truncated at item 87 ("events/sec, orders/sec, fi…") | we completed it as fills/sec + backtests/worker + memory + API p95; please send any remaining items |

## 28. Requirements traceability (spec items 1–87)

| # | Requirement | Where addressed |
|---|---|---|
| 1 | Problem decomposition (30 sub-domains) | PROBLEM_ANALYSIS §2 (7 clusters) |
| 2 | OSS survey per tool (name/GH/license/activity/strengths/weaknesses/perf/fit/decision) | OSS_SURVEY (all categories) |
| 3 | Strict free policy; Data Layer for free/exchange/user/local/future providers | §24; THIRD_PARTY policy; §8.1; §19 (DataProvider plugin) |
| 4 | License table + THIRD_PARTY.md; no conflicting deps in core | THIRD_PARTY.md (verified 2026-09-10) |
| 5 | ≥3 architectures compared on 9 axes, one chosen + why | §6 (A/B/C + matrix + rationale) |
| 6 | FAILURE MODEL before features; prevent by design | FAILURE_MODEL.md (F1–F8, invariants I-1..I-8) |
| 7 | ARCHITECTURE_PROPOSAL with all listed sections | this document (all sections present) |
| 8 | Domain model ≥ all listed objects + relations | DOMAIN_MODEL.md (§1–§10, all objects) |
| 9 | Event-driven core, full event list, traceable transitions | §7 (Scheduler), §9 (taxonomy, envelope, sequence) |
| 10 | Strategy cannot touch money; intent-only pipeline | P3; §7 (pipeline); §12.3 (no write API); I-1 |
| 11 | Virtual Broker: all order types/TIF/flags, partial fills, rejections, expiry, precision, tick/step/mins | §15.1; DOMAIN_MODEL (Order invariants) |
| 12 | Matching Model; real L2 when available; declared synthetic otherwise; never pretend | §15.2 (tiers + stamps); F1.4/F3.1 |
| 13 | Unified Order Book abstraction (levels, spread, depth, consumption, est. exec price) | DOMAIN_MODEL (OrderBook); §7 (Matching Engine) |
| 14 | Queue Model: position/consumption/partial/full/no-fill/cancel/expire; changeable | §15.3 (plugin); F3.7 |
| 15 | Latency: 6 independent layers; deterministic + stochastic with stored seed | §15.4; spec `seed.streams.exec` |
| 16 | Slippage plugin interface (fixed/pct/spread/vol/volume/book/latency/custom) | §15.5 |
| 17 | Market impact (fixed/volume/participation/book/custom; size & liquidity sensitive) | §15.5 |
| 18 | $1,000 real in accounting; full account view set | §14.1; I (F4.7) |
| 19 | Double-entry ledger for all ops + reconciliation; no phantom money | §14.2; I-1/I-6 |
| 20 | Decimal for money; no binary float as accounting truth | P2; §14.2; F4.4 |
| 21 | Independent Risk Engine; all limits; circuit breaker; kill switch; can reject | §7 (Risk Engine); §22 (switches); F4.1 context |
| 22 | Margin & liquidation: IM/MM, utilization, warnings, threshold, full process, costs | §14.3 (7-step process); F4.5 |
| 23 | Strategy SDK: 6 callbacks; same strategy in Backtest/Replay/Paper/Live | §12.1; P4 |
| 24 | Strategy DSL / IR: logical/arithmetic/indicators/thresholds/rolling/time/state/vol/liquidity/order-flow | §12.2 (grammar; order-flow via book/spread/imbalance features) |
| 25 | Evolution Engine: all listed operators & selection concepts | §13.1–§13.2 (full operator list, Pareto + survival) |
| 26 | Population per-generation record set + checkpointing | §13.6; DOMAIN_MODEL (Population/Generation) |
| 27 | Genome: logic/indicators/params/entry/exit/sizing/risk/execution + hash | §12.2; §12.3 (sha256 identity) |
| 28 | Lineage: parents/mutation/crossover/generation/hash/experiments/fitness/death/descendants + tree | §13.7; DOMAIN_MODEL (LineageEdge) |
| 29 | Alpha Cemetery: full death record (reason, DD, regime, execution failure, sensitivity, overfitting, cost/latency sensitivity) | §13.7; DOMAIN_MODEL (DeathRecord) |
| 30 | Novelty search for structurally/behaviorally different strategies + archive | §13.3 |
| 31 | Diversity pressure; detect ~95% convergence; boost diversity | §13.4 (0.95 default) |
| 32 | Niching/speciation; non-fixed, formable labels | §13.5 (dynamic clustering) |
| 33 | Multi-objective fitness (full list) + Pareto frontier | §13.2 (12 objectives) |
| 34 | Complexity penalty (depth/nodes/features/params/logical) | §13.2 (complexity objective); §12.2 (caps) |
| 35 | Walk-forward: rolling/expanding, configurable train/validation/OOS/step | §16 (WFA row) |
| 36 | Anti-leakage: lookahead/repainting/future data/resampling/timestamp/future rolling + tests | §20 (Anti-leakage suite); F2.1–F2.6 |
| 37 | Robustness Lab: all 8 perturbations | §16 (Robustness row) |
| 38 | Monte Carlo Lab: reshuffled trades, execution randomness, slippage/latency variation, random fills + distributions | §16 (MC row) |
| 39 | Counterfactual Engine: change capital/fees/spread/slippage/latency/liquidity/leverage/execution → rerun | §8.3; §16 (Counterfactual row); §25 (parent_id) |
| 40 | Sensitivity Engine: maps vs capital/latency/fees/slippage/liquidity | §16 (Sensitivity row) |
| 41 | Regime Engine: observable-only, no unjustified causality, per-regime performance | §16 (Regime row); F2.6 |
| 42 | Capacity Engine: $1K→$1M; degradation/slippage/impact/liquidity consumption | §16 (Capacity row); F6.7 |
| 43 | Portfolio Evolution: portfolio genome (weights/cash/limits/selection) | §13.8 |
| 44 | Shared Capital Tournament: 100+ strategies, one $1,000, allocation/risk/exposure/correlation penalties | §13.8 |
| 45 | Execution Evolution: genome chooses execution style | §15.6; §13.8 |
| 46 | Strategy Competition: 7 tournament modes | §13.8 (scenario presets) |
| 47 | Co-Evolution: 4 populations; optional; must not touch historical deterministic engine | §13.8 (guard); F6.8 |
| 48 | Synthetic Exchange: book/matching/liquidity/agents/fees/latency/impact/regimes; seeded | §7 (synthetic adapter); Phase 4; §8 |
| 49 | Historical Replay: date selection, sequential, no future, 1x–100x, play/pause/step event/step trade/jump trade/jump drawdown | §8.4; §17.1 (Replay page); DOMAIN_MODEL (ReplaySession/Command) |
| 50 | Counterfactual Replay from a point | §8.3/§16 (parent chains; seek in replay UI) |
| 51 | Experiment Registry: EVL-YYYY-XXXXXXXX + full linkage | §25 |
| 52 | Immutable experiments; change ⇒ new experiment | §25.2; §11.1 (trigger); F6.4 |
| 53 | Data versioning: source/version/symbol/timeframe/timezone/transform history/quality | §8.1; DOMAIN_MODEL (DatasetVersion) |
| 54 | Data quality: duplicates/gaps/invalid OHLC/bad timestamps/bad volume/suspicious jumps | §8.1 (VALIDATE); F1.1 |
| 55 | Deterministic reproducibility + test | P1; §25.3; §20 (Determinism suite) |
| 56 | Frontend: Next.js/TS/Tailwind + ECharts (chosen over Plotly) + SSE/WS | §17 |
| 57 | Dashboard contents | §17.1 (Dashboard row) |
| 58 | Portfolio page contents | §17.1 (Portfolio row) |
| 59 | Strategy Lab capabilities | §17.1 (Strategy Lab row) |
| 60 | Evolution Lab contents (flagship) | §17.1 (Evolution Lab row) |
| 61 | Population Map 2D/3D (fitness/novelty/complexity/behavior) | §17.1 (Population Map row) |
| 62 | Evolution Tree interactive + per-individual detail | §17.1 (Evolution Tree row) |
| 63 | Genome View visual (Entry/Exit/Risk/Size/Execution/Features/Params) | §17.1 (Genome View row) |
| 64 | Genome Diff parent vs child (added/removed/changed/mutation/crossover) | §17.1 (Genome Diff row); §13.1 ops[] |
| 65 | Alpha Cemetery UI (strategy/age/generations/peak fitness/death reason/failure regime/sensitivity) | §17.1 (Cemetery row) |
| 66 | Tournament UI (ranking/equity/DD/survival/capital efficiency/risk/robustness; open any) | §17.1 (Tournaments row) |
| 67 | Market Replay UI (candles/trades/bid-ask/book/signals/orders/fills/portfolio/PnL + timeline) | §17.1 (Market Replay row) |
| 68 | Order Book UI (bid/ask/spread/depth/trades + strategy markers) | §17.1 (Order Book row) |
| 69 | Trade Autopsy UI (Signal→…→Exit timeline) | §17.1 (Trade Autopsy row); §9.3 |
| 70 | Portfolio Autopsy UI at drawdown (contribution by strategy/asset/leverage/execution/fees/funding/correlation) | §17.1 (Portfolio Autopsy row); §14.1 (attribution) |
| 71 | Experiment page sections (Summary…Assumptions) | §17.1 (Experiment page row) |
| 72 | Reports exportable HTML/JSON/CSV/MD (+PDF if sensible) | §17.1 (Reports row); D6 |
| 73 | Live/Paper UI (connection/market/portfolio/orders/fills/latency/PnL/risk/kill switches); Live DISABLED BY DEFAULT | §17.1 (Live/Paper row); §22; F7.3 |
| 74 | Responsive desktop/tablet (mobile optional) | §17.2 (responsive) |
| 75 | Visual design: dark-first, professional, data-dense, minimal, fast, keyboard-friendly, readable, consistent; Design Tokens | §17.2 (design system) |
| 76 | Realtime: experiment/generation progress, live orders/fills, portfolio, replay via WS/SSE; no needless polling | §17.2 (realtime) |
| 77 | Backend: FastAPI/Pydantic/SQLAlchemy/PostgreSQL (+Redis-when-needed) — after comparing options | §18 (comparison done; Valkey instead of Redis, licensed reason) |
| 78 | Data storage: PG (metadata/strategies/experiments/users/portfolios/orders/trades/lineage) + Parquet/Arrow (big data) | §11 (PG tables + mirrors; Parquet system of record) |
| 79 | Compute: single machine + workers first; scalable interfaces; no K8s without real need | §6 (C); §21 (scale path) |
| 80 | Parallel evolution: Coordinator→Worker Pool→Simulation Workers→Result Aggregator; checkpoint/resume/cancel/progress/failure recovery | §13.7; §18.2 (job system) |
| 81 | CLI: data validate / backtest / evolve / tournament run / replay / report / paper start | §18 (CLI peer to API); Phase 1–3 commands; Textual TUI for replay |
| 82 | REST API (OpenAPI-documented) with listed + necessary endpoints | §18.3 (full surface) |
| 83 | Plugin system: data provider/broker/fee/slippage/latency/execution/fitness/mutation/crossover/allocator/strategy/exchange adapter | §19 (all categories + StrategyCompiler via SDK/genome; ExchangeAdapter) |
| 84 | Security: env secrets / no key logging / read-only default / live disabled / explicit enablement / kill switch / audit log | §22 (all, mapped) |
| 85 | Testing: full pyramid (14 listed layers) | §20 (all layers named) |
| 86 | Property testing invariants (no phantom money, no double fill, fill ≤ qty, no fee twice, position & ledger reconciliation, deterministic replay) | §20 (Property row); I-1..I-8 |
| 87 | Performance benchmarks: events/sec, orders/sec, fills/sec (+ backtests/worker, memory, API p95) | §23 (targets + CI baselines) *(spec text truncated here in the original message — D8)* |

## 29. Glossary (short)

- **EVL** — Experiment identifier `EVL-YYYY-XXXXXXXX` (immutable experiment).
- **Genome** — canonical-JSON strategy gene (logic AST + sizing + risk + execution); hash = identity.
- **Tier (T2/T1/T0)** — market data fidelity: real L2 / L1+trades / OHLCV (synthetic book declared).
- **Cemetery** — the Alpha Cemetery; classified, permanent records of dead strategies.
- **Checkpoint** — atomic generation-level snapshot (population + RNG states + archive) enabling exact resume.
- **Counterfactual** — child experiment differing from its parent by declared knobs only.
- **Behavior descriptor** — normalized feature vector describing *how* a strategy trades (for novelty/speciation).
- **Hp** — effective population size, `1/Σp_i²` (diversity monitor).
- **Spec hash** — sha256 of the canonical experiment spec; the reproducibility anchor.

---
*End of proposal. On approval: record decisions D1–D8 as ADRs, then start Phase 1 (Vertical Slice)
per §26.*
