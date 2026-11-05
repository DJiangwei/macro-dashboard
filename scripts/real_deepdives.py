"""Inflation and labour deepdive views built only from canonical series.

Replaces the earlier synthetic deepdive generators (2026-11-05). Every number
in the output JSON and HTML is either an observation from a scope's canonical
frame or a documented arithmetic transformation of such observations, and
carries the ``(indicator_id, date)`` references it was computed from. Panels
whose inputs are missing are simply not rendered.

Usage:
    scripts/uv_project.sh run python scripts/real_deepdives.py      # build JSON for all scopes
    from real_deepdives import render_inflation_view, render_labour_view
"""
from __future__ import annotations

import json
import math
from datetime import date
from html import escape
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
CONFIG = ROOT / "config" / "deepdive_views.yaml"
SLUGS = {
    "US": "us", "UK": "uk", "EA": "euro_area", "JP": "japan", "CN": "china", "ZA": "south_africa",
    "TR": "turkey", "HK": "hong_kong", "KR": "south_korea", "TW": "taiwan", "KZ": "kazakhstan",
    "UZ": "uzbekistan", "EG": "egypt", "NG": "nigeria", "HU": "hungary", "PL": "poland",
    "CZ": "czechia", "RO": "romania",
}
SAHM_THRESHOLD = 0.5  # Sahm (2019)


# ----------------------------------------------------------------------------- data access
def load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG.read_text()) or {}


def _load_scope_series(code: str, config: dict[str, Any], cache: dict[str, Any]) -> dict[str, dict[str, Any]]:
    frame_name = (config.get("frames") or {}).get(code)
    if not frame_name:
        return {}
    if frame_name not in cache:
        path = OUTPUT / frame_name
        cache[frame_name] = json.loads(path.read_text()) if path.exists() else {}
    payload = cache[frame_name]
    out: dict[str, dict[str, Any]] = {}
    for item in payload.get("series", []):
        if frame_name == "cee_canonical_frame.json" and item.get("country") != code:
            continue
        sid = item.get("indicator_id") or item.get("id")
        meta = item.get("metadata") or {}
        source = item.get("source") or meta.get("source") or ""
        observations = []
        for row in item.get("observations", []):
            try:
                observations.append((str(row[0])[:10], float(row[1])))
            except (TypeError, ValueError, IndexError):
                continue
        out[sid] = {
            "id": sid,
            "label_en": item.get("label_en") or meta.get("label") or sid,
            "label_zh": item.get("label_zh") or meta.get("label_zh") or item.get("label_en") or meta.get("label") or sid,
            "unit": item.get("unit") or meta.get("unit") or "",
            "frequency": item.get("frequency") or meta.get("frequency") or "",
            "source": source.get("name", "") if isinstance(source, dict) else str(source),
            "quality": (item.get("quality") or {}).get("status") or meta.get("quality_status") or "",
            "observations": sorted(observations),
        }
    return out


def _month_key(d: str) -> str:
    return d[:7]


def _shift_month(key: str, months: int) -> str:
    year, month = int(key[:4]), int(key[5:7])
    total = year * 12 + (month - 1) + months
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _by_month(observations: list[tuple[str, float]]) -> dict[str, tuple[str, float]]:
    return {_month_key(d): (d, v) for d, v in observations if len(d) >= 7}


# ----------------------------------------------------------------------------- transforms
def yoy_from_index(observations: list[tuple[str, float]]) -> list[tuple[str, float]]:
    months = _by_month(observations)
    out = []
    for key, (d, v) in sorted(months.items()):
        base = months.get(_shift_month(key, -12))
        if base and base[1]:
            out.append((d, round((v / base[1] - 1.0) * 100.0, 2)))
    return out


def annualised_from_index(observations: list[tuple[str, float]], months_back: int) -> tuple[float, str, str] | None:
    months = _by_month(observations)
    if not months:
        return None
    key = max(months)
    base = months.get(_shift_month(key, -months_back))
    if not base or not base[1]:
        return None
    rate = ((months[key][1] / base[1]) ** (12 / months_back) - 1.0) * 100.0
    return round(rate, 2), months[key][0], base[0]


