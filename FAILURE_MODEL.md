# EVOLTRADE — FAILURE MODEL

How the system can fail, and how the architecture **prevents each failure by construction**
(not by vigilance). Every row names the detection mechanism and the dedicated test that must
exist. Tests marked **[P]** are property-based (Hypothesis). Group = F-group.

Legend: Prevention-by-design (PbD) · Detection (Det) · Test (T).

---

## F1. DATA INTEGRITY

| # | Failure | How it manifests | PbD | Det | T |
|---|---|---|---|---|---|
| F1.1 | Duplicates / gaps / invalid OHLC / bad timestamps / bad volume / suspicious jumps in ingested data | Strategies train on corruption; results silently wrong | Ingestion **quality gate**: every dataset run through pandera schema + statistical checks (monotonic ts, `H≥max(O,C)`, `L≤min(O,C)`, `C>0`, volume≥0, jump z-scores, gap detection). Ingest fails closed: dataset status = `REJECTED` until reviewed | Quality report stored with dataset version; UI shows it on every dataset page | Unit per checker; [P] corrupt-random-dataset ⇒ rejected or flagged fields listed |
| F1.2 | Survivorship bias | Universe of symbols excludes delisted → returns overstated | Dataset carries an explicit `universe_mode` (fixed-at-past vs current); backtests over a **point-in-time universe** when symbol history is available; flag `survivorship_risk=possible` otherwise | Flag visible in experiment summary | Regression: same strategy on survivorship-universe vs full-universe differs and is labeled |
| F1.3 | Bad market reconstruction | L2 book rebuilt wrong (missed updates) → fake fills | Book backend records update sequence numbers; gap ⇒ **resync event** + book marked `degraded` for that interval; fills in degraded intervals are labeled | Book health metrics per interval; degradation count in report | [P] drop random updates ⇒ no fill is produced from a level that was not present at that time |
| F1.4 | Synthetic data presented as real | A T0/OHLCV run is read as if it were L2-accurate | **Data-tier stamp** (`T2/T1/T0`) is part of every experiment spec and is printed in every report, metric row, and UI header; ranking endpoints never mix tiers without explicit flag | `match_tier` field audited in report generation | Integration: report generator fails (assert) if tier label missing |
| F1.5 | Dataset drift between runs | "Same experiment" uses different data over time | Datasets are **versioned and content-hashed**; experiment spec references `dataset_version_hash`, not a symbol name; old versions immutable | Spec hash ≠ re-run spec hash ⇒ registry refuses "same experiment" claim | Determinism test pair (F8.1) includes dataset hash |

## F2. TIME & LEAKAGE (anti-leakage is a first-class subsystem)

| # | Failure | PbD | Det | T |
|---|---|---|---|---|
| F2.1 | **Lookahead** (strategy sees future) | Strategies access data **only** through `HistoryView` whose watermark = current sim time; any access with `ts > watermark` raises `LookaheadError` (fail-loud) and aborts the run with an `ANTI_LEAKAGE_VIOLATION` event. Indicators are computed **pre-windowed** by the data layer (never live on an infinite frame) | Engine asserts watermark on every view read; ABORT is recorded in the event log | [P] any strategy that probes `t+1` ⇒ run aborted with violation event; truncation-equivalence suite: results on data[:T] == results on full data restricted to ≤T, for all T in a sample |
| F2.2 | **Repainting** indicators (value at t changes when later data arrives) | Indicator computation is part of the **dataset version** (precomputed, immutable); the repainter detector recomputes each indicator value on `[:t]` vs `[:t+k]` and flags values that moved | Repaint detector run per dataset version (sampling); flagged indicators blocked from strategy use unless explicitly accepted | Unit on known repainting patterns (e.g., pivot highs); [P] random series ⇒ detector catches injected repainters |
| F2.3 | Future rolling information (shift errors, center-aligned windows) | Rolling windows in the IR are **causal by construction**: node `ROLL(w)` is defined over the closed window ending at the current bar; no centering operator exists in the IR grammar | Grammar review (static); IR validator rejects any node with non-causal semantics | Property: for any expression, value at t depends only on rows ≤ t (shuffled tail leaves it unchanged) |
| F2.4 | Timestamp/timezone leakage (mixing exchange-local and UTC, DST jumps) | Storage canonical form = **UTC, nanosecond, tz-aware**; dataset records source timezone + conversion history; all comparisons in one clock domain | Ingest validates tz integrity; mixed-tz rows are rejected | Unit on DST boundaries and exchange tz edges |
| F2.5 | Improper resampling (bar close used before it closed) | Bar bars are emitted as `BarClosed` events **only at bar end**; intrabar access is a separate, explicitly-labeled feed | Event type discipline (no `BarUpdated`-as-signal path) | Unit: signal computed on forming bar ⇒ rejected |
| F2.6 | Regime labels using future | Regime detector = causal filters only (rolling realized vol quantile, trend slope, liquidity — all at-time-t); the regime *series* is a versioned artifact, and **during a run the strategy never sees labels — only the observable features** | Label computation is post-hoc research tooling; run-time code has no label input channel | Suite: mutate data after T ⇒ regime labels ≤ T unchanged |

