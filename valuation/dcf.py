"""
Acquisition Underwriting Model
-------------------------------
Translates annual revenue into investor-level returns — the output an acquisitions
team produces when underwriting a BESS asset:

  Project IRR  — return on total capital (debt + equity)
  Equity IRR   — return on the equity cheque
  Equity MOIC  — multiple on invested capital (equity)

Model structure (simplified but correct):
  Year 0:  Pay CapEx  →  funded by equity + term loan
  Years 1–N: Revenue − OpEx − Debt Service = Equity Free Cash Flow
             Debt amortizes on a straight 20-year schedule

Degradation is applied: revenue falls 2%/yr as battery capacity fades.
No taxes in the base model — keeps it transparent and avoids guessing the LP
structure.  A full model would layer in MACRS depreciation and ITC/IRA credits.
"""

import numpy as np
import numpy_financial as npf


def build_cash_flows(
    annual_revenue: float,
    power_mw: float,
    capacity_mwh: float,
    capex_per_kwh: float,
    opex_per_mw_year: float,
    project_life: int,
    debt_ratio: float,
    debt_rate: float,
    annual_degradation: float,
) -> dict:
    """
    Build year-by-year cash flow schedules.

    Returns a dict with:
        capex, equity, debt_principal
        project_cf  — list[float] for project IRR  (year 0 = -capex)
        equity_cf   — list[float] for equity IRR   (year 0 = -equity)
        rows        — list of dicts for the dashboard table
    """
    capex          = capacity_mwh * 1_000 * capex_per_kwh   # MWh → kWh → $
    opex           = power_mw * opex_per_mw_year
    equity         = capex * (1 - debt_ratio)
    debt_principal = capex * debt_ratio
    annual_payment = _flat_debt_service(debt_principal, debt_rate, project_life)

    project_cf = [-capex]
    equity_cf  = [-equity]
    rows       = []

    remaining_debt = debt_principal
    for yr in range(1, project_life + 1):
        # Revenue degrades with battery capacity
        rev = annual_revenue * ((1 - annual_degradation) ** (yr - 1))

        # Debt service split into interest + principal
        interest   = remaining_debt * debt_rate
        principal  = annual_payment - interest
        remaining_debt = max(0, remaining_debt - principal)

        ebitda     = rev - opex
        equity_fcf = ebitda - annual_payment

        project_cf.append(ebitda)
        equity_cf.append(equity_fcf)
        rows.append({
            "Year":          yr,
            "Revenue ($M)":  round(rev / 1e6, 2),
            "OpEx ($M)":     round(opex / 1e6, 2),
            "EBITDA ($M)":   round(ebitda / 1e6, 2),
            "Debt Svc ($M)": round(annual_payment / 1e6, 2),
            "Equity FCF ($M)": round(equity_fcf / 1e6, 2),
        })

    return {
        "capex":         capex,
        "equity":        equity,
        "debt_principal": debt_principal,
        "project_cf":    project_cf,
        "equity_cf":     equity_cf,
        "rows":          rows,
    }


def compute_returns(cf: dict) -> dict:
    """Compute IRR, NPV, and MOIC from the cash flow dict."""
    project_irr = npf.irr(cf["project_cf"])
    equity_irr  = npf.irr(cf["equity_cf"])

    # Equity MOIC = total cash returned / equity invested
    total_equity_in  = abs(cf["equity_cf"][0])
    total_equity_out = sum(x for x in cf["equity_cf"][1:] if x > 0)
    moic = total_equity_out / total_equity_in if total_equity_in > 0 else 0

    return {
        "project_irr": project_irr,
        "equity_irr":  equity_irr,
        "moic":        moic,
    }


def irr_sensitivity(
    annual_revenue: float,
    power_mw: float,
    capacity_mwh: float,
    opex_per_mw_year: float,
    project_life: int,
    debt_ratio: float,
    debt_rate: float,
    annual_degradation: float,
    capex_range: list,
    price_multipliers: list,
) -> dict:
    """
    Build a 2-D sensitivity grid:
        rows    = price multipliers  (demand / price scenarios)
        columns = CapEx ($/kWh)      (cost scenarios)
        values  = equity IRR
    """
    grid = {}
    for pm in price_multipliers:
        row = {}
        rev = annual_revenue * pm
        for cpx in capex_range:
            cf = build_cash_flows(
                annual_revenue=rev,
                power_mw=power_mw,
                capacity_mwh=capacity_mwh,
                capex_per_kwh=cpx,
                opex_per_mw_year=opex_per_mw_year,
                project_life=project_life,
                debt_ratio=debt_ratio,
                debt_rate=debt_rate,
                annual_degradation=annual_degradation,
            )
            ret = compute_returns(cf)
            row[cpx] = ret["equity_irr"]
        grid[pm] = row
    return grid


# ── Internal helper ────────────────────────────────────────────────────────

def _flat_debt_service(principal: float, rate: float, years: int) -> float:
    """Level annual debt service (mortgage-style amortization)."""
    if rate == 0:
        return principal / years
    return principal * rate / (1 - (1 + rate) ** (-years))
