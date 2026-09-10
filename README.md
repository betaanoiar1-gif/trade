# EVOLTRADE — Evolutionary Trading Laboratory

A professional platform for **trading simulation, experimentation, and evolutionary research**:
deterministic market simulation, a real $1,000 virtual account, an event-driven broker/matching/
accounting core, evolvable strategies/portfolios/execution policies, synthetic markets, and a full
research lab (robustness, Monte Carlo, counterfactuals, regimes, capacity) — with every result
reproducible and fully auditable.

> **No AI/LLM in the core. Free and open-source core. Live trading disabled by default.**

## Status: PHASE 0 — DISCOVERY & ARCHITECTURAL RESEARCH

This phase is **documentation and design only** — no code is written until the architecture is
approved.

| Document | Contents |
|---|---|
| [ARCHITECTURE_PROPOSAL.md](ARCHITECTURE_PROPOSAL.md) | The full proposal: vision, principles, 3 architecture options + choice, components, data/event flow, domain model, database, strategy/evolution/portfolio/execution models, frontend/backend/plugin/testing/deployment/security/performance/licensing, roadmap, requirements traceability |
| [THIRD_PARTY.md](THIRD_PARTY.md) | Dependency & license table (verified via GitHub API on 2026-09-10) |
| [FAILURE_MODEL.md](FAILURE_MODEL.md) | How the system can fail, and how the design prevents each failure by construction |
| [DOMAIN_MODEL.md](DOMAIN_MODEL.md) | Domain objects, relationships, state machines, invariants |
| [docs/PROBLEM_ANALYSIS.md](docs/PROBLEM_ANALYSIS.md) | Problem decomposition into sub-problems + assumptions challenged |
| [docs/OSS_SURVEY.md](docs/OSS_SURVEY.md) | Open-source ecosystem survey: every candidate tool, license, activity, strengths/weaknesses, decision (adopt / borrow / reject) |
| [docs/phase0/github_repos.tsv](docs/phase0/github_repos.tsv) | Raw GitHub API evidence used for license/activity verification |

## The one-line architecture decision (pending approval)

**Modular monolith + event-sourced simulation core + stateless worker pool.**
Python 3.12 core (Decimal money, event-driven deterministic scheduler), PostgreSQL (metadata) +
Parquet/DuckDB (events & tick data), FastAPI + SSE/WS, Next.js/TypeScript/ECharts frontend,
plugins for everything replaceable, and a content-addressed immutable experiment registry
(`EVL-YYYY-XXXXXXXX`).
