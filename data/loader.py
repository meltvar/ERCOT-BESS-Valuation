import os
import pandas as pd
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config

_MONTH_SHEETS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load_lmp(hub: str = config.DEFAULT_HUB, season: str = config.DEFAULT_SEASON) -> pd.DataFrame:
    """
    Load ERCOT settlement point price data for a given season and hub,
    returning a clean hourly DataFrame.

    Handles both seasonal CSV slices (3 months) and full-year data
    (pre-converted CSVs from ERCOT MIS report 13061 RTMLZHBSPP XLSX files).

    Parameters
    ----------
    hub    : one of config.HUBS
    season : one of config.SEASONS keys

    Returns
    -------
    pd.DataFrame with columns: ['datetime', 'lmp']
        datetime — hourly timestamp
        lmp      — average settlement price for that hour ($/MWh)
    """
    season_val = config.SEASONS[season]

    if isinstance(season_val, int):
        return _load_lmp_year(hub, season_val)
    else:
        return _load_lmp_csvs(hub, season_val)


def _load_lmp_csvs(hub: str, filenames: list) -> pd.DataFrame:
    """Load hourly LMP from monthly CSV files (original 3-month seasons)."""
    frames = []
    for filename in filenames:
        path = os.path.join(config.ERCOT_DATA_DIR, filename)
        frames.append(pd.read_csv(path))

    raw = pd.concat(frames, ignore_index=True)
    return _clean_raw(raw, hub)


def _load_lmp_year(hub: str, year: int) -> pd.DataFrame:
    """
    Load hourly LMP from a pre-converted full-year CSV.

    The source is ERCOT MIS report 13061 (RTMLZHBSPP), originally delivered
    as a multi-sheet XLSX (one sheet per month). The one-time conversion script
    (convert_xlsx_to_csv.py) extracted hub rows only and wrote a flat CSV,
    reducing load time from ~16 min (openpyxl) to <5 sec (pandas CSV reader).
    """
    filename = f"RTMLZHBSPP_{year}.csv"
    path = os.path.join(config.ERCOT_RTM_CSV_DIR, filename)
    raw = pd.read_csv(path)
    return _clean_raw(raw, hub)


def _clean_raw(raw: pd.DataFrame, hub: str) -> pd.DataFrame:
    """Filter to hub, strip comma-formatted prices, aggregate to hourly."""
    raw = raw[raw["Settlement Point Name"] == hub].copy()

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
