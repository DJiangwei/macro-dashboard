"""Cross-scope and summary panels for market pages.

Energy: cross-economy pass-through. Precious metals: official gold holdings.


For every economy in the registry: the latest energy CPI print, the energy
contribution to headline CPI and energy import dependence where published, and
Brent's year-on-year change in local currency (monthly means of Brent and the
economy's exchange rate). All inputs are read from canonical frames through the
registry roles; nothing is estimated. Definitions differ across economies
(household energy vs total energy, CPI vs HICP), so the panel is a table of
observed values, not a comparable concept.
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from .derived import _points, monthly_mean
from .scopes import Scope, all_scopes, get_scope


def _frame(scope: Scope, cache: dict[str, Any]) -> dict[str, dict[str, Any]]:
    path = scope.canonical_path
    if str(path) not in cache:
        cache[str(path)] = json.loads(path.read_text()) if path.exists() else {}
    payload = cache[str(path)]
    return {
        str(s.get("indicator_id")): s for s in payload.get("series") or []
        if scope.pipeline != "cee_v4" or str(s.get("country") or "").upper() == scope.id
    }


def _first(series: dict[str, dict[str, Any]], ids: tuple[str, ...] | list[str]) -> dict[str, Any] | None:
    return next((series[i] for i in ids if series.get(i, {}).get("observations")), None)


def _latest(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not item:
        return None
    points = [p for p in _points(item.get("observations") or [])]
    # CEE frames flag projections in the third column; keep observed rows only.
    rows = [r for r in item.get("observations") or [] if isinstance(r, list) and len(r) >= 3 and r[2] == "projection"]
    projected = {str(r[0])[:10] for r in rows}
    points = [p for p in points if p[0] not in projected]
    if not points:
        return None
    label = item.get("label_en") or (item.get("metadata") or {}).get("label") or item.get("indicator_id")
    return {"date": points[-1][0], "value": round(points[-1][1], 2), "id": item.get("indicator_id"), "label": label}


def _monthly_fx_per_usd(scope: Scope, series: dict[str, dict[str, Any]], cache: dict[str, Any]) -> tuple[dict[str, float], str] | None:
    """Local currency per USD, monthly means; None when no verified FX role exists."""
    if scope.id == "US":
        return None
    if (item := _first(series, scope.roles.get("fx_per_usd", ()))):
        return dict(monthly_mean(_points(item["observations"]))), item["indicator_id"]
    if (item := _first(series, scope.roles.get("fx_usd_per_local", ()))):
        return {m: 1.0 / v for m, v in monthly_mean(_points(item["observations"])) if v}, f"1 / {item['indicator_id']}"
    if (item := _first(series, scope.roles.get("fx_per_eur", ()))):
        ea = get_scope("EA")
        eurusd = _first(_frame(ea, cache), ea.roles.get("fx_usd_per_local", ()))
        if not eurusd:
            return None
        usd_per_eur = dict(monthly_mean(_points(eurusd["observations"])))
        local_per_eur = dict(monthly_mean(_points(item["observations"])))
        cross = {m: local_per_eur[m] / usd_per_eur[m] for m in local_per_eur if usd_per_eur.get(m)}
        return cross, f"{item['indicator_id']} / EA:{eurusd['indicator_id']}"
    return None


def _yoy_latest(series: dict[str, float]) -> tuple[str, float] | None:
    for month in sorted(series, reverse=True):
        base = series.get(f"{int(month[:4]) - 1:04d}{month[4:]}")
        if base:
            return month, (series[month] / base - 1.0) * 100.0
    return None


def energy_passthrough(brent_observations: list[Any]) -> dict[str, Any]:
    brent = dict(monthly_mean(_points(brent_observations)))
    cache: dict[str, Any] = {}
    rows = []
    for scope in all_scopes():
        series = _frame(scope, cache)
        energy = _latest(_first(series, scope.role("energy_cpi_yoy") or ("energy_cpi_yoy",)))
        contribution = _latest(_first(series, ("cpi_contrib_energy_yoy",)))
        dependency = _latest(_first(series, ("energy_import_dependency",)))
        local = None
        fx_source = ""
        if scope.id == "US":
            local_series = brent
            fx_source = "USD"
        else:
            fx = _monthly_fx_per_usd(scope, series, cache)
            local_series = {m: brent[m] * fx[0][m] for m in brent if m in fx[0]} if fx else {}
            fx_source = fx[1] if fx else ""
        yoy = _yoy_latest(local_series)
        if yoy:
            usd_yoy = (brent[yoy[0]] / brent[f"{int(yoy[0][:4]) - 1:04d}{yoy[0][4:]}"] - 1.0) * 100.0
            local = {"month": yoy[0][:7], "value": round(yoy[1], 1), "usd_value": round(usd_yoy, 1), "fx": fx_source}
        if not any((energy, contribution, dependency, local)):
            continue
        rows.append({
            "code": scope.id, "name_en": scope.name_en, "name_zh": scope.name_zh, "flag": scope.flag,
            "energy_cpi": energy, "energy_contribution": contribution, "import_dependency": dependency,
            "brent_local_yoy": local,
        })
    return {"schema_version": "energy-passthrough-v1", "rows": rows}


def _cell(item: dict[str, Any] | None, *, suffix: str = "", date_key: str = "date") -> str:
    if not item:
        return '<td class="num muted">—</td>'
    value = item["value"]
    sign = "+" if isinstance(value, (int, float)) and value > 0 and suffix in {"%", " pp"} else ""
    return f'<td class="num"><strong>{sign}{value}{suffix}</strong><br><span class="muted">{escape(str(item[date_key])[:7])}</span></td>'


def render_energy_passthrough(payload: dict[str, Any]) -> str:
    rows = []
    for row in payload.get("rows") or []:
        energy = row["energy_cpi"]
        local = row["brent_local_yoy"]
        local_cell = (
            f'<td class="num"><strong>{local["value"]:+.1f}%</strong><br><span class="muted">{escape(local["month"])} · USD {local["usd_value"]:+.1f}%</span></td>'
            if local else '<td class="num muted">—</td>'
        )
        rows.append(
            "<tr>"
            f'<td>{escape(row["flag"])} <strong>{escape(row["code"])}</strong> <span class="muted">{escape(row["name_en"])}</span></td>'
            + _cell(energy, suffix="%")
            + f'<td class="muted">{escape(str(energy["label"])) if energy else ""}</td>'
            + _cell(row["energy_contribution"], suffix=" pp")
            + _cell(row["import_dependency"], suffix="%")
            + local_cell
            + "</tr>"
        )
    return f"""
