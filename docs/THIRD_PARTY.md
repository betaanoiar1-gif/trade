# Third-party dependency register

Core choices are intentionally permissive/open and kept behind interfaces where replacement is valuable.

- FastAPI — MIT — API
- Pydantic — MIT — validation
- SQLAlchemy — MIT — persistence
- DuckDB — MIT — embedded analytics
- Apache Arrow/PyArrow — Apache-2.0 — columnar data
- Apache ECharts — Apache-2.0 — quantitative visualization
- Next.js — MIT — frontend
- Tailwind CSS — MIT — styling
- Hypothesis — MPL-2.0 — property testing

NautilusTrader and DEAP are **reference-only**, not core dependencies: both are LGPL-3.0 projects. Their architectural/algorithmic ideas can inform adapters without coupling EVOLTRADE's core to them.
