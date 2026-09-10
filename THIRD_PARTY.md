# EVOLTRADE — THIRD_PARTY.md

Dependency & license register. **All licenses/activity verified via GitHub API on 2026-09-10**
(evidence: [`docs/phase0/github_repos.tsv`](docs/phase0/github_repos.tsv)).
Exact minor versions are pinned at Phase 1 start into the lockfile; the *major line* is recorded
below.

## License policy (strict free core)

| Class | Licenses | Allowed where |
|---|---|---|
| **Permissive (core-OK)** | MIT, Apache-2.0, BSD-2/3, ISC, PostgreSQL License | anywhere, including core |
| **Weak copyleft (core-OK with note)** | MPL-2.0 (file-scoped), LGPL-3.0 (separately-replaceable drivers only, e.g. DB client) | core, with per-item review note |
| **Strong copyleft (core-NOT-OK)** | GPL-2/3, AGPL-3/3 | **optional standalone processes** only (never imported by core); e.g. Grafana as a separate observability appliance |
| **Source-available / fair-code (rejected for core)** | SSPL, RSALv2, Commons Clause, custom "open-core" | **never** in the core; at most optional out-of-process tools the user may choose |
| **Proprietary / SaaS** | — | **never** in the core; optional user-keyed provider plugins only (user accepts their own terms) |

Rules:
1. Any new dependency requires a PR that adds its row to this file (license + purpose + review).
2. Core = the deterministic simulation/accounting/evolution code paths. "Core" code may only
   import classes *Permissive* (and the two noted weak-copyleft drivers).
3. Plugins run in worker processes; a GPL/AGPL plugin is tolerated as a **user-installed,
   separately-installed, clearly-labeled** package (it must not be shipped in our distributions).
4. No dependency may be *mandatory* and *paid*. Paid feeds (Polygon, Databento, …) are optional
   provider plugins that the user enables with their own keys.

---

## A. Core engine (Python 3.12)