def annualised_from_mom(observations: list[tuple[str, float]], months_back: int) -> tuple[float, str, str] | None:
    months = _by_month(observations)
    if not months:
        return None
    key = max(months)
    window = [months.get(_shift_month(key, -k)) for k in range(months_back)]
    if any(item is None for item in window):
        return None
    growth = math.prod(1.0 + item[1] / 100.0 for item in window)
    return round((growth ** (12 / months_back) - 1.0) * 100.0, 2), months[key][0], window[-1][0]


def sahm_indicator(observations: list[tuple[str, float]]) -> dict[str, Any] | None:
    months = _by_month(observations)
    keys = sorted(months)
    if len(keys) < 15:
        return None
    # require a monthly series without gaps over the window used
    latest = keys[-1]
    window_keys = [_shift_month(latest, -k) for k in range(14, -1, -1)]
    if any(k not in months for k in window_keys):
        return None
    three_m = []
    for i in range(2, len(window_keys)):
        vals = [months[window_keys[i - j]][1] for j in range(3)]
        three_m.append(sum(vals) / 3.0)
    current = three_m[-1]
    prior_min = min(three_m[:-1][-12:])
    return {
        "value": round(current - prior_min, 2),
        "date": months[latest][0],
        "threshold": SAHM_THRESHOLD,
        "triggered": current - prior_min >= SAHM_THRESHOLD,
    }


def real_wage(wage: list[tuple[str, float]], cpi: list[tuple[str, float]]) -> list[tuple[str, float]]:
    cpi_m = _by_month(cpi)
    return [
        (d, round(v - cpi_m[_month_key(d)][1], 2))
        for d, v in wage
        if _month_key(d) in cpi_m
    ]


def beveridge_points(u: list[tuple[str, float]], v: list[tuple[str, float]], limit: int = 24) -> list[dict[str, Any]]:
    u_m = _by_month(u)
    points = []
    for d, vv in v:
        key = _month_key(d)
        if key in u_m:
            points.append({"date": d, "u": u_m[key][1], "v": vv})
    return points[-limit:]


