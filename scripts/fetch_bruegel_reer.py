"""Fetch and parse Bruegel Real Effective Exchange Rates (REER) dataset.

Reference:
Darvas, Zsolt (2021) 'Timely measurement of real effective exchange rates', Bruegel Working Paper 2021/15.
Darvas, Zsolt (2012) 'Real effective exchange rates for 178 countries: a new database', Bruegel Working Paper 2012/06.
DOI: https://doi.org/10.64153/SZCG6180
"""
from __future__ import annotations

import argparse
import io
import json
import logging
from pathlib import Path
import urllib.request
import zipfile
from typing import Any

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fetch_bruegel_reer")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_JSON = DATA_DIR / "bruegel_reer_monthly.json"

DEFAULT_URL = "https://www.bruegel.org/sites/default/files/2026-10/REER_database_ver11Oct2026.zip"

COUNTRY_MAPPING = {
    "US": "US",
    "EA": "EA12",
    "UK": "GB",
    "JP": "JP",
    "CN": "CN",
    "ZA": "ZA",
    "PL": "PL",
    "CZ": "CZ",
    "HU": "HU",
    "RO": "RO",
}


def _date_conv(val: Any) -> str:
    s = str(val).strip()
    if "M" in s:
        parts = s.split("M")
        if len(parts) == 2:
            return f"{parts[0]}-{int(parts[1]):02d}-01"
    return s


def parse_bruegel_xls(xls_bytes: bytes) -> dict[str, Any]:
    xl = pd.ExcelFile(io.BytesIO(xls_bytes))
    df_reer_120 = xl.parse("REER_MONTHLY_120", header=None)
    df_neer_120 = xl.parse("NEER_MONTHLY_120", header=None)

    version_str = str(df_reer_120.iloc[0, 0]).replace("Updated:", "").strip()

    # Build col index maps
    reer_cols = list(df_reer_120.iloc[0].values)
    neer_cols = list(df_neer_120.iloc[0].values)

    reer_map = {}
    for idx, c in enumerate(reer_cols):
        col_name = str(c).strip()
        reer_map[col_name] = idx

    neer_map = {}
    for idx, c in enumerate(neer_cols):
        col_name = str(c).strip()
        neer_map[col_name] = idx

    dates = [_date_conv(d) for d in df_reer_120.iloc[1:, 0].values]

    countries_data: dict[str, Any] = {}

    for c_code, bruegel_code in COUNTRY_MAPPING.items():
        reer_col_name = f"REER_120_{bruegel_code}"
        neer_col_name = f"NEER_120_{bruegel_code}"

        reer_idx = reer_map.get(reer_col_name)
        neer_idx = neer_map.get(neer_col_name)

        reer_obs = []
        if reer_idx is not None:
            raw_vals = df_reer_120.iloc[1:, reer_idx].values
            for dt, v in zip(dates, raw_vals):
                if pd.notna(v) and str(v).strip() != "":
                    try:
                        reer_obs.append({"date": dt, "value": round(float(v), 4)})
                    except (ValueError, TypeError):
                        pass

        neer_obs = []
        if neer_idx is not None:
            raw_vals = df_neer_120.iloc[1:, neer_idx].values
            for dt, v in zip(dates, raw_vals):
                if pd.notna(v) and str(v).strip() != "":
                    try:
                        neer_obs.append({"date": dt, "value": round(float(v), 4)})
                    except (ValueError, TypeError):
                        pass

        countries_data[c_code] = {
            "country_code": c_code,
            "bruegel_code": bruegel_code,
            "reer_120": reer_obs,
            "neer_120": neer_obs,
            "latest_reer": reer_obs[-1] if reer_obs else None,
            "latest_neer": neer_obs[-1] if neer_obs else None,
        }

    return {
        "source": "Bruegel",
        "dataset": "Real effective exchange rates for 178 countries: a new database",
        "authors": "Zsolt Darvas",
        "version": version_str,
        "doi": "https://doi.org/10.64153/SZCG6180",
        "citation": "Darvas, Zsolt (2021) 'Timely measurement of real effective exchange rates', Bruegel Working Paper 2021/15.",
        "basket": "120 trading partners",
        "index_base": "2007=100",
        "date_range": f"{dates[0]} to {dates[-1]}" if dates else "",
        "countries": countries_data,
    }


def fetch_bruegel(url: str = DEFAULT_URL, local_zip: Path | None = None) -> dict[str, Any]:
    if local_zip and local_zip.exists():
        logger.info(f"Reading local zip file: {local_zip}")
        data = local_zip.read_bytes()
    else:
        logger.info(f"Downloading Bruegel REER dataset from {url}...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        logger.info(f"Downloaded {len(data):,} bytes.")

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        xls_names = [n for n in zf.namelist() if n.endswith(".xls") or n.endswith(".xlsx")]
        if not xls_names:
            raise FileNotFoundError("No Excel file found inside Bruegel zip archive.")
        xls_name = xls_names[0]
        logger.info(f"Extracting Excel workbook: {xls_name}")
        xls_bytes = zf.read(xls_name)

    logger.info("Parsing sheets REER_MONTHLY_120 and NEER_MONTHLY_120...")
    payload = parse_bruegel_xls(xls_bytes)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and parse Bruegel REER dataset")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL to Bruegel REER zip file")
    parser.add_argument("--local-zip", type=Path, default=None, help="Path to local zip file if already downloaded")
    parser.add_argument("--out", type=Path, default=OUTPUT_JSON, help="Path to output JSON")
    args = parser.parse_args()

    payload = fetch_bruegel(url=args.url, local_zip=args.local_zip)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Wrote {args.out} with {len(payload['countries'])} economies.")

    for code, c_info in payload["countries"].items():
        reer_latest = c_info.get("latest_reer")
        neer_latest = c_info.get("latest_neer")
        logger.info(
            f"{code:3}: REER count={len(c_info['reer_120'])} latest={reer_latest['value'] if reer_latest else 'n/a'} ({reer_latest['date'] if reer_latest else ''}) | "
            f"NEER latest={neer_latest['value'] if neer_latest else 'n/a'}"
        )


if __name__ == "__main__":
    main()
