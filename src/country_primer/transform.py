"""Minimal transforms: YoY from a level series, latest-print summary."""
from __future__ import annotations

import pandas as pd

from .fetch import Series


def to_dataframe(series: Series) -> pd.DataFrame:
    if not series.observations:
        return pd.DataFrame(columns=["date", "value"]).set_index("date")
    df = pd.DataFrame(series.observations, columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date").sort_index()
    return df


def yoy(df: pd.DataFrame, freq: str | None = None) -> pd.DataFrame:
    """Year-on-year % change. freq one of M/Q/A; if None, infer from index spacing."""
    if df.empty:
        return df
    if freq is None:
        delta = (df.index[-1] - df.index[0]).days / max(len(df) - 1, 1)
        freq = "M" if delta < 45 else ("Q" if delta < 130 else "A")
    lag = {"M": 12, "Q": 4, "A": 1}.get(freq, 12)
    if len(df) <= lag:
        return df.assign(value=pd.NA).iloc[0:0]
    out = df.copy()
    out["value"] = (df["value"] / df["value"].shift(lag) - 1.0) * 100.0
    return out.dropna()


def latest_change(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    last = df["value"].iloc[-1]
    prev = df["value"].iloc[-2] if len(df) > 1 else None
    return {
        "date": df.index[-1].strftime("%Y-%m-%d"),
        "value": float(last),
        "prev": float(prev) if prev is not None else None,
        "delta": float(last - prev) if prev is not None else None,
    }