## F3. EXECUTION REALISM

| # | Failure | PbD | Det | T |
|---|---|---|---|---|
| F3.1 | "Candle touched price" fills | Forbidden as default. Fills come from the **matching model over book state** (T2 depth, T1 estimated depth, T0 declared synthetic). `fill_model=candle_touch` exists only as a flagged `UNRELIABLE` variant, excluded from rankings, labeled in every output | Fill model recorded per experiment; ranking service asserts model ∈ {trusted set} | Integration: T0 vs candle-touch divergence report; UI shows the flag |
| F3.2 | **Duplicate fills** (same order filled twice) | Fill id = `(order_id, fill_seq)`; matching engine holds per-order `filled_qty`; any fill where `filled_qty + q > qty` is a hard invariant violation → engine aborts + `ENGINE_INTEGRITY_VIOLATION` | Invariant checked per fill and at checkpoints | [P] any event stream ⇒ per-order fills are disjoint, Σ ≤ qty |
| F3.3 | Fill > order quantity / negative fills | Same invariant layer as F3.2 + broker pre-checks (qty vs remaining) | — | [P] covered above |
| F3.4 | **Incorrect fees** (double-charged, missing leg, wrong basis) | Fee is **one journal entry per fill**, computed by a single FeeModel plugin from (side, qty, price, contract); fee model config is part of the spec; round-trip fee is a derived metric, never manually summed | Reconciliation: `Σ fee entries == FeeModel.recompute(all fills)` at experiment end | [P] random fills ⇒ ledger fee total == independent recomputation, exactly (Decimal) |
| F3.5 | **Incorrect funding** (crypto perps: wrong accrual, wrong side) | Funding accrues on **position × rate at funding timestamps** only; each accrual = one ledger entry; rate series is a dataset artifact (declared source); sign convention unit-tested per asset class | Funding entries reconciled against rate series × positions | Unit on rate sign flips, partial periods, position opened mid-period |
| F3.6 | Wrong latency shape (constant offset instead of distribution; negative values) | Latency = per-layer **scheduled future events**; distributions validated at config time (support ≥ 0, declared parameters); deterministic mode = fixed config values, never random | Latency budget report per trade (autopsy shows layer-by-layer decomposition) | [P] sampled latencies ≥ 0; distribution moments match config within tolerance; deterministic mode ⇒ identical delays across reruns |
| F3.7 | Invisible queue assumptions | Queue model is a **named plugin** (exact-FIFO on trade data / probabilistic / conservative); the assumption is stamped in the spec and reports | `queue_model` field audited like `match_tier` | Unit per model; sensitivity report includes queue model swap |
| F3.8 | Market impact ignored (small $1K looks fine, $1M fantasy) | Impact plugins are **mandatory** in the pipeline (default = sqrt-volume model scaled by ADV/depth); capacity engine is a first-class lab | Impact model recorded per experiment | Unit: impact monotone in size; capacity curve test |
| F3.9 | Post-only / IOC / FOK / GTD semantics wrong | Broker rule engine implements each TIF as an explicit state transition with its own unit matrix (cross ⇒ reject for post-only; IOC remainder cancels; FOK all-or-nothing at decision time; GTD expiry event) | Order lifecycle events fully logged | Exhaustive unit matrix per TIF × order type |

## F4. ACCOUNTING (the sacred invariants)

