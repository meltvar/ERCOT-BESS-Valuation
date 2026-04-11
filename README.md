# ERCOT BESS Valuation

A battery energy storage system (BESS) dispatch simulation, revenue stacking model, and acquisition underwriting tool built on ERCOT real-time market settlement price data.

**Three seasons covered:** Summer 2024 · Winter 2024–25 · Summer 2025

---

## Motivation

Excelsior Energy Capital's portfolio company Lydian Energy recently closed **$233M in project financing** for three BESS projects in the ERCOT market, and has since secured a further **$689M** across BESS and solar projects in Texas, New Mexico, and Utah. As a BESS asset becomes operational, an acquisitions team needs to answer one question before committing capital: *what does this asset earn, and at what price does it generate acceptable returns?*

This project models exactly that — combining the physical constraints of a battery (an electrical engineering problem) with the revenue economics and capital structure of a project finance investment (a financial engineering problem).

---

## Dashboard

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ercot-bess-valuation.streamlit.app)

Run locally:

```bash
git clone https://github.com/meltvar/ERCOT-BESS-Valuation.git
cd ERCOT-BESS-Valuation
pip install -r requirements.txt
streamlit run dashboard/app.py
```

---

## Project Structure

```
ercot-bess-valuation/
├── config.py                  # All defaults — battery specs, dispatch thresholds, financial params
├── requirements.txt
│
├── ercot_data/                # ERCOT real-time market settlement prices (4 hubs, 9 months)
│   ├── June_2024.csv          ┐
│   ├── July_2024.csv          ├── Summer 2024
│   ├── August_2024.csv        ┘
│   ├── December_2024.csv      ┐
│   ├── January_2025.csv       ├── Winter 2024–25
│   ├── February_2025.csv      ┘
│   ├── June_2025.csv          ┐
│   ├── July_2025.csv          ├── Summer 2025
│   └── August_2025.csv        ┘
│
├── data/
│   └── loader.py              # Loads and cleans ERCOT CSVs into hourly LMP series
│
├── bess/
│   ├── engine.py              # Physical battery model (SoC, efficiency, C-rate, degradation)
│   └── dispatch.py            # Bang-bang dispatch controller with price-threshold deadband
│
├── revenue/
│   └── calculator.py          # Energy arbitrage + ancillary services revenue stacking
│
├── valuation/
│   └── dcf.py                 # Project/equity IRR, MOIC, sensitivity grid
│
├── dashboard/
│   └── app.py                 # Streamlit dashboard (4 tabs, dark theme)
│
└── notebook/
    └── analysis.ipynb         # Step-by-step narrative walkthrough of the full analysis
```

---

## Methodology

### 1 — Battery Physical Model (`bess/engine.py`)

The engine enforces four real operating constraints that a financial model often ignores:

| Constraint | Value | Why it matters |
|---|---|---|
| Round-trip efficiency | 85% | Split symmetrically: √RTE loss on charge, √RTE on discharge |
| SoC operating window | 10 – 90% | Operating outside this range accelerates Li-ion cell degradation |
| C-rate (power limit) | 0.5C (2-hr battery) | Cannot charge/discharge faster than rated power regardless of headroom |
| Annual capacity degradation | 2%/yr | Li-ion cells lose capacity each year; material over a 20-year project life |

### 2 — Dispatch Logic (`bess/dispatch.py`)

A **bang-bang controller with deadband** — a control-systems concept applied to price-driven dispatch:

```
CHARGE     if LMP < 25th percentile of season prices
DISCHARGE  if LMP > 75th percentile of season prices
IDLE       otherwise  →  earns ancillary services revenue
```

The deadband is intentional: when price is mediocre, holding capacity for ancillary services earns more than marginal arbitrage.

### 3 — Revenue Stacking (`revenue/calculator.py`)

BESS assets earn from two simultaneous streams:

- **Energy arbitrage** — net revenue from charge/discharge spread (discharge revenue minus charge cost, after efficiency losses)
- **Ancillary services** — ERCOT pays batteries to hold reserve capacity for grid stability (ECRS, Reg-Up, Reg-Down). When idle, the battery offers its full MW rating into these markets at a blended proxy rate of ~$8/MW-hr based on ERCOT historical averages

Ancillary services consistently dominate (~87% of total revenue), which is realistic — energy arbitrage alone rarely clears a PE hurdle rate in ERCOT.

### 4 — Acquisition Valuation (`valuation/dcf.py`)

Standard project finance structure:

- **CapEx** funded by 55% debt (6% rate, 20-yr amortization) + 45% equity
- **Revenue** degrades 2%/yr with battery capacity
- **Outputs**: Project IRR, Equity IRR, Equity MOIC, and a 2-D IRR sensitivity grid (CapEx × revenue scenario)

*Model excludes ITC/MACRS. The IRA's 30% ITC on standalone storage (up to 40% with domestic content qualification — relevant given Excelsior's LG ES supply deal) would materially improve equity IRR.*

---

## Key Results

| Season | Total Rev (ann.) | Revenue / MW | Equity IRR | MOIC |
|---|---|---|---|---|
| Summer 2024 | $3.62M / yr | $72k / MW | 12.3% | 2.33× |
| Winter 2024–25 | $3.77M / yr | $75k / MW | 14.0% | 2.55× |
| Summer 2025 | $3.82M / yr | $76k / MW | 14.6% | 2.63× |

Battery: 50 MW / 100 MWh · CapEx: $240/kWh · Hub: HB_WEST · 55% leverage at 6%

Revenue benchmark: $72–76k/MW/yr sits within the published ERCOT BESS range of **$50–100k/MW/yr** for 2024–25.

---

## Data

**Source:** ERCOT Real-Time Market Settlement Point Prices (public, free)  
[ERCOT Market Data Portal](http://www.ercot.com/mp/data-products/data-product-details?id=NP6-785-ER)

**Hubs included:** HB_WEST · HB_NORTH · HB_SOUTH · HB_HOUSTON  
**Granularity:** 15-minute intervals, aggregated to hourly averages  
**Coverage:** June–August 2024, December 2024–February 2025, June–August 2025

---

## Honest Limitations

- **Annualization** — 3-month seasons × 4 is a simplification. A full 12-month dataset would be more robust.
- **Ancillary services proxy** — $8/MW-hr on all idle hours is a conservative estimate. Actual clearing prices vary and battery owners must bid into the market daily.
- **Dispatch strategy** — threshold-based heuristic, not an optimized look-ahead dispatch. A forecasting-based optimizer would earn more.
- **Hub prices** — model uses hub settlement prices. Actual node prices at the interconnection point may differ due to local congestion.
- **No tax modeling** — ITC/MACRS excluded. Full project finance model would layer in tax equity.

---

## Tech Stack

Python · Streamlit · Plotly · pandas · NumPy · numpy-financial
