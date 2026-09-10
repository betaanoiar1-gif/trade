# EVOLTRADE — PHASE 0: OPEN-SOURCE ECOSYSTEM SURVEY

Date: 2026-09-10 · All licenses and activity **verified via GitHub API** on this date
(raw evidence: [`docs/phase0/github_repos.tsv`](phase0/github_repos.tsv)).

Decision key:
- **ADOPT** — becomes a core dependency (license-clean, fits)
- **ADOPT-OPT** — optional dependency / separate module (license-clean, useful but not core)
- **BORROW** — no code dependency; we study and reuse its architecture/patterns
- **REJECT** — not used (license conflict, frozen, or wrong fit)

Performance figures marked *(est.)* are our estimates from published benchmarks/behavior; the rest
are the project's own claims.

---

## 1. Event-driven trading engines & backtesting

| Project | GitHub | License | Last push | Stars | Decision |
|---|---|---|---|---|---|
| NautilusTrader | [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader) | **LGPL-3.0** | 2026-09-10 | 28.7k | **BORROW** |
| QuantConnect LEAN | [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | Apache-2.0 | 2026-09-09 | 21.6k | **BORROW** |
| Hummingbot | [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot) | Apache-2.0 | 2026-09-09 | 20.0k | **BORROW** (+ADOPT-OPT for exchange connectors) |
| Freqtrade | [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | **GPL-3.0** | 2026-09-10 | 54.2k | **REJECT** (core); BORROW strategy API ideas |
| backtesting.py | [kernc/backtesting.py](https://github.com/kernc/backtesting.py) | **AGPL-3.0** | 2026-08-05 | 9.0k | **REJECT** (core) |
| vectorbt | [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | **Apache-2.0 + Commons Clause** (fair-code) | 2026-08-02 | 9.1k | **REJECT** (core); BORROW vectorized screening ideas |
| backtrader | [mementum/backtrader](https://github.com/mementum/backtrader) | **GPL-3.0** | 2024-08-19 | 23.2k | **REJECT** (frozen + GPL) |
| zipline-reloaded | [stefan-jansen/zipline-reloaded](https://github.com/stefan-jansen/zipline-reloaded) | Apache-2.0 | 2026-01-06 | 1.9k | **BORROW** (pipeline API, data bundles) |
| zipline (Quantopian) | [quantopian/zipline](https://github.com/quantopian/zipline) | Apache-2.0 | **archived** 2024-02 | 20.1k | **REJECT** (archived) |
| OpenBB | [openbb-finance/openbb](https://github.com/openbb-finance/openbb) | Custom (open-core) | 2026-07-30 | 72.9k | **REJECT** (core); data platform, not an engine |
| PyBroker | [edtechre/pybroker](https://github.com/edtechre/pybroker) | Custom (unresolved by API) | 2026-09-07 | 3.5k | **BORROW** (ML-walk-forward patterns; license to verify before any use) |
| FinRL / Qlib | (research) | varies | — | — | **REJECT** (core): ML/RL — violates "no AI in core"; research references only |

**Notes.**
- **NautilusTrader** is the closest existing system to what we need (deterministic event-driven
  architecture, adaptive matching engine, Rust core, same code backtest↔live). It is the single
  best **architecture reference** for: event bus design, catalog/data model, matching engine
  abstraction, determinism discipline. *Why not a dependency: LGPL-3.0* — importing it into our
  MIT/Apache core creates copyleft obligations we must not take on; it is also a large
  dependency that would constrain our genome-as-data model (its strategies are Python classes,
  not evolvable data).
- **LEAN** (Apache-2.0) validates the "research/live parity via a message bus" pattern and is an
  excellent reference for order lifecycle semantics across many assets; C# core makes it unsuitable
  as our dependency, but its `BrokerageBase`/`FillModel` abstractions are directly borrowable.
- **Hummingbot** (Apache-2.0) is the best reference for: exchange connector architecture, paper
  trading, crypto market-making loops, order book reconstruction from exchange streams. Its
  exchange adapters can be used as *optional provider plugins* (it is Apache-2.0).
- **Freqtrade** (GPL-3.0): excellent community, but GPL in-process import conflicts with a
  permissive core; strategy API (candles in → orders out) is a useful UX reference only.
- **vectorbt**: fastest research sweeps in Python, but the Commons Clause forbids selling products
  whose primary value is this software — unacceptable for a platform whose core *is* the engine.
  Its vectorized approach inspires our **fast pre-screening tier** (implemented natively, no
  dependency).
- **backtrader / backtesting.py / zipline (original)**: frozen or AGPL — historical references only.
- **zipline-reloaded**: good "data bundle + pipeline" ideas; US-equity bundle model doesn't fit our
  multi-provider, multi-asset data layer.

**Conclusion for cluster:** no incumbent is both license-clean *and* fit for
"evolvable strategies as data + deterministic ledger + evolutionary population at scale".
→ **Build the core engine; borrow architecture from NautilusTrader/LEAN/Hummingbot.**

---

## 2. Matching engines, order books, LOB simulation

| Project | GitHub | License | Activity | Decision |
|---|---|---|---|---|
| ABIDES | [abides-sim/abides](https://github.com/abides-sim/abides) | No standard license file (NOASSERTION) | last push 2023 | **BORROW methodology** (agent-based, stylized facts, interactive discrete events; do not copy code) |
| DeepMarket (TRADES) | [LeonardoBerti00/DeepMarket](https://github.com/LeonardoBerti00/DeepMarket) | MIT | 2026-01, small | **BORROW/ADOPT-OPT** (diffusion-based LOB simulation — optional research module *only*, AI-adjacent, never in deterministic core) |
| C++ LOB simulators (3yit, mansoor-mamnoon) | various | varies | recent | **BORROW** (price-time priority data layout, FIFO ladders, microsecond timestamps) |
| NautilusTrader matching engine | (part of #1) | LGPL-3.0 | active | **BORROW** (adaptive fill model, fill model configurability) |
| Hummingbot market/LOB utilities | (part of #1) | Apache-2.0 | active | **ADOPT-OPT** (book reconstruction from exchange snapshots/updates) |

**Conclusion for cluster:** the matching core (book + queue + matching tiers) is **built in-house**
— it is a core differentiator (declared synthetic tiers, queue-model plugins, audit of every fill).
ABIDES gives the research methodology for synthetic exchange agents; C++ LOB codebases give data
layout patterns (intrusive FIFO ladders, price ladders) for a future compiled core.

---

## 3. Evolutionary computation

| Project | GitHub | License | Activity | Decision |
|---|---|---|---|---|
| DEAP | [DEAP/DEAP](https://github.com/DEAP/DEAP) | **LGPL-3.0** | 2026-04 | **BORROW** (operator/algorithm patterns); optional out-of-process reference only |
| gplearn | (PyPI `gplearn`) | BSD-3-Clause (per PyPI metadata; repo path re-verify at Phase 1) | steady | **BORROW** (genetic expression tree representation for symbolic strategy logic) |
| mnevo | (PyPI `mnevo`) | MIT | dormant (2018) | **REJECT** (neuroevolution; dormant) |

**Prior art (academic, informs design, no code):**
- Brock, Lakonishok, LeBaron (1992) — simple technical trading rules; the canonical problem.
- "Using genetic algorithms to find technical trading rules" (1999) — GA rule discovery.
- NSGA-II + boosting for technical trading systems (2011); GP risk-adjusted technical rules (2011)
  — validates **multi-objective** evolution of trading rules.
- ABIDES (Byrd et al. 2020), TRADES/DeepMarket (2024) — synthetic LOB realism.

**Conclusion for cluster:** DEAP is LGPL (cannot be an in-process core dependency); gplearn is
BSD but scikit-learn-bound and designed for symbolic regression, not trading genomes with
execution/risk sub-blocks. **We build our own evolution core** (it is a core differentiator:
fitness = full experiment results, novelty archive, dynamic speciation, cemetery, checkpoints).
References inform operator design; no heavy dependency is needed (numpy-based population ops).

---

## 4. Portfolio optimization

| Project | GitHub | License | Activity | Decision |
|---|---|---|---|---|
| PyPortfolioOpt | [robertmartin8/PyPortfolioOpt](https://github.com/robertmartin8/PyPortfolioOpt) | MIT | 2026-07 | **ADOPT-OPT** (mean-variance / Black-Litterman baselines for allocator evaluation) |
| Riskfolio-Lib | [dcajasn/Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib) | BSD-3-Clause | 2026-08 | **ADOPT-OPT** (risk measures; good coverage) |
| cvxpy | [cvxpy/cvxpy](https://github.com/cvxpy/cvxpy) | Apache-2.0 | 2026-09 | **ADOPT-OPT** (convex allocation problems under risk constraints) |

**Conclusion:** the *evolvable* allocator is ours (genome-driven); these libraries provide
**non-evolved baselines** to compare against (a portfolio-evolution result must beat a
cvxpy/constrained baseline to mean anything).

---

## 5. Numerics, statistics, Monte Carlo

| Project | License | Activity | Decision |
|---|---|---|---|
| NumPy (BSD + patent clause) | active | **ADOPT** |
| SciPy (BSD-3) | active | **ADOPT** (distributions, clustering for speciation) |
| Numba (BSD-2) | active | **ADOPT-OPT** (JIT hotspots if Python proves too slow) |
| statsmodels (BSD-3) | active | **ADOPT** (regression/diagnostics in research lab) |
| scikit-learn (BSD-3) | active | **ADOPT-OPT** (clustering/PCA for behavior descriptors only — *not* predictive ML in the core loop) |
| QuantStats (Apache-2.0) | 2026-01 | **ADOPT** (metric/reporting definitions: Sharpe, Sortino, Ulcer, drawdown tables) |

---

## 6. Data, versioning, experiment tracking

| Project | GitHub | License | Activity | Decision |
|---|---|---|---|---|
| Polars | [pola-rs/polars](https://github.com/pola-rs/polars) | MIT | 2026-09 | **ADOPT** (data frame engine) |
| DuckDB | [duckdb/duckdb](https://github.com/duckdb/duckdb) | MIT | 2026-09 | **ADOPT** (in-process analytics over Parquet) |
| PyArrow/Arrow | (Apache-2.0) | active | **ADOPT** (Parquet/IPC, zero-copy) |
| DVC | [iterative/dvc](https://github.com/iterative/dvc) | Apache-2.0 | 2026-09 | **ADOPT-OPT** (dataset versioning alternative/complement) |
| ArcticDB | [man-group/ArcticDB](https://github.com/man-group/ArcticDB) | Custom (verify) | 2026-09 | **ADOPT-OPT** (tick-scale storage candidate for Phase 4; license verify) |
| MLflow | [mlflow/mlflow](https://github.com/mlflow/mlflow) | Apache-2.0 | 2026-09 | **ADOPT-OPT** (export/integration only — not our registry) |
| ClearML | [ClearML/ClearML](https://github.com/ClearML/ClearML) | Apache-2.0 | 2026-09 | **ADOPT-OPT** (optional) |
| Weights & Biases | (SaaS) | proprietary | — | **REJECT** (SaaS, violates free-core policy) |
| ccxt | [ccxt/ccxt](https://github.com/ccxt/ccxt) | MIT | 2026-09 | **ADOPT** (exchange data + connectivity provider) |
| yfinance | [ranaroussi/yfinance](https://github.com/ranaroussi/yfinance) | Apache-2.0 | 2026-08 | **ADOPT** (free public data provider; ToS-compliant use only) |
| Alpha Vantage / Polygon / Databento | (free tiers, paid plans) | — | — | **ADOPT-OPT** (user-keyed provider plugins; **no core assumption of paid plans**) |
| NetworkX | [networkx/networkx](https://github.com/networkx/networkx) | BSD (custom) | 2026-09 | **ADOPT** (lineage/evolution graph algorithms) |

**Conclusion:** our **experiment registry (EVL-…) is built in-house** (content-addressed,
immutable, trading-specific) — MLflow is ML-model-shaped and would fight our model. DVC remains
optional for large dataset versioning.

---

## 7. Orchestration, workers, distribution, cache

| Project | GitHub | License | Activity | Decision |
|---|---|---|---|---|
| Celery | [celery/celery](https://github.com/celery/celery) | BSD-style (NOASSERTION; verify at pin) | 2026-09 | **ADOPT (Phase 2)** distributed task queue |
| Valkey | [valkey-io/valkey](https://github.com/valkey-io/valkey) | **BSD-3-Clause** | 2026-09 | **ADOPT** (broker/cache from Phase 2; wire-compatible with Redis 7.2) |
| Redis | [redis/redis](https://github.com/redis/redis) | **SSPL/RSALv2 (+AGPLv3) ≥7.4** | 2026-09 | **REJECT** (license change 2024 → use Valkey) |
| Ray | [ray-project/ray](https://github.com/ray-project/ray) | Apache-2.0 | 2026-09 | **ADOPT-OPT (Phase 3)** evolution farm scale-out |
| Dask | [dask/dask](https://github.com/dask/dask) | BSD-3 | 2026-08 | **ADOPT-OPT** (embarrassingly parallel batches) |
| Prefect / Dagster | (Apache-2.0) | active | **REJECT (core)** — pipeline orchestration, not compute farms; usable later for data pipelines |

**Conclusion:** Phase 1 = PG job table + process pool (zero new infra). Interfaces
(`WorkerPool`, `JobQueue`) are designed so Phase 2 = Celery+Valkey and Phase 3 = Ray without API
changes.

---

## 8. Backend stack

| Project | License | Activity | Decision |
|---|---|---|---|
| FastAPI | MIT | 2026-09 | **ADOPT** |
| Pydantic v2 | MIT | 2026-09 | **ADOPT** |
| SQLAlchemy 2.0 | **MIT** (re-licensed from MPL) | 2026-09 | **ADOPT** |
| Alembic | MIT | 2026-09 | **ADOPT** |
| psycopg 3 | **LGPL-3.0** | 2026-08 | **ADOPT** (DB driver; LGPL driver is acceptable as a separately-replaceable component — noted in THIRD_PARTY) |
| Uvicorn (+ uvloop Apache-2.0) | BSD-3 | 2026-09 | **ADOPT** |
| httpx | BSD-3 | steady | **ADOPT** (client + API tests) |
| websockets | BSD-3 | 2026-08 | **ADOPT** (replay sessions) |
| msgspec | BSD-3 | 2026-09 | **ADOPT** (fast event (de)serialization) |
| orjson | Apache-2.0 | 2026-08 | **ADOPT** (API JSON) |
| Typer + Rich (+ Textual opt) | MIT | 2026-09 | **ADOPT** (CLI; TUI for `evoltrade replay`) |
| structlog | BSD (verify) | 2026-09 | **ADOPT** (JSON logging) |
| PyJWT / argon2-cffi / cryptography | MIT/MIT/dual-permissive | active | **ADOPT** (auth) |
| Prometheus client / OpenTelemetry-Python | Apache-2.0 | active | **ADOPT** (observability) |
| Grafana | **AGPL-3.0** | 2026-09 | **ADOPT-OPT** (standalone observability appliance, separate process; never a dependency) |

**Alternatives compared** (see proposal §18 for the full matrix): Django/DRF (heavier, less
native async/typing fit), Flask (less structured), Go/Actix services (wrong ecosystem for the
Python core), NestJS (splits the backend from the core language).

**Conclusion:** FastAPI+Pydantic+SQLAlchemy+PG is **confirmed on merit** (async-native, typed
schemas shared with the core via codegen, best-in-class OpenAPI), not by habit.

---

## 9. Frontend

| Project | License | Activity | Decision |
|---|---|---|---|
| Next.js | MIT | 2026-09 | **ADOPT** (App Router, RSC for data-dense pages) |
| TypeScript | Apache-2.0 | active | **ADOPT** |
| Tailwind CSS | MIT | 2026-09 | **ADOPT** (design tokens layer) |
| shadcn/ui | MIT | 2026-09 | **ADOPT** (accessible primitives, owned components) |
| TanStack Query / Table | MIT | 2026-09 | **ADOPT** (server state + data-dense grids) |
| Zustand | MIT | 2026-09 | **ADOPT** (client state) |
| **Apache ECharts** | Apache-2.0 | 2026-09 | **ADOPT** (analytics: equity, Pareto, population maps, evolution tree via graph) |
| **Lightweight Charts** | Apache-2.0 | 2026-08 | **ADOPT** (candles/trades/order-book markers in Replay) |
| Plotly.js | MIT | active | **REJECT** (bundle weight and interaction performance on 100k+ point datasets; ECharts canvas wins) |
| Vite + Vitest / Playwright / React Testing Library | MIT / Apache-2.0 / MIT | active | **ADOPT** (testing) |

**Alternatives considered:** React+Vite SPA (no RSC; replay pages benefit from server streaming),
Svelte/SvelteKit (smaller ecosystem for data grids/charts integration), Angular (heavier, poor
fit). Decision rationale in proposal §17.

---

## 10. Testing & load

| Project | License | Activity | Decision |
|---|---|---|---|
| pytest (+ pytest-asyncio Apache-2.0) | MIT | 2026-09 | **ADOPT** |
| Hypothesis | **MPL-2.0** | 2026-09 | **ADOPT** (property-based invariants; MPL is a free copyleft license, acceptable — documented) |
| pytest-benchmark | BSD-2 | 2026-08 | **ADOPT** |
| vegeta | MIT | steady | **ADOPT** (HTTP load tests, single binary) |
| Locust | MIT (re-licensed from AGPL) | 2026-09 | **ADOPT-OPT** (Python-based load scenarios) |
| Playwright | Apache-2.0 | 2026-09 | **ADOPT** (e2e) |

---

## 11. Data quality & reports

| Project | License | Activity | Decision |
|---|---|---|---|
| pandera | MIT | 2026-09 | **ADOPT** (schema + statistical validation on ingest) |
| Great Expectations | Apache-2.0 | 2026-09 | **ADOPT-OPT** (heavier; pandera covers v1) |
| Jinja2 | BSD-3 | steady | **ADOPT** (HTML/MD reports) |
| WeasyPrint | BSD-3 | 2026-09 | **ADOPT-OPT** (PDF reports — optional) |

---

## 12. Cross-cutting survey conclusions

1. **No existing OSS project is "an evolutionary trading laboratory".** The closest pieces exist
   separately (engines, GA libraries, LOB simulators, experiment trackers). Our value is the
   *integration contract*: genome-as-data + deterministic ledger + Pareto/novelty evolution +
   immutable audited experiments. → **build core, borrow periphery.**
2. **Licensing is the sharpest filter**: the two most relevant engines (NautilusTrader LGPL,
   freqtrade/backtrader GPL, backtesting.py AGPL, vectorbt Commons Clause) are all unsuitable as
   in-process dependencies for a permissive core. This is a *design constraint*, not an accident.
3. **Redis is out; Valkey is in.** Everything else in the recommended stack is MIT/Apache/BSD/PSFL
   (full table in `THIRD_PARTY.md`).
4. **Data**: ccxt + yfinance + user files cover the free baseline; exchange APIs and paid feeds
   are optional provider plugins keyed by the user — the core never assumes them.
5. **Synthetic markets**: ABIDES gives the scientific method (stylized-fact validation); we build
   our own seeded agent-based exchange inside the core (deterministic by construction).