| # | Failure | PbD | Det | T |
|---|---|---|---|---|
| F4.1 | **Phantom money** (cash created/destroyed) | Money exists **only** as ledger entries; every journal entry is balanced (Σ=0); cash account is a *view* of the ledger; there is no API anywhere in the codebase to "set cash" (no setter exists — static analysis rule `NO_DIRECT_MONEY_MUTATION`) | Per-entry balance check at write; `CASH + CASH_RESERVE + Σ POSITION(marked) == equity` checked at every checkpoint and at end | [P] any event stream ⇒ all invariants hold exactly (Decimal); fuzzed strategy + market ⇒ no negative-unexplained cash |
| F4.2 | **Position accounting errors** (qty/avg price drift) | Position qty = Σ fills (recomputed, never incrementally trusted alone); avg cost updated by a single formula; reconciliation at checkpoints compares incremental vs recomputed | Checkpoint reconciler aborts on drift | [P] random fills/cancels/liquidations ⇒ position == recomputation, exactly |
| F4.3 | Ledger imbalance (unbalanced entry slipped in) | Writer API **cannot** produce an unbalanced entry (constructor rejects Σ≠0) | Double-check at persistence (defense in depth) | [P] + persistence fuzz |
| F4.4 | Float money drift | **Decimal everywhere** for money; `Money` type rejects float construction (runtime + mypy rule); arithmetic quantized to instrument tick/step at entry points only | Lint rule + type tests | Unit: float injection attempts rejected; 1e6-operation drift test == exact |
| F4.5 | Margin/liquidation errors (wrong threshold, double liquidation, liquidation that ignores costs) | Liquidation = **stateful process** (detect → shortfall → forced orders through the normal pipeline with impact + penalty fee → realize → release → event). Maintenance check on every mark update; a position can only be liquidated while `state=OPEN`; re-entry barred until fully settled | Liquidation chain fully evented (autopsy-able); margin ratio series recorded | [P] price paths through thresholds ⇒ exactly one liquidation chain; forced fills respect the book; no position resurrects |
| F4.6 | Drawdown metrics wrong (lookahead in HWM, equity timing) | HWM and drawdown computed **on the checkpoint equity series** (causal), not on raw marks; definition (peak-to-trough on equity) is fixed in the metrics registry | Metrics registry (single source for definitions) | Unit on known series (golden values) |
| F4.7 | $1,000 not actually $1,000 | Default account opens with a **single opening journal entry** (Equity:Opening 1,000.00 → CASH 1,000.00); available vs reserved split enforced by ledger rules; `available_cash < order notional ⇒ REJECT(BALANCE)` | Opening entry asserted in every new account test | Unit + golden |

## F5. EVOLUTIONARY PATHOLOGIES

| # | Failure | PbD | Det | T |
|---|---|---|---|---|
| F5.1 | **Evolutionary overfitting** (training-window memorization) | "Strong" is only claimed after **WFA/OOS gates**: fitness splits (IS/OOS/WFA) are recorded per individual; final selection applies a degradation penalty; cemetery records overfitting evidence (IS/OOS gap, parameter-sensitivity, WFA degradation) | Overfit-evidence fields mandatory on promotion | Integration: a memorizing individual (works only on one window) ⇒ not promoted; [P] synthetic regime-shift ⇒ winners degrade measurably and are recorded |
| F5.2 | **Data mining / multiple testing** (5000 tries ⇒ some "win" by chance) | Experiment registry makes the **search count visible** (individuals evaluated, generations, seeds); reports include a multiple-testing section (deflated Sharpe computed from search effort); tournament winners require robustness-lab passage before "strong" label | `search_effort` metadata on every population result | Unit on deflated-Sharpe golden values; e2e: random-strategy population ⇒ no promoted individual passes the robustness gate (negative control) |
| F5.3 | **Premature convergence** (95% identical) | Convergence monitor per generation: cluster-size ratio on behavior descriptors; default threshold **0.95** (configurable). On trigger: `CONVERGENCE` event + actions (mutation-rate boost with decay, novelty-slot reservation, cemetery **resurrection** of high-peak dead individuals, speciation pressure) | Diversity panel on Evolution Lab (cluster ratio, effective pop size Hp, novelty distribution) per generation | [P] homogenizing mutation policy ⇒ monitor triggers at expected generation; actions observed in event log |
| F5.4 | Population collapse / diversity loss without trigger | Effective population size (Hp = 1/Σp²) tracked alongside cluster ratio (two monitors) | Same panel | Unit |
| F5.5 | **Frozen niche labels** | Niche/species = **computed** clustering per generation (threshold-based agglomeration on behavior descriptors; no fixed taxonomy); species ids are stable *within* a generation only; lineage stores the cluster id + parameters at the time | Per-generation speciation report | Unit: descriptors shifted ⇒ species re-formed |
| F5.6 | Misleading single-objective fitness | Selection is **Pareto** over the full objective vector; profit-only views exist in UI but are explicitly "not the selection basis"; default objective set includes risk, stability, OOS, turnover, capacity, complexity, novelty, correlation | Objective vector stored per individual; selection decisions evented with the front snapshot | Unit on constructed fronts |
| F5.7 | Complexity runaway (10,000-node trees that "win") | **Complexity penalty** objective: C = w₁·nodes + w₂·depth + w₃·params + w₄·distinct_features; IR validator hard-caps structural size; complexity shown in Genome View and rankings | Complexity distribution per generation in Evolution Lab | Unit: penalty monotone; cap enforced |
| F5.8 | Duplicate genomes (silent population shrinkage) | Genome **hash** (sha256 of canonical JSON) at registration; duplicates replaced by the existing individual (parentage noted) instead of new individuals | Duplicate counter per generation | [P] random genome generation ⇒ registry unique |