<div class="dd-panel" id="energy-passthrough" style="margin:18px 0;padding:16px 18px;border:1px solid var(--border,#d9d3c7);background:var(--surface,#fff);">
  <div style="font-weight:700;margin-bottom:4px;"><span data-lang="en">Energy shock by economy</span><span data-lang="zh">各经济体能源冲击</span></div>
  <div class="muted" style="font-size:12px;margin-bottom:10px;"><span data-lang="en">Latest observed values from each economy's page. Definitions differ (household energy vs total energy, CPI vs HICP). Brent in local currency uses monthly means of Brent and the economy's exchange rate; CEE currencies are crossed through EUR/USD.</span><span data-lang="zh">取自各经济体页面的最新观测值。口径不同（居民能源与全部能源、CPI与HICP）。本币布伦特使用布伦特与汇率的月均值计算；中东欧货币经EUR/USD交叉换算。</span></div>
  <div style="overflow-x:auto;"><table class="inflation-table" style="width:100%;border-collapse:collapse;font-size:13px;">
    <thead><tr>
      <th style="text-align:left;"><span data-lang="en">Economy</span><span data-lang="zh">经济体</span></th>
      <th><span data-lang="en">Energy CPI YoY</span><span data-lang="zh">能源CPI同比</span></th>
      <th style="text-align:left;"><span data-lang="en">Series</span><span data-lang="zh">序列</span></th>
      <th><span data-lang="en">Contribution to headline</span><span data-lang="zh">对总体通胀拉动</span></th>
      <th><span data-lang="en">Energy import dependence</span><span data-lang="zh">能源进口依存度</span></th>
      <th><span data-lang="en">Brent YoY in local currency</span><span data-lang="zh">本币计价布伦特同比</span></th>
    </tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
