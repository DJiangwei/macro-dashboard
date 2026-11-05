"""MODEL: first-round effect of an oil price shock on consumer prices.

For each economy with an energy CPI series:

1. Pass-through (estimated): OLS of energy CPI YoY on Brent YoY in local
   currency at lags 0..L months (monthly data from ``sample_start``), with a
   constant. The cumulative pass-through is the sum of the lag coefficients:
   percentage points of energy CPI inflation per 1 pp of local-currency Brent
   inflation after L months.
2. Weight (official): the energy share of the CPI basket (Eurostat HICP item
   weights, ONS CPI weights). The direct effect on headline CPI is
   ``weight / 1000 × pass-through × shock``.

What it is not: a forecast, or a full model. It ignores second-round effects
(wages, transport and food costs), regulated-price timing beyond L months,
exchange-rate responses and policy reactions. Overlapping YoY observations
make residuals autocorrelated, so R² and fit statistics overstate precision.
Every input is an observed series referenced as ``scope:indicator@last date``;
the output lives in ``output/models/`` and never enters a canonical frame.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

import numpy as np

from .derived import _points, monthly_mean
from .scopes import all_scopes, get_scope
from .transmission import _first, _frame, _monthly_fx_per_usd

MODEL_ID = "oil_shock_cpi"
# Energy-weight series on the Energy page, by scope.
WEIGHT_SERIES = {
    "EA": "hicp_energy_weight_ea", "CZ": "hicp_energy_weight_cz", "HU": "hicp_energy_weight_hu",
    "PL": "hicp_energy_weight_pl", "RO": "hicp_energy_weight_ro", "TR": "hicp_energy_weight_tr",
    "UK": "cpi_energy_weight_uk",
}


def distributed_lag_ols(y: dict[str, float], x: dict[str, float], lags: int, start: str) -> dict[str, Any] | None:
    """y_t = a + Σ_k b_k x_{t-k}; months keyed YYYY-MM-01. None if fewer than 36 usable months."""
    months = sorted(m for m in y if m[:7] >= start)
    keys = sorted(x)
    index = {m: i for i, m in enumerate(keys)}
    rows, target = [], []
    for m in months:
        if m not in index or index[m] < lags:
            continue
        lagged = [x.get(keys[index[m] - k]) for k in range(lags + 1)]
        # Lagged months must be consecutive calendar months.
        expected = [_shift(m, -k) for k in range(lags + 1)]
        if any(v is None for v in lagged) or [keys[index[m] - k] for k in range(lags + 1)] != expected:
            continue
        rows.append([1.0, *lagged])
        target.append(y[m])
    if len(rows) < 36:
        return None
    X, Y = np.array(rows), np.array(target)
    coef, *_ = np.linalg.lstsq(X, Y, rcond=None)
    fitted = X @ coef
    ss_res = float(((Y - fitted) ** 2).sum())
    ss_tot = float(((Y - Y.mean()) ** 2).sum())
    used = [m for m in months if m in index and index[m] >= lags][: len(rows)]
    return {
        "coefficients": [round(float(c), 4) for c in coef[1:]],
        "pass_through": round(float(coef[1:].sum()), 4),
        "r2": round(1.0 - ss_res / ss_tot, 3) if ss_tot > 0 else None,
        "n": len(rows),
        "sample": f"{used[0][:7]} to {used[-1][:7]}" if used else "",
    }


def _shift(month: str, k: int) -> str:
    year, mon = int(month[:4]), int(month[5:7]) + k
    while mon <= 0:
        year, mon = year - 1, mon + 12
    while mon > 12:
        year, mon = year + 1, mon - 12
    return f"{year:04d}-{mon:02d}-01"


def _yoy(series: dict[str, float]) -> dict[str, float]:
    out = {}
    for m, v in series.items():
        base = series.get(f"{int(m[:4]) - 1:04d}{m[4:]}")
        if base:
            out[m] = (v / base - 1.0) * 100.0
    return out


def oil_shock_cpi(panel: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    lags = int(panel.get("lags", 6))
    start = str(panel.get("sample_start", "2015-01"))
    shock = float(panel.get("shock_pct", 10))
    brent_item = by_id.get(panel["input"]) or {}
    brent_points = _points(brent_item.get("observations") or [])
    brent = dict(monthly_mean(brent_points))
    cache: dict[str, Any] = {}
    rows = []
    for scope in all_scopes():
        series = _frame(scope, cache)
        energy = _first(series, scope.role("energy_cpi_yoy") or ("energy_cpi_yoy",))
        if not energy:
            continue
        driver_note = "Brent in local currency"
        fx = _monthly_fx_per_usd(scope, series, cache) if scope.id != "US" else None
        if scope.id == "US":
            local = brent
            driver_note = "Brent in USD"
        elif fx and len(fx[0]) >= 60:
            local = {m: brent[m] * fx[0][m] for m in brent if m in fx[0]}
        elif scope.pipeline == "cee_v4":
            # CEE frames hold only a few months of local FX; use Brent in EUR, the
            # currency CEE energy is largely invoiced in, and say so.
            ea = get_scope("EA")
            eur = _first(_frame(ea, cache), ea.roles.get("fx_usd_per_local", ()))
            usd_per_eur = dict(monthly_mean(_points(eur["observations"]))) if eur else {}
            local = {m: brent[m] / usd_per_eur[m] for m in brent if usd_per_eur.get(m)}
            driver_note = "Brent in EUR (local-currency FX history unavailable)"
        else:
            continue
        energy_monthly = {p[0][:7] + "-01": p[1] for p in _points(energy["observations"])}
        fit = distributed_lag_ols(energy_monthly, _yoy(local), lags, start)
        if not fit:
            continue
        weight_item = by_id.get(WEIGHT_SERIES.get(scope.id, ""), {})
        weight_points = _points(weight_item.get("observations") or [])
        weight = {"value": round(weight_points[-1][1], 2), "year": weight_points[-1][0][:4], "series": f"ENERGY:{weight_item.get('id')}",
                  "source": weight_item.get("source_name") or ""} if weight_points else None
        energy_label = energy.get("label_en") or (energy.get("metadata") or {}).get("label") or energy.get("indicator_id")
        rows.append({
            "code": scope.id, "name_en": scope.name_en, "flag": scope.flag,
            "energy_cpi": {"series": f"{scope.id}:{energy.get('indicator_id')}", "label": energy_label,
                           "last": _points(energy["observations"])[-1][0][:7]},
            "driver": driver_note,
            "fit": fit,
            "weight": weight,
            "energy_cpi_impact_pp": round(fit["pass_through"] * shock, 2),
            "headline_impact_pp": round(weight["value"] / 1000 * fit["pass_through"] * shock, 2) if weight else None,
        })
    return {
        "schema_version": "model-oil-shock-cpi-v1",
        "model_id": MODEL_ID,
        "label": "MODEL",
        "generated": datetime.now(UTC).isoformat(),
        "params": {"shock_pct": shock, "lags_months": lags, "sample_start": start},
        "inputs": {"brent": f"ENERGY:{panel['input']}@{brent_points[-1][0] if brent_points else 'missing'}"},
        "method": (__doc__ or "").strip(),
        "rows": rows,
    }


def render_oil_shock_cpi(payload: dict[str, Any]) -> str:
    params = payload["params"]
    body = []
    for row in payload.get("rows") or []:
        fit, weight = row["fit"], row["weight"]
        weight_cell = (f'{weight["value"]:.1f}‰<br><span class="muted">{escape(weight["year"])}</span>' if weight
                       else '<span class="muted">—<br>no free official weight</span>')
        body.append(
            f'<tr data-pt="{fit["pass_through"]}" data-w="{weight["value"] if weight else ""}">'
            f'<td>{escape(row["flag"])} <strong>{escape(row["code"])}</strong><br><span class="muted">{escape(row["energy_cpi"]["label"])}</span></td>'
            f'<td class="num"><strong>{fit["pass_through"]:.2f}</strong><br><span class="muted">R² {fit["r2"]} · n {fit["n"]}</span></td>'
            f'<td class="num">{weight_cell}</td>'
            f'<td class="num"><strong class="oil-energy">{row["energy_cpi_impact_pp"]:+.2f}</strong> pp</td>'
            f'<td class="num"><strong class="oil-headline">{"—" if row["headline_impact_pp"] is None else f"{row["headline_impact_pp"]:+.2f}"}</strong>{"" if row["headline_impact_pp"] is None else " pp"}</td>'
            f'<td class="muted" style="font-size:11px;">{escape(row["driver"])}; {escape(fit["sample"])}</td>'
            "</tr>"
        )
    return f"""
