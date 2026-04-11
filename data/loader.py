import os
import pandas as pd
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def load_lmp(hub: str = config.DEFAULT_HUB, season: str = config.DEFAULT_SEASON) -> pd.DataFrame:
    """
    Load ERCOT settlement point price CSVs for a given season and hub,
    returning a clean hourly DataFrame.

    Parameters
    ----------
    hub    : one of config.HUBS
    season : one of config.SEASONS keys ("Summer 2024", "Winter 2024-25", "Summer 2025")

    Returns
    -------
    pd.DataFrame with columns: ['datetime', 'lmp']
        datetime — hourly timestamp
        lmp      — average settlement price for that hour ($/MWh)
    """
    filenames = config.SEASONS[season]
    frames = []
    for filename in filenames:
        path = os.path.join(config.ERCOT_DATA_DIR, filename)
        frames.append(pd.read_csv(path))

    raw = pd.concat(frames, ignore_index=True)
    raw = raw[raw["Settlement Point Name"] == hub].copy()
    # Strip commas from prices formatted as "1,613.07" (ERCOT uses commas for values >999)
    raw["Settlement Point Price"] = (
        raw["Settlement Point Price"]
        .astype(str)
        .str.replace(",", "", regex=False)
    )
    raw["Settlement Point Price"] = pd.to_numeric(raw["Settlement Point Price"], errors="coerce")

    raw["datetime"] = pd.to_datetime(raw["Delivery Date"], format="%m/%d/%Y") + pd.to_timedelta(
        raw["Delivery Hour"] - 1, unit="h"
    )

    hourly = (
        raw.groupby("datetime")["Settlement Point Price"]
        .mean()
        .reset_index()
        .rename(columns={"Settlement Point Price": "lmp"})
        .sort_values("datetime")
        .reset_index(drop=True)
    )

    return hourly
