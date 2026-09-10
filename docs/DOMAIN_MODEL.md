# Domain Model

## Market
Instrument, MarketTick, Quote/Trade extensions, OrderBook.

## Trading
OrderIntent -> Order -> Fill -> Fee.

## Capital
Ledger -> Position -> Portfolio. Strategy code never writes capital state.

## Evolution
StrategyGenome -> Individual -> Population -> Generation -> Fitness -> Lineage. Failed individuals remain addressable through cemetery/death records.

## Experiments
Dataset + genome + engine + execution/risk assumptions + seed -> immutable ExperimentResult.