</div>"""


def official_gold(series: dict[str, dict[str, Any]], prefix: str) -> dict[str, Any]:
    """Central-bank gold holdings (tonnes) from this page's ``<prefix>*`` series."""
    rows = []
    for sid, item in series.items():
        if not sid.startswith(prefix):
            continue
        points = _points(item.get("observations") or [])
        if not points:
            continue
        by_date = dict(points)
        last_date, last = points[-1]

        def change(months: int) -> float | None:
            year, month = int(last_date[:4]), int(last_date[5:7]) - months
            while month <= 0:
                year, month = year - 1, month + 12
            base = by_date.get(f"{year:04d}-{month:02d}-01")
            return round(last - base, 1) if base is not None else None

        rows.append({
            "id": sid, "holder": item.get("holder") or sid, "date": last_date[:7], "tonnes": round(last, 1),
            "change_12m": change(12), "change_36m": change(36),
        })
    rows.sort(key=lambda r: (r["change_12m"] is None, -(r["change_12m"] or 0)))
    return {"schema_version": "official-gold-v1", "rows": rows}


def render_official_gold(payload: dict[str, Any]) -> str:
    def fmt(value: float | None) -> str:
        return "—" if value is None else f"{value:+,.1f}"

    body = "".join(
        f'<tr><td><strong>{escape(r["holder"])}</strong></td><td class="num"><strong>{r["tonnes"]:,.1f}</strong><br><span class="muted">{escape(r["date"])}</span></td>'
        f'<td class="num">{fmt(r["change_12m"])}</td><td class="num">{fmt(r["change_36m"])}</td></tr>'
        for r in payload.get("rows") or []
    )
    return f"""
<div class="dd-panel" id="official-gold" style="margin:18px 0;padding:16px 18px;border:1px solid var(--border,#d9d3c7);background:var(--surface,#fff);">
  <div style="font-weight:700;margin-bottom:4px;"><span data-lang="en">Official gold holdings (tonnes)</span><span data-lang="zh">官方黄金储备（吨）</span></div>
  <div class="muted" style="font-size:12px;margin-bottom:10px;"><span data-lang="en">IMF International Liquidity (fine troy ounces ÷ 32,150.7466), latest month reported by each country; sorted by 12-month change.</span><span data-lang="zh">IMF国际流动性数据（金衡盎司 ÷ 32,150.7466），各国最新报告月份；按12个月变化排序。</span></div>
  <div style="overflow-x:auto;"><table class="inflation-table" style="width:100%;border-collapse:collapse;font-size:13px;">
    <thead><tr><th style="text-align:left;"><span data-lang="en">Holder</span><span data-lang="zh">持有方</span></th>
    <th><span data-lang="en">Holdings</span><span data-lang="zh">持有量</span></th>
    <th><span data-lang="en">12-month change</span><span data-lang="zh">12个月变化</span></th>
    <th><span data-lang="en">36-month change</span><span data-lang="zh">36个月变化</span></th></tr></thead>
    <tbody>{body}</tbody>
  </table></div>
</div>"""


def _oil_shock(panel: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    from .oil_shock_model import oil_shock_cpi
    return oil_shock_cpi(panel, by_id)


def _render_oil_shock(payload: dict[str, Any]) -> str:
    from .oil_shock_model import render_oil_shock_cpi
    return render_oil_shock_cpi(payload)


PANELS = {
    "energy_passthrough": (lambda panel, by_id: energy_passthrough((by_id.get(panel["input"]) or {}).get("observations") or []), render_energy_passthrough),
    "official_gold": (lambda panel, by_id: official_gold(by_id, panel["prefix"]), render_official_gold),
    # MODEL output: written to output/models/, never to a canonical frame.
    "oil_shock_cpi": (_oil_shock, _render_oil_shock),
}


def build_panels(config: dict[str, Any], series_list: list[dict[str, Any]], output_dir: Path, slug: str) -> dict[str, str]:
    """Compute configured panels; returns {section_id: html} and writes their JSON."""
    by_id = {str(item.get("id")): item for item in series_list}
    html: dict[str, str] = {}
    payloads = {}
    for panel in config.get("panels") or []:
        compute, render = PANELS[panel["type"]]
        payload = compute(panel, by_id)
        payloads[panel["type"]] = payload
        if payload.get("label") == "MODEL":
            from .oil_shock_model import write_model
            write_model(payload, output_dir)
        html[panel["section"]] = html.get(panel["section"], "") + render(payload)
    if payloads:
        (output_dir / f"{slug}_panels.json").write_text(json.dumps(payloads, ensure_ascii=False, indent=1) + "\n")
    return html
