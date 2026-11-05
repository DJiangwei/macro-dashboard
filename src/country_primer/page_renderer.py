from __future__ import annotations
from country_primer.cross_checks import evaluate_cross_checks
import json
import math
import os
import re
from country_primer.framework import concept_id_for
from datetime import datetime, UTC
from html import escape
from pathlib import Path
from typing import Any

from dashboard_summary_utils import (
    apply_quality_assessments,
    build_summary_metadata,
    canonical_frame_metadata,
    write_canonical_data_first_frame,
)
from country_primer.source_health import write_source_health_report
from country_primer.scopes import all_scopes

OUTPUT = Path("output")
ACCENT = "#990f3d"
INK = "#12151a"
MUTED = "#737c8c"
PAPER = "#ffffff"


def _normalize_lw_time(raw_date: object) -> str | None:
    s = str(raw_date or "").strip()
    if not s:
        return None
    if len(s) == 4 and s.isdigit():
        return f"{s}-12-31"
    if len(s) == 7 and s[4] == "-":
        return f"{s}-01"
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def _build_lw_points(x_list, y_list, *, is_bar: bool = False) -> list[dict]:
    by_time: dict[str, dict] = {}
    for raw_x, raw_y in zip(x_list or [], y_list or []):
        if raw_y is None:
            continue
        try:
            val = float(raw_y)
        except (TypeError, ValueError):
            continue
        if math.isnan(val) or math.isinf(val):
            continue
        t = _normalize_lw_time(raw_x)
        if not t:
            continue
        rval = round(val, 4)
        pt: dict[str, Any] = {"time": t, "value": rval}
        if is_bar:
            pt["color"] = "#0d7680" if rval >= 0 else "#990f3d"
        by_time[t] = pt
    return [by_time[k] for k in sorted(by_time)]


def _resolve_display_scale(
    indicator_id: str,
    raw_unit: str,
    values: list[float] | None = None,
) -> tuple[float, str]:
    """Scale large numbers with many zeros into thousands / millions / billions based on content."""
    unit = str(raw_unit or "").strip()
    unit_lower = unit.lower()
    max_abs = max((abs(v) for v in (values or []) if v is not None), default=0.0)
    if indicator_id == "eur_usd":
        return 1.0, "USD per EUR"
    if unit == "USD":
        if max_abs >= 1_000_000_000:
            return 1_000_000_000.0, "USD bn"
        if max_abs >= 1_000_000:
            return 1_000_000.0, "USD mn"
        return 1.0, unit
    if unit == "people":
        if max_abs >= 1_000_000:
            return 1_000_000.0, "millions"
        if max_abs >= 1_000:
            return 1_000.0, "thousands"
        return 1.0, unit
    if unit_lower == "persons" and max_abs >= 10_000:
        if max_abs >= 5_000_000 and indicator_id == "long_term_unemployment":
            return 1_000_000.0, "millions"
        return 1_000.0, "thousands"
    if unit_lower == "persons m/m" and max_abs >= 10_000:
        return 1_000.0, "thousands m/m"
    if unit_lower in {"listings", "units", "dwellings", "transactions", "number"} and max_abs >= 100_000:
        return 1_000.0, (f"thousand {unit_lower}" if unit_lower != "number" else "thousands")
    if unit_lower == "jpy 100mn" and max_abs >= 10_000:
        return 10_000.0, "JPY tn"
    if unit_lower == "jpy bn" and max_abs >= 10_000:
        return 1_000.0, "JPY tn"
    if indicator_id == "tax_receipts_ytd_akshare" and max_abs >= 10_000:
        return 10_000.0, "CNY tn"
    if unit_lower == "gbp" and max_abs >= 100_000:
        return 1_000.0, "GBP thousands"
    if unit_lower.endswith(" mn") and max_abs >= 10_000:
        prefix = unit[:-3].strip()
        return 1_000.0, f"{prefix} bn"
    if max_abs >= 1_000_000_000:
        return 1_000_000_000.0, (f"{unit} (bn)".strip() if "bn" not in unit_lower else unit)
    if max_abs >= 1_000_000:
        return 1_000_000.0, (f"{unit} (mn)".strip() if "mn" not in unit_lower and "million" not in unit_lower else unit)
    return 1.0, unit


def _render_cards(series_list: list[dict[str, Any]], extra_cards: list[dict[str, Any]], summary_key_ids: list[str]) -> str:
    by_id = {item["id"]: item for item in series_list}
    cards_html: list[str] = []
    
    # Renders the headline IDs from the series list
    for indicator_id in summary_key_ids[:4]:
        series = by_id.get(indicator_id)
        latest = _latest(series) if series else None
        if not series or not latest:
            continue
        raw_unit = series.get("unit", "")
        obs_vals = [float(o["value"]) for o in (series.get("observations") or []) if o.get("value") is not None]
        divisor, unit = _resolve_display_scale(indicator_id, raw_unit, obs_vals)
        scaled_vals = [v / divisor for v in obs_vals]
        curr_v = float(latest["value"]) / divisor
        spark_html = ""
        if len(scaled_vals) >= 3:
            min_v = min(scaled_vals)
            max_v = max(scaled_vals)
            pos_pct = max(0, min(100, int(round((curr_v - min_v) / (max_v - min_v) * 100)))) if max_v != min_v else 50
            spark_html = f'''
  <div class="ft-spark-range" title="Historical Range Context">
    <div class="ft-spark-track"><div class="ft-spark-point" style="left: {pos_pct}%;"></div></div>
    <div class="ft-spark-labels"><span>{_format_value(min_v, unit)}</span><span class="ft-spark-pct">{pos_pct}%</span><span>{_format_value(max_v, unit)}</span></div>
  </div>'''

        cards_html.append(f'''
<div class="data-card">
  <span><span data-lang="en">{escape(series.get('label_en', series.get('label', '')))}</span><span data-lang="zh">{escape(series.get('label_zh', series.get('label', '')))}</span></span>
  <strong>{_format_value(curr_v, unit)}</strong>
  <small>{escape(str(latest['date']))} · {escape(series.get('source_name', ''))}</small>{spark_html}
</div>''')
        
    for card in extra_cards:
        cards_html.append(f'''
<div class="data-card">
  <span><span data-lang="en">{escape(card.get('label_en', card.get('label', '')))}</span><span data-lang="zh">{escape(card.get('label_zh', card.get('label', '')))}</span></span>
  <strong>{escape(str(card.get('value', 'n/a')))}</strong>
  <small>{escape(str(card.get('updated', 'n/a')))} · {escape(card.get('source', 'Extra'))}</small>
</div>''')
        
    return "\n".join(cards_html)


summary_key_ids = [
    "real_gdp_growth",
    "industrial_value_added_yoy_akshare",
    "fixed_asset_investment_yoy_akshare",
    "commercial_housing_sales_value_eastmoney",
    "real_estate_development_investment_ytd_eastmoney",
    "passenger_vehicle_retail_cpca",
    "new_energy_vehicle_share_cpca",
    "customs_exports_yoy_akshare",
    "usd_cny_midpoint",
    "m2_yoy_akshare",
    "financial_institution_deposits_stock_akshare",
    "vegetable_basket_price_index_akshare",
    "pbc_total_assets_akshare",
    "pbc_reserve_money_akshare",
    "cpi_yoy_akshare",
    "ppi_yoy_akshare",
]

def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)

def _write_clean(path: Path, content: str) -> None:
    path.write_text("\n".join(line.rstrip() for line in content.splitlines()) + "\n")

def _parse_year(value: str) -> int | None:
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None

def _latest(series: dict[str, Any]) -> dict[str, Any] | None:
    observations = series.get("observations") or []
    if not observations:
        return None

    actual_through = series.get("actual_through")
    if actual_through not in (None, ""):
        try:
            cutoff_year = int(actual_through)
        except (TypeError, ValueError):
            cutoff_year = None
        if cutoff_year is not None:
            actual = [
                item for item in observations
                if (_parse_year(str(item.get("date", ""))) or 9999) <= cutoff_year
            ]
            if actual:
                return actual[-1]

    observed = [
        item for item in observations
        if not bool(item.get("is_projection"))
        and str(item.get("observation_type") or "").lower() not in {"forecast", "projection"}
    ]
    return observed[-1] if observed else observations[-1]