# ----------------------------------------------------------------------------- row builder
def _row(series: dict[str, Any], spec: dict[str, Any], scope_series: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    observations = series["observations"]
    if spec.get("transform") == "yoy_from_index":
        observations = yoy_from_index(observations)
    if not observations:
        return None
    latest_d, latest_v = observations[-1]
    prior = observations[-2] if len(observations) > 1 else None
    year_ago = None
    months = _by_month(observations)
    if months:
        year_ago = months.get(_shift_month(_month_key(latest_d), -12))
    row = {
        "id": series["id"],
        "label_en": spec.get("label_en") or series["label_en"],
        "label_zh": spec.get("label_zh") or series["label_zh"],
        "unit": "% YoY" if spec.get("transform") == "yoy_from_index" else series["unit"],
        "source": series["source"],
        "quality": series["quality"],
        "latest": {"value": latest_v, "date": latest_d},
        "prior": {"value": prior[1], "date": prior[0]} if prior else None,
        "year_ago": {"value": year_ago[1], "date": year_ago[0]} if year_ago else None,
        "derivation": "yoy_from_index" if spec.get("transform") == "yoy_from_index" else "observed",
        "refs": [[series["id"], latest_d]],
    }
    momentum = spec.get("momentum") or {}
    m_index, m_mom = momentum.get("index"), momentum.get("mom")
    base_series = scope_series.get(m_index or m_mom or "", {})
    if base_series.get("observations"):
        fn = annualised_from_index if m_index else annualised_from_mom
        for horizon in (3, 6):
            result = fn(base_series["observations"], horizon)
            if result:
                row[f"ann_{horizon}m"] = {
                    "value": result[0], "date": result[1], "base_date": result[2],
                    "from": m_index or m_mom, "method": "index" if m_index else "compounded_mom",
                }
    return row


def build_scope(code: str, config: dict[str, Any], cache: dict[str, Any]) -> dict[str, Any]:
    scope_series = _load_scope_series(code, config, cache)
    view: dict[str, Any] = {"scope": code, "generated": date.today().isoformat()}
    for kind in ("inflation", "labour"):
        spec = (config.get(kind) or {}).get(code)
        if spec is None:
            continue
        rows = []
        for row_spec in spec.get("rows") or []:
            series = scope_series.get(row_spec["id"])
            if not series or not series["observations"]:
                continue
            row = _row(series, row_spec, scope_series)
            if row:
                rows.append(row)
        panel: dict[str, Any] = {"rows": rows}
        if kind == "labour":
            bev = spec.get("beveridge") or {}
            u, v = scope_series.get(bev.get("u", "")), scope_series.get(bev.get("v", ""))
            if u and v:
                points = beveridge_points(u["observations"], v["observations"])
                if len(points) >= 4:
                    panel["beveridge"] = {
                        "u_id": u["id"], "v_id": v["id"],
                        "u_label": u["label_en"], "v_label": v["label_en"], "v_unit": v["unit"],
                        "points": points,
                    }
            sahm_id = spec.get("sahm")
            if sahm_id and scope_series.get(sahm_id):
                s = sahm_indicator(scope_series[sahm_id]["observations"])
                if s:
                    panel["sahm"] = {**s, "from": sahm_id}
            rw = spec.get("real_wage") or {}
            wage, cpi = scope_series.get(rw.get("wage", "")), scope_series.get(rw.get("cpi", ""))
            if wage and cpi:
                series = real_wage(wage["observations"], cpi["observations"])
                if series:
                    panel["real_wage"] = {
                        "latest": {"value": series[-1][1], "date": series[-1][0]},
                        "history": series[-36:],
                        "from": [wage["id"], cpi["id"]],
                    }
        view[kind] = panel
    return view


def build_all() -> list[Path]:
    config = load_config()
    cache: dict[str, Any] = {}
    written = []
    scopes = set((config.get("inflation") or {})) | set((config.get("labour") or {}))
    for code in sorted(scopes):
        view = build_scope(code, config, cache)
        path = OUTPUT / f"{SLUGS[code]}_deepdive_views.json"
        path.write_text(json.dumps(view, ensure_ascii=False, indent=1) + "\n")
        written.append(path)
    return written


# ----------------------------------------------------------------------------- rendering
CSS = """
<style>
.dd-panel { border: 1px solid var(--border, #e2e8f0); border-radius: 6px; padding: 16px 18px; margin: 0 0 18px; background: var(--surface, #fff); }
.dd-head { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
.dd-badge { display: inline-block; font-size: 10px; letter-spacing: .06em; text-transform: uppercase; font-weight: 700; color: #0d7680; background: rgba(13,118,128,.08); padding: 2px 8px; border-radius: 3px; }
.dd-title { font-size: 15px; font-weight: 700; margin: 6px 0 2px; }
.dd-note { font-size: 11.5px; color: var(--muted, #64748b); max-width: 860px; }
.dd-table-wrap { overflow-x: auto; }
.dd-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.dd-table th { text-align: left; font-size: 10.5px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted, #64748b); border-bottom: 1px solid var(--border, #e2e8f0); padding: 6px 8px; white-space: nowrap; }
.dd-table td { border-bottom: 1px solid var(--border, #f1f5f9); padding: 6px 8px; vertical-align: top; }
.dd-num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.dd-sub { display: block; font-size: 10.5px; color: var(--muted, #94a3b8); }
.dd-kpis { display: flex; gap: 12px; flex-wrap: wrap; margin: 12px 0; }
.dd-kpi { border: 1px solid var(--border, #e2e8f0); border-radius: 4px; padding: 8px 12px; min-width: 180px; }
.dd-kpi-v { font-size: 18px; font-weight: 700; }
.dd-alert { color: #990f3d; }
.dd-bev { margin-top: 12px; }
</style>
"""


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return escape(str(value))


def _cell(obj: dict[str, Any] | None) -> str:
    if not obj:
        return '<td class="dd-num">—</td>'
    return f'<td class="dd-num">{_fmt(obj["value"])}<span class="dd-sub">{escape(obj["date"])}</span></td>'


def _rows_table(rows: list[dict[str, Any]], with_momentum: bool) -> str:
    head_m = (
        '<th class="dd-num"><span data-lang="en">3M ann.</span><span data-lang="zh">3个月年化</span></th>'
        '<th class="dd-num"><span data-lang="en">6M ann.</span><span data-lang="zh">6个月年化</span></th>'
        if with_momentum else ""
    )
    body = []
    for r in rows:
        mom = ""
        if with_momentum:
            for h in ("ann_3m", "ann_6m"):
                m = r.get(h)
                mom += (
                    f'<td class="dd-num">{_fmt(m["value"])}<span class="dd-sub">{escape(m["base_date"])}→{escape(m["date"])}</span></td>'
                    if m else '<td class="dd-num">—</td>'
                )
        derived = ' <span class="dd-sub">derived from published index</span>' if r["derivation"] == "yoy_from_index" else ""
        body.append(
            "<tr>"
            f'<td><span data-lang="en">{escape(r["label_en"])}</span><span data-lang="zh">{escape(r["label_zh"])}</span>{derived}'
            f'<span class="dd-sub">{escape(r["unit"])} · {escape(r["source"][:48])} · {escape(r["quality"])}</span></td>'
            f"{_cell(r['latest'])}{_cell(r['prior'])}{_cell(r['year_ago'])}{mom}"
            "</tr>"
        )
    return (
        '<div class="dd-table-wrap"><table class="dd-table"><thead><tr>'
        '<th><span data-lang="en">Series</span><span data-lang="zh">序列</span></th>'
        '<th class="dd-num"><span data-lang="en">Latest</span><span data-lang="zh">最新</span></th>'
        '<th class="dd-num"><span data-lang="en">Prior</span><span data-lang="zh">前值</span></th>'
        '<th class="dd-num"><span data-lang="en">1Y ago</span><span data-lang="zh">一年前</span></th>'
        f"{head_m}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def _beveridge_svg(bev: dict[str, Any]) -> str:
    pts = bev["points"]
    us = [p["u"] for p in pts]
    vs = [p["v"] for p in pts]
    w, h, pad = 520, 260, 44
    umin, umax = min(us), max(us)
    vmin, vmax = min(vs), max(vs)
    du = (umax - umin) or 1.0
    dv = (vmax - vmin) or 1.0

    def xy(p):
        x = pad + (p["u"] - umin) / du * (w - 2 * pad)
        y = h - pad - (p["v"] - vmin) / dv * (h - 2 * pad)
        return x, y

    coords = [xy(p) for p in pts]
    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(coords))
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{4.5 if i == len(coords) - 1 else 2.2}" '
        f'fill="{"#990f3d" if i == len(coords) - 1 else "#0d7680"}"><title>{escape(pts[i]["date"])}: U {pts[i]["u"]}, V {pts[i]["v"]}</title></circle>'
        for i, (x, y) in enumerate(coords)
    )
    first, last = pts[0], pts[-1]
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" role="img" aria-label="Beveridge curve">'
        f'<line x1="{pad}" y1="{h - pad}" x2="{w - pad}" y2="{h - pad}" stroke="#cbd5e1"/>'
        f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{h - pad}" stroke="#cbd5e1"/>'
        f'<path d="{path}" fill="none" stroke="#0d7680" stroke-width="1.2" stroke-dasharray="3 2"/>{dots}'
        f'<text x="{w / 2}" y="{h - 10}" font-size="10" text-anchor="middle" fill="#64748b">{escape(bev["u_label"])} ({_fmt(umin, 1)}–{_fmt(umax, 1)})</text>'
        f'<text x="12" y="{h / 2}" font-size="10" text-anchor="middle" fill="#64748b" transform="rotate(-90 12 {h / 2})">{escape(bev["v_label"])} ({_fmt(vmin, 1)}–{_fmt(vmax, 1)} {escape(bev["v_unit"])})</text>'
        f'<text x="{coords[0][0]:.1f}" y="{coords[0][1] - 6:.1f}" font-size="9" fill="#64748b">{escape(first["date"][:7])}</text>'
        f'<text x="{coords[-1][0]:.1f}" y="{coords[-1][1] - 8:.1f}" font-size="9" fill="#990f3d">{escape(last["date"][:7])}</text>'
        "</svg>"
    )


