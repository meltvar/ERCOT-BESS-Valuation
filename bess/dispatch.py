"""
Dispatch Logic
--------------
A simple bang-bang controller with a deadband — the kind of rule an EE would
write for a power-electronics controller:

  CHARGE     if LMP < low_threshold   (buy cheap energy)
  DISCHARGE  if LMP > high_threshold  (sell expensive energy)
  IDLE       otherwise                (offer capacity to ancillary markets)

Thresholds are set as percentiles of the full LMP series so they adapt to
whichever hub or time period is selected.
"""

import numpy as np
import pandas as pd
from bess.engine import BESSEngine


def run_dispatch(
    lmp: pd.Series,
    engine: BESSEngine,
    charge_pct: float = 25,
    discharge_pct: float = 75,
) -> pd.DataFrame:
    """
    Simulate hour-by-hour dispatch over the supplied LMP series.

    Parameters
    ----------
    lmp          : hourly LMP prices ($/MWh), indexed 0..N-1
    engine       : BESSEngine instance (will be reset before simulation)
    charge_pct   : LMP percentile below which we charge
    discharge_pct: LMP percentile above which we discharge

    Returns
    -------
    pd.DataFrame with one row per hour:
        lmp, action, grid_mwh, soc, energy_revenue
        action: 'charge' | 'discharge' | 'idle'
        grid_mwh: positive = sold to grid, negative = bought from grid
        energy_revenue: $ earned this hour from energy market
    """
    engine.reset()

    low_thresh  = np.percentile(lmp, charge_pct)
    high_thresh = np.percentile(lmp, discharge_pct)

    records = []
    for price in lmp:
        if price <= low_thresh and engine.max_charge_mwh > 0:
            grid_draw = engine.charge(engine.max_charge_mwh)
            records.append({
                "lmp":            price,
                "action":         "charge",
                "grid_mwh":       -grid_draw,                  # cost to buy
                "energy_revenue": -grid_draw * price,          # negative = expense
                "soc":            engine.soc,
            })

        elif price >= high_thresh and engine.max_discharge_mwh > 0:
            delivered = engine.discharge(engine.max_discharge_mwh)
            records.append({
                "lmp":            price,
                "action":         "discharge",
                "grid_mwh":       delivered,
                "energy_revenue": delivered * price,
                "soc":            engine.soc,
            })

        else:
            records.append({
                "lmp":            price,
                "action":         "idle",
                "grid_mwh":       0.0,
                "energy_revenue": 0.0,
                "soc":            engine.soc,
            })

    return pd.DataFrame(records)