<div class="dd-panel" id="model-oil-shock-cpi" style="margin:18px 0;padding:16px 18px;border:1px dashed #b45309;background:var(--surface,#fff);">
  <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:4px;">
    <span style="font-size:11px;font-weight:700;letter-spacing:.06em;padding:2px 8px;border:1px solid #b45309;color:#b45309;">MODEL</span>
    <strong><span data-lang="en">Oil shock → CPI: first-round effect</span><span data-lang="zh">油价冲击 → CPI：一轮直接效应</span></strong>
    <label style="margin-left:auto;font-size:13px;"><span data-lang="en">Brent shock (local currency)</span><span data-lang="zh">本币布伦特冲击</span>
      <input id="oil-shock-pct" type="number" step="1" value="{params["shock_pct"]:g}" style="width:64px;margin-left:6px;">%</label>
  </div>
  <div class="muted" style="font-size:12px;margin-bottom:10px;"><span data-lang="en">Pass-through is estimated by OLS of energy CPI YoY on Brent YoY in local currency at lags 0–{params["lags_months"]} months (monthly, from {escape(params["sample_start"])}); the headline effect multiplies it by the official energy weight. Not a forecast: second-round effects, regulated-price timing beyond the lag window and policy responses are excluded, and overlapping YoY data overstate fit. Energy CPI definitions differ (the UK series is household energy only).</span><span data-lang="zh">传导系数由能源CPI同比对本币布伦特同比（滞后0–{params["lags_months"]}个月，月度，自{escape(params["sample_start"])}起）的OLS回归估计；总体通胀效应等于该系数乘以官方能源权重。这不是预测：未包含二轮效应、超出滞后窗口的管制价格调整与政策反应，且同比数据重叠会高估拟合度。各国能源CPI口径不同（英国仅为居民能源）。</span></div>
  <div style="overflow-x:auto;"><table class="inflation-table" style="width:100%;border-collapse:collapse;font-size:13px;">
    <thead><tr>
      <th style="text-align:left;"><span data-lang="en">Economy / energy CPI</span><span data-lang="zh">经济体 / 能源CPI</span></th>
      <th><span data-lang="en">Pass-through (sum of lags)</span><span data-lang="zh">传导系数（各滞后之和）</span></th>
      <th><span data-lang="en">Energy weight</span><span data-lang="zh">能源权重</span></th>
      <th><span data-lang="en">Energy CPI effect</span><span data-lang="zh">能源CPI影响</span></th>
      <th><span data-lang="en">Headline CPI effect</span><span data-lang="zh">总体CPI影响</span></th>
      <th style="text-align:left;"><span data-lang="en">Driver · sample</span><span data-lang="zh">驱动变量 · 样本</span></th>
    </tr></thead>
    <tbody>{''.join(body)}</tbody>
  </table></div>
</div>
<script>
(function () {{
  var input = document.getElementById('oil-shock-pct');
  if (!input) return;
  function update() {{
    var shock = parseFloat(input.value) || 0;
    document.querySelectorAll('#model-oil-shock-cpi tbody tr').forEach(function (tr) {{
      var pt = parseFloat(tr.dataset.pt), w = parseFloat(tr.dataset.w);
      var e = tr.querySelector('.oil-energy'), h = tr.querySelector('.oil-headline');
      if (e && !isNaN(pt)) e.textContent = (pt * shock >= 0 ? '+' : '') + (pt * shock).toFixed(2);
      if (h && !isNaN(pt) && !isNaN(w)) h.textContent = (w / 1000 * pt * shock >= 0 ? '+' : '') + (w / 1000 * pt * shock).toFixed(2);
    }});
  }}
  input.addEventListener('input', update);
}})();
</script>"""


def write_model(payload: dict[str, Any], output_dir: Path) -> Path:
    path = output_dir / "models" / f"{MODEL_ID}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    return path