def _load_view(code: str) -> dict[str, Any] | None:
    slug = SLUGS.get(code.upper())
    if not slug:
        return None
    path = OUTPUT / f"{slug}_deepdive_views.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


NOTE_EN = ("Built only from series in this page's canonical data. A row or chart appears only when an official series "
           "exists; momentum is annualised from the published index or month-on-month series (not seasonally adjusted "
           "unless the source says so).")
NOTE_ZH = ("仅由本页标准数据中的序列构建；只有存在官方序列时才显示对应行或图表。动量由公布的指数或环比序列年化计算"
           "（除非来源注明，否则未经季节调整）。")


def render_inflation_view(code: str) -> str:
    view = _load_view(code)
    panel = (view or {}).get("inflation")
    if not panel or not panel.get("rows"):
        return ""
    with_momentum = any(r.get("ann_3m") or r.get("ann_6m") for r in panel["rows"])
    return (
        f'{CSS}<div class="dd-panel" id="deepdive-inflation-{escape(code)}"><div class="dd-head"><div>'
        '<span class="dd-badge"><span data-lang="en">Inflation detail</span><span data-lang="zh">通胀明细</span></span>'
        '<div class="dd-title"><span data-lang="en">Inflation components and momentum</span><span data-lang="zh">通胀分项与动量</span></div>'
        f'<div class="dd-note"><span data-lang="en">{NOTE_EN}</span><span data-lang="zh">{NOTE_ZH}</span></div>'
        "</div></div>"
        f"{_rows_table(panel['rows'], with_momentum)}</div>"
    )


