# Failure Model

| Failure | Prevention / detection |
|---|---|
| Lookahead bias | Event-time APIs, OOS boundaries, leakage tests |
| Unrealistic fills | Liquidity-aware matching, queue/latency plugins |
| Duplicate fills | Stable order/fill identities and quantity invariants |
| Phantom money | Decimal ledger and portfolio reconciliation |
| Wrong fees | Single fee model and reconciliation |
| Latency distortion | Explicit seeded latency model |
| Synthetic contamination | Source/model provenance |
| Survivorship bias | Dataset universe snapshots |
| Evolution overfit | WFA, OOS, robustness, complexity and novelty objectives |
| Premature convergence | Genome/behavior diversity metrics |
| Fitness hacking | Independent metrics and Pareto constraints |

## Core invariants
- Fill quantity never exceeds order quantity.
- Fees are charged exactly once.
- Ledger and portfolio reconcile.
- Identical inputs + seed produce identical event digest.
- Historical replay never receives future observations.
- Synthetic assumptions never masquerade as historical facts.