| Package | Version line | License | URL | Purpose | Restrictions | Compatibility |
|---|---|---|---|---|---|---|
| numpy | 2.x | BSD + patent clause (permissive) | [numpy.org](https://github.com/numpy/numpy) | numeric arrays, distributions | none | ✔ core |
| scipy | 1.16+ | BSD-3 | [scipy.org](https://github.com/scipy/scipy) | stats, clustering (speciation), optimization | none | ✔ core |
| polars | 1.44 | MIT | [polars.rs](https://github.com/pola-rs/polars) | data frame / query engine | none | ✔ core |
| duckdb | 1.5 | MIT | [duckdb.org](https://github.com/duckdb/duckdb) | in-process analytics over Parquet | none | ✔ core |
| pyarrow | 18+ | Apache-2.0 | [arrow.apache.org](https://arrow.apache.org) | Parquet/IPC, zero-copy | none | ✔ core |
| msgspec | 0.21 | BSD-3 | [msgspec](https://github.com/msgspec/msgspec) | fast event (de)serialization | none | ✔ core |
| orjson | 3.12 | Apache-2.0 | [orjson](https://github.com/ijl/orjson) | JSON I/O (API/IO) | none | ✔ core |
| networkx | 3.x | BSD (custom, permissive) | [networkx.org](https://github.com/networkx/networkx) | lineage/evolution graph algorithms | none | ✔ core |
| PyYAML | 6.0 | MIT | [pyyaml.org](https://github.com/yaml/pyyaml) | config/strategy YAML | none | ✔ core |
| quantstats | 0.0.81 | Apache-2.0 | [quantstats](https://github.com/ranaroussi/quantstats) | metric definitions (Sharpe/Sortino/Drawdown tables) | none | ✔ core (reporting) |
| statsmodels | 0.14+ | BSD-3 | [statsmodels](https://github.com/statsmodels/statsmodels) | research lab stats | none | ✔ core |
| numba | 0.61+ | BSD-2 | [numba](https://github.com/numba/numba) | optional JIT hotspots | none | ✔ optional |
| scikit-learn | 1.7+ | BSD-3 | [scikit-learn](https://github.com/scikit-learn/scikit-learn) | clustering/PCA for behavior descriptors **only** | none | ✔ optional |

## B. Data providers (plugins)

| Package | Version line | License | URL | Purpose | Restrictions | Compatibility |
|---|---|---|---|---|---|---|
| ccxt | 4.5 | MIT | [ccxt](https://github.com/ccxt/ccxt) | exchange public data + connectivity (user keys) | user must comply with exchange ToS | ✔ plugin |
| yfinance | 0.2.x | Apache-2.0 | [yfinance](https://github.com/ranaroussi/yfinance) | free public equity/FX data | Yahoo ToS; no SLA; rate limits | ✔ plugin (declared lower-quality tier) |
| Alpha Vantage / Polygon / Databento (optional) | — | proprietary APIs, **free tiers exist** | — | extra history via **user-provided keys** | user's own license/terms; **never a core assumption**; paid plans not required | ✔ optional plugin |
| User CSV/Parquet | — | — | — | user-provided datasets | user's data license is the user's responsibility | ✔ core feature |
| pandera | 0.33 | MIT | [pandera](https://github.com/unionai-oss/pandera) | schema/statistical validation at ingest | none | ✔ core (ingest) |
| DVC | 3.67 | Apache-2.0 | [dvc.org](https://github.com/iterative/dvc) | optional dataset versioning | none | ✔ optional |

## C. Server / API

| Package | Version line | License | URL | Purpose | Restrictions | Compatibility |
|---|---|---|---|---|---|---|
| fastapi | 0.141 | MIT | [fastapi](https://github.com/fastapi/fastapi) | REST API | none | ✔ |
| pydantic | 2.13 | MIT | [pydantic](https://github.com/pydantic/pydantic) | schemas/validation (shared with core via codegen) | none | ✔ |
| sqlalchemy | 2.0 | MIT (re-licensed) | [sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) | ORM | none | ✔ |
| alembic | 1.19 | MIT | [alembic](https://github.com/sqlalchemy/alembic) | migrations | none | ✔ |
| psycopg | 3.2+ | **LGPL-3.0** | [psycopg](https://github.com/psycopg/psycopg) | PostgreSQL driver | LGPL: separately-replaceable driver (pure-Python fallback exists: `psycopg` pure mode / `pg8000`); keep as swappable component | ✔ (noted) |
| uvicorn | 0.52 | BSD-3 | [uvicorn](https://github.com/encode/uvicorn) | ASGI server | none | ✔ |
| uvloop | 0.22 | Apache-2.0 | [uvloop](https://github.com/MagicStack/uvloop) | fast event loop | none | ✔ |
| httpx | 0.28+ | BSD-3 | [httpx](https://github.com/encode/httpx) | HTTP client (providers, tests) | none | ✔ |
| websockets | 15+ | BSD-3 | [websockets](https://github.com/aaugustin/websockets) | replay sessions | none | ✔ |
| structlog | 26.x | BSD (verify at pin) | [structlog](https://github.com/hynek/structlog) | JSON logging | none | ✔ |
| Typer | 0.27 | MIT | [typer](https://github.com/fastapi/typer) | CLI | none | ✔ |
| rich | 13+ | MIT | [rich](https://github.com/Textualize/rich) | CLI output | none | ✔ |
| textual | 8.x | MIT | [textual](https://github.com/Textualize/textual) | CLI TUI (replay) | none | ✔ optional |
| PyJWT | 2.x | MIT | [pyjwt](https://github.com/jpadilla/pyjwt) | tokens | none | ✔ |
| argon2-cffi | 23+ | MIT | [argon2-cffi](https://github.com/hynek/argon2-cffi) | password hashing | none | ✔ |
| cryptography | 44+ | Apache-2.0/MIT dual + OpenSSL | [cryptography](https://github.com/pyca/cryptography) | TLS, key handling | none | ✔ |
| prometheus-client | 0.21+ | Apache-2.0 | [prometheus](https://github.com/prometheus/client_python) | metrics | none | ✔ |
| opentelemetry-python | 1.x | Apache-2.0 | [otel](https://github.com/open-telemetry/opentelemetry-python) | tracing | none | ✔ |
| Jinja2 | 3.1 | BSD-3 | [jinja2](https://github.com/pallets/jinja2) | report templates | none | ✔ |
| WeasyPrint | 62+ | BSD-3 | [weasyprint](https://github.com/Kozea/WeasyPrint) | PDF reports (optional) | system libs (pango/cairo) | ✔ optional |
| celery | 5.6 | BSD-style (verify at pin) | [celery](https://github.com/celery/celery) | distributed workers (Phase 2) | none | ✔ Phase 2 |
| valkey-py | 9.x | BSD-3 (client BSD/see project) | [valkey](https://github.com/valkey-io/valkey) | broker/cache (Phase 2) | none | ✔ Phase 2 |
| PostgreSQL (server) | 16+ | PostgreSQL License | [postgresql.org](https://www.postgresql.org) | metadata DB | none | ✔ |
| Valkey (server) | 9.x | BSD-3 | [valkey.io](https://valkey.io) | cache/pub-sub (Phase 2) | none | ✔ |
| Ray | 2.x | Apache-2.0 | [ray.io](https://github.com/ray-project/ray) | evolution farm (Phase 3) | none | ✔ optional Phase 3 |

## D. Frontend

| Package | Version line | License | URL | Purpose | Restrictions | Compatibility |
|---|---|---|---|---|---|---|
| next | 16.x | MIT | [nextjs.org](https://github.com/vercel/next.js) | app framework (App Router) | none | ✔ |
| react / react-dom | 19.x | MIT | [react](https://github.com/facebook/react) | UI runtime | none | ✔ |
| typescript | 5.x | Apache-2.0 | [typescript](https://github.com/microsoft/TypeScript) | language | none | ✔ |
| tailwindcss | 4.x | MIT | [tailwindcss](https://github.com/tailwindlabs/tailwindcss) | design tokens/stylesheet | none | ✔ |
| shadcn/ui (components) | — | MIT (you own the code) | [shadcn/ui](https://github.com/shadcn-ui/ui) | accessible primitives | none | ✔ |
| @tanstack/react-query | 5.x | MIT | [tanstack](https://github.com/TanStack/query) | server state | none | ✔ |
| @tanstack/react-table | 8.x | MIT | [tanstack](https://github.com/TanStack/table) | data-dense grids | none | ✔ |
| zustand | 5.x | MIT | [zustand](https://github.com/pmndrs/zustand) | client state | none | ✔ |
| echarts | 6.x | Apache-2.0 | [echarts](https://github.com/apache/echarts) | analytics viz (Pareto, maps, trees) | none | ✔ |
| lightweight-charts | 5.x | Apache-2.0 | [lightweight-charts](https://github.com/tradingview/lightweight-charts) | candles/trades/book in Replay | none | ✔ |

## E. Testing

| Package | Version line | License | URL | Purpose | Restrictions | Compatibility |
|---|---|---|---|---|---|---|
| pytest | 9.x | MIT | [pytest](https://github.com/pytest-dev/pytest) | test runner | none | ✔ |
| pytest-asyncio | 1.x | Apache-2.0 | [pytest-dev](https://github.com/pytest-dev/pytest-asyncio) | async tests | none | ✔ |
| hypothesis | 6.x | **MPL-2.0** | [hypothesis](https://github.com/hypothesisworks/hypothesis) | property-based invariants | MPL-2.0: file-level copyleft — fine for test code, never product code | ✔ (tests only) |
| pytest-benchmark | 4.x | BSD-2 | [pytest-dev](https://github.com/ionelmc/pytest-benchmark) | micro-benchmarks | none | ✔ |
| vegeta | 12.x | MIT | [vegeta](https://github.com/tsenart/vegeta) | HTTP load tests | none | ✔ |
| locust | 2.3x | MIT (re-licensed) | [locust](https://github.com/locustio/locust) | load scenarios (optional) | none | ✔ optional |
| playwright | 1.x | Apache-2.0 | [playwright](https://github.com/microsoft/playwright) | e2e | none | ✔ |
| vitest | 3.x | MIT | [vitest](https://github.com/vitest-dev/vitest) | frontend unit | none | ✔ |
| @testing-library/react | 16.x | MIT | [testing-library](https://github.com/testing-library/react-testing-library) | frontend component tests | none | ✔ |

## F. Explicitly NOT used (and why)

| Project | License (verified) | Reason for rejection |
|---|---|---|
| NautilusTrader | LGPL-3.0 | copyleft; architecture **borrowed**, not imported |
| backtrader | GPL-3.0, frozen 2024 | copyleft + unmaintained |
| backtesting.py | AGPL-3.0 | network copyleft |
| freqtrade | GPL-3.0 | copyleft; bot-shaped, not lab-shaped |
| vectorbt | Apache-2.0 + **Commons Clause** | fair-code; cannot be the core of a product |
| zipline (original) | Apache-2.0, **archived** | unmaintained |
| OpenBB | custom open-core | platform, not engine; custom license |
| Redis ≥ 7.4 | **SSPL/RSALv2 (+AGPLv3)** | source-available, not OSI; **Valkey** used instead |
| Weights & Biases | proprietary SaaS | SaaS in core forbidden |
| MLflow / ClearML (as registry) | Apache-2.0 | ML-model-shaped; our registry is custom; kept as optional exporters |
| Grafana (as dependency) | AGPL-3.0 | standalone appliance only, separate process |
| TA-Lib C core | BSD-3 (core) | binary-distribution friction; we implement indicators in-house (pandas-ta MIT as reference) |
| Kubernetes | Apache-2.0 | deployment choice, not a dependency — not used until real need (spec §79) |

## G. Review status

- [x] All core/server/frontend/test dependencies verified permissive (2026-09-10).
- [x] All rejected items documented with reasons.
- [ ] To do at Phase 1 start: freeze exact versions in lockfile; re-verify `structlog`, `celery`,
  `valkey-py` license files; re-locate `gplearn` canonical repo (BSD-3 per PyPI).