def render_labour_view(code: str) -> str:
    view = _load_view(code)
    panel = (view or {}).get("labour")
    if not panel or not (panel.get("rows") or panel.get("beveridge") or panel.get("sahm")):
        return ""
    kpis = []
    sahm = panel.get("sahm")
    if sahm:
        cls = "dd-kpi-v dd-alert" if sahm["triggered"] else "dd-kpi-v"
        kpis.append(
            f'<div class="dd-kpi"><div class="dd-sub"><span data-lang="en">Sahm-rule indicator (3M avg U − prior 12M low)</span>'
            f'<span data-lang="zh">萨姆规则指标（3个月均值失业率 − 此前12个月低点）</span></div>'
            f'<div class="{cls}">{_fmt(sahm["value"])} pp</div><div class="dd-sub">{escape(sahm["date"])} · '
            f'<span data-lang="en">threshold</span><span data-lang="zh">阈值</span> {sahm["threshold"]} pp</div></div>'
        )
    rw = panel.get("real_wage")
    if rw:
        kpis.append(
            f'<div class="dd-kpi"><div class="dd-sub"><span data-lang="en">Real wage growth (wage YoY − CPI YoY, derived)</span>'
            f'<span data-lang="zh">实际工资增速（工资同比 − CPI同比，推导）</span></div>'
            f'<div class="dd-kpi-v">{_fmt(rw["latest"]["value"])} pp</div><div class="dd-sub">{escape(rw["latest"]["date"])} · {escape(" − ".join(rw["from"]))}</div></div>'
        )
    bev = panel.get("beveridge")
    bev_html = (
        '<div class="dd-bev"><div class="dd-sub"><span data-lang="en">Beveridge curve: observed (U, V) pairs, '
        f'latest {len(bev["points"])} matched periods</span><span data-lang="zh">贝弗里奇曲线：实际观测的（失业率、职位空缺）配对，最近 {len(bev["points"])} 期</span></div>'
        f"{_beveridge_svg(bev)}</div>"
        if bev else ""
    )
    table = _rows_table(panel["rows"], False) if panel.get("rows") else ""
    return (
        f'{CSS}<div class="dd-panel" id="deepdive-labour-{escape(code)}"><div class="dd-head"><div>'
        '<span class="dd-badge"><span data-lang="en">Labour detail</span><span data-lang="zh">劳动力明细</span></span>'
        '<div class="dd-title"><span data-lang="en">Labour market and wages</span><span data-lang="zh">劳动力市场与工资</span></div>'
        f'<div class="dd-note"><span data-lang="en">{NOTE_EN}</span><span data-lang="zh">{NOTE_ZH}</span></div>'
        "</div></div>"
        f'<div class="dd-kpis">{"".join(kpis)}</div>{table}{bev_html}</div>'
    )


if __name__ == "__main__":
    for path in build_all():
        print(f"Wrote {path.relative_to(ROOT)}")
