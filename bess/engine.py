"""
BESS Physical Engine
--------------------
Models the real operating constraints of a battery energy storage system:

  • Round-trip efficiency  — energy is lost in every charge/discharge cycle
  • State-of-charge (SoC) limits  — operating outside 10–90% degrades cells
  • C-rate limit  — the battery cannot charge or discharge faster than its
                    rated power (MW) regardless of available energy headroom
  • Annual capacity degradation  — Li-ion cells lose ~2 % of capacity per year

These are engineering realities a finance model often ignores; modelling them
explicitly produces more credible revenue estimates.
"""


class BESSEngine:
    def __init__(
        self,
        capacity_mwh: float,
        power_mw: float,
        round_trip_eff: float,
        soc_min: float,
        soc_max: float,
        annual_degradation: float,
    ):
        self.nominal_capacity = capacity_mwh   # nameplate (degrades over time)
        self.power_mw         = power_mw
        self.rte              = round_trip_eff
        self.soc_min          = soc_min
        self.soc_max          = soc_max
        self.annual_deg       = annual_degradation

        # Current capacity after degradation (updated each year)
        self.effective_capacity = capacity_mwh
        # Start at 50 % SoC
        self.soc = 0.50

    # ── Limits ────────────────────────────────────────────────────────────

    @property
    def usable_capacity(self) -> float:
        """MWh between soc_min and soc_max floors/ceilings."""
        return self.effective_capacity * (self.soc_max - self.soc_min)

    @property
    def max_charge_mwh(self) -> float:
        """Max energy we can add this hour (C-rate + SoC headroom)."""
        headroom = (self.soc_max - self.soc) * self.effective_capacity
        return min(self.power_mw, headroom)          # power_mw = 1-hr max

    @property
    def max_discharge_mwh(self) -> float:
        """Max energy we can extract this hour (C-rate + SoC floor)."""
        available = (self.soc - self.soc_min) * self.effective_capacity
        return min(self.power_mw, available)

    # ── Actions ───────────────────────────────────────────────────────────

    def charge(self, mwh_requested: float) -> float:
        """
        Charge up to mwh_requested.  Returns actual MWh drawn from the grid.

        RTE is split symmetrically: sqrt(RTE) loss on charge, sqrt(RTE) loss on
        discharge, so the net round-trip = sqrt(RTE) * sqrt(RTE) = RTE exactly.
        grid draw = mwh_stored / sqrt(RTE)
        """
        mwh_stored = min(mwh_requested, self.max_charge_mwh)
        self.soc   = min(self.soc_max, self.soc + mwh_stored / self.effective_capacity)
        grid_draw  = mwh_stored / (self.rte ** 0.5)
        return grid_draw

    def discharge(self, mwh_requested: float) -> float:
        """
        Discharge up to mwh_requested.  Returns actual MWh delivered to grid
        (grid delivery = mwh_from_battery * RTE — efficiency loss on the way out).
        We split RTE evenly: √RTE on charge side, √RTE on discharge side.
        """
        mwh_from_battery = min(mwh_requested, self.max_discharge_mwh)
        self.soc = max(self.soc_min, self.soc - mwh_from_battery / self.effective_capacity)
        grid_delivery = mwh_from_battery * (self.rte ** 0.5)
        return grid_delivery

    def apply_annual_degradation(self):
        """Call once per simulated year to shrink effective capacity."""
        self.effective_capacity *= (1 - self.annual_deg)
        self.soc = min(self.soc, self.soc_max)        # re-clamp after shrink

    def reset(self):
        """Reset SoC to 50 % (call between simulation runs)."""
        self.soc = 0.50
        self.effective_capacity = self.nominal_capacity