## F6. SYSTEM / DETERMINISM / AUDIT

| # | Failure | PbD | Det | T |
|---|---|---|---|---|
| F6.1 | **Non-deterministic reruns** | Single deterministic scheduler with total event order `(sim_time, seq)`; one seeded master RNG → derived streams (market/exec/evo) via KDF; no wall clock inside the engine; money = Decimal; fixed reduction order for float metrics; engine git SHA recorded in every result | Result hash = hash(event log + metrics); **golden experiments** (5 pinned spec+dataset → expected hashes) in CI | Determinism test: two separate processes, same spec ⇒ identical event-log hash; golden suite per release |
| F6.2 | Worker crash mid-generation | Generation is an **atomic checkpoint unit** (population + RNG states + archive + results So-far); coordinator resumes from last checkpoint; crashed individuals re-executed exactly (determinism makes re-execution safe) | Checkpoint manifest + resume test | [P] kill worker at random generation ⇒ resume ⇒ identical final result |
| F6.3 | Replay divergence (UI state ≠ engine state) | Replay streams the **actual event log**; the UI runs the **same reducer** over the same events (shared `domain-events` schema, codegen'd from Python); server can re-broadcast from any offset for self-heal | Periodic hash checkpoint of UI state vs server state during replay sessions | E2E: 100k-event replay ⇒ final UI state hash == server state hash |
| F6.4 | **Mutated history** (someone edits an old experiment) | Experiments are **immutable**: spec + results are content-addressed (hash-named), DB rows protected by trigger (no UPDATE/DELETE), "change" = new experiment with `parent_id` | Registry integrity job re-hashes a sample of stored specs daily | Integration: UPDATE attempt ⇒ blocked + audit entry; counterfactual ⇒ new EVL id |
| F6.5 | Version drift (engine update silently changes results) | Engine version = git SHA recorded per experiment; results are always presented *with* their engine version; golden suite fails loudly when a change alters pinned results (then results are explicitly re-baselined with a changelog entry) | Golden suite + version field in all reports | CI gate |
| F6.6 | **UI false precision** | Number formatting rules: declared precision per metric type (money 2 dp, ratios 4 dp, rates % 2 dp); "estimated" quantities (T0 fills, queue position) carry a visible `~`/estimated chip; no raw 17-digit floats anywhere | Formatting library unit-tested; codegen schema carries precision metadata | E2E snapshot on key pages |
| F6.7 | Capacity false optimism | Capacity runs go through the **same** impact/liquidity models (no separate "small account" fantasy path); degradation curve + capacity ceiling are mandatory in any "strong" report | Capacity section mandatory in report schema | Unit: doubling capital degrades return monotonically under impact |
| F6.8 | Co-evolution contaminating historical results | **Hard guard** in the scheduler: co-evolution config + historical market adapter ⇒ run rejected with `CONFIG_GUARD` event. Co-evolution runs only against the synthetic exchange | Guard unit-tested; co-ev results stamped `synthetic=coev` | Integration (negative) |
| F6.9 | Silent data corruption (storage bit rot, partial writes) | Parquet written atomically (temp + rename) with per-file SHA-256 manifest; registry integrity job re-hashes; event logs are append-only segments with per-segment checksums | Integrity job + startup verification of inputs (spec/dataset hashes re-checked before every run) | Fuzz: corrupt a byte in a segment ⇒ run refused |

## F7. SECURITY & OPERATIONS

| # | Failure | PbD | Det | T |
|---|---|---|---|---|
| F7.1 | Strategy code = untrusted input (infinite loops, resource exhaustion, path tricks) | Strategies run in **sandboxed worker subprocesses**: CPU-time + memory rlimits, no network (disabled at OS level in v1), read-only filesystem except a per-run scratch dir, separate uid; non-responsive strategy ⇒ killed + `TIMEOUT`/`RESOURCE` death reason | Resource usage per run recorded | [P] fuzzed strategies (infinite loop, fork bomb, huge alloc) ⇒ sandbox kills, host unaffected |
| F7.2 | Secret leakage (API keys in logs/reports) | Secrets only via environment; logging redaction filter (key-pattern + env-name aware); reports generated from the registry (which never contains secrets) | Log-scan in CI (secret patterns) | Integration: run with fake keys ⇒ no key bytes in logs/reports/DB |
| F7.3 | Accidental live trading | Live module **disabled by default**: absent adapter + config flag + separate enable command (`evoltrade live enable --acknowledge-risk`) + per-kill-switches; paper is the default "realistic" mode | Live status visible on Dashboard and Live UI | Integration (negative): live attempt without enablement ⇒ refused + audit |
| F7.4 | Unbounded API abuse / unauthenticated mutation | API keys (hashed, scoped) + local auth; mutating endpoints require write scope; rate limiting; read-only default DB role for the API process | Audit log on every mutation | Load + auth negative tests |
| F7.5 | Tampered audit trail | Audit log = **hash-chained** append-only table (each row hashes the previous); daily integrity check | Chain verification job | Unit: middle-row edit ⇒ chain breaks |
| F7.6 | One user's bad dataset poisons shared results | Datasets are namespaced + versioned + quality-gated; experiments reference versions, not names; quality flags propagate to reports | Dataset provenance on every experiment | Integration |

## F8. PROJECT-LEVEL FAILURE MODES (process risks)

| # | Risk | Mitigation |
|---|---|---|
| F8.1 | **Scope creep** ("build everything at once") | Phased roadmap with exit criteria (proposal §26); Phase 1 is a *vertical slice* that proves the core loop; nothing in Phases 2–5 blocks Phase 1 |
| F8.2 | **Data starvation** (no good free data ⇒ engine never validated) | Phase 1 bundles a **reference dataset** (synthetic-but-realistic T0 generated by the seeded synthetic exchange + a real free dataset via ccxt/yfinance); the golden suite runs on both |
| F8.3 | **Benchmark theater** (perf claims without pinned measurements) | Benchmarks are CI jobs with stored baselines and regression alerts (events/s, fills/s, backtests/worker, API p95) |
| F8.4 | **Determinism erosion** (someone adds `time.time()` / `set` iteration in a hot path) | Lint rules (banned APIs in core), code review checklist, and the determinism test in CI catches regressions immediately |
| F8.5 | **Metric inflation** (UI shows only in-sample, cost-free results) | Report schema **requires** cost-inclusive, tier-labeled, engine-versioned metrics; UI defaults to the full view |
| F8.6 | **Single-maintainer bus factor on the evolution core** | Core modules are small, documented with ADRs, and covered by the golden + property suites so any change is immediately validated |

## Invariant ledger (the eight always-true statements)

1. **I-1 No phantom money**: ledger balanced; cash = ledger view; no money setter exists.
2. **I-2 No double fill**: per-order fills disjoint, Σ ≤ qty.
3. **I-3 Fill ≤ order quantity** (and ≥ 0) always.
4. **I-4 No fee twice**: one fee entry per fill; total == recomputation.
5. **I-5 Position reconciliation**: positions == Σ fills (recomputed), exactly.
6. **I-6 Ledger reconciliation**: Σ entries → equity == account views, at all checkpoints.
7. **I-7 Deterministic replay**: same spec+dataset+seed ⇒ identical event log hash.
8. **I-8 Point-in-time**: no strategy access to data with ts > current sim time, ever.

Every invariant has (a) a by-construction enforcement point and (b) a property test in CI.
If any invariant can be violated, the run aborts with an `ENGINE_INTEGRITY_VIOLATION` event —
**failure is loud, never silent.**
