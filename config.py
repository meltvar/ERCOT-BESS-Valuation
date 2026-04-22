import os

# ── Battery physical defaults ──────────────────────────────────────────────
CAPACITY_MWH      = 100    # Total energy storage capacity (MWh)
POWER_MW          = 50     # Max charge / discharge rate (MW) → 2-hour battery (C-rate = 0.5)
ROUND_TRIP_EFF    = 0.85   # Round-trip efficiency: energy out / energy in
SOC_MIN           = 0.10   # Don't discharge below 10% — protects cell longevity
SOC_MAX           = 0.90   # Don't charge above 90% — same reason
ANNUAL_DEGRADATION = 0.02  # Capacity fade per year (2% — typical Li-ion BESS)

# ── Dispatch thresholds ────────────────────────────────────────────────────
# Simple bang-bang controller with deadband:
#   Charge  when LMP < CHARGE_PCT  percentile of the full price series
#   Discharge when LMP > DISCHARGE_PCT percentile
#   Idle (ancillary services) when price is between the two thresholds
CHARGE_PCT      = 25   # Percentile below which we charge
DISCHARGE_PCT   = 75   # Percentile above which we discharge

# ── Ancillary services proxy ───────────────────────────────────────────────
# When the battery is idle it can offer capacity to ERCOT's ancillary markets
# (ECRS, Reg-Up, Reg-Down).  We use a flat proxy rate based on ERCOT's
# published historical average clearing prices (~$8/MW-hr blended).
ANCILLARY_RATE_PER_MW_HR = 8.0   # $/MW-hr of available capacity while idle

# ── Financial defaults ─────────────────────────────────────────────────────
CAPEX_PER_KWH     = 240        # All-in installed cost ($/kWh) — 2025 market for utility-scale BESS
OPEX_PER_MW_YEAR  = 12_000     # Fixed O&M ($/MW/year)
PROJECT_LIFE      = 20         # Years
DEBT_RATIO        = 0.55       # Debt as fraction of total CapEx
DEBT_RATE         = 0.060      # Annual interest rate on project debt
DISCOUNT_RATE     = 0.08       # Equity hurdle rate / WACC proxy

# ── Data paths ─────────────────────────────────────────────────────────────
ERCOT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ercot_data")

# Full-year RTM hub price data — pre-converted from ERCOT MIS report 13061 XLSX.
# One CSV per year, hub rows only (HB_WEST/NORTH/SOUTH/HOUSTON).
# Source XLSX files are in ercot_rtm/; run convert_xlsx_to_csv.py once to generate these.
ERCOT_RTM_CSV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ercot_data")

# Seasonal 3-month slices (original model).
# Summer months are the highest-consistency revenue period (solar duck curve).
# Winter months have higher variance — potential for extreme weather-driven spikes.
SEASONS = {
    "Summer 2024":    ["June_2024.csv",    "July_2024.csv",    "August_2024.csv"],
    "Winter 2024-25": ["December_2024.csv","January_2025.csv", "February_2025.csv"],
    "Summer 2025":    ["June_2025.csv",    "July_2025.csv",    "August_2025.csv"],
    "Full Year 2023": 2023,
    "Full Year 2024": 2024,
    "Full Year 2025": 2025,
}

# How many months each season entry covers — used to annualize revenue correctly.
SEASON_MONTHS = {
    "Summer 2024":    3,
    "Winter 2024-25": 3,
    "Summer 2025":    3,
    "Full Year 2023": 12,
    "Full Year 2024": 12,
    "Full Year 2025": 12,
}

DEFAULT_SEASON = "Full Year 2024"

HUBS = ["HB_WEST", "HB_NORTH", "HB_SOUTH", "HB_HOUSTON"]
DEFAULT_HUB = "HB_WEST"   # West Texas: solar-rich, frequent low/negative prices
