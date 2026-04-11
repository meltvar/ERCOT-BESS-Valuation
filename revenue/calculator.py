"""
Revenue Calculator
------------------
Two revenue streams for a BESS in ERCOT:

1. Energy arbitrage  — net $ from the dispatch simulation (discharge revenue
                        minus charge cost).

2. Ancillary services proxy — ERCOT pays batteries to hold capacity in reserve
   for grid stability (ECRS, Reg-Up, Reg-Down).  When the battery is idle it
   can offer its available power (MW) into these markets.  We use a flat proxy
   rate ($/MW-hr) based on ERCOT's published historical average clearing prices.
   This is clearly a simplification; a full model would use actual clearing price
   time series from ERCOT's ancillary market reports.

The combination of both streams — "revenue stacking" — is how BESS projects
actually pencil out financially.  Arbitrage alone rarely clears the hurdle rate.
"""

import pandas as pd
import numpy as np
from bess.engine import BESSEngine
from bess.dispatch import run_dispatch


def simulate_annual_revenue(
    lmp: pd.Series,
    power_mw: float,
    capacity_mwh: float,
    round_trip_eff: float,
    soc_min: float,
    soc_max: float,
    annual_degradation: float,
    charge_pct: float,
    discharge_pct: float,
    ancillary_rate: float,
    price_multiplier: float = 1.0,
) -> dict:
    """
    Run dispatch over the provided LMP series (scaled by price_multiplier)
    and return a revenue summary dict.

    price_multiplier is used for scenario analysis (0.7x, 1.0x, 1.3x, etc.)
    """
    scaled_lmp = lmp * price_multiplier

    engine = BESSEngine(
        capacity_mwh=capacity_mwh,
        power_mw=power_mw,
        round_trip_eff=round_trip_eff,
        soc_min=soc_min,
        soc_max=soc_max,
        annual_degradation=annual_degradation,
    )

    dispatch_df = run_dispatch(scaled_lmp.values, engine, charge_pct, discharge_pct)

    # ── Energy arbitrage ──────────────────────────────────────────────────
    energy_revenue = dispatch_df["energy_revenue"].sum()   # net (can be negative)

    # ── Ancillary services ────────────────────────────────────────────────
    idle_hours = (dispatch_df["action"] == "idle").sum()
    # Available MW while idle = full power rating (battery isn't doing energy)
    ancillary_revenue = idle_hours * power_mw * ancillary_rate

    total_revenue = energy_revenue + ancillary_revenue

    # ── Cycle stats ───────────────────────────────────────────────────────
    discharge_mwh = dispatch_df.loc[dispatch_df["action"] == "discharge", "grid_mwh"].sum()
    charge_mwh    = dispatch_df.loc[dispatch_df["action"] == "charge",    "grid_mwh"].abs().sum()
    # One full cycle = discharge of full usable capacity
    usable = capacity_mwh * (soc_max - soc_min)
    cycles = discharge_mwh / usable if usable > 0 else 0

    return {
        "energy_revenue":    energy_revenue,
        "ancillary_revenue": ancillary_revenue,
        "total_revenue":     total_revenue,
        "discharge_mwh":     discharge_mwh,
        "charge_mwh":        charge_mwh,
        "idle_hours":        idle_hours,
        "cycles":            cycles,
        "dispatch_df":       dispatch_df,
    }


def annualize(result: dict, data_months: int = 3) -> dict:
    """
    Scale a simulation result (which covers `data_months` of data) to a
    full-year estimate by simple linear extrapolation.

    Summer months are the highest-revenue period in ERCOT, so annualizing
    from summer data is an optimistic upper bound — worth noting in the pitch.
    """
    scale = 12 / data_months
    return {
        "energy_revenue":    result["energy_revenue"]    * scale,
        "ancillary_revenue": result["ancillary_revenue"] * scale,
        "total_revenue":     result["total_revenue"]     * scale,
        "discharge_mwh":     result["discharge_mwh"]     * scale,
        "charge_mwh":        result["charge_mwh"]        * scale,
        "cycles":            result["cycles"]             * scale,
    }