def _format_period(date_text: str, frequency: str, locale: str) -> str:
    text = str(date_text or "")
    try:
        parsed = datetime.strptime(text[:10], "%Y-%m-%d")
    except ValueError:
        year = _parse_year(text)
        return f"{year}年" if year and locale == "zh" else str(year or text)

    frequency = str(frequency or "").lower()
    if frequency == "annual":
        return f"{parsed.year}年" if locale == "zh" else str(parsed.year)
    if frequency == "quarterly":
        quarter = ((parsed.month - 1) // 3) + 1
        return f"{parsed.year}年 Q{quarter}" if locale == "zh" else f"Q{quarter} {parsed.year}"
    if frequency == "monthly":
        return f"{parsed.year}年{parsed.month}月" if locale == "zh" else parsed.strftime("%b %Y")
    if locale == "zh":
        return f"{parsed.year}年{parsed.month}月{parsed.day}日"
    return f"{parsed.day} {parsed.strftime('%b %Y')}"

def _format_value(value: float, unit: str) -> str:
    if unit == "USD" and abs(value) < 1000:
        return f"${value:,.2f}tn"
    if unit == "people" and abs(value) < 100:
        return f"{value:,.2f}bn"
    if abs(value) >= 1000:
        return f"{value:,.0f}" if abs(value - round(value)) < 1e-6 else f"{value:,.2f}"
    if abs(value) >= 100:
        return f"{value:,.0f}" if abs(value - round(value)) < 1e-6 else f"{value:,.1f}"
    if abs(value) >= 10:
        return f"{value:,.1f}"
    return f"{value:,.2f}"

def _chart_html(
    series: dict[str, Any],
    country_code: str,
    lw_specs: dict[str, dict[str, Any]] | None = None,
) -> str:
    observations = series.get("observations") or []
    if not observations:
        return ""
    sid = str(series.get("id", "")).strip()
    chart_id = f"chart-{sid}"
    raw_unit = str(series.get("unit", "") or "")
    raw_vals = [float(item["value"]) for item in observations if item.get("value") is not None]
    divisor, display_unit = _resolve_display_scale(sid, raw_unit, raw_vals)
    scaled_vals = [v / divisor for v in raw_vals]

    actual_through = series.get("actual_through")
    lw_series: list[dict[str, Any]] = []
    if actual_through:
        try:
            cutoff = int(str(actual_through)[:4])
            actual = [item for item in observations if (_parse_year(item["date"]) or 9999) <= cutoff]
            forecast = [item for item in observations if (_parse_year(item["date"]) or 0) >= cutoff]
        except (ValueError, TypeError):
            actual = observations
            forecast = []
        if actual:
            lw_series.append({
                "name": "Actual / history",
                "type": "line",
                "color": ACCENT,
                "width": 2,
                "style": 0,
                "isPrimary": True,
                "data": _build_lw_points(
                    [item["date"] for item in actual],
                    [float(item["value"]) / divisor if item.get("value") is not None else None for item in actual],
                ),
            })
        if forecast:
            lw_series.append({
                "name": "IMF WEO estimate / forecast",
                "type": "line",
                "color": "#364b61",
                "width": 2,
                "style": 2,
                "isPrimary": not bool(actual),
                "data": _build_lw_points(
                    [item["date"] for item in forecast],
                    [float(item["value"]) / divisor if item.get("value") is not None else None for item in forecast],
                ),
            })
    else:
        lw_series.append({
            "name": series["label_en"],
            "type": "line",
            "color": ACCENT,
            "width": 2,
            "style": 0,
            "isPrimary": True,
            "data": _build_lw_points(
                [item["date"] for item in observations],
                [float(item["value"]) / divisor if item.get("value") is not None else None for item in observations],
            ),
        })

    latest = _latest(series)

    target_bands = {
        "US": {"center": 2.0, "min": 2.0, "max": 2.0, "label": "Fed Target: 2.0%"},
        "UK": {"center": 2.0, "min": 2.0, "max": 2.0, "label": "BoE Target: 2.0%"},
        "JP": {"center": 2.0, "min": 2.0, "max": 2.0, "label": "BoJ Target: 2.0%"},
        "ZA": {"center": 4.5, "min": 3.0, "max": 6.0, "label": "SARB Target: 4.5% (3.0%–6.0% band)"},
        "CN": {"center": 3.0, "min": 3.0, "max": 3.0, "label": "Official CPI Target Ceiling: 3.0%"},
        "EA": {"center": 2.0, "min": 2.0, "max": 2.0, "label": "ECB Target: 2.0%"},
        "TR": {"center": 5.0, "min": 3.0, "max": 7.0, "label": "CBRT Target: 5.0% (3.0%–7.0% band)"},
        "KR": {"center": 2.0, "min": 2.0, "max": 2.0, "label": "BoK Target: 2.0%"},
        "KZ": {"center": 5.0, "min": 5.0, "max": 5.0, "label": "NBK Target: 5.0%"},
        "UZ": {"center": 5.0, "min": 5.0, "max": 5.0, "label": "CBU Target: 5.0%"},
    }
    eligible_target_indicators = {
        "US": {"cpi_inflation", "core_cpi_inflation", "pce_inflation", "core_pce_inflation"},
        "UK": {"cpi_yoy", "core_cpi_yoy", "cpih_yoy"},
        "JP": {"cpi_inflation", "cpi_inflation_estat", "core_inflation", "core_core_inflation"},
        "ZA": {"cpi_inflation", "cpi_inflation_imf"},
        "CN": {"cpi_inflation", "cpi_yoy_akshare"},
        "EA": {"hicp_inflation", "hicp_core_inflation", "spf_inflation_expectations_lt"},
        "TR": {"cpi_inflation", "cpi_yoy"},
        "KR": {"cpi_inflation", "cpi_yoy"},
        "KZ": {"cpi_inflation", "cpi_yoy"},
        "UZ": {"cpi_inflation", "cpi_yoy"},
    }

    cc_upper = country_code.upper()
    price_lines: list[dict[str, Any]] = []
    badge: dict[str, str] | None = None

    # 1. Check for custom reference lines declared on the series
    custom_ref_lines = series.get("reference_lines") or []
    if custom_ref_lines:
        for ref in custom_ref_lines:
            val = ref.get("value")
            label = str(ref.get("label") or "")
            color = str(ref.get("color") or "#0d7680")
            if "min" in ref and "max" in ref:
                r_min = float(ref["min"]) / divisor
                r_max = float(ref["max"]) / divisor
                price_lines.append({
                    "price": r_max,
                    "color": "rgba(13, 118, 128, 0.55)",
                    "width": 1,
                    "style": 3,
                    "title": f"Upper {r_max:g}",
                    "axisLabel": False,
                })
                price_lines.append({
                    "price": r_min,
                    "color": "rgba(13, 118, 128, 0.55)",
                    "width": 1,
                    "style": 3,
                    "title": f"Lower {r_min:g}",
                    "axisLabel": False,
                })
            if val is not None:
                s_val = float(val) / divisor
                price_lines.append({
                    "price": s_val,
                    "color": color,
                    "width": 2,
                    "style": 2,
                    "title": label or f"{s_val:g}",
                    "axisLabel": False,
                })
            if label and not badge:
                badge = {"text": label, "color": "#0d7680", "bg": "rgba(13, 118, 128, 0.10)"}
    else:
        # 2. Check for policy inflation target overlays
        c_band = target_bands.get(cc_upper)
        if c_band and sid in eligible_target_indicators.get(cc_upper, set()):
            badge = {"text": c_band["label"], "color": "#0d7680", "bg": "rgba(13, 118, 128, 0.10)"}
            if c_band["min"] != c_band["max"]:
                price_lines.append({
                    "price": c_band["max"],
                    "color": "rgba(13, 118, 128, 0.55)",
                    "width": 1,
                    "style": 3,
                    "title": f"Upper {c_band['max']:g}%",
                    "axisLabel": False,
                })
            price_lines.append({
                "price": c_band["center"],
                "color": "#0d7680",
                "width": 2,
                "style": 2,
                "title": f"Target {c_band['center']:g}%",
                "axisLabel": False,
            })
            if c_band["min"] != c_band["max"]:
                price_lines.append({
                    "price": c_band["min"],
                    "color": "rgba(13, 118, 128, 0.55)",
                    "width": 1,
                    "style": 3,
                    "title": f"Lower {c_band['min']:g}%",
                    "axisLabel": False,
                })

        # 3. EU Maastricht fiscal deficit threshold (legally binding only for EU / Euro Area member states)
        if cc_upper in {"HU", "PL", "CZ", "RO", "EA"} and ("fiscal_balance" in sid or "budget_balance" in sid):
            if not badge:
                badge = {"text": "EU Maastricht Deficit Limit: -3.0%", "color": "#990f3d", "bg": "rgba(153, 15, 61, 0.08)"}
            price_lines.append({
                "price": -3.0,
                "color": "#990f3d",
                "width": 2,
                "style": 2,
                "title": "Maastricht -3%",
                "axisLabel": False,
            })

    if scaled_vals and min(scaled_vals) <= 0 <= max(scaled_vals):
        price_lines.append({
            "price": 0.0,
            "color": "rgba(18, 21, 26, 0.35)",
            "width": 1,
            "style": 0,
            "title": "",
            "axisLabel": False,
        })

    if lw_specs is not None:
        spec_entry: dict[str, Any] = {
            "title": series["label_en"],
            "unit": display_unit,
            "series": lw_series,
            "priceLines": price_lines,
        }
        if badge:
            spec_entry["badge"] = badge
        lw_specs[chart_id] = spec_entry

    latest_reading = ""
    if latest:
        value = _format_value(float(latest["value"]) / divisor, display_unit)
        unit = escape(display_unit)
        date_text = escape(str(latest["date"]))
        period_en = escape(_format_period(str(latest["date"]), series.get("frequency", ""), "en"))
        period_zh = escape(_format_period(str(latest["date"]), series.get("frequency", ""), "zh"))
        latest_reading = f"""
      <div class="latest-reading" data-latest-reading data-latest-date="{date_text}">
        <span class="latest-label"><span data-lang="en">Latest observation</span><span data-lang="zh">最新读数</span></span>
        <span class="latest-value"><strong>{value}</strong><em>{unit}</em></span>
        <time datetime="{date_text}"><span data-lang="en">{period_en}</span><span data-lang="zh">{period_zh}</span></time>
      </div>"""
    quality_data = series.get("data_quality") or {}
    authority = escape(str(quality_data.get("source_authority", "")).replace("_", " "))
    freshness = escape(str(quality_data.get("freshness", "")).replace("_", " "))
    quality = escape(series.get("quality_status", "unchecked").replace("_", " "))
    chips = (
        f'<span class="quality-pill">{quality}</span>'
        f'<span class="authority-chip">{authority}</span>'
        f'<span class="freshness-chip">{freshness}</span>'
    )
    caveat_en = escape(series.get("caveat_en", ""))
    caveat_zh = escape(series.get("caveat_zh", ""))
    source_url = escape(series.get("source_url") or series.get("api_url") or "#")
    concept_id = concept_id_for(country_code, str(series["id"]))
    view = "deep" if ":" in concept_id else "core"
    cross = series.get("cross_check") or {}
    cross_html = ""
    if cross:
        status = cross["status"]
        window_months = cross.get("window_months")
        window_label = f"last {window_months} months" if window_months else "recent window"
        if status == "insufficient":
            # No overlapping observations in the recent window (and possibly none
            # at all) — nothing to agree or diverge on, so say so plainly rather
            # than formatting fields (e.g. `latest_diff`) that may be None here.
            mark = "— No recent overlap for"
            headline = f"{window_label}: no common periods to compare"
            cls = "cross-check"
        elif status in {"agree", "minor"}:
            mark = "✓ Agrees with"
            headline = (
                f"{window_label}: {cross['window_n_common']} common periods, "
                f"max gap {cross['window_max_abs_diff']:.2f} (tolerance {cross['tolerance']:.2f})"
            )
            cls = "cross-check"
        else:
            mark = "⚠ Diverges from"
            headline = (
                f"{window_label}: {cross['window_n_breaches']} of {cross['window_n_common']} periods "
                f"beyond tolerance {cross['tolerance']:.2f}, latest gap {cross['latest_diff']:.2f} "
                f"({cross['last_breach_date']})"
            )
            cls = "cross-check diverged"
        if cross["n_breaches"]:
            history = (
                f"Full history: {cross['n_breaches']} of {cross['n_common']} periods beyond tolerance "
                f"(most recently {cross['last_breach_date']}; max gap {cross['max_abs_diff']:.2f})."
            )
        else:
            history = f"Full history: no breaches across {cross['n_common']} common periods."
        cross_html = (
            f'\n  <p class="{cls}">{mark} <strong>{escape(cross["label_en"])}</strong> · {escape(headline)}'
            f'<br><span class="cross-check-history">{escape(history)}</span></p>'
        )
    return f"""
<article class="chart-card chart-quality-{escape(series.get('quality_status', 'unchecked'))}" data-dashboard-view="{view}" data-concept-id="{escape(concept_id)}">
  <div class="chart-head">
    <div class="chart-title">
      <h3><span data-lang="en">{escape(series['label_en'])}</span><span data-lang="zh">{escape(series['label_zh'])}</span></h3>
    </div>
    <div class="chart-status">
      {latest_reading}
      {chips}
    </div>
  </div>
  <div class="lw-chart-wrap" style="height:350px;width:100%;">
    <div class="lw-chart-header">
      <div class="lw-chart-title-group">
        <span class="lw-chart-unit">{escape(display_unit)}</span>
      </div>
      <div class="lw-chart-meta" id="lw-meta-{chart_id}"></div>
    </div>
    <div id="{chart_id}" class="lw-chart-plot" data-lw-chart="{chart_id}"></div>
  </div>
  <footer>
    <span>Source: <a href="{source_url}" target="_blank" rel="noreferrer">{escape(series.get('source_name', 'unknown'))}</a></span>
    <span>Series: {escape(series.get('series', ''))}</span>
    <span>Frequency: {escape(series.get('frequency', ''))}</span>
    <span>Provider update: {escape(series.get('provider_updated', '') or 'n/a')}</span>
  </footer>{cross_html}
  <p class="caveat"><span data-lang="en">{caveat_en}</span><span data-lang="zh">{caveat_zh}</span></p>
</article>
"""

def _section_nav(config: dict[str, Any]) -> str:
    links = []
    for section_id, section in config.get("sections", {}).items():
        links.append(
            f'<a href="#{escape(section_id)}"><span data-lang="en">{escape(section["title_en"])}</span>'
            f'<span data-lang="zh">{escape(section["title_zh"])}</span></a>'
        )
    links.append('<a href="#data-gaps"><span data-lang="en">Data Gaps</span><span data-lang="zh">数据缺口</span></a>')
    return "\n".join(links)

def _sections_html(
    config: dict[str, Any],
    series_list: list[dict[str, Any]],
    country_code: str,
    lw_specs: dict[str, dict[str, Any]] | None = None,
) -> str:
    order_map = {
        str(ind.get("id")): i
        for i, ind in enumerate(config.get("indicators") or [])
        if ind.get("id")
    }
    by_section: dict[str, list[dict[str, Any]]] = {}
    for item in series_list:
        if item.get("observations"):
            by_section.setdefault(item["section"], []).append(item)
    html_parts: list[str] = []
    for section_id, section in config.get("sections", {}).items():
        items = by_section.get(section_id, [])
        if order_map:
            items = sorted(items, key=lambda it: order_map.get(str(it.get("id")), 9999))
        charts = "\n".join(_chart_html(item, country_code, lw_specs) for item in items)
        empty = ""
        if not charts:
            empty = '<div class="empty-note"><span data-lang="en">Official chart series for this section are currently in development.</span><span data-lang="zh">本分析模块的官方指标序列正在标准化接入中。</span></div>'

        deepdive_block = ""
        if section_id in ("prices_wages", "prices_costs", "prices"):
            cc_upper = (country_code or "").upper()
            if cc_upper == "US":
                try:
                    import sys
                    from pathlib import Path
                    scripts_dir = str(Path(__file__).resolve().parent.parent.parent / "scripts")
                    if scripts_dir not in sys.path:
                        sys.path.insert(0, scripts_dir)
                    from render_us_inflation_deepdive import render_us_deepdive_panel
                    deepdive_block = render_us_deepdive_panel()
                except Exception:
                    pass
            elif cc_upper in ("EA", "EURO_AREA", "EA20"):
                try:
                    import sys
                    from pathlib import Path
                    scripts_dir = str(Path(__file__).resolve().parent.parent.parent / "scripts")
                    if scripts_dir not in sys.path:
                        sys.path.insert(0, scripts_dir)
                    from render_cee_inflation_deepdive import render_deepdive_panel
                    deepdive_block = render_deepdive_panel("EA")
                except Exception:
                    pass
            else:
                # Any other scope: config/deepdive_views.yaml view, if one is configured.
                try:
                    import sys
                    from pathlib import Path
                    scripts_dir = str(Path(__file__).resolve().parent.parent.parent / "scripts")
                    if scripts_dir not in sys.path:
                        sys.path.insert(0, scripts_dir)
                    from real_deepdives import render_inflation_view
                    deepdive_block = render_inflation_view(cc_upper)
                except Exception:
                    pass

        labour_block = ""
        if section_id in ("labour_wages", "labour_market", "employment", "population_labor", "labour_structural"):
            cc_upper = (country_code or "").upper()
            try:
                import sys
                from pathlib import Path
                scripts_dir = str(Path(__file__).resolve().parent.parent.parent / "scripts")
                if scripts_dir not in sys.path:
                    sys.path.insert(0, scripts_dir)
                from real_deepdives import render_labour_view
                labour_block = render_labour_view(cc_upper)
            except Exception:
                pass

        html_parts.append(f"""
<section class="panel" id="{escape(section_id)}">
  <div class="section-title">
    <h2><span data-lang="en">{escape(section['title_en'])}</span><span data-lang="zh">{escape(section['title_zh'])}</span></h2>
    <div class="logic"><span data-lang="en">{escape(section['report_logic_en'])}</span><span data-lang="zh">{escape(section['report_logic_zh'])}</span></div>
  </div>
  {deepdive_block}
  {labour_block}
  <div class="charts-grid">
    {charts}
    {empty}
  </div>
</section>""")
    return "\n".join(html_parts)

def _gaps_html(config: dict[str, Any]) -> str:
    sections = config.get("sections", {})
    rows = []
    for gap in config.get("data_gaps", []):
        section = sections.get(gap["section"], {})
        rows.append(f"""
<tr>
  <td><span data-lang="en">{escape(section.get('title_en', gap['section']))}</span><span data-lang="zh">{escape(section.get('title_zh', gap['section']))}</span></td>
  <td><span data-lang="en">{escape(gap['item_en'])}</span><span data-lang="zh">{escape(gap['item_zh'])}</span></td>
  <td><span data-lang="en">{escape(gap['status_en'])}</span><span data-lang="zh">{escape(gap['status_zh'])}</span></td>
</tr>""")
    return "\n".join(rows)

CSS = """
:root {
  --bg-canvas: #fcfaf7;
  --bg-surface: #ffffff;
  --bg-deep: #f7f5f0;
  --fg: #12151a;
  --text-secondary: #4b525f;
  --muted: #737c8c;
  --accent: #990f3d;
  --accent-soft: rgba(153, 15, 61, 0.08);
  --border: rgba(18, 21, 26, 0.08);
  --border-strong: rgba(18, 21, 26, 0.16);
  --card: #ffffff;
  --blue: #262a33;
  --warn: #b86200;
  --low: #990f3d;
  --font-display: "Newsreader", "Iowan Old Style", "Songti SC", "Noto Serif SC", Georgia, serif;
  --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", "Helvetica Neue", Arial, sans-serif;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
html[lang="en"] [data-lang="zh"] { display: none !important; }
html[lang="zh"] [data-lang="en"] { display: none !important; }
html:not([lang="zh"]) [data-lang="zh"] { display: none !important; }
body {
  margin: 0;
  background: var(--bg-canvas);
  color: var(--fg);
  font-family: var(--font-body);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
body::before { display: none !important; }
a { color: inherit; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 32px;
  background: rgba(252, 250, 247, 0.94);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(12px);
  font-size: 12px;
  letter-spacing: normal;
}
.brand { font-family: var(--font-display); font-size: 16px; font-weight: 600; letter-spacing: -0.01em; white-space: nowrap; }
.brand span { color: var(--accent); }
.country-nav { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }
.country-nav a {
  text-decoration: none;
  color: var(--muted);
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s ease;
}
.country-nav a:hover { background: rgba(0,0,0,0.04); color: var(--fg); }
.country-nav a.active { background: var(--fg); color: #ffffff; border-color: var(--fg); font-weight: 600; }
.lang-toggle {
  border: 1px solid var(--border);
  background: #ffffff;
  color: var(--fg);
  border-radius: 4px;
  padding: 4px 10px;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
}
.container { position: relative; max-width: 1320px; margin: 0 auto; padding: 32px 24px 56px; }
header { border-bottom: 1px solid var(--border); padding: 32px 0 24px; margin-bottom: 24px; }
h1 {
  margin: 0;
  max-width: 980px;
  font-family: var(--font-display);
  font-size: clamp(32px, 4.5vw, 56px);
  font-weight: 600;
  letter-spacing: -0.03em;
  line-height: 1.05;
}
.subtitle { max-width: 860px; color: var(--text-secondary); font-size: 15px; margin-top: 12px; line-height: 1.6; }
.meta-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }
.meta-chip {
  border: 1px solid var(--border);
  background: #ffffff;
  border-radius: 4px;
  padding: 4px 10px;
  color: var(--text-secondary);
  font-size: 12px;
}
.toc {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin: 18px 0 24px;
}
.toc a {
  text-decoration: none;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 5px 12px;
  background: #ffffff;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s;
}
.toc a:hover {
  background: var(--fg);
  color: #ffffff;
  border-color: var(--fg);
}
.view-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin: -10px 0 24px;
}
.view-switch > span { color: var(--muted); font-size: 12px; margin-right: 3px; }
.view-switch button {
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 5px 12px;
  background: #ffffff;
  color: var(--text-secondary);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
}
.view-switch button[aria-pressed="true"] { background: var(--fg); color: #ffffff; border-color: var(--fg); font-weight: 600; }
body[data-dashboard-view="core"] .chart-card[data-dashboard-view="deep"] { display: none; }
.data-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.data-card, .chart-card, .panel, .data-note, .gaps-table {
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}
.data-card {
  padding: 14px 16px;
  border-top: 3px solid var(--border-strong);
}
.data-card span {
  display: block;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: normal;
  text-transform: none;
}
.data-card strong {
  display: block;
  font-family: var(--font-body);
  font-size: 26px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
  margin: 6px 0 4px;
  color: var(--fg);
}
.data-card small { color: var(--muted); font-size: 11px; }

/* Spark-Range component */
.ft-spark-range {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}
.ft-spark-track {
  position: relative;
  height: 4px;
  background: rgba(18, 21, 26, 0.08);
  border-radius: 2px;
  margin: 6px 0 4px;
}
.ft-spark-point {
  position: absolute;
  top: -3px;
  width: 10px;
  height: 10px;
  background: var(--accent);
  border: 2px solid #ffffff;
  border-radius: 50%;
  transform: translateX(-50%);
  box-shadow: 0 1px 2px rgba(0,0,0,0.3);
}
.ft-spark-labels {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--muted);
}
.ft-spark-pct {
  font-weight: 600;
  color: var(--fg);
}

.panel {
  padding: 0;
  margin-bottom: 36px;
  background: transparent;
  border: none;
  box-shadow: none;
}
.section-title {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-bottom: 2px solid var(--fg);
  padding-bottom: 12px;
  margin-bottom: 18px;
}
.section-title h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(24px, 2.8vw, 36px);
  font-weight: 600;
  letter-spacing: -0.025em;
  color: var(--fg);
}
.logic { color: var(--text-secondary); max-width: 920px; font-size: 13.5px; line-height: 1.55; }
.charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(520px, 100%), 1fr)); gap: 16px; margin-bottom: 20px; }
.chart-card {
  padding: 14px 16px 12px;
  min-width: 0;
  overflow: hidden;
  transition: border-color 0.15s ease;
}
.chart-card:hover { border-color: var(--border-strong); }
.chart-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: stretch;
  border-bottom: 1px solid var(--border);
  padding-bottom: 10px;
  margin-bottom: 8px;
}
.chart-title { min-width: 0; flex: 1 1 auto; padding-top: 2px; }
.chart-head h3 {
  margin: 0;
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--fg);
}
.chart-status { display: flex; align-items: flex-start; gap: 8px; flex: 0 0 auto; }
.latest-reading {
  display: grid;
  grid-template-columns: auto auto;
  column-gap: 8px;
  align-items: baseline;
  min-width: 140px;
  padding-left: 12px;
  border-left: 1px solid var(--border);
  font-variant-numeric: tabular-nums;
}
.latest-label {
  grid-column: 1 / -1;
  color: var(--accent);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: normal;
  line-height: 1.2;
  text-transform: none;
}
.latest-value { display: inline-flex; align-items: baseline; gap: 5px; min-width: 0; }
.latest-value strong {
  font-family: var(--font-body);
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
  color: var(--fg);
  white-space: nowrap;
}
.latest-value em { color: var(--muted); font-size: 10px; font-style: normal; white-space: nowrap; }
.latest-reading time { color: var(--muted); font-size: 11px; white-space: nowrap; }
.quality-pill {
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 3px 7px;
  color: var(--muted);
  font-size: 11px;
  white-space: nowrap;
}
.chart-quality-verified .quality-pill { color: #0d7680; border-color: rgba(13,118,128,0.3); background: rgba(13,118,128,0.06); }
.chart-quality-watch .quality-pill { color: var(--warn); border-color: rgba(184,98,0,0.3); background: rgba(184,98,0,0.06); }
.chart-quality-low_confidence .quality-pill { color: var(--low); border-color: rgba(153,15,61,0.3); background: rgba(153,15,61,0.06); }
.authority-chip, .freshness-chip {
  font-size: 11px; letter-spacing: normal; padding: 2px 7px; border-radius: 3px;
  border: 1px solid var(--border); color: var(--text-secondary); margin-left: 4px;
}
.authority-chip { background: #fcfaf7; }
.freshness-chip { background: #fcfaf7; }
.cross-check { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
.cross-check.diverged { color: var(--low); font-weight: 600; }
.cross-check-history { color: var(--muted); }
.plotly-chart { width: 100%; min-width: 0; height: 360px; }
.lw-chart-wrap {
  display: flex;
  flex-direction: column;
  height: 350px;
  width: 100%;
  background: #ffffff;
  padding: 4px 0 4px;
}
.lw-chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
  min-height: 22px;
}
.lw-chart-title-group {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}
.lw-chart-unit {
  font-size: 11px;
  color: var(--muted);
  font-weight: 500;
}
.lw-chart-meta {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}
.lw-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  user-select: none;
  padding: 1px 5px;
  border-radius: 3px;
  border: 1px solid transparent;
  transition: opacity 0.14s ease, background 0.14s ease, border-color 0.14s ease;
}
.lw-legend-item:hover {
  background: rgba(18, 21, 26, 0.04);
  border-color: rgba(18, 21, 26, 0.12);
}
.lw-legend-item.is-hidden {
  opacity: 0.36;
  text-decoration: line-through;
}
.lw-legend-swatch {
  display: inline-block;
  width: 10px;
  height: 3px;
  border-radius: 1.5px;
}
.lw-legend-val {
  font-weight: 600;
  color: var(--fg);
}
.lw-badge-pill {
  display: inline-flex;
  align-items: center;
  padding: 1px 7px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
}
.lw-toolbar {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-left: 4px;
  padding-left: 6px;
  border-left: 1px solid rgba(18, 21, 26, 0.10);
}
.lw-range-group, .lw-action-group {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.lw-action-group {
  margin-left: 3px;
  padding-left: 4px;
  border-left: 1px solid rgba(18, 21, 26, 0.08);
}
.lw-range-btn, .lw-tool-btn {
  appearance: none;
  border: 1px solid rgba(18, 21, 26, 0.12);
  background: #fcfaf7;
  color: var(--text-secondary);
  font-family: inherit;
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
  padding: 3px 5px;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.12s ease;
}
.lw-range-btn:hover, .lw-tool-btn:hover {
  border-color: var(--accent, #990f3d);
  color: var(--accent, #990f3d);
  background: rgba(153, 15, 61, 0.05);
}
.lw-range-btn.is-active, .lw-tool-btn.is-active {
  background: var(--accent, #990f3d);
  border-color: var(--accent, #990f3d);
  color: #ffffff;
}
.lw-zoom-rect {
  position: absolute;
  top: 0;
  bottom: 24px;
  background: rgba(153, 15, 61, 0.10);
  border: 1px dashed #990f3d;
  pointer-events: none;
  z-index: 8;
  display: none;
}
.lw-delta-banner {
  display: none;
  align-items: center;
  gap: 5px;
  padding: 2px 7px;
  border-radius: 3px;
  background: rgba(153, 15, 61, 0.08);
  border: 1px solid rgba(153, 15, 61, 0.24);
  color: #12151a;
  font-size: 10.5px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.lw-delta-banner.is-visible {
  display: inline-flex;
}
.lw-delta-close {
  border: none;
  background: transparent;
  color: #990f3d;
  font-weight: 700;
  cursor: pointer;
  padding: 0 2px;
  font-size: 12px;
  line-height: 1;
}
.lw-chart-plot.is-boxzoom {
  cursor: crosshair !important;
}
.lw-lightbox-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(18, 21, 26, 0.55);
  backdrop-filter: blur(2px);
  z-index: 9990;
  display: none;
}
.lw-lightbox-backdrop.is-open {
  display: block;
}
.lw-card-expanded {
  position: fixed !important;
  top: 4vh !important;
  left: 4vw !important;
  width: 92vw !important;
  height: 90vh !important;
  max-width: 1440px !important;
  margin: 0 auto !important;
  z-index: 9995 !important;
  background: #ffffff !important;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.28) !important;
  border-radius: 6px !important;
  padding: 20px 24px !important;
  display: flex !important;
  flex-direction: column !important;
  overflow: auto !important;
}
.lw-card-expanded .chart-canvas,
.lw-card-expanded .lw-chart-wrap {
  flex: 1 1 auto !important;
  height: 62vh !important;
  min-height: 460px !important;
}
.lw-card-expanded .lw-chart-plot {
  height: calc(62vh - 44px) !important;
  min-height: 410px !important;
}
.lw-chart-plot {
  flex: 1 1 auto;
  width: 100%;
  min-height: 290px;
  position: relative;
}
.plot-container, .svg-container { max-width: 100% !important; }
#js-plotly-tester { width: 1px !important; max-width: 1px !important; overflow: hidden !important; }
.chart-card footer {
  display: grid;
  gap: 3px;
  color: var(--muted);
  font-size: 11px;
  border-top: 1px solid var(--border);
  padding-top: 10px;
}
.chart-card footer a { color: var(--accent); }
.caveat { color: var(--muted); font-size: 12px; margin: 10px 0 0; }
.empty-note { padding: 20px; color: var(--muted); border: 1px dashed var(--border); border-radius: 4px; }
.data-note { padding: 14px 18px; margin-bottom: 24px; color: var(--text-secondary); background: #ffffff; font-size: 13px; line-height: 1.6; }
.gaps-table { width: 100%; border-collapse: collapse; font-size: 13px; background: #ffffff; }
.gaps-table th, .gaps-table td { padding: 10px 14px; border-bottom: 1px solid var(--border); vertical-align: top; text-align: left; }
.gaps-table th { color: var(--text-secondary); font-size: 11px; font-weight: 600; letter-spacing: normal; text-transform: none; background: #fcfaf7; }
footer.page-footer { color: var(--muted); border-top: 1px solid var(--border); padding-top: 20px; font-size: 12px; }
@media (max-width: 760px) {
  .topbar { align-items: flex-start; flex-direction: column; padding: 12px 18px; }
  .container { padding: 24px 16px 42px; }
  .charts-grid { grid-template-columns: 1fr; }
  .panel { overflow-x: auto; }
  .chart-card { padding: 13px; }
  .chart-head { flex-direction: column; gap: 8px; }
  .chart-head h3 { font-size: 16px; }
  .chart-status { width: 100%; justify-content: space-between; align-items: center; }
  .latest-reading { flex: 1 1 auto; min-width: 0; border-left: 0; border-top: 1px solid var(--border); padding: 8px 0 0; }
  .latest-value strong { font-size: 21px; }
  .plotly-chart { height: 320px; }
  .lw-chart-wrap { height: 320px; }
}
"""


LW_GLOBAL_HORIZON_HTML = """    <span class="horizon-sep" aria-hidden="true" style="width:1px;height:18px;background:rgba(18,21,26,0.16);margin:0 4px;"></span>
    <span><span data-lang="en">Horizon</span><span data-lang="zh">时间跨度</span></span>
    <button type="button" data-horizon-option="1Y" aria-pressed="false" onclick="window.CPChart && window.CPChart.setGlobalHorizon('1Y')">1Y</button>
    <button type="button" data-horizon-option="3Y" aria-pressed="false" onclick="window.CPChart && window.CPChart.setGlobalHorizon('3Y')">3Y</button>
    <button type="button" data-horizon-option="5Y" aria-pressed="false" onclick="window.CPChart && window.CPChart.setGlobalHorizon('5Y')">5Y</button>
    <button type="button" data-horizon-option="10Y" aria-pressed="false" onclick="window.CPChart && window.CPChart.setGlobalHorizon('10Y')">10Y</button>
    <button type="button" data-horizon-option="ALL" aria-pressed="true" onclick="window.CPChart && window.CPChart.setGlobalHorizon('ALL')"><span data-lang="en">All</span><span data-lang="zh">全部</span></button>
    <span class="horizon-hint" style="font-size:11px;color:var(--muted);margin-left:6px;"><span data-lang="en">Drag: pan · Shift+Drag (or 🔍): box-zoom &amp; Δ · Click legend: toggle · Double-click: reset</span><span data-lang="zh">拖拽：平移 · Shift+拖拽（或点🔍）：框选测算Δ · 单击图例：显隐 · 双击：重置</span></span>"""


def _lw_runtime_script(lw_specs: dict[str, dict[str, Any]], country_code: str) -> str:
    date_pool: dict[tuple[str, ...], int] = {}
    date_list: list[list[str]] = []
    compact_specs: dict[str, dict[str, Any]] = {}
    for cid, spec in lw_specs.items():
        c_spec = dict(spec)
        c_series = []
        for s in spec.get("series") or []:
            cs = dict(s)
            pts = cs.pop("data", None) or []
            times = tuple(str(pt["time"]) for pt in pts)
            if times not in date_pool:
                date_pool[times] = len(date_list)
                date_list.append(list(times))
            cs["x"] = date_pool[times]
            cs["y"] = [pt["value"] for pt in pts]
            if any("color" in pt for pt in pts):
                cs["c"] = [pt.get("color", "") for pt in pts]
            c_series.append(cs)
        c_spec["series"] = c_series
        compact_specs[cid] = c_spec

    dates_json = json.dumps(date_list, ensure_ascii=False, separators=(",", ":"))
    specs_json = json.dumps(compact_specs, ensure_ascii=False, separators=(",", ":"))
    return f"""<script>
window.CP_LW_DATES = {dates_json};
window.CP_LW_CHARTS = Object.assign(window.CP_LW_CHARTS || {{}}, {specs_json});
(function() {{
  var mainCountry = '{country_code}';
  var mountedCharts = {{}};
  var currentGlobalHorizon = 'ALL';
  var isShiftDown = false;
  var backdropEl = null;
  var expandedCardId = null;

  function getPts(s) {{
    if (!s) return [];
    if (s.data) return s.data;
    var dates = (window.CP_LW_DATES || [])[s.x] || [];
    var vals = s.y || [];
    var cols = s.c || null;
    var out = [];
    for (var i = 0; i < dates.length && i < vals.length; i++) {{
      var pt = {{ time: dates[i], value: vals[i] }};
      if (cols && cols[i]) pt.color = cols[i];
      out.push(pt);
    }}
    s.data = out;
    return out;
  }}

  function formatVal(val) {{
    if (val === null || val === undefined || isNaN(val)) return 'n/a';
    var n = Number(val);
    var abs = Math.abs(n);
    if (abs >= 1e9) {{
      return (n / 1e9).toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }}) + ' bn';
    }}
    if (abs >= 1e6) {{
      return (n / 1e6).toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }}) + ' mn';
    }}
    if (abs >= 1e5) {{
      return (n / 1e3).toLocaleString('en-US', {{ minimumFractionDigits: 1, maximumFractionDigits: 1 }}) + 'k';
    }}
    if (abs >= 1000) {{
      var isInt = Math.abs(n - Math.round(n)) < 1e-6;
      return n.toLocaleString('en-US', {{
        minimumFractionDigits: isInt ? 0 : 2,
        maximumFractionDigits: isInt ? 0 : 2
      }});
    }}
    if (abs >= 10) {{
      var isInt10 = Math.abs(n - Math.round(n)) < 1e-6;
      return n.toLocaleString('en-US', {{
        minimumFractionDigits: isInt10 ? 0 : 1,
        maximumFractionDigits: 1
      }});
    }}
    return n.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
  }}

  function syncToolbarReadout(cid, spec) {{
    var series = (spec && spec.series) || [];
    if (!series.length) return;
    var best = null;
    for (var i = 0; i < series.length; i++) {{
      if (series[i].name === mainCountry || series[i].isPrimary) {{
        best = series[i];
        break;
      }}
    }}
    if (!best) best = series[0];
    var pts = getPts(best);
    if (!pts.length) return;
    var lastPt = pts[pts.length - 1];
    var valStr = formatVal(lastPt.value);
    var readout = document.querySelector('.chart-reading[data-chart-id="' + cid + '"]');
    if (readout) {{
      var number = readout.querySelector('.chart-reading-value strong');
      if (number && number.textContent.trim() === 'n/a') number.textContent = valStr;
      var periods = readout.querySelectorAll('time span');
      if (!readout.dataset.latestDate && periods.length) {{
        periods.forEach(function(period) {{ period.textContent = String(lastPt.time); }});
      }}
    }}
  }}

  function collectAllTimes(spec) {{
    var set = {{}};
    var series = (spec && spec.series) || [];
    for (var i = 0; i < series.length; i++) {{
      var pts = getPts(series[i]);
      for (var j = 0; j < pts.length; j++) {{
        if (pts[j] && pts[j].time) set[pts[j].time] = true;
      }}
    }}
    return Object.keys(set).sort();
  }}

  function getAvailableHorizons(allTimes) {{
    if (!allTimes || allTimes.length < 2) return ['ALL'];
    var minYear = parseInt(allTimes[0].slice(0, 4), 10);
    var maxYear = parseInt(allTimes[allTimes.length - 1].slice(0, 4), 10);
    var span = Math.max(1, maxYear - minYear);
    var out = [];
    if (span >= 1) out.push('1Y');
    if (span >= 3) out.push('3Y');
    if (span >= 5) out.push('5Y');
    if (span >= 10) out.push('10Y');
    out.push('ALL');
    return out;
  }}

  function renderMetaBar(cid, spec, allTimes) {{
    var metaEl = document.getElementById('lw-meta-' + cid);
    if (!metaEl) return;
    var html = [];
    if (spec.badge && spec.badge.text) {{
      html.push(
        '<span class="lw-badge-pill" style="color:' + (spec.badge.color || '#0d7680') +
        ';background:' + (spec.badge.bg || 'rgba(13,118,128,0.08)') + ';">' +
        spec.badge.text + '</span>'
      );
    }}
    var series = spec.series || [];
    for (var i = 0; i < series.length; i++) {{
      var s = series[i];
      var pts = getPts(s);
      var lastVal = pts.length ? formatVal(pts[pts.length - 1].value) : '—';
      html.push(
        '<span class="lw-legend-item" data-series-idx="' + i + '" role="button" tabindex="0" title="Click: show/hide · Double-click (or Alt+Click): solo series / 单击显隐 · 双击独显">' +
        '<span class="lw-legend-swatch" style="background:' + (s.color || '#990f3d') + ';"></span>' +
        '<span>' + (s.name || ('S' + (i + 1))) + '</span>' +
        '<span class="lw-legend-val" data-series-idx="' + i + '">' + lastVal + '</span>' +
        '</span>'
      );
    }}
    html.push('<span class="lw-delta-banner" id="lw-delta-' + cid + '"></span>');
    var horizons = getAvailableHorizons(allTimes);
    var rangeBtns = [];
    for (var h = 0; h < horizons.length; h++) {{
      var hz = horizons[h];
      var label = hz === 'ALL' ? 'All' : hz;
      var activeCls = hz === currentGlobalHorizon ? ' is-active' : '';
      rangeBtns.push(
        '<button type="button" class="lw-range-btn' + activeCls + '" data-lw-horizon="' + hz + '" title="Show ' + label + ' range">' + label + '</button>'
      );
    }}
    html.push(
      '<span class="lw-toolbar">' +
        '<span class="lw-range-group">' + rangeBtns.join('') + '</span>' +
        '<span class="lw-action-group">' +
          '<button type="button" class="lw-tool-btn" data-lw-action="boxzoom" title="Box-select time range & compute Δ (or hold Shift + drag) / 框选时间段并测算区间变动 Δ（或按住 Shift 拖拽）">🔍</button>' +
          '<button type="button" class="lw-tool-btn" data-lw-action="reset" title="Reset zoom & restore all series (or double-click chart) / 重置缩放并恢复全部序列（或双击图表）">↺</button>' +
          '<button type="button" class="lw-tool-btn" data-lw-action="csv" title="Download CSV data / 导出 CSV 数据">CSV</button>' +
          '<button type="button" class="lw-tool-btn" data-lw-action="png" title="Download PNG chart snapshot / 导出高清 PNG 截图">PNG</button>' +
          '<button type="button" class="lw-tool-btn" data-lw-action="expand" title="Fullscreen view / 全屏放大检视">⛶</button>' +
        '</span>' +
      '</span>'
    );
    metaEl.innerHTML = html.join('');

    metaEl.onclick = function(e) {{
      var rangeBtn = e.target.closest('.lw-range-btn[data-lw-horizon]');
      if (rangeBtn) {{
        setChartHorizon(cid, rangeBtn.dataset.lwHorizon);
        return;
      }}
      var actBtn = e.target.closest('[data-lw-action]');
      if (actBtn) {{
        var act = actBtn.dataset.lwAction;
        if (act === 'boxzoom') toggleBoxZoomMode(cid);
        else if (act === 'reset') resetChart(cid);
        else if (act === 'csv') exportCSV(cid);
        else if (act === 'png') exportPNG(cid);
        else if (act === 'expand') toggleExpand(cid);
        return;
      }}
      var legItem = e.target.closest('.lw-legend-item[data-series-idx]');
      if (legItem) {{
        var idx = Number(legItem.dataset.seriesIdx);
        if (e.altKey || e.metaKey) soloSeries(cid, idx);
        else toggleSeries(cid, idx);
      }}
    }};

    metaEl.ondblclick = function(e) {{
      var legItem = e.target.closest('.lw-legend-item[data-series-idx]');
      if (legItem) {{
        e.preventDefault();
        soloSeries(cid, Number(legItem.dataset.seriesIdx));
      }}
    }};
  }}

  function clearDeltaBanner(cid) {{
    var banner = document.getElementById('lw-delta-' + cid);
    if (banner) {{
      banner.classList.remove('is-visible');
      banner.innerHTML = '';
    }}
  }}

  function updateDeltaBanner(cid, inst, fromT, toT) {{
    var banner = document.getElementById('lw-delta-' + cid);
    if (!banner || !inst || !inst.spec) return;
    var series = inst.spec.series || [];
    var primary = null;
    for (var i = 0; i < series.length; i++) {{
      if (inst.seriesVisible[i] !== false && (series[i].isPrimary || series[i].name === mainCountry)) {{
        primary = series[i];
        break;
      }}
    }}
    if (!primary) {{
      for (var j = 0; j < series.length; j++) {{
        if (inst.seriesVisible[j] !== false) {{ primary = series[j]; break; }}
      }}
    }}
    if (!primary) return;
    var pts = getPts(primary);
    var pStart = null, pEnd = null;
    for (var k = 0; k < pts.length; k++) {{
      if (pts[k].time >= fromT && !pStart) pStart = pts[k];
      if (pts[k].time <= toT) pEnd = pts[k];
    }}
    if (!pStart || !pEnd || pStart.time === pEnd.time) return;
    var v1 = Number(pStart.value);
    var v2 = Number(pEnd.value);
    var diff = v2 - v1;
    var sign = diff > 0 ? '+' : '';
    var unit = String(inst.spec.unit || '');
    var isRateUnit = /%|pp|bp|bps|index/i.test(unit);
    var pctStr = '';
    if (!isRateUnit && Math.abs(v1) > 1e-9) {{
      var pct = ((v2 - v1) / Math.abs(v1)) * 100;
      pctStr = ' (' + (pct > 0 ? '+' : '') + pct.toFixed(1) + '%)';
    }}
    banner.innerHTML =
      '<span>' + pStart.time.slice(0, 7) + ' → ' + pEnd.time.slice(0, 7) + ': ' +
      formatVal(v1) + ' → ' + formatVal(v2) + ' · <strong>Δ ' + sign + formatVal(diff) + '</strong>' + pctStr + '</span>' +
      '<button type="button" class="lw-delta-close" data-lw-action="reset" title="Clear selection & reset zoom">×</button>';
    banner.classList.add('is-visible');
  }}

  function setChartHorizon(cid, horizon) {{
    var inst = mountedCharts[cid];
    if (!inst || !inst.chart) return;
    var allTimes = inst.allTimes || [];
    if (!allTimes.length) return;
    clearDeltaBanner(cid);
    var hz = String(horizon || 'ALL').toUpperCase();
    if (hz === 'ALL') {{
      inst.chart.timeScale().fitContent();
    }} else {{
      var years = parseInt(hz, 10) || 5;
      var maxT = allTimes[allTimes.length - 1];
      var cutoffYear = parseInt(maxT.slice(0, 4), 10) - years;
      var cutoffStr = String(cutoffYear) + maxT.slice(4);
      var fromT = allTimes[0];
      for (var i = 0; i < allTimes.length; i++) {{
        if (allTimes[i] >= cutoffStr) {{
          fromT = allTimes[i];
          break;
        }}
      }}
      if (fromT >= maxT && allTimes.length > 1) {{
        fromT = allTimes[Math.max(0, allTimes.length - 2)];
      }}
      try {{
        inst.chart.timeScale().setVisibleRange({{ from: fromT, to: maxT }});
      }} catch (err) {{
        inst.chart.timeScale().fitContent();
      }}
    }}
    inst.chart.priceScale('right').applyOptions({{ autoScale: true }});
    if (inst.hasLeftScale) inst.chart.priceScale('left').applyOptions({{ autoScale: true }});
    var metaEl = document.getElementById('lw-meta-' + cid);
    if (metaEl) {{
      metaEl.querySelectorAll('.lw-range-btn').forEach(function(btn) {{
        btn.classList.toggle('is-active', btn.dataset.lwHorizon === hz);
      }});
    }}
  }}

  function setGlobalHorizon(horizon) {{
    var hz = String(horizon || 'ALL').toUpperCase();
    currentGlobalHorizon = hz;
    document.querySelectorAll('[data-horizon-option]').forEach(function(btn) {{
      btn.setAttribute('aria-pressed', String(btn.dataset.horizonOption === hz));
    }});
    Object.keys(mountedCharts).forEach(function(cid) {{
      setChartHorizon(cid, hz);
    }});
  }}

  function syncSeriesVisibility(cid) {{
    var inst = mountedCharts[cid];
    if (!inst) return;
    var metaEl = document.getElementById('lw-meta-' + cid);
    Object.keys(inst.apiByIdx).forEach(function(k) {{
      var idx = Number(k);
      var vis = inst.seriesVisible[idx] !== false;
      inst.apiByIdx[idx].applyOptions({{ visible: vis }});
    }});
    if (metaEl) {{
      metaEl.querySelectorAll('.lw-legend-item[data-series-idx]').forEach(function(item) {{
        var idx = Number(item.dataset.seriesIdx);
        item.classList.toggle('is-hidden', inst.seriesVisible[idx] === false);
      }});
    }}
  }}

  function toggleSeries(cid, sIdx) {{
    var inst = mountedCharts[cid];
    if (!inst || !inst.spec || (inst.spec.series || []).length <= 1) return;
    var total = inst.spec.series.length;
    inst.seriesVisible[sIdx] = inst.seriesVisible[sIdx] === false ? true : false;
    var anyVis = false;
    for (var i = 0; i < total; i++) {{
      if (inst.seriesVisible[i] !== false) {{ anyVis = true; break; }}
    }}
    if (!anyVis) {{
      for (var j = 0; j < total; j++) inst.seriesVisible[j] = true;
    }}
    syncSeriesVisibility(cid);
  }}

  function soloSeries(cid, sIdx) {{
    var inst = mountedCharts[cid];
    if (!inst || !inst.spec || (inst.spec.series || []).length <= 1) return;
    var total = inst.spec.series.length;
    var onlyThis = true;
    for (var i = 0; i < total; i++) {{
      var v = inst.seriesVisible[i] !== false;
      if ((i === sIdx && !v) || (i !== sIdx && v)) {{ onlyThis = false; break; }}
    }}
    for (var j = 0; j < total; j++) {{
      inst.seriesVisible[j] = onlyThis ? true : (j === sIdx);
    }}
    syncSeriesVisibility(cid);
  }}

  function toggleBoxZoomMode(cid, forceState) {{
    var inst = mountedCharts[cid];
    if (!inst) return;
    inst.boxZoomMode = forceState !== undefined ? Boolean(forceState) : !inst.boxZoomMode;
    inst.el.classList.toggle('is-boxzoom', Boolean(inst.boxZoomMode || isShiftDown));
    var metaEl = document.getElementById('lw-meta-' + cid);
    if (metaEl) {{
      var btn = metaEl.querySelector('[data-lw-action="boxzoom"]');
      if (btn) btn.classList.toggle('is-active', Boolean(inst.boxZoomMode));
    }}
  }}

  function resetChart(cid) {{
    var inst = mountedCharts[cid];
    if (!inst) return;
    var total = (inst.spec.series || []).length;
    for (var i = 0; i < total; i++) inst.seriesVisible[i] = true;
    syncSeriesVisibility(cid);
    toggleBoxZoomMode(cid, false);
    setChartHorizon(cid, 'ALL');
  }}

  function exportCSV(cid) {{
    var spec = (window.CP_LW_CHARTS || {{}})[cid];
    if (!spec || !spec.series || !spec.series.length) return;
    var allTimes = collectAllTimes(spec);
    var series = spec.series;
    var maps = series.map(function(s) {{
      var m = {{}};
      getPts(s).forEach(function(pt) {{ m[pt.time] = pt.value; }});
      return m;
    }});
    var unitSuffix = spec.unit ? ' (' + spec.unit + ')' : '';
    var headers = ['Date'].concat(series.map(function(s, i) {{
      var name = String(s.name || ('Series_' + (i + 1))).replace(/"/g, '""');
      return '"' + name + unitSuffix.replace(/"/g, '""') + '"';
    }}));
    var rows = [headers.join(',')];
    allTimes.forEach(function(t) {{
      var row = [t];
      for (var i = 0; i < maps.length; i++) {{
        var v = maps[i][t];
        row.push(v !== undefined && v !== null ? String(v) : '');
      }}
      rows.push(row.join(','));
    }});
    var blob = new Blob(['\\ufeff' + rows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = mainCountry + '_' + cid.replace(/[^a-zA-Z0-9_-]/g, '_') + '.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }}

  function exportPNG(cid) {{
    var inst = mountedCharts[cid];
    if (!inst || !inst.chart || typeof inst.chart.takeScreenshot !== 'function') return;
    var shot = inst.chart.takeScreenshot();
    var padX = 20, topH = 54, botH = 26;
    var out = document.createElement('canvas');
    out.width = shot.width + padX * 2;
    out.height = shot.height + topH + botH;
    var ctx = out.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, out.width, out.height);
    ctx.fillStyle = '#990f3d';
    ctx.fillRect(0, 0, out.width, 4);
    var card = inst.el.closest('.chart-card, .chart-cell');
    var headingEl = card ? card.querySelector('h3 span[data-lang="en"], h3, .lw-chart-title') : null;
    var titleText = (headingEl && headingEl.textContent.trim()) || inst.spec.title || cid;
    var unitText = inst.spec.unit ? ' (' + inst.spec.unit + ')' : '';
    ctx.fillStyle = '#12151a';
    ctx.font = 'bold 14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.fillText(titleText + unitText, padX, 26);
    var lx = padX;
    (inst.spec.series || []).forEach(function(s, idx) {{
      if (inst.seriesVisible[idx] === false) return;
      var pts = getPts(s);
      var lastV = pts.length ? formatVal(pts[pts.length - 1].value) : '';
      var lbl = (s.name || ('S' + (idx + 1))) + (lastV ? ': ' + lastV : '');
      ctx.fillStyle = s.color || '#990f3d';
      ctx.fillRect(lx, 36, 10, 3);
      ctx.fillStyle = '#4b525f';
      ctx.font = '11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.fillText(lbl, lx + 14, 41);
      lx += ctx.measureText(lbl).width + 28;
    }});
    ctx.drawImage(shot, padX, topH);
    ctx.fillStyle = '#737c8c';
    ctx.font = '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.fillText('East Meridian · Macro Dashboard (' + mainCountry + ')', padX, out.height - 9);
    var a = document.createElement('a');
    a.href = out.toDataURL('image/png');
    a.download = mainCountry + '_' + cid.replace(/[^a-zA-Z0-9_-]/g, '_') + '.png';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }}

  function ensureBackdrop() {{
    if (backdropEl) return backdropEl;
    backdropEl = document.createElement('div');
    backdropEl.className = 'lw-lightbox-backdrop';
    backdropEl.onclick = function() {{
      if (expandedCardId) toggleExpand(expandedCardId);
    }};
    document.body.appendChild(backdropEl);
    return backdropEl;
  }}

  function toggleExpand(cid) {{
    var inst = mountedCharts[cid];
    if (!inst || !inst.el) return;
    var card = inst.el.closest('.chart-card, .chart-cell, .deepdive-chart-box') || inst.el.parentElement;
    if (!card) return;
    var bd = ensureBackdrop();
    var isClosing = card.classList.contains('lw-card-expanded');
    document.querySelectorAll('.lw-card-expanded').forEach(function(c) {{
      c.classList.remove('lw-card-expanded');
    }});
    if (isClosing) {{
      bd.classList.remove('is-open');
      expandedCardId = null;
    }} else {{
      card.classList.add('lw-card-expanded');
      bd.classList.add('is-open');
      expandedCardId = cid;
    }}
    setTimeout(function() {{
      if (inst.chart && inst.el.clientWidth > 20) {{
        inst.chart.applyOptions({{
          width: inst.el.clientWidth,
          height: inst.el.clientHeight || (isClosing ? 300 : 480)
        }});
        inst.chart.timeScale().fitContent();
      }}
    }}, 30);
  }}

  function resolveTimeAtX(inst, x) {{
    if (!inst || !inst.chart) return null;
    var t = inst.chart.timeScale().coordinateToTime(x);
    if (t) {{
      if (typeof t === 'string') return t;
      if (typeof t === 'object' && t.year) {{
        return t.year + '-' + String(t.month).padStart(2, '0') + '-' + String(t.day).padStart(2, '0');
      }}
    }}
    var logIdx = inst.chart.timeScale().coordinateToLogical(x);
    if (logIdx !== null && logIdx !== undefined && inst.allTimes && inst.allTimes.length) {{
      var idx = Math.max(0, Math.min(inst.allTimes.length - 1, Math.round(logIdx)));
      return inst.allTimes[idx];
    }}
    return null;
  }}

  window.addEventListener('keydown', function(e) {{
    if (e.key === 'Shift' && !isShiftDown) {{
      isShiftDown = true;
      Object.keys(mountedCharts).forEach(function(cid) {{
        mountedCharts[cid].el.classList.add('is-boxzoom');
      }});
    }} else if (e.key === 'Escape' && expandedCardId) {{
      toggleExpand(expandedCardId);
    }}
  }});

  window.addEventListener('keyup', function(e) {{
    if (e.key === 'Shift') {{
      isShiftDown = false;
      Object.keys(mountedCharts).forEach(function(cid) {{
        var inst = mountedCharts[cid];
        inst.el.classList.toggle('is-boxzoom', Boolean(inst.boxZoomMode));
      }});
    }}
  }});

  var resizeObs = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(function(entries) {{
    entries.forEach(function(entry) {{
      var el = entry.target;
      var cid = el.dataset.lwChart || el.id;
      var inst = mountedCharts[cid];
      if (inst && inst.chart && el.clientWidth > 20) {{
        inst.chart.applyOptions({{ width: el.clientWidth }});
      }}
    }});
  }}) : null;

  function mountChart(el) {{
    if (!el || el.dataset.lwMounted === '1') return;
    if (!window.LightweightCharts) return;
    if (el.offsetParent === null || el.clientWidth < 20) return;
    var cid = el.dataset.lwChart || el.id;
    var spec = (window.CP_LW_CHARTS || {{}})[cid];
    if (!spec) return;

    el.dataset.lwMounted = '1';
    var allTimes = collectAllTimes(spec);
    renderMetaBar(cid, spec, allTimes);
    var seriesSpecs = spec.series || [];
    var hasLeftScale = seriesSpecs.some(function(s) {{ return s.scale === 'left'; }});

    var chart = LightweightCharts.createChart(el, {{
      width: el.clientWidth,
      height: el.clientHeight || 295,
      localization: {{
        priceFormatter: formatVal
      }},
      layout: {{
        background: {{ type: 'solid', color: '#ffffff' }},
        textColor: '#737c8c',
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        fontSize: 11,
        attributionLogo: false
      }},
      grid: {{
        vertLines: {{ visible: false }},
        horzLines: {{ color: 'rgba(18, 21, 26, 0.06)', style: 0 }}
      }},
      leftPriceScale: {{
        visible: hasLeftScale,
        borderVisible: false,
        scaleMargins: {{ top: 0.12, bottom: 0.10 }}
      }},
      rightPriceScale: {{
        borderVisible: false,
        scaleMargins: {{ top: 0.12, bottom: 0.10 }}
      }},
      timeScale: {{
        borderColor: 'rgba(18, 21, 26, 0.14)',
        rightOffset: 2,
        fixLeftEdge: true,
        timeVisible: false
      }},
      crosshair: {{
        mode: 0,
        vertLine: {{ color: 'rgba(18, 21, 26, 0.25)', width: 1, style: 2, labelBackgroundColor: '#12151a' }},
        horzLine: {{ color: 'rgba(18, 21, 26, 0.25)', width: 1, style: 2, labelBackgroundColor: '#12151a' }}
      }},
      handleScroll: {{ mouseWheel: false, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false }},
      handleScale: {{ mouseWheel: false, pinch: true, axisPressedMouseMove: true }}
    }});

    var order = [];
    for (var i = 0; i < seriesSpecs.length; i++) {{
      if (!seriesSpecs[i].isPrimary) order.push(i);
    }}
    for (var j = 0; j < seriesSpecs.length; j++) {{
      if (seriesSpecs[j].isPrimary) order.push(j);
    }}

    var apiByIdx = {{}};
    var seriesVisible = {{}};
    var primaryApi = null;
    order.forEach(function(idx) {{
      var s = seriesSpecs[idx];
      seriesVisible[idx] = true;
      var api;
      if (s.type === 'histogram') {{
        api = chart.addHistogramSeries({{
          color: s.color || '#0d7680',
          priceScaleId: s.scale || 'right',
          priceLineVisible: false,
          lastValueVisible: false,
          base: 0
        }});
      }} else {{
        api = chart.addLineSeries({{
          color: s.color || '#990f3d',
          lineWidth: s.width || 2,
          lineStyle: s.style || 0,
          priceScaleId: s.scale || 'right',
          priceLineVisible: false,
          lastValueVisible: Boolean(s.isPrimary),
          crosshairMarkerVisible: true,
          crosshairMarkerRadius: s.isPrimary ? 4 : 3
        }});
      }}
      var pts = getPts(s);
      api.setData(pts);
      if (s.isPrimary && s.type !== 'histogram' && pts.length > 0 && typeof api.setMarkers === 'function') {{
        var lastPt = pts[pts.length - 1];
        api.setMarkers([{{
          time: lastPt.time,
          position: 'inBar',
          color: s.color || '#990f3d',
          shape: 'circle',
          size: 0.7
        }}]);
      }}
      apiByIdx[idx] = api;
      if (s.isPrimary || !primaryApi) primaryApi = api;
    }});

    if (primaryApi && spec.priceLines && spec.priceLines.length) {{
      spec.priceLines.forEach(function(pl) {{
        primaryApi.createPriceLine({{
          price: Number(pl.price),
          color: pl.color || '#0d7680',
          lineWidth: pl.width || 1,
          lineStyle: pl.style !== undefined ? pl.style : 2,
          axisLabelVisible: Boolean(pl.axisLabel),
          title: pl.title || ''
        }});
      }});
    }}

    var metaEl = document.getElementById('lw-meta-' + cid);
    if (metaEl) {{
      chart.subscribeCrosshairMove(function(param) {{
        var valSpans = metaEl.querySelectorAll('.lw-legend-val');
        if (!param || !param.time || !param.seriesData) {{
          valSpans.forEach(function(sp) {{
            var sIdx = Number(sp.dataset.seriesIdx);
            var pts = getPts(seriesSpecs[sIdx]);
            sp.textContent = pts.length ? formatVal(pts[pts.length - 1].value) : '—';
          }});
          return;
        }}
        valSpans.forEach(function(sp) {{
          var sIdx = Number(sp.dataset.seriesIdx);
          var api = apiByIdx[sIdx];
          var d = api ? param.seriesData.get(api) : null;
          if (d && d.value !== undefined) {{
            sp.textContent = formatVal(d.value);
          }}
        }});
      }});
    }}

    var zoomRect = document.createElement('div');
    zoomRect.className = 'lw-zoom-rect';
    el.appendChild(zoomRect);

    var inst = {{
      chart: chart,
      el: el,
      spec: spec,
      allTimes: allTimes,
      apiByIdx: apiByIdx,
      seriesVisible: seriesVisible,
      hasLeftScale: hasLeftScale,
      boxZoomMode: false
    }};
    mountedCharts[cid] = inst;

    el.addEventListener('mousedown', function(e) {{
      if (e.button !== 0 || (!e.shiftKey && !inst.boxZoomMode)) return;
      e.stopPropagation();
      e.preventDefault();
      var rect = el.getBoundingClientRect();
      var startX = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
      zoomRect.style.display = 'block';
      zoomRect.style.left = startX + 'px';
      zoomRect.style.width = '0px';

      function onMove(ev) {{
        var curX = Math.max(0, Math.min(rect.width, ev.clientX - rect.left));
        var x1 = Math.min(startX, curX);
        var x2 = Math.max(startX, curX);
        zoomRect.style.left = x1 + 'px';
        zoomRect.style.width = (x2 - x1) + 'px';
        if (x2 - x1 >= 8) {{
          var t1 = resolveTimeAtX(inst, x1);
          var t2 = resolveTimeAtX(inst, x2);
          if (t1 && t2 && t1 !== t2) {{
            updateDeltaBanner(cid, inst, t1 < t2 ? t1 : t2, t1 < t2 ? t2 : t1);
          }}
        }}
      }}

      function onUp(ev) {{
        window.removeEventListener('mousemove', onMove, true);
        window.removeEventListener('mouseup', onUp, true);
        zoomRect.style.display = 'none';
        var curX = Math.max(0, Math.min(rect.width, ev.clientX - rect.left));
        var x1 = Math.min(startX, curX);
        var x2 = Math.max(startX, curX);
        if (x2 - x1 >= 12) {{
          var t1 = resolveTimeAtX(inst, x1);
          var t2 = resolveTimeAtX(inst, x2);
          if (t1 && t2 && t1 !== t2) {{
            var fromT = t1 < t2 ? t1 : t2;
            var toT = t1 < t2 ? t2 : t1;
            try {{
              chart.timeScale().setVisibleRange({{ from: fromT, to: toT }});
              updateDeltaBanner(cid, inst, fromT, toT);
              if (metaEl) {{
                metaEl.querySelectorAll('.lw-range-btn').forEach(function(b) {{ b.classList.remove('is-active'); }});
              }}
            }} catch (err) {{}}
          }}
        }}
        if (inst.boxZoomMode) toggleBoxZoomMode(cid, false);
      }}

      window.addEventListener('mousemove', onMove, true);
      window.addEventListener('mouseup', onUp, true);
    }}, true);

    el.addEventListener('wheel', function(e) {{
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      var lr = chart.timeScale().getVisibleLogicalRange();
      if (!lr) return;
      var span = Math.max(2, lr.to - lr.from);
      var factor = e.deltaY < 0 ? 0.82 : 1.22;
      var newSpan = Math.max(2, Math.min((allTimes.length || 200) + 10, span * factor));
      var center = (lr.from + lr.to) / 2;
      chart.timeScale().setVisibleLogicalRange({{
        from: center - newSpan / 2,
        to: center + newSpan / 2
      }});
      if (metaEl) {{
        metaEl.querySelectorAll('.lw-range-btn').forEach(function(b) {{ b.classList.remove('is-active'); }});
      }}
    }}, {{ passive: false }});

    el.addEventListener('dblclick', function() {{
      resetChart(cid);
    }});

    if (currentGlobalHorizon !== 'ALL') {{
      setChartHorizon(cid, currentGlobalHorizon);
    }} else {{
      chart.timeScale().fitContent();
    }}
    if (resizeObs) resizeObs.observe(el);
  }}

  var io = typeof IntersectionObserver !== 'undefined' ? new IntersectionObserver(function(entries) {{
    entries.forEach(function(entry) {{
      if (entry.isIntersecting) {{
        mountChart(entry.target);
        if (entry.target.dataset.lwMounted === '1') {{
          io.unobserve(entry.target);
        }}
      }}
    }});
  }}, {{ rootMargin: '320px 0px' }}) : null;

  function observeAll(root) {{
    var scope = root || document;
    var plots = scope.querySelectorAll('.lw-chart-plot[data-lw-chart]');
    plots.forEach(function(el) {{
      var cid = el.dataset.lwChart || el.id;
      var spec = (window.CP_LW_CHARTS || {{}})[cid];
      if (spec) syncToolbarReadout(cid, spec);
      if (el.dataset.lwMounted === '1') {{
        var inst = mountedCharts[cid];
        if (inst && inst.chart && el.offsetParent !== null && el.clientWidth > 20) {{
          inst.chart.applyOptions({{ width: el.clientWidth }});
          inst.chart.timeScale().fitContent();
        }}
        return;
      }}
      if (el.offsetParent === null) return;
      if (io) {{
        io.observe(el);
        var rect = el.getBoundingClientRect();
        if (rect.top < window.innerHeight + 320 && rect.bottom > -320) {{
          mountChart(el);
        }}
      }} else {{
        mountChart(el);
      }}
    }});
  }}

  window.CPChart = {{
    mount: mountChart,
    mountVisibleIn: observeAll,
    refreshAll: function() {{ observeAll(document); }},
    setChartHorizon: setChartHorizon,
    setGlobalHorizon: setGlobalHorizon,
    resetChart: resetChart,
    exportCSV: exportCSV,
    exportPNG: exportPNG,
    toggleExpand: toggleExpand
  }};

  function boot() {{
    if (window.LightweightCharts) {{
      observeAll(document);
    }} else {{
      var timer = setInterval(function() {{
        if (window.LightweightCharts) {{
          clearInterval(timer);
          observeAll(document);
        }}
      }}, 40);
    }}
  }}

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', boot);
  }} else {{
    boot();
  }}
}})();
</script>"""

COUNTRY_META: dict[str, dict[str, str]] = {s.id: {"name": s.name_en, "name_zh": s.name_zh, "file": s.html_file} for s in all_scopes()}


def render_html(
    config: dict[str, Any],
    series_list: list[dict[str, Any]],
    cards: list[dict[str, Any]],
    summary_key_ids: list[str] | None = None,
    country_code: str = "",
) -> str:
    if not country_code:
        country_code = str(config.get("iso2") or config.get("code") or "CN")
    code_upper = country_code.upper()
    meta = COUNTRY_META.get(code_upper, {})
    country_name = config.get("name") or meta.get("name", "Country")
    country_name_zh = config.get("name_zh") or meta.get("name_zh", country_name)

    nav_links = []
    for code, item in COUNTRY_META.items():
        active_cls = ' class="active"' if code == code_upper else ""
        nav_links.append(f'<a href="{item["file"]}"{active_cls} title="{item.get("name", code)}">{code}</a>')
    nav_links.append('<a href="chart_studio.html" style="color:var(--accent);font-weight:600;margin-left:4px;" title="Macro Chart Studio · 自定义对比图表工坊">📈 Studio</a>')
    nav_links.append('<a href="my_dashboard.html" style="color:var(--teal);font-weight:600;margin-left:4px;" title="My Dashboard · 我的自选宏观看板">⭐ My Dashboard</a>')
    nav_links.append('<a href="policy_tracker.html" style="color:var(--slate,#364b61);font-weight:600;margin-left:4px;" title="Central Bank Policy & Event Tracker · 全球央行与宏观事件追踪">🏛️ Policy</a>')
    country_nav_html = "\n    ".join(nav_links)

    chart_count = sum(1 for item in series_list if item.get("observations"))
    source_count = len({item.get("source_name") for item in series_list if item.get("observations")})
    gap_count = len(config.get("data_gaps", []))
    low_count = sum(1 for item in series_list if item.get("quality_status") == "low_confidence" and item.get("observations"))
    def _authority(item: dict[str, Any]) -> str:
        # The assessed authority (quality block) wins over the declared one.
        assessed = item.get("data_quality") or item.get("quality") or {}
        return str(assessed.get("source_authority") or item.get("source_authority") or "")

    native = sum(1 for item in series_list if _authority(item) == "official_primary" and item.get("observations"))
    mirror = sum(1 for item in series_list if _authority(item) == "official_mirror" and item.get("observations"))
    generated_date = datetime.now(UTC).date().isoformat()

    if code_upper == "CN":
        data_note_en = (
            "Data policy: no fabricated proxies. World Bank and IMF annual series provide the durable public skeleton; "
            "SAFE provides official daily RMB fixing data; PBC cards show latest official monetary prints where history is not yet wired."
        )
        data_note_zh = (
            "数据原则：不制造 proxy。World Bank 与 IMF 年度序列提供可维护的公开骨架；"
            "SAFE 提供官方人民币日度中间价；PBC 卡片展示暂未接入历史序列的最新官方货币数据。"
        )
    else:
        data_note_en = (
            f"Data policy: no fabricated proxies. Official public sources provide the primary foundation for {country_name}; "
            "native statistical and central bank releases are prioritized where available."
        )
        data_note_zh = (
            f"数据原则：不制造 proxy。官方公开来源提供{country_name_zh}的基础数据；优先接入本国统计局与央行的原生发布序列。"
        )

    lw_specs: dict[str, dict[str, Any]] = {}
    sections_html = _sections_html(config, series_list, code_upper, lw_specs)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{country_name} Dashboard</title>
<script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js" defer></script>
<style>{CSS}</style>
</head>
<body data-dashboard-view="core">
<div class="topbar">
  <a href="../index.html" style="text-decoration:none;color:inherit;"><div class="brand">East Meridian <span>/ Macro Dashboard</span></div></a>
  <nav class="country-nav" aria-label="country dashboards">
    {country_nav_html}
  </nav>
  <button class="lang-toggle" onclick="toggleLang()" id="lang-btn">中文</button>
</div>

<main class="container">
  <header>
    <h1><span data-lang="en">{country_name} Dashboard</span><span data-lang="zh">{country_name_zh}宏观仪表盘</span></h1>
    <p class="subtitle"><span data-lang="en">{config.get("subtitle_en", f"A data-first macro page for {country_name}.")}</span><span data-lang="zh">{config.get("subtitle_zh", f"{country_name_zh}数据优先宏观页面。")}</span></p>
    <div class="meta-row">
      <span class="meta-chip">{chart_count} <span data-lang="en">charts</span><span data-lang="zh">张图</span></span>
      <span class="meta-chip">{source_count} <span data-lang="en">public source groups</span><span data-lang="zh">组公开来源</span></span>
      <span class="meta-chip">{gap_count} <span data-lang="en">official-data gaps tracked</span><span data-lang="zh">个官方数据缺口</span></span>
      <span class="meta-chip">{low_count} <span data-lang="en">low-confidence charts</span><span data-lang="zh">张低置信图</span></span>
      <span class="meta-chip">{native} <span data-lang="en">native official</span><span data-lang="zh">原生官方</span> · {mirror} <span data-lang="en">mirror</span><span data-lang="zh">镜像</span></span>
    </div>
  </header>

  <section class="data-grid" aria-label="latest data cards">
    {_render_cards(series_list, cards, summary_key_ids or [])}
  </section>

  <nav class="toc" aria-label="section navigation">
    {_section_nav(config)}
  </nav>

  <div class="view-switch" role="group" aria-label="chart density">
    <span><span data-lang="en">Chart view</span><span data-lang="zh">图表视图</span></span>
    <button type="button" data-view-option="core" aria-pressed="true" onclick="setDashboardView('core')"><span data-lang="en">Core 48</span><span data-lang="zh">核心 48</span></button>
    <button type="button" data-view-option="deep" aria-pressed="false" onclick="setDashboardView('deep')"><span data-lang="en">All deep-dive charts</span><span data-lang="zh">全部深度指标</span></button>
{LW_GLOBAL_HORIZON_HTML}
  </div>

  <div class="data-note">
    <span data-lang="en">{data_note_en}</span>
    <span data-lang="zh">{data_note_zh}</span>
  </div>

  {sections_html}

  <section class="panel" id="data-gaps">
    <div class="section-title">
      <h2><span data-lang="en">Official Data Gaps</span><span data-lang="zh">官方数据缺口</span></h2>
      <div class="logic"><span data-lang="en">These core macroeconomic indicators are tracked within the analytical framework; official public feeds are currently being verified before chart rendering.</span><span data-lang="zh">这些指标属于宏观分析框架中的核心序列，官方公开数据源当前正在验证标准化接入，完成后将统一绘图展示。</span></div>
    </div>
    <table class="gaps-table">
      <thead><tr><th>Section</th><th>Indicator family</th><th>Status</th></tr></thead>
      <tbody>{_gaps_html(config)}</tbody>
    </table>
  </section>

  <footer class="page-footer">
    <span data-lang="en">Research artefact only, not investment advice. Generated {generated_date} from <code>{config.get("config_file", f"{country_name.lower().replace(' ', '_')}_indicators.yaml")}</code>.</span>
    <span data-lang="zh">仅为研究工具，不构成投资建议。生成日期 {generated_date}，配置来源 <code>{config.get("config_file", f"{country_name.lower().replace(' ', '_')}_indicators.yaml")}</code>。</span>
  </footer>
</main>

{_lw_runtime_script(lw_specs, code_upper)}
<script>
function resizeCharts() {{
  if (window.CPChart && window.CPChart.refreshAll) {{
    window.CPChart.refreshAll();
  }}
}}
function setDashboardView(view) {{
  var normalized = view === 'deep' ? 'deep' : 'core';
  document.body.dataset.dashboardView = normalized;
  localStorage.setItem('cp-dashboard-view', normalized);
  document.querySelectorAll('[data-view-option]').forEach(function(btn) {{
    btn.setAttribute('aria-pressed', String(btn.dataset.viewOption === normalized));
  }});
  requestAnimationFrame(resizeCharts);
}}
(function() {{
  var saved = localStorage.getItem('cp-lang');
  if (saved === 'zh') {{
    document.documentElement.lang = 'zh';
    document.getElementById('lang-btn').textContent = 'English';
  }}
  setDashboardView(localStorage.getItem('cp-dashboard-view') || 'core');
  requestAnimationFrame(resizeCharts);
}})();
function toggleLang() {{
  var html = document.documentElement;
  var btn = document.getElementById('lang-btn');
  if (html.lang === 'en') {{
    html.lang = 'zh';
    btn.textContent = 'English';
    localStorage.setItem('cp-lang', 'zh');
  }} else {{
    html.lang = 'en';
    btn.textContent = '中文';
    localStorage.setItem('cp-lang', 'en');
  }}
  requestAnimationFrame(resizeCharts);
}}
window.addEventListener('resize', resizeCharts);
</script>
</body>
</html>
"""

def _index_card(summary: dict[str, Any]) -> str:
    return f"""
  <!-- Dashboard card -->
  <a href="{config.get("name", "Country").lower().replace(" ", "_")}.html" class="card clean">
    <div class="card-kicker">{summary.get("card_kicker", "")}</div>
    <h2>{summary.get("card_title", "Country")}</h2>
    <div class="stats">
      <div class="stat"><span>Rendered charts</span><strong>{summary['charts']}</strong></div>
      <div class="stat"><span>Proxy fills</span><strong>0</strong></div>
      <div class="stat"><span>Official gaps tracked</span><strong>{summary['data_gaps']}</strong></div>
      <div class="stat"><span>Latest USD/CNY fixing</span><strong>{escape(summary.get('usd_cny_latest', 'n/a'))}</strong></div>
      <div class="stat"><span>Source groups</span><strong>{summary['source_groups']}</strong></div>
      <div class="stat"><span>Framework</span><strong>{summary.get("framework", "")}</strong></div>
    </div>
  </a>
  <!-- /Dashboard card -->"""

def inject_index(summary: dict[str, Any]) -> None:
    index_path = OUTPUT / "index.html"
    if not index_path.exists():
        return
    html = index_path.read_text()
    html = re.sub(r"\n\s*<!-- Dashboard card -->.*?<!-- /Dashboard card -->", "", html, flags=re.S)
    marker = '  </section>\n  <nav class="links"'
    if marker in html:
        html = html.replace(marker, _index_card(summary) + "\n  </section>\n  <nav class=\"links\"", 1)
    html = html.replace("<title>Country Primer — CEE-4 Macro Dashboard</title>", "<title>Macro Dashboard</title>")
    html = html.replace("<title>Macro Dashboard — CEE-4</title>", "<title>Macro Dashboard</title>")
    html = html.replace("CEE-4 Macro Dashboard · v4 · Proxy-free public pages", "Macro Dashboard · CEE-4 v4 + China")
    html = html.replace("<h1>CEE-4 Macro Dashboard</h1>", "<h1>Macro Dashboard</h1>")
    html = html.replace(
        "Generated archive entry for the four country dashboards. This page is rebuilt by <code>build_v4.py ALL</code>, so its links, indicator counts, proxy status, and quality summary stay synchronized with the individual country pages.",
        "Generated archive entry for the proxy-free CEE-4 dashboards plus the China data-first page. This page is rebuilt by <code>make build-v4</code>, so links, indicator counts, proxy status, and quality summary stay synchronized with generated pages.",
    )
    html = html.replace("<span>rendered country-indicator slots</span>", "<span>CEE-4 rendered indicator slots</span>")
    html = html.replace("<strong>4</strong><span>country dashboards</span>", "<strong>5</strong><span>country dashboards</span>")
    _write_clean(index_path, html)
def _key_series_latest(series_list: list[dict[str, Any]], indicator_ids: list[str]) -> list[dict[str, Any]]:
    by_id = {item["id"]: item for item in series_list}
    rows: list[dict[str, Any]] = []
    for indicator_id in indicator_ids:
        series = by_id.get(indicator_id)
        latest = _latest(series) if series else None
        if not series or not latest:
            continue
        raw_unit = str(series.get("unit", ""))
        obs_vals = [float(o["value"]) for o in (series.get("observations") or []) if o.get("value") is not None]
        scale_div, display_unit = _resolve_display_scale(indicator_id, raw_unit, obs_vals)
        value = float(latest["value"])
        display_value = round(value / scale_div, 4) if scale_div != 1.0 else value
        rows.append({
            "id": indicator_id,
            "label_en": series.get("label_en", indicator_id),
            "label_zh": series.get("label_zh", indicator_id),
            "latest_date": str(latest["date"]),
            "latest_value": value,
            "latest_display": f"{_format_value(display_value, display_unit)} {display_unit}".strip(),
            "frequency": series.get("frequency", ""),
            "source_name": series.get("source_name", ""),
            "series": series.get("series", ""),
            "quality_status": series.get("quality_status", ""),
        })
    return rows

def build_country_page(
    country_code: str,
    config: dict[str, Any],
    series_list: list[dict[str, Any]],
    out_html: Path,
    summary_json: Path,
    canonical_json: Path,
    data_mode: str,
    summary_key_ids: list[str],
    extra_cards: list[dict[str, Any]] | None = None,
    latest_value_key: str = "",
    latest_value_display: str = ""
) -> dict[str, Any]:
    apply_quality_assessments(series_list)

    cross_checks = evaluate_cross_checks(config, series_list)
    checks_by_id = {}
    for check in cross_checks:
        for side in (check["primary"], check["secondary"]):
            checks_by_id[side] = check
    for item in series_list:
        item["cross_check"] = checks_by_id.get(item["id"])

    html = render_html(config, series_list, extra_cards or [], summary_key_ids, country_code=country_code)
    _write_clean(out_html, html)

    charted = [item for item in series_list if item.get("observations")]
    summary = {
        "file": out_html.name,
        "generated": datetime.now(UTC).isoformat(),
        "charts": len(charted),
        "source_groups": len({item.get("source_name") for item in charted}),
        "data_gaps": len(config.get("data_gaps", [])),
        "low_confidence": sum(1 for item in charted if item.get("quality_status") == "low_confidence"),
        "key_series_latest": _key_series_latest(charted, summary_key_ids),
        "unavailable": [item["id"] for item in series_list if not item.get("observations")],
        "data_mode": data_mode,
        "latest_cards": extra_cards or [],
    }
    if latest_value_key and latest_value_display:
        summary[latest_value_key] = latest_value_display
        
    summary["cross_checks"] = cross_checks
    summary["canonical_frame"] = (
        canonical_frame_metadata(canonical_json)
        if data_mode == "snapshot"
        else write_canonical_data_first_frame(canonical_json, country_code, series_list)
    )
    summary.update(build_summary_metadata(config, series_list, country_code))
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    
    if data_mode != "snapshot":
        write_source_health_report(out_html.parent / "source_health.json", [country_code])
        
    return summary
