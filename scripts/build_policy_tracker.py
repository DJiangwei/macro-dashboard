#!/usr/bin/env python3
"""Build script for the Central Bank Policy & Monetary Cycle Tracker.

Generates output/policy_tracker.html and policy_tracker.html in the root.

Every number on this page is derived from the committed canonical frames (or
the BIS WS_CBPOL snapshot written during refresh):
  1. Stance matrix: policy rate with as-of date and source, last change,
     12-month change, headline CPI, real policy rate, BIS reference value.
  2. Historical nominal and real policy-rate cycles.
  3. Real policy-rate ranking (stale inputs excluded) and a Taylor-rule
     comparison that is explicitly labelled as a MODEL with its parameters.

Removed on 2026-11-05 because they were hand-typed rather than sourced: the
meeting calendar, "consensus" calls and probabilities, corridor/balance-sheet
cards, the FOMC dot plot and the statement-diff studio.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from macro_workbench import TAYLOR_PARAMETERS as TAYLOR_REFERENCE  # noqa: E402  (model parameters)
from country_primer.scopes import all_scopes

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

COUNTRY_NAV = [(s.id, s.name_en, s.name_zh, s.html_file) for s in all_scopes()]

# Static metadata for all 18 economies
REGION_LABELS = {
    "dm": ("Developed Markets (G4)", "发达成体系 (G4)"),
    "em": ("Major Emerging Markets", "重要新兴市场"),
    "cee": ("CEE-4 Economies", "中东欧核心四国"),
    "frontier": ("Frontier & Regional Anchors", "前沿与离岸锚点"),
}


def _economy_metadata() -> dict[str, dict[str, str]]:
    """Display metadata per scope, from config/scopes.yaml."""
    meta: dict[str, dict[str, str]] = {}
    for scope in all_scopes():
        cb = scope.central_bank
        region_en, region_zh = REGION_LABELS.get(scope.region, (scope.region, scope.region))
        meta[scope.id] = {
            "flag": scope.flag,
            "name_en": scope.name_en,
            "name_zh": scope.name_zh,
            "region": scope.region,
            "region_en": region_en,
            "region_zh": region_zh,
            "cb_name_en": (cb.get("name") or {}).get("en", scope.institution),
            "cb_name_zh": (cb.get("name") or {}).get("zh", scope.institution),
            "cb_short": scope.institution.upper(),
            "policy_tool_en": (cb.get("policy_tool") or {}).get("en", "Policy rate"),
            "policy_tool_zh": (cb.get("policy_tool") or {}).get("zh", "政策利率"),
        }
    return meta


ECONOMY_METADATA = _economy_metadata()

# 60+ Scheduled 2026/2027 Central Bank Meetings across all 18 economies
def load_macro_workbench_summary() -> dict:
    """Load latest compiled macro workbench summary if available."""
    wb_file = OUTPUT / "macro_workbench_summary.json"
    if wb_file.exists():
        try:
            with open(wb_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {wb_file}: {e}")
    return {}


def load_historical_policy_cycles() -> dict:
    """Extract monthly historical nominal & real policy rate trajectories for the 18 economies."""
    # Nominal series: the market rate where a scope declares one (US EFFR), else its policy rate.
    frame_map = {
        scope.id: (scope.canonical_file, scope.market_policy_rate[0], "real_policy_rate")
        for scope in all_scopes()
    }
    frame_cache: dict = {}
    out: dict = {}

    def _norm_month(raw_dt: str) -> str:
        s = str(raw_dt).strip()
        if len(s) == 4 and s.isdigit():
            return f"{s}-12-01"
        if "-Q" in s:
            yr, q = s.split("-Q")
            mo = int(q) * 3
            return f"{yr}-{mo:02d}-01"
        if len(s) >= 7 and s[4] == "-":
            return f"{s[:7]}-01"
        return s[:10]

    for code, (fn, nom_id, real_id) in frame_map.items():
        fpath = OUTPUT / fn
        if fn not in frame_cache and fpath.exists():
            try:
                frame_cache[fn] = json.loads(fpath.read_text(encoding="utf-8"))
            except Exception:
                frame_cache[fn] = {}
        frame = frame_cache.get(fn, {})
        series_list = frame.get("series", [])

        def _extract(ind_id: str) -> list:
            for s in series_list:
                if fn == "cee_canonical_frame.json" and s.get("country") != code:
                    continue
                if (s.get("indicator_id") or s.get("id")) == ind_id:
                    by_mo: dict = {}
                    for o in s.get("observations", []):
                        dt_raw = o[0] if isinstance(o, list) else o.get("date")
                        val_raw = o[1] if isinstance(o, list) else o.get("value")
                        if dt_raw is None or val_raw is None:
                            continue
                        try:
                            v = round(float(val_raw), 3)
                        except (ValueError, TypeError):
                            continue
                        mo = _norm_month(str(dt_raw))
                        if mo >= "2000-01-01":
                            by_mo[mo] = v
                    return [{"time": k, "value": by_mo[k]} for k in sorted(by_mo.keys())]
            return []

        out[code] = {
            "nominal": _extract(nom_id),
            "real": _extract(real_id),
        }
    return out



# --------------------------------------------------------------------------
# Policy-rate snapshot computed from canonical frames (no hand-typed values)
# --------------------------------------------------------------------------
STALE_POLICY_DAYS = 120

# Canonical frame, policy-rate candidates and CPI YoY candidates per scope
# (roles in config/scopes.yaml; first series with observations wins).
POLICY_INPUTS = {
    scope.id: (scope.canonical_file, list(scope.role("policy_rate")), list(scope.role("cpi_yoy")))
    for scope in all_scopes()
}


def _frame_series(frame_name: str, code: str, cache: dict) -> dict[str, dict]:
    if frame_name not in cache:
        path = OUTPUT / frame_name
        cache[frame_name] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    out: dict[str, dict] = {}
    for item in cache[frame_name].get("series", []):
        if frame_name == "cee_canonical_frame.json" and item.get("country") != code:
            continue
        sid = item.get("indicator_id") or item.get("id")
        obs = []
        for row in item.get("observations", []):
            try:
                obs.append((str(row[0])[:10], float(row[1])))
            except (TypeError, ValueError, IndexError):
                continue
        meta = item.get("metadata") or {}
        source = item.get("source") or meta.get("source") or ""
        quality = item.get("quality") or {}
        out[sid] = {
            "observations": sorted(obs),
            "source": source.get("name", "") if isinstance(source, dict) else str(source),
            "quality": quality.get("status") or meta.get("quality_status") or "",
        }
    return out


def _date_of(text: str) -> date | None:
    text = str(text)
    try:
        if len(text) == 4:
            return date(int(text), 12, 31)
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _in_force(obs: list[tuple[str, float]], on: date) -> float | None:
    value = None
    for d, v in obs:
        parsed = _date_of(d)
        if parsed and parsed <= on:
            value = v
    return value


def policy_snapshot(code: str, today: date, cache: dict, bis: dict) -> dict:
    """Latest policy rate, changes and inflation for one scope, from canonical data."""
    frame_name, policy_ids, cpi_ids = POLICY_INPUTS[code]
    series = _frame_series(frame_name, code, cache)
    policy = next((series[i] for i in policy_ids if series.get(i, {}).get("observations")), None)
    cpi = next((series[i] for i in cpi_ids if series.get(i, {}).get("observations")), None)
    real = series.get("real_policy_rate", {})
    snap: dict = {"code": code, "available": bool(policy)}
    if not policy:
        return snap
    obs = policy["observations"]
    as_of_date, rate = obs[-1]
    as_of = _date_of(as_of_date) or today
    lower = series.get("fed_target_lower", {}).get("observations") or [] if code == "US" else []
    if lower:
        lower_now = _in_force(lower, as_of)
        if lower_now is not None:
            snap["range_display"] = f"{lower_now:.2f}–{rate:.2f}%"
            rate = (rate + lower_now) / 2
    last_change = None
    for (_, v_prev), (d_cur, v_cur) in zip(obs, obs[1:]):
        if abs(v_cur - v_prev) > 1e-9:
            last_change = (d_cur, round((v_cur - v_prev) * 100))
    try:
        year_ago_day = as_of.replace(year=as_of.year - 1)
    except ValueError:
        year_ago_day = as_of.replace(year=as_of.year - 1, day=28)
    year_ago = _in_force(obs, year_ago_day)
    if lower and year_ago is not None:
        lower_then = _in_force(lower, year_ago_day)
        if lower_then is not None:
            year_ago = (year_ago + lower_then) / 2
    age = (today - as_of).days
    snap.update({
        "rate": round(rate, 3),
        "as_of": as_of_date,
        "age_days": age,
        "stale": age > STALE_POLICY_DAYS,
        "source": policy.get("source") or "",
        "quality": policy.get("quality") or "",
        "last_change_date": last_change[0] if last_change else None,
        "last_change_bps": last_change[1] if last_change else None,
        "change_12m_bps": round((rate - year_ago) * 100) if year_ago is not None else None,
    })
    if cpi:
        snap["cpi"] = cpi["observations"][-1][1]
        snap["cpi_date"] = cpi["observations"][-1][0]
    if real.get("observations"):
        snap["real_rate"] = real["observations"][-1][1]
        snap["real_date"] = real["observations"][-1][0]
    bis_scope = (bis.get("scopes") or {}).get(code)
    if bis_scope:
        snap["bis_rate"] = bis_scope.get("latest_value")
        snap["bis_date"] = bis_scope.get("last_observation_date")
    return snap


def load_bis_snapshot() -> dict:
    path = OUTPUT / "bis_policy_rates.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def build_policy_tracker_html() -> str:
    """Generate the complete standalone Policy Tracker HTML application."""
    wb = load_macro_workbench_summary()
    stances = wb.get("monetary_stance_monitor", {})
    ref_date = date.today()
    frame_cache: dict = {}
    bis = load_bis_snapshot()

    country_nav_links = "\n    ".join(
        f'<a href="{href}" title="{name_en} ({name_zh})">{code}</a>'
        for code, name_en, name_zh, href in COUNTRY_NAV
    )

    # Compile enriched master table data for all 18 economies
    table_rows_data = []
    real_rate_chart_data = []
    taylor_chart_data = []

    for code, name_en, name_zh, href in COUNTRY_NAV:
        meta = ECONOMY_METADATA.get(code, {})
        stance = stances.get(code, {})
        snap = policy_snapshot(code, ref_date, frame_cache, bis)
        if not snap.get("available"):
            continue
        policy_rate = snap["rate"]
        cpi = snap.get("cpi")
        real_rate = snap.get("real_rate")
        target = stance.get("inflation_target")
        target_gap = round(cpi - target, 2) if (cpi is not None and target is not None) else None
        taylor_rate = stance.get("taylor_implied_rate")

        if real_rate is None:
            rr_class, rr_tag_en, rr_tag_zh = "rr-neutral", "n/a", "无数据"
        elif real_rate >= 5.0:
            rr_class, rr_tag_en, rr_tag_zh = "rr-deep-restr", "Deep Restrictive", "深度限制性"
        elif real_rate >= 2.0:
            rr_class, rr_tag_en, rr_tag_zh = "rr-restr", "Restrictive", "限制性"
        elif real_rate >= 0.0:
            rr_class, rr_tag_en, rr_tag_zh = "rr-neutral", "Modestly positive", "温和为正"
        else:
            rr_class, rr_tag_en, rr_tag_zh = "rr-accomm", "Negative", "负实际利率"

        chg = snap.get("change_12m_bps")
        chg_display = "—" if chg is None else f"{chg:+d} bps"
        chg_class = "zero-delta" if not chg else ("pos-delta" if chg > 0 else "neg-delta")
        last_bps = snap.get("last_change_bps")
        last_display = "—" if last_bps is None else f"{last_bps:+d} bps · {snap['last_change_date']}"

        row_item = {
            "code": code,
            "flag": meta.get("flag", ""),
            "name_en": name_en,
            "name_zh": name_zh,
            "region": meta.get("region", "dm"),
            "cb_name_en": meta.get("cb_name_en", ""),
            "cb_name_zh": meta.get("cb_name_zh", ""),
            "cb_short": meta.get("cb_short", code),
            "tool_en": meta.get("policy_tool_en", ""),
            "tool_zh": meta.get("policy_tool_zh", ""),
            "policy_rate": policy_rate,
            "policy_display": snap.get("range_display") or f"{policy_rate:.2f}%",
            "as_of": snap["as_of"],
            "stale": snap["stale"],
            "source": snap["source"],
            "quality": snap["quality"],
            "cpi": cpi,
            "cpi_date": snap.get("cpi_date", ""),
            "real_rate": real_rate,
            "real_date": snap.get("real_date", ""),
            "target": target,
            "target_gap": target_gap,
            "rate_change_12m": chg if chg is not None else 0,
            "chg_display": chg_display,
            "chg_class": chg_class,
            "last_display": last_display,
            "bis_rate": snap.get("bis_rate"),
            "bis_date": snap.get("bis_date"),
            "rr_class": rr_class,
            "rr_tag_en": rr_tag_en,
            "rr_tag_zh": rr_tag_zh,
            "href": href,
        }
        table_rows_data.append(row_item)

        if real_rate is not None and not snap["stale"]:
            real_rate_chart_data.append({
                "code": code,
                "flag": meta.get("flag", ""),
                "name_en": name_en,
                "name_zh": name_zh,
                "policy_rate": policy_rate,
                "cpi": cpi,
                "real_rate": real_rate,
            })

        if taylor_rate is not None and not snap["stale"]:
            taylor_chart_data.append({
                "code": code,
                "flag": meta.get("flag", ""),
                "name_en": name_en,
                "name_zh": name_zh,
                "actual_rate": policy_rate,
                "taylor_rate": taylor_rate,
                "policy_gap": round(policy_rate - taylor_rate, 2),
                "stance_label": stance.get("stance_label", "neutral"),
            })

    # Sort real rate data descending for horizontal chart
    real_rate_chart_data.sort(key=lambda x: x["real_rate"], reverse=True)

    # Master Table HTML generation
    table_rows_html = []
    for r in table_rows_data:
        stale_badge = (
            '<span class="stale-badge" title="Policy-rate observation older than '
            f'{STALE_POLICY_DAYS} days">stale</span>' if r["stale"] else ""
        )
        bis_cell = "—"
        if r["bis_rate"] is not None:
            bis_match = abs(float(r["bis_rate"]) - float(r["policy_rate"])) < 0.051
            bis_cell = (
                f'<span class="{"bis-ok" if bis_match else "bis-diff"}">{float(r["bis_rate"]):.2f}%</span>'
                f'<span class="target-sub">{r["bis_date"]}</span>'
            )
        cpi_cell = "—" if r["cpi"] is None else f'{r["cpi"]:.2f}%<span class="target-sub">{r["cpi_date"]}</span>'
        real_cell = "—" if r["real_rate"] is None else (
            f'<span class="rr-pill {r["rr_class"]}"><strong>{r["real_rate"]:+.2f}%</strong></span>'
            f'<span class="target-sub">{r["real_date"]}</span>'
        )
        gap_cell = "—" if r["target_gap"] is None else (
            f'<span class="gap-display {"gap-pos" if r["target_gap"] > 0 else "gap-neg"}">{r["target_gap"]:+.2f}%</span>'
            f'<span class="target-sub">(ref. target {r["target"]:.1f}%)</span>'
        )
        row_html = f"""
        <tr class="table-row{' row-stale' if r['stale'] else ''}" data-region="{r['region']}" data-search="{r['code']} {r['name_en']} {r['name_zh']} {r['cb_short']} {r['cb_name_en']} {r['cb_name_zh']}">
          <td class="col-entity">
            <a href="{r['href']}" class="entity-link" title="View {r['name_en']} macro dashboard">
              <span class="entity-flag">{r['flag']}</span>
              <div class="entity-names">
                <span class="entity-code">{r['code']}</span>
                <span class="entity-title en-only">{r['name_en']}</span>
                <span class="entity-title zh-only">{r['name_zh']}</span>
                <span class="entity-cb en-only">{r['cb_short']}</span>
                <span class="entity-cb zh-only">{r['cb_name_zh'][:14]}</span>
              </div>
            </a>
          </td>
          <td class="col-tool">
            <div class="tool-name en-only">{r['tool_en']}</div>
            <div class="tool-name zh-only">{r['tool_zh']}</div>
          </td>
          <td class="col-num col-policy" data-sort="{r['policy_rate']}">
            <strong>{r['policy_display']}</strong>{stale_badge}
            <span class="target-sub">{r['as_of']} · {r['source'][:42]}</span>
          </td>
          <td class="col-num col-last">{r['last_display']}</td>
          <td class="col-num col-delta" data-sort="{r['rate_change_12m']}">
            <span class="{r['chg_class']}">{r['chg_display']}</span>
          </td>
          <td class="col-num col-cpi" data-sort="{r['cpi'] if r['cpi'] is not None else ''}">{cpi_cell}</td>
          <td class="col-num col-real" data-sort="{r['real_rate'] if r['real_rate'] is not None else ''}">{real_cell}</td>
          <td class="col-num col-gap" data-sort="{r['target_gap'] if r['target_gap'] is not None else ''}">{gap_cell}</td>
          <td class="col-num col-bis">{bis_cell}</td>
          <td class="col-action">
            <a href="{r['href']}" class="table-action-btn">
              <span class="en-only">Open →</span><span class="zh-only">看板 →</span>
            </a>
          </td>
        </tr>
        """
        table_rows_html.append(row_html)

    all_table_rows = "\n".join(table_rows_html)

    live_rows = [r for r in table_rows_data if not r["stale"] and r["real_rate"] is not None]
    stale_rows = [r for r in table_rows_data if r["stale"]]
    if live_rows:
        hi = max(live_rows, key=lambda r: r["real_rate"])
        lo = min(live_rows, key=lambda r: r["real_rate"])
        spread_badge = f"{hi['real_rate']:+.1f}% ({hi['code']}) ~ {lo['real_rate']:+.1f}% ({lo['code']})"
    else:
        spread_badge = "n/a"

    def _bucket(rows, lo_bound, hi_bound):
        picked = sorted(
            (r for r in rows if lo_bound <= r["real_rate"] < hi_bound),
            key=lambda r: r["real_rate"], reverse=True,
        )
        return ", ".join(f"{r['name_en']} {r['real_rate']:+.2f}% ({r['real_date']})" for r in picked) or "none"

    def _bucket_zh(rows, lo_bound, hi_bound):
        picked = sorted(
            (r for r in rows if lo_bound <= r["real_rate"] < hi_bound),
            key=lambda r: r["real_rate"], reverse=True,
        )
        return "、".join(f"{r['name_zh']} {r['real_rate']:+.2f}%（{r['real_date']}）" for r in picked) or "无"

    insight_cards_html = f"""
    <div class="insight-row">
      <div class="insight-card">
        <div class="insight-title"><span class="en-only">Real rate ≥ +2%</span><span class="zh-only">实际利率 ≥ +2%</span></div>
        <div class="insight-text en-only">{_bucket(live_rows, 2.0, 99.0)}</div>
        <div class="insight-text zh-only">{_bucket_zh(live_rows, 2.0, 99.0)}</div>
      </div>
      <div class="insight-card neutral">
        <div class="insight-title"><span class="en-only">0% to +2%</span><span class="zh-only">0% 至 +2%</span></div>
        <div class="insight-text en-only">{_bucket(live_rows, 0.0, 2.0)}</div>
        <div class="insight-text zh-only">{_bucket_zh(live_rows, 0.0, 2.0)}</div>
      </div>
      <div class="insight-card warning">
        <div class="insight-title"><span class="en-only">Negative real rate</span><span class="zh-only">负实际利率</span></div>
        <div class="insight-text en-only">{_bucket(live_rows, -99.0, 0.0)}</div>
        <div class="insight-text zh-only">{_bucket_zh(live_rows, -99.0, 0.0)}</div>
      </div>
    </div>
    <div class="insight-text" style="margin-top:8px;">
      <span class="en-only">Generated from the canonical frames at build time (ex-post real rate = policy rate in force at month end − headline CPI YoY). Excluded as stale (policy observation older than {STALE_POLICY_DAYS} days): {", ".join(f"{r['code']} (as of {r['as_of']})" for r in stale_rows) or "none"}.</span>
      <span class="zh-only">构建时由标准数据框计算（事后实际利率 = 月末有效政策利率 − 当月CPI同比）。以下因政策利率数据超过 {STALE_POLICY_DAYS} 天未更新而排除：{"、".join(f"{r['code']}（截至 {r['as_of']}）" for r in stale_rows) or "无"}。</span>
    </div>
    """

    taylor_rows = "".join(
        f"<tr><td>{code}</td><td>{p['target']}%</td><td>{p['r_star']}%</td><td>{p['trend_growth']}%</td></tr>"
        for code, p in sorted(TAYLOR_REFERENCE.items())
    )
    data_notes_html = f"""
    <div class="chart-card" id="card-data-notes" style="margin-top:20px;">
      <div class="chart-title"><span class="en-only">Data notes</span><span class="zh-only">数据说明</span></div>
      <div class="chart-desc en-only">
        Policy rates come from each page's canonical frame: BIS WS_CBPOL (CEE-4, JP, HK), ECB, BoE, Fed target range,
        SARB, TCMB, BOK, CBC and AKShare LPR; KZ, UZ, EG and NG use lagging IMF IFS mirrors until native feeds are wired.
        The BIS column is the BIS daily feed captured at the last refresh; a red value means the page differs from BIS by more than 5 bp.
        The Taylor-rule chart is a <strong>MODEL</strong> (Taylor 1993 with the parameters below), not data.
        Meeting calendars, market-implied pricing, dot plots and statement analysis were removed on 2026-11-05 because they were hand-typed; they return only with verifiable sources.
      </div>
      <div class="chart-desc zh-only">
        政策利率取自各国页面的标准数据框：BIS WS_CBPOL（中东欧四国、日本、香港）、欧央行、英格兰银行、美联储目标区间、
        南非央行、土耳其央行、韩国央行、台湾央行与 AKShare LPR；哈萨克斯坦、乌兹别克斯坦、埃及、尼日利亚在接入原生数据前使用滞后的 IMF IFS 镜像。
        BIS 列为最近一次刷新时抓取的 BIS 日度数据；红色表示页面数值与 BIS 相差超过 5 个基点。
        泰勒规则图为<strong>模型</strong>（Taylor 1993，参数见下表），并非数据。
        会议日程、市场隐含定价、点阵图与声明分析因系手工录入，已于 2026-11-05 移除；接入可验证来源后才会恢复。
      </div>
      <table class="matrix-table" style="margin-top:10px;max-width:520px;">
        <thead><tr><th>Scope</th><th>Ref. inflation target</th><th>Neutral real rate r*</th><th>Trend growth</th></tr></thead>
        <tbody>{taylor_rows}</tbody>
      </table>
    </div>
    """


    # JSON payloads for Lightweight Charts & FT Studio Canvas charts
    real_rate_json = json.dumps(real_rate_chart_data, ensure_ascii=False)
    taylor_json = json.dumps(taylor_chart_data, ensure_ascii=False)
    historical_cycles_json = json.dumps(load_historical_policy_cycles(), ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Central Bank Policy & Monetary Cycle Tracker · 全球央行与货币政策周期追踪器</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏛️</text></svg>">
  <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    :root {{
      --bg: #fffdfa;
      --surface: #ffffff;
      --card-bg: #ffffff;
      --border: #e8e4df;
      --border-subtle: #f0ebe4;
      --fg: #12151a;
      --text-secondary: #737c8c;
      --accent: #990f3d; /* FT Burgundy */
      --teal: #0d7680;   /* FT Teal */
      --slate: #364b61;  /* Slate Navy */
      --amber: #d97706;  /* Claude Amber */
      --good: #0d7680;
      --bad: #990f3d;
      --font-main: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-serif: "Newsreader", "Iowan Old Style", "Songti SC", Georgia, serif;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --radius-sm: 4px;
      --radius-md: 6px;
      --radius-lg: 8px;
      --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
      --shadow-md: 0 2px 6px rgba(0,0,0,0.06);
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background-color: var(--bg);
      color: var(--fg);
      font-family: var(--font-main);
      line-height: 1.45;
      -webkit-font-smoothing: antialiased;
    }}

    /* Topbar */
    .topbar {{
      background: #1a1e24;
      color: #e0e4eb;
      padding: 9px 18px;
      font-size: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }}
    .topbar a {{ color: inherit; text-decoration: none; }}
    .brand {{ font-weight: 700; letter-spacing: 0.04em; display: flex; align-items: center; gap: 8px; }}
    .brand span {{ color: #9da8b6; font-weight: 400; }}
    .topbar-nav {{ display: flex; align-items: center; gap: 14px; overflow-x: auto; padding: 2px 0; }}
    .country-nav {{ display: flex; gap: 4px; align-items: center; }}
    .country-nav a {{
      padding: 2px 6px;
      border-radius: var(--radius-sm);
      color: #b8c2cc;
      font-size: 11px;
      font-family: var(--font-mono);
      transition: all 0.15s ease;
    }}
    .country-nav a:hover {{ background: rgba(255,255,255,0.12); color: #ffffff; }}
    .topbar-actions {{ display: flex; gap: 8px; align-items: center; flex-shrink: 0; }}
    .topbar-btn {{
      padding: 4px 10px;
      border-radius: var(--radius-sm);
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      border: 1px solid rgba(255,255,255,0.15);
      background: rgba(255,255,255,0.06);
      color: #e0e4eb;
      transition: all 0.15s;
    }}
    .topbar-btn:hover {{ background: rgba(255,255,255,0.14); color: #fff; }}
    .topbar-btn.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}

    /* Layout Container */
    .container {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px 20px 48px;
    }}

    /* Header Header */
    .page-header {{
      margin-bottom: 24px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .header-main h1 {{
      font-family: var(--font-serif);
      font-size: 28px;
      font-weight: 700;
      color: var(--fg);
      letter-spacing: -0.01em;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .header-subtitle {{
      color: var(--text-secondary);
      font-size: 13.5px;
      max-width: 820px;
    }}
    .header-badges {{
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .stat-badge {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 6px 12px;
      font-size: 12px;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow-sm);
    }}
    .stat-badge-num {{
      font-weight: 700;
      font-family: var(--font-mono);
      color: var(--accent);
      font-size: 15px;
    }}
    .stat-badge-desc {{
      color: var(--text-secondary);
      font-size: 10.5px;
    }}

    /* Tab Navigation */
    .tab-bar {{
      display: flex;
      gap: 8px;
      border-bottom: 2px solid var(--border);
      margin-bottom: 24px;
      overflow-x: auto;
      padding-bottom: 0;
    }}
    .tab-btn {{
      padding: 10px 18px;
      border: none;
      background: transparent;
      color: var(--text-secondary);
      font-size: 13.5px;
      font-weight: 600;
      cursor: pointer;
      border-bottom: 3px solid transparent;
      margin-bottom: -2px;
      transition: all 0.2s;
      white-space: nowrap;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .tab-btn:hover {{ color: var(--fg); }}
    .stale-badge {{ display:inline-block; margin-left:6px; padding:1px 6px; border-radius:3px; font-size:10px; background:rgba(153,15,61,0.12); color:#990f3d; }}
    .row-stale td {{ opacity: 0.6; }}
    .bis-ok {{ color: var(--teal, #0d7680); font-weight:600; }}
    .bis-diff {{ color: #990f3d; font-weight:700; }}
    .col-num .target-sub {{ display:block; }}
    .tab-btn.active {{
      color: var(--accent);
      border-bottom-color: var(--accent);
    }}

    /* Filter Controls Bar */
    .filter-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 18px;
      background: var(--surface);
      padding: 12px 16px;
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-sm);
    }}
    .filter-chips {{
      display: flex;
      gap: 6px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .filter-chip {{
      padding: 5px 12px;
      font-size: 12px;
      font-weight: 500;
      border: 1px solid var(--border);
      background: var(--bg);
      color: var(--text-secondary);
      border-radius: 20px;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .filter-chip:hover {{ color: var(--fg); border-color: var(--text-secondary); }}
    .filter-chip.active {{
      background: var(--slate);
      color: #ffffff;
      border-color: var(--slate);
      font-weight: 600;
    }}
    .search-box {{
      position: relative;
      display: flex;
      align-items: center;
    }}
    .search-input {{
      padding: 6px 12px 6px 28px;
      font-size: 12px;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      width: 220px;
      background: #ffffff;
      color: var(--fg);
    }}
    .search-input:focus {{
      outline: none;
      border-color: var(--accent);
    }}
    .search-icon {{
      position: absolute;
      left: 8px;
      font-size: 12px;
      color: var(--text-secondary);
    }}

    /* Tab Panes */
    .tab-pane {{ display: none; }}
    .tab-pane.active {{ display: block; }}

    /* ==============================================================================
       TAB 1: Master Policy Matrix Table
       ============================================================================== */
    .table-responsive {{
      overflow-x: auto;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-sm);
    }}
    .matrix-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }}
    .matrix-table th {{
      background: #fbf9f6;
      padding: 10px 14px;
      border-bottom: 1px solid var(--border);
      color: var(--text-secondary);
      font-weight: 600;
      font-size: 11.5px;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      white-space: nowrap;
      cursor: pointer;
      user-select: none;
    }}
    .matrix-table th:hover {{ color: var(--fg); background: #f3efe9; }}
    .matrix-table th.sorted-asc::after {{ content: " ▲"; font-size: 9px; }}
    .matrix-table th.sorted-desc::after {{ content: " ▼"; font-size: 9px; }}
    .matrix-table td {{
      padding: 10px 14px;
      border-bottom: 1px solid var(--border-subtle);
      vertical-align: middle;
    }}
    .matrix-table tr:hover {{ background: #faf8f5; }}
    .col-entity {{ min-width: 170px; }}
    .entity-link {{
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
      color: var(--fg);
    }}
    .entity-flag {{ font-size: 20px; }}
    .entity-names {{ display: flex; flex-direction: column; }}
    .entity-code {{ font-weight: 700; font-family: var(--font-mono); font-size: 12px; color: var(--accent); }}
    .entity-title {{ font-weight: 600; font-size: 13px; }}
    .entity-cb {{ font-size: 11px; color: var(--text-secondary); }}
    .col-tool {{ max-width: 180px; font-size: 11.5px; color: var(--text-secondary); }}
    .col-num {{ font-family: var(--font-mono); text-align: right; }}
    .matrix-table th.col-num {{ text-align: right; }}

    /* Badges */
    .rr-pill {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: var(--radius-sm);
      font-size: 12px;
      font-weight: 700;
    }}
    .rr-deep-restr {{ background: rgba(13, 118, 128, 0.18); color: #085259; border: 1px solid rgba(13, 118, 128, 0.3); }}
    .rr-restr {{ background: rgba(13, 118, 128, 0.10); color: #0d7680; }}
    .rr-neutral {{ background: rgba(115, 124, 140, 0.12); color: #364b61; }}
    .rr-accomm {{ background: rgba(153, 15, 61, 0.12); color: #990f3d; }}

    .gap-display {{ font-weight: 600; }}
    .gap-pos {{ color: var(--bad); }}
    .gap-neg {{ color: var(--good); }}
    .target-sub {{ display: block; font-size: 10.5px; color: var(--text-secondary); }}

    .cycle-pill {{
      display: inline-block;
      padding: 3px 9px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
      white-space: nowrap;
    }}
    .cycle-pill.easing {{ background: rgba(13, 118, 128, 0.12); color: #0d7680; }}
    .cycle-pill.plateau {{ background: rgba(217, 119, 6, 0.12); color: #b45309; }}
    .cycle-pill.hiking {{ background: rgba(153, 15, 61, 0.12); color: #990f3d; }}
    .cycle-pill.neutral {{ background: rgba(54, 75, 97, 0.12); color: #364b61; }}

    .pos-delta {{ color: var(--bad); font-weight: 600; }}
    .neg-delta {{ color: var(--good); font-weight: 600; }}
    .zero-delta {{ color: var(--text-secondary); }}

    .next-date-box {{ display: flex; flex-direction: column; }}
    .next-date-text {{ font-weight: 600; font-family: var(--font-mono); font-size: 12px; }}
    .days-badge {{
      display: inline-block;
      background: #f0ebe4;
      color: #555e6d;
      padding: 1px 6px;
      border-radius: 3px;
      font-size: 10px;
      width: fit-content;
      margin-top: 2px;
    }}
    .consensus-tag {{ font-size: 11.5px; color: #444b58; }}
    .table-action-btn {{
      display: inline-block;
      padding: 3px 8px;
      background: #f4efe9;
      color: var(--accent);
      border-radius: var(--radius-sm);
      font-size: 11.5px;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.15s;
    }}
    .table-action-btn:hover {{ background: var(--accent); color: #fff; }}

    /* ==============================================================================
       TAB 2: Real Rate Studio & Charts
       ============================================================================== */
    .studio-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 20px;
      margin-bottom: 24px;
    }}
    @media (min-width: 1024px) {{
      .studio-grid {{ grid-template-columns: 3fr 2fr; }}
    }}
    .chart-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 20px;
      box-shadow: var(--shadow-sm);
    }}
    .chart-card-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }}
    .chart-title {{
      font-size: 16px;
      font-weight: 700;
      color: var(--fg);
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .chart-desc {{
      color: var(--text-secondary);
      font-size: 12px;
      margin-top: 2px;
    }}
    .chart-plot-area {{
      min-height: 480px;
      width: 100%;
      position: relative;
    }}
    .lw-toolbar-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
      padding: 6px 10px;
      background: #FAF8F5;
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
    }}
    .lw-btn-group {{
      display: inline-flex;
      align-items: center;
      gap: 3px;
      flex-wrap: wrap;
    }}
    .lw-ctrl-btn {{
      appearance: none;
      border: 1px solid transparent;
      background: transparent;
      color: var(--text-secondary);
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 3px;
      cursor: pointer;
      transition: all 0.12s ease;
    }}
    .lw-ctrl-btn:hover {{
      background: #EFECE6;
      color: var(--fg);
    }}
    .lw-ctrl-btn.active {{
      background: #12151a;
      color: #ffffff;
    }}
    .lw-ctrl-btn.tool-active {{
      background: rgba(13, 118, 128, 0.14);
      border-color: var(--teal);
      color: var(--teal);
    }}
    .lw-legend-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px 12px;
      margin-bottom: 8px;
      font-size: 11.5px;
    }}
    .lw-legend-pill {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 2px 7px;
      border-radius: 4px;
      border: 1px solid var(--border-subtle);
      background: #ffffff;
      cursor: pointer;
      user-select: none;
      transition: opacity 0.15s, border-color 0.15s;
    }}
    .lw-legend-pill:hover {{
      border-color: var(--text-secondary);
    }}
    .lw-legend-pill.muted {{
      opacity: 0.35;
      text-decoration: line-through;
    }}
    .lw-delta-box {{
      display: none;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 5px 10px;
      margin-bottom: 8px;
      background: #F4F9F9;
      border: 1px solid rgba(13, 118, 128, 0.3);
      border-radius: 4px;
      font-family: var(--font-mono);
      font-size: 11px;
    }}
    .lw-delta-box.active {{
      display: flex;
    }}
    .chart-card.lw-fullscreen {{
      position: fixed !important;
      inset: 24px !important;
      z-index: 9999 !important;
      background: #FFFDFA !important;
      box-shadow: 0 24px 64px rgba(18, 21, 26, 0.38) !important;
      overflow-y: auto !important;
    }}
    .chart-card.lw-fullscreen .chart-plot-area {{
      height: calc(100vh - 220px) !important;
      min-height: 500px !important;
    }}

    /* Carry Insight Cards */
    .insight-row {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }}
    .insight-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 14px 16px;
      border-left: 4px solid var(--teal);
    }}
    .insight-card.warning {{ border-left-color: var(--accent); }}
    .insight-card.neutral {{ border-left-color: var(--slate); }}
    .insight-title {{
      font-size: 13px;
      font-weight: 700;
      color: var(--fg);
      margin-bottom: 4px;
      display: flex;
      justify-content: space-between;
    }}
    .insight-text {{
      font-size: 12px;
      color: var(--text-secondary);
      line-height: 1.45;
    }}

    /* ==============================================================================
       TAB 3: 2026/2027 Central Bank Calendar
       ============================================================================== */
    .cal-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    .cal-table th {{
      background: #fbf9f6;
      padding: 10px 14px;
      border-bottom: 1px solid var(--border);
      color: var(--text-secondary);
      font-size: 11.5px;
      text-transform: uppercase;
    }}
    .cal-table td {{
      padding: 11px 14px;
      border-bottom: 1px solid var(--border-subtle);
      vertical-align: middle;
    }}
    .cal-table tr:hover {{ background: #faf8f5; }}
    .cal-date-col {{ min-width: 120px; }}
    .cal-date-main {{ font-family: var(--font-mono); font-weight: 700; color: var(--fg); }}
    .cal-days-sub {{ font-size: 11px; color: var(--text-secondary); }}
    .cal-cb-info {{ display: flex; align-items: center; gap: 10px; }}
    .cal-flag {{ font-size: 20px; }}
    .cal-event-desc {{ font-size: 12px; color: var(--text-secondary); }}
    .cal-badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: var(--radius-sm);
      font-size: 11px;
      font-weight: 600;
    }}
    .tier-1-badge {{ background: rgba(153, 15, 61, 0.1); color: var(--accent); border: 1px solid rgba(153, 15, 61, 0.2); }}
    .tier-2-badge {{ background: rgba(54, 75, 97, 0.08); color: var(--slate); }}
    .cal-rate-col {{ font-family: var(--font-mono); font-weight: 600; }}
    .cal-consensus-text {{ font-size: 12px; font-weight: 500; color: var(--fg); }}
    .cal-link {{
      color: var(--teal);
      text-decoration: none;
      font-weight: 600;
      font-size: 12px;
    }}
    .cal-link:hover {{ text-decoration: underline; }}

    /* ==============================================================================
       TAB 4: Corridor Cards Grid
       ============================================================================== */
    .corridor-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
      gap: 18px;
    }}
    .corridor-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 18px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 14px;
      transition: transform 0.15s, box-shadow 0.15s;
    }}
    .corridor-card:hover {{
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }}
    .card-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}
    .card-id {{ display: flex; align-items: center; gap: 10px; }}
    .card-flag {{ font-size: 26px; }}
    .card-title {{ font-size: 15px; font-weight: 700; color: var(--fg); }}
    .card-sub {{ font-size: 12px; color: var(--text-secondary); }}

    .corridor-metric-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      background: #faf8f5;
      padding: 10px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border-subtle);
    }}
    .metric-item {{ display: flex; flex-direction: column; }}
    .metric-label {{ font-size: 10.5px; color: var(--text-secondary); }}
    .metric-val {{ font-family: var(--font-mono); font-size: 15px; font-weight: 700; margin: 1px 0; }}
    .metric-val.primary-val {{ color: var(--accent); }}
    .metric-val.pos {{ color: var(--good); }}
    .metric-val.neg {{ color: var(--bad); }}
    .metric-sub {{ font-size: 10px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

    /* Corridor visual bar */
    .corridor-visualizer-box {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .corridor-track-labels {{
      display: flex;
      justify-content: space-between;
      font-size: 10.5px;
      color: var(--text-secondary);
      font-family: var(--font-mono);
    }}
    .corridor-bar-track {{
      position: relative;
      height: 14px;
      background: #e8e4df;
      border-radius: 7px;
      margin: 4px 0;
    }}
    .corridor-fill {{
      position: absolute;
      top: 0;
      bottom: 0;
      background: rgba(13, 118, 128, 0.25);
      border-radius: 7px;
    }}
    .corridor-marker {{
      position: absolute;
      top: -3px;
      width: 6px;
      height: 20px;
      border-radius: 3px;
      transform: translateX(-50%);
    }}
    .corridor-marker.floor {{ background: var(--slate); }}
    .corridor-marker.center {{ background: var(--accent); width: 8px; z-index: 2; }}
    .corridor-marker.ceil {{ background: var(--slate); }}

    .card-context-line {{
      display: flex;
      flex-direction: column;
      gap: 3px;
      font-size: 11.5px;
      border-top: 1px dashed var(--border);
      padding-top: 10px;
    }}
    .context-item {{ display: flex; gap: 6px; }}
    .ctx-title {{ color: var(--text-secondary); font-weight: 600; min-width: 90px; }}
    .ctx-val {{ color: var(--fg); font-family: var(--font-mono); }}

    .card-decision-banner {{
      background: #fbf9f6;
      border-radius: var(--radius-sm);
      padding: 8px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      border: 1px solid var(--border-subtle);
    }}
    .next-decision-label strong {{ font-family: var(--font-mono); margin-left: 4px; color: var(--fg); }}
    .consensus-badge {{ font-weight: 500; color: #475569; }}
    .card-deep-link {{
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
      font-size: 11.5px;
    }}
    .card-deep-link:hover {{ text-decoration: underline; }}

    /* ==============================================================================
       TAB 5: Guidance & Statement Diff
       ============================================================================== */
    .diff-container {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 22px;
      margin-top: 20px;
      box-shadow: var(--shadow-sm);
    }}
    .diff-controls {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 14px;
      margin-bottom: 20px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }}
    .diff-selector {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .diff-select {{
      padding: 6px 12px;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      font-size: 13px;
      background: #ffffff;
      color: var(--fg);
    }}
    .diff-body {{
      font-size: 14px;
      line-height: 1.8;
      color: #2b303a;
    }}
    .diff-paragraph {{ margin-bottom: 16px; text-align: justify; }}
    .diff-del {{
      background-color: #fee2e2;
      color: #991b1b;
      text-decoration: line-through;
      padding: 1px 4px;
      border-radius: 2px;
    }}
    .diff-add {{
      background-color: #dcfce7;
      color: #166534;
      text-decoration: none;
      font-weight: 500;
      padding: 1px 4px;
      border-radius: 2px;
    }}
    .keyword-tag {{
      display: inline-block;
      padding: 0 4px;
      border-radius: 2px;
      font-weight: 600;
      font-size: 12.5px;
    }}
    .keyword-tag.hawk {{ background: rgba(153, 15, 61, 0.15); color: #990f3d; }}
    .keyword-tag.dove {{ background: rgba(13, 118, 128, 0.15); color: #0d7680; }}

    /* Sentiment Meter */
    .sentiment-meter-box {{
      display: flex;
      align-items: center;
      gap: 10px;
      background: #faf8f5;
      padding: 8px 14px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border);
    }}
    .meter-label {{ font-size: 12px; font-weight: 600; color: var(--text-secondary); }}
    .gauge-track {{
      width: 120px;
      height: 10px;
      background: #e2e8f0;
      border-radius: 5px;
      position: relative;
      overflow: hidden;
    }}
    .gauge-fill {{
      position: absolute;
      top: 0;
      bottom: 0;
      border-radius: 5px;
    }}
    .gauge-fill.dove {{ background: var(--teal); left: 0; }}
    .gauge-fill.hawk {{ background: var(--accent); right: 0; }}
    .meter-score {{ font-family: var(--font-mono); font-weight: 700; font-size: 12px; }}

    /* Language toggles */
    .zh-only {{ display: none; }}
    .en-only {{ display: inline; }}
    html[lang="zh"] .zh-only {{ display: inline; }}
    html[lang="zh"] .en-only {{ display: none; }}
    div.zh-only {{ display: none; }}
    div.en-only {{ display: block; }}
    html[lang="zh"] div.zh-only {{ display: block; }}
    html[lang="zh"] div.en-only {{ display: none; }}
    span.zh-only {{ display: none; }}
    span.en-only {{ display: inline; }}
    html[lang="zh"] span.zh-only {{ display: inline; }}
    html[lang="zh"] span.en-only {{ display: none; }}

    /* Responsive */
    @media (max-width: 768px) {{
      .corridor-grid {{ grid-template-columns: 1fr; }}
      .topbar-nav {{ display: none; }}
      .matrix-table th, .matrix-table td {{ padding: 8px 10px; }}
      .header-main h1 {{ font-size: 22px; }}
    }}
  </style>
</head>
<body>

<!-- Top Navigation -->
<div class="topbar">
  <div class="brand">
    <span>East Meridian / Macro Dashboard</span>
  </div>
  <div class="topbar-nav">
    <nav class="country-nav" aria-label="country dashboards">
      {country_nav_links}
    </nav>
  </div>
  <div class="topbar-actions">
    <a href="chart_studio.html" class="topbar-btn" title="Macro Chart Studio · 宏观图表工坊">📈 Studio</a>
    <a href="my_dashboard.html" class="topbar-btn" title="My Dashboard · 我的自选宏观看板">⭐ My Dashboard</a>
    <a href="policy_tracker.html" class="topbar-btn active" title="Central Bank Policy & Event Tracker · 全球央行与宏观事件追踪">🏛️ Policy</a>
    <button class="topbar-btn" onclick="toggleLang()" id="lang-btn">中文</button>
  </div>
</div>

<div class="container">
  <!-- Header Section -->
  <header class="page-header">
    <div class="header-main">
      <h1>
        <span>🏛️</span>
        <span class="en-only">Central Bank Policy & Monetary Cycle Tracker</span>
        <span class="zh-only">全球央行与货币政策周期追踪器</span>
      </h1>
      <div class="header-subtitle en-only">
        Policy rates, changes and ex-post real rates for 18 economies, computed from the dashboard's canonical data and cross-checked against the BIS daily policy-rate feed.
      </div>
      <div class="header-subtitle zh-only">
        18 个经济体的政策利率、变动与事后实际利率，均由本看板标准数据计算，并与 BIS 日度政策利率数据交叉核对。
      </div>
    </div>
    <div class="header-badges">
      <div class="stat-badge">
        <span class="stat-badge-num">18</span>
        <span class="stat-badge-desc en-only">Central Banks Tracked</span>
        <span class="stat-badge-desc zh-only">覆盖央行总数</span>
      </div>
      <div class="stat-badge">
        <span class="stat-badge-num">{len(stale_rows)}</span>
        <span class="stat-badge-desc en-only">Stale policy inputs</span>
        <span class="stat-badge-desc zh-only">政策利率数据过期</span>
      </div>
      <div class="stat-badge">
        <span class="stat-badge-num">{spread_badge}</span>
        <span class="stat-badge-desc en-only">Real policy-rate range (non-stale)</span>
        <span class="stat-badge-desc zh-only">实际利率区间（不含过期）</span>
      </div>
    </div>
  </header>

  <!-- Main Tabs Navigation -->
  <div class="tab-bar">
    <button class="tab-btn active" onclick="switchTab('matrix')">
      🏛️ <span class="en-only">Global Policy Matrix</span><span class="zh-only">全景政策矩阵与周期雷达</span>
    </button>
    <button class="tab-btn" onclick="switchTab('realrate')">
      📊 <span class="en-only">Real Rate & Carry Studio</span><span class="zh-only">实际利率与利差套息工作室</span>
    </button>
  </div>

  <!-- TAB 1: Global Policy Stance Matrix -->
  <div id="tab-matrix" class="tab-pane active">
    <!-- Filter Chips & Search Bar -->
    <div class="filter-bar">
      <div class="filter-chips" id="matrix-region-filters">
        <button class="filter-chip active" onclick="filterMatrix('all')">
          <span class="en-only">All Economies (18)</span><span class="zh-only">全部经济体 (18)</span>
        </button>
        <button class="filter-chip" onclick="filterMatrix('dm')">
          <span class="en-only">Developed G4 (4)</span><span class="zh-only">发达成体系 G4</span>
        </button>
        <button class="filter-chip" onclick="filterMatrix('cee')">
          <span class="en-only">CEE-4 Economies (4)</span><span class="zh-only">中东欧核心四国</span>
        </button>
        <button class="filter-chip" onclick="filterMatrix('em')">
          <span class="en-only">Major Emerging (5)</span><span class="zh-only">重要新兴市场</span>
        </button>
        <button class="filter-chip" onclick="filterMatrix('frontier')">
          <span class="en-only">Frontier & Anchors (5)</span><span class="zh-only">前沿与离岸锚点</span>
        </button>
      </div>
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" id="matrix-search-input" class="search-input" placeholder="Search economy or CB..." onkeyup="searchMatrix()">
      </div>
    </div>

    <!-- Master Table -->
    <div class="table-responsive">
      <table class="matrix-table" id="master-policy-table">
        <thead>
          <tr>
            <th onclick="sortTable(0, 'text')"><span class="en-only">Economy / CB</span><span class="zh-only">经济体 / 机构</span></th>
            <th><span class="en-only">Primary Tool</span><span class="zh-only">核心政策工具</span></th>
            <th class="col-num" onclick="sortTable(2, 'num')"><span class="en-only">Policy Rate · as of · source</span><span class="zh-only">政策利率 · 日期 · 来源</span></th>
            <th class="col-num"><span class="en-only">Last change</span><span class="zh-only">最近一次调整</span></th>
            <th class="col-num" onclick="sortTable(4, 'num')"><span class="en-only">12M change</span><span class="zh-only">12个月变动</span></th>
            <th class="col-num" onclick="sortTable(5, 'num')"><span class="en-only">CPI YoY</span><span class="zh-only">CPI同比</span></th>
            <th class="col-num" onclick="sortTable(6, 'num')"><span class="en-only">Real rate</span><span class="zh-only">实际利率</span></th>
            <th class="col-num" onclick="sortTable(7, 'num')"><span class="en-only">CPI vs ref. target</span><span class="zh-only">CPI与参考目标差</span></th>
            <th class="col-num"><span class="en-only">BIS feed</span><span class="zh-only">BIS数据</span></th>
            <th><span class="en-only">Page</span><span class="zh-only">看板</span></th>
          </tr>
        </thead>
        <tbody id="matrix-tbody">
          {all_table_rows}
        </tbody>
      </table>
    </div>
  </div>

  <!-- TAB 2: Real Rate Studio -->
  <div id="tab-realrate" class="tab-pane">
    <!-- Interactive Historical Policy & Real Rate Cycle Explorer (Lightweight Charts) -->
    <div class="chart-card" id="card-policy-cycle-lw" style="margin-bottom: 20px;">
      <div class="chart-card-header">
        <div>
          <div class="chart-title">
            <span>⏱️</span>
            <span class="en-only">Global Central Bank Policy & Real Rate Cycle Trajectories (2000–2026)</span>
            <span class="zh-only">全球核心央行名义与实际政策利率历史周期演进 (2000–2026)</span>
          </div>
          <div class="chart-desc en-only">
            Interactive multi-country monetary cycle comparison. Click legend pills to toggle, double-click to solo, drag to pan, or hold Shift + drag (🔍) to measure cycle rate adjustments (Δ).
          </div>
          <div class="chart-desc zh-only">
            跨国货币周期联动与分化对比。单击图例隐藏/显示，双击图例单独聚焦某国央行，拖拽平移，按住 Shift 或点击 🔍 框选时间段自动计算加降息累计幅度 (Δ)。
          </div>
        </div>
      </div>

      <div class="lw-toolbar-row">
        <div class="lw-btn-group" id="cycle-cohort-btns">
          <button type="button" class="lw-ctrl-btn active" onclick="setPolicyCycleCohort('g4', this)">G4 (US·EA·UK·JP)</button>
          <button type="button" class="lw-ctrl-btn" onclick="setPolicyCycleCohort('em', this)">Major EM (CN·KR·ZA·TW)</button>
          <button type="button" class="lw-ctrl-btn" onclick="setPolicyCycleCohort('cee', this)">CEE-4 (PL·CZ·HU·RO)</button>
          <button type="button" class="lw-ctrl-btn" onclick="setPolicyCycleCohort('frontier', this)">High-Carry (TR·KZ·UZ·EG·NG)</button>
        </div>
        <div class="lw-btn-group" id="cycle-metric-btns">
          <button type="button" class="lw-ctrl-btn active" onclick="setPolicyCycleMetric('nominal', this)">
            <span class="en-only">Nominal Policy Rate (%)</span><span class="zh-only">名义政策利率 (%)</span>
          </button>
          <button type="button" class="lw-ctrl-btn" onclick="setPolicyCycleMetric('real', this)">
            <span class="en-only">Real Policy Rate (i − π)</span><span class="zh-only">实际政策利率 (i − π)</span>
          </button>
        </div>
        <div class="lw-btn-group" id="cycle-range-btns">
          <button type="button" class="lw-ctrl-btn" data-range="1Y" onclick="setPolicyCycleRange('1Y', this)">1Y</button>
          <button type="button" class="lw-ctrl-btn" data-range="3Y" onclick="setPolicyCycleRange('3Y', this)">3Y</button>
          <button type="button" class="lw-ctrl-btn" data-range="5Y" onclick="setPolicyCycleRange('5Y', this)">5Y</button>
          <button type="button" class="lw-ctrl-btn" data-range="10Y" onclick="setPolicyCycleRange('10Y', this)">10Y</button>
          <button type="button" class="lw-ctrl-btn active" data-range="ALL" onclick="setPolicyCycleRange('ALL', this)">All</button>
          <button type="button" class="lw-ctrl-btn" id="cycle-boxzoom-btn" title="Box-zoom time range & calculate delta (or Shift + drag)" onclick="togglePolicyCycleBoxZoom(this)">🔍</button>
          <button type="button" class="lw-ctrl-btn" title="Reset view" onclick="resetPolicyCycleZoom()">↺</button>
          <button type="button" class="lw-ctrl-btn" title="Export CSV" onclick="exportPolicyCycleCSV()">CSV</button>
          <button type="button" class="lw-ctrl-btn" title="Download PNG" onclick="exportPolicyCyclePNG()">PNG</button>
          <button type="button" class="lw-ctrl-btn" title="Expand fullscreen" onclick="toggleCardFullscreen('card-policy-cycle-lw', () => resizePolicyCycleLw())">⛶</button>
        </div>
      </div>

      <div class="lw-legend-row" id="policy-cycle-legend"></div>
      <div class="lw-delta-box" id="policy-cycle-delta"></div>
      <div id="policy-cycle-lw-chart" class="chart-plot-area" style="min-height: 360px; height: 360px;"></div>
    </div>

    <div class="studio-grid">
      <!-- Horizontal Real Rate Chart -->
      <div class="chart-card" id="card-real-rate-bar">
        <div class="chart-card-header">
          <div>
            <div class="chart-title">
              <span>📊</span>
              <span class="en-only">Real Policy Rate Ranking (non-stale inputs)</span>
              <span class="zh-only">实际政策利率排名（不含过期数据）</span>
            </div>
            <div class="chart-desc en-only">
              Net real policy yield ($i - \\pi$) ranked from deepest restrictive carry down to negative real rates.
            </div>
            <div class="chart-desc zh-only">
              名义政策利率减去最新头寸 CPI 通胀率，衡量真实紧缩力度与跨国套息收益护城河。
            </div>
          </div>
          <div class="lw-btn-group">
            <button type="button" class="lw-ctrl-btn" onclick="exportRealRateCSV()">CSV</button>
            <button type="button" class="lw-ctrl-btn" onclick="exportCanvasCardPNG('real-rate-canvas', 'global_real_policy_rate_ranking.png')">PNG</button>
            <button type="button" class="lw-ctrl-btn" onclick="toggleCardFullscreen('card-real-rate-bar', () => initRealRateChart())">⛶</button>
          </div>
        </div>
        <div id="real-rate-plot" class="chart-plot-area"></div>
      </div>

      <!-- Taylor Stance Deviation Studio -->
      <div class="chart-card" id="card-taylor-scatter">
        <div class="chart-card-header">
          <div>
            <div class="chart-title">
              <span>🎯</span>
              <span class="en-only">MODEL · Policy Rate vs. Taylor Rule (1993) Benchmark</span>
              <span class="zh-only">模型 · 政策利率 vs. 泰勒规则（1993）基准</span>
            </div>
            <div class="chart-desc en-only">
              Actual policy rates plotted against standard Taylor Rule specifications (neutral $r^*$, trend growth, target gap).
            </div>
            <div class="chart-desc zh-only">
              各央行实际政策基准与泰勒规则理论中性利率对比（衡量政策是否走在曲线前面或过度紧缩）。
            </div>
          </div>
          <div class="lw-btn-group">
            <button type="button" class="lw-ctrl-btn" onclick="exportTaylorCSV()">CSV</button>
            <button type="button" class="lw-ctrl-btn" onclick="exportCanvasCardPNG('taylor-scatter-canvas', 'taylor_rule_stance_scatter.png')">PNG</button>
            <button type="button" class="lw-ctrl-btn" onclick="toggleCardFullscreen('card-taylor-scatter', () => initTaylorChart())">⛶</button>
          </div>
        </div>
        <div id="taylor-scatter-plot" class="chart-plot-area"></div>
      </div>
    </div>

    {insight_cards_html}
    {data_notes_html}
  </div>

</div>

<script>
/* ==============================================================================
   State Management & Language Toggle
   ============================================================================== */
let currentLang = 'en';

function formatVal(v, decimals = 2) {{
  if (v === null || v === undefined || isNaN(v)) return '—';
  const num = Number(v);
  return num.toLocaleString('en-US', {{
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }});
}}

function toggleLang() {{
  currentLang = currentLang === 'en' ? 'zh' : 'en';
  document.documentElement.lang = currentLang;
  document.getElementById('lang-btn').innerText = currentLang === 'en' ? '中文' : 'English';

  // Re-render language-dependent components
  renderDiffStatement();
  initPolicyCycleLwChart();
  initRealRateChart();
  initTaylorChart();
  initDotplot();
}}

function switchTab(tabId) {{
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

  event.currentTarget.classList.add('active');
  const target = document.getElementById('tab-' + tabId);
  if (target) {{
    target.classList.add('active');
    window.dispatchEvent(new Event('resize'));
    if (tabId === 'realrate') {{
      initPolicyCycleLwChart();
      initRealRateChart();
      initTaylorChart();
    }} else if (tabId === 'guidance') {{
      initDotplot();
      renderDiffStatement();
    }}
  }}
}}

function toggleCardFullscreen(cardId, onResize) {{
  const card = document.getElementById(cardId);
  if (!card) return;
  card.classList.toggle('lw-fullscreen');
  setTimeout(() => {{
    if (typeof onResize === 'function') onResize();
  }}, 60);
}}

/* ==============================================================================
   Table Sorting & Filtering Engine
   ============================================================================== */
function filterMatrix(region) {{
  document.querySelectorAll('#matrix-region-filters .filter-chip').forEach(c => c.classList.remove('active'));
  event.currentTarget.classList.add('active');

  const rows = document.querySelectorAll('#matrix-tbody tr');
  rows.forEach(r => {{
    if (region === 'all' || r.getAttribute('data-region') === region) {{
      r.style.display = '';
    }} else {{
      r.style.display = 'none';
    }}
  }});
}}

function searchMatrix() {{
  const query = document.getElementById('matrix-search-input').value.toLowerCase().trim();
  const rows = document.querySelectorAll('#matrix-tbody tr');
  rows.forEach(r => {{
    const text = (r.getAttribute('data-search') || '').toLowerCase();
    r.style.display = text.includes(query) ? '' : 'none';
  }});
}}

let sortState = {{ col: -1, asc: true }};

function sortTable(colIndex, type) {{
  const table = document.getElementById('master-policy-table');
  const tbody = document.getElementById('matrix-tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const th = table.querySelectorAll('th')[colIndex];

  if (sortState.col === colIndex) {{
    sortState.asc = !sortState.asc;
  }} else {{
    sortState.col = colIndex;
    sortState.asc = true;
  }}

  table.querySelectorAll('th').forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
  th.classList.add(sortState.asc ? 'sorted-asc' : 'sorted-desc');

  rows.sort((a, b) => {{
    let valA, valB;
    if (type === 'num') {{
      valA = parseFloat(a.children[colIndex].getAttribute('data-sort')) || 0;
      valB = parseFloat(b.children[colIndex].getAttribute('data-sort')) || 0;
    }} else if (type === 'date') {{
      valA = a.children[colIndex].getAttribute('data-sort') || '';
      valB = b.children[colIndex].getAttribute('data-sort') || '';
    }} else {{
      valA = a.children[colIndex].innerText.trim().toLowerCase();
      valB = b.children[colIndex].innerText.trim().toLowerCase();
    }}

    if (valA < valB) return sortState.asc ? -1 : 1;
    if (valA > valB) return sortState.asc ? 1 : -1;
    return 0;
  }});

  rows.forEach(r => tbody.appendChild(r));
}}

/* ==============================================================================
   Calendar Filtering & Search
   ============================================================================== */
const HISTORICAL_CYCLES = {historical_cycles_json};
const REAL_RATE_DATA = {real_rate_json};
const TAYLOR_DATA = {taylor_json};

const COHORT_MAP = {{
  g4: [
    {{ code: 'US', color: '#0d7680', label_en: '🇺🇸 Fed (US)', label_zh: '🇺🇸 美联储 (US)' }},
    {{ code: 'EA', color: '#990f3d', label_en: '🇪🇺 ECB (EA)', label_zh: '🇪🇺 欧央行 (EA)' }},
    {{ code: 'UK', color: '#364b61', label_en: '🇬🇧 BoE (UK)', label_zh: '🇬🇧 英格兰银行 (UK)' }},
    {{ code: 'JP', color: '#d97706', label_en: '🇯🇵 BoJ (JP)', label_zh: '🇯🇵 日本银行 (JP)' }}
  ],
  em: [
    {{ code: 'CN', color: '#990f3d', label_en: '🇨🇳 PBC (CN)', label_zh: '🇨🇳 中国央行 (CN)' }},
    {{ code: 'KR', color: '#0d7680', label_en: '🇰🇷 BOK (KR)', label_zh: '🇰🇷 韩国银行 (KR)' }},
    {{ code: 'ZA', color: '#d97706', label_en: '🇿🇦 SARB (ZA)', label_zh: '🇿🇦 南非央行 (ZA)' }},
    {{ code: 'TW', color: '#364b61', label_en: '🇹🇼 CBC (TW)', label_zh: '🇹🇼 台湾央行 (TW)' }}
  ],
  cee: [
    {{ code: 'PL', color: '#0d7680', label_en: '🇵🇱 NBP (PL)', label_zh: '🇵🇱 波兰央行 (PL)' }},
    {{ code: 'CZ', color: '#364b61', label_en: '🇨🇿 CNB (CZ)', label_zh: '🇨🇿 捷克央行 (CZ)' }},
    {{ code: 'HU', color: '#990f3d', label_en: '🇭🇺 MNB (HU)', label_zh: '🇭🇺 匈牙利央行 (HU)' }},
    {{ code: 'RO', color: '#d97706', label_en: '🇷🇴 BNR (RO)', label_zh: '🇷🇴 罗马尼亚央行 (RO)' }}
  ],
  frontier: [
    {{ code: 'TR', color: '#990f3d', label_en: '🇹🇷 TCMB (TR)', label_zh: '🇹🇷 土耳其央行 (TR)' }},
    {{ code: 'KZ', color: '#0d7680', label_en: '🇰🇿 NBK (KZ)', label_zh: '🇰🇿 哈萨克斯坦央行 (KZ)' }},
    {{ code: 'UZ', color: '#364b61', label_en: '🇺🇿 CBU (UZ)', label_zh: '🇺🇿 乌兹别克斯坦央行 (UZ)' }},
    {{ code: 'EG', color: '#d97706', label_en: '🇪🇬 CBE (EG)', label_zh: '🇪🇬 埃及央行 (EG)' }},
    {{ code: 'NG', color: '#6b21a8', label_en: '🇳🇬 CBN (NG)', label_zh: '🇳🇬 尼日利亚央行 (NG)' }}
  ]
}};

let cycleCohort = 'g4';
let cycleMetric = 'nominal';
let cycleRange = 'ALL';
let cycleLwChart = null;
let cycleSeriesEntries = [];
let cycleBoxZoom = false;

function initPolicyCycleLwChart() {{
  const plotEl = document.getElementById('policy-cycle-lw-chart');
  if (!plotEl || typeof LightweightCharts === 'undefined') return;

  if (cycleLwChart) {{
    try {{ cycleLwChart.remove(); }} catch (e) {{}}
    cycleLwChart = null;
  }}
  plotEl.innerHTML = '';

  const tooltip = document.createElement('div');
  tooltip.style.cssText = 'position:absolute;top:10px;left:12px;z-index:15;pointer-events:none;background:rgba(255,253,250,0.95);border:1px solid #d9d2c7;border-radius:4px;padding:6px 10px;font-size:11px;display:none;box-shadow:0 2px 8px rgba(0,0,0,0.08);';
  plotEl.appendChild(tooltip);

  const selectOverlay = document.createElement('div');
  selectOverlay.style.cssText = 'position:absolute;top:0;bottom:24px;background:rgba(13,118,128,0.15);border-left:1.5px dashed #0d7680;border-right:1.5px dashed #0d7680;pointer-events:none;z-index:14;display:none;';
  plotEl.appendChild(selectOverlay);

  const chart = LightweightCharts.createChart(plotEl, {{
    width: plotEl.clientWidth || 900,
    height: plotEl.clientHeight || 360,
    layout: {{
      background: {{ type: 'solid', color: 'transparent' }},
      textColor: '#737c8c',
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      fontSize: 11,
      attributionLogo: false
    }},
    grid: {{
      vertLines: {{ visible: false }},
      horzLines: {{ color: 'rgba(18, 21, 26, 0.06)', style: 0 }}
    }},
    rightPriceScale: {{
      borderVisible: false,
      scaleMargins: {{ top: 0.10, bottom: 0.10 }}
    }},
    timeScale: {{
      borderColor: 'rgba(18, 21, 26, 0.14)',
      rightOffset: 2,
      fixLeftEdge: true,
      fixRightEdge: true
    }},
    localization: {{
      priceFormatter: (val) => `${{formatVal(val, 2)}}%`
    }},
    crosshair: {{
      mode: 0,
      vertLine: {{ color: 'rgba(18, 21, 26, 0.25)', width: 1, style: 2, labelBackgroundColor: '#12151a' }},
      horzLine: {{ color: 'rgba(18, 21, 26, 0.25)', width: 1, style: 2, labelBackgroundColor: '#12151a' }}
    }},
    handleScroll: {{
      mouseWheel: false,
      pressedMouseMove: !cycleBoxZoom,
      horzTouchDrag: true,
      vertTouchDrag: false
    }},
    handleScale: {{
      mouseWheel: false,
      pinch: true,
      axisPressedMouseMove: {{ time: true, price: true }},
      axisDoubleClickReset: {{ time: true, price: true }}
    }}
  }});

  cycleLwChart = chart;
  cycleSeriesEntries = [];
  const members = COHORT_MAP[cycleCohort] || COHORT_MAP.g4;
  const legendEl = document.getElementById('policy-cycle-legend');
  if (legendEl) legendEl.innerHTML = '';

  members.forEach((m, idx) => {{
    const rawPts = ((HISTORICAL_CYCLES[m.code] || {{}})[cycleMetric] || []).filter(p => p && p.time && !isNaN(p.value));
    if (!rawPts.length) return;
    const s = chart.addLineSeries({{
      color: m.color,
      lineWidth: 2.2,
      priceLineVisible: false,
      lastValueVisible: true
    }});
    s.setData(rawPts);
    if (idx === 0) {{
      s.createPriceLine({{
        price: 0,
        color: '#12151a',
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: false,
        title: '0%'
      }});
    }}
    const label = currentLang === 'zh' ? m.label_zh : m.label_en;
    const lastVal = rawPts[rawPts.length - 1].value;
    const entry = {{ code: m.code, color: m.color, label, series: s, data: rawPts, visible: true }};
    cycleSeriesEntries.push(entry);

    if (legendEl) {{
      const pill = document.createElement('span');
      pill.className = 'lw-legend-pill';
      pill.dataset.idx = String(cycleSeriesEntries.length - 1);
      pill.title = 'Click to show/hide · Double-click to solo';
      pill.innerHTML = `<span style="width:10px;height:3px;background:${{m.color}};display:inline-block;border-radius:1px;"></span>` +
        `<strong>${{label}}</strong> <span style="font-family:var(--font-mono);color:var(--text-secondary);">${{formatVal(lastVal, 2)}}%</span>`;
      const sIdx = cycleSeriesEntries.length - 1;
      pill.addEventListener('click', (e) => {{
        if (e.altKey || e.metaKey) soloPolicyCycleSeries(sIdx);
        else togglePolicyCycleSeries(sIdx);
      }});
      pill.addEventListener('dblclick', (e) => {{
        e.preventDefault();
        soloPolicyCycleSeries(sIdx);
      }});
      legendEl.appendChild(pill);
    }}
  }});

  chart.timeScale().fitContent();

  chart.subscribeCrosshairMove(param => {{
    if (!param.time || !param.point || param.point.x < 0 || param.point.y < 0) {{
      tooltip.style.display = 'none';
      return;
    }}
    const tStr = typeof param.time === 'string'
      ? param.time
      : `${{param.time.year}}-${{String(param.time.month).padStart(2, '0')}}-${{String(param.time.day).padStart(2, '0')}}`;
    const rows = [];
    cycleSeriesEntries.forEach(en => {{
      if (!en.visible) return;
      const sv = param.seriesData.get(en.series);
      if (sv && sv.value !== undefined) {{
        rows.push(`<div><span style="color:${{en.color}};font-weight:700;">● ${{en.label}}:</span> <strong>${{formatVal(sv.value, 2)}}%</strong></div>`);
      }}
    }});
    if (!rows.length) {{
      tooltip.style.display = 'none';
      return;
    }}
    tooltip.innerHTML = `<div style="font-weight:700;margin-bottom:2px;color:#12151a;">${{tStr}}</div>` + rows.join('');
    tooltip.style.display = 'block';
  }});

  // Ctrl/Cmd + wheel zoom
  plotEl.addEventListener('wheel', e => {{
    if (!(e.ctrlKey || e.metaKey)) return;
    e.preventDefault();
    const vr = chart.timeScale().getVisibleLogicalRange();
    if (!vr) return;
    const span = vr.to - vr.from;
    if (span <= 2 && e.deltaY < 0) return;
    const factor = e.deltaY < 0 ? 0.82 : 1.22;
    const center = (vr.from + vr.to) / 2;
    const half = (span * factor) / 2;
    chart.timeScale().setVisibleLogicalRange({{ from: center - half, to: center + half }});
  }}, {{ passive: false }});

  // Shift + drag or 🔍 box-zoom
  let dragStartX = null;
  plotEl.addEventListener('mousedown', e => {{
    if (!(cycleBoxZoom || e.shiftKey)) return;
    const rect = plotEl.getBoundingClientRect();
    dragStartX = e.clientX - rect.left;
    chart.applyOptions({{ handleScroll: {{ pressedMouseMove: false }} }});
    selectOverlay.style.left = `${{dragStartX}}px`;
    selectOverlay.style.width = '0px';
    selectOverlay.style.display = 'block';
  }});
  window.addEventListener('mousemove', e => {{
    if (dragStartX === null) return;
    const rect = plotEl.getBoundingClientRect();
    const curX = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    selectOverlay.style.left = `${{Math.min(dragStartX, curX)}}px`;
    selectOverlay.style.width = `${{Math.abs(curX - dragStartX)}}px`;
  }});
  window.addEventListener('mouseup', e => {{
    if (dragStartX === null) return;
    const rect = plotEl.getBoundingClientRect();
    const endX = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    const x1 = Math.min(dragStartX, endX);
    const x2 = Math.max(dragStartX, endX);
    dragStartX = null;
    selectOverlay.style.display = 'none';
    if (!cycleBoxZoom) {{
      chart.applyOptions({{ handleScroll: {{ pressedMouseMove: true }} }});
    }}
    if (x2 - x1 < 12) return;
    const l1 = chart.timeScale().coordinateToLogical(x1);
    const l2 = chart.timeScale().coordinateToLogical(x2);
    if (l1 !== null && l2 !== null && l2 > l1) {{
      chart.timeScale().setVisibleLogicalRange({{ from: l1, to: l2 }});
      updatePolicyCycleDelta(l1, l2);
    }}
  }});

  plotEl.addEventListener('dblclick', () => resetPolicyCycleZoom());

  if (cycleRange !== 'ALL') {{
    setPolicyCycleRange(cycleRange, document.querySelector(`#cycle-range-btns [data-range="${{cycleRange}}"]`));
  }}
}}

function resizePolicyCycleLw() {{
  const plotEl = document.getElementById('policy-cycle-lw-chart');
  if (!plotEl || !cycleLwChart) return;
  cycleLwChart.applyOptions({{
    width: plotEl.clientWidth || 900,
    height: plotEl.clientHeight || 360
  }});
  cycleLwChart.timeScale().fitContent();
}}

function setPolicyCycleCohort(cohort, btnEl) {{
  cycleCohort = cohort;
  document.querySelectorAll('#cycle-cohort-btns .lw-ctrl-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  initPolicyCycleLwChart();
}}

function setPolicyCycleMetric(metric, btnEl) {{
  cycleMetric = metric;
  document.querySelectorAll('#cycle-metric-btns .lw-ctrl-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  initPolicyCycleLwChart();
}}

function setPolicyCycleRange(rangeKey, btnEl) {{
  cycleRange = rangeKey;
  document.querySelectorAll('#cycle-range-btns [data-range]').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  if (!cycleLwChart || !cycleSeriesEntries.length) return;
  if (rangeKey === 'ALL') {{
    cycleLwChart.timeScale().fitContent();
    const dBox = document.getElementById('policy-cycle-delta');
    if (dBox) dBox.classList.remove('active');
    return;
  }}
  const yrs = {{ '1Y': 1, '3Y': 3, '5Y': 5, '10Y': 10 }}[rangeKey] || 5;
  const primary = cycleSeriesEntries.find(e => e.visible && e.data.length) || cycleSeriesEntries[0];
  if (!primary || !primary.data.length) return;
  const maxIso = primary.data[primary.data.length - 1].time;
  const parts = maxIso.split('-').map(Number);
  const fromIso = `${{parts[0] - yrs}}-${{String(parts[1] || 1).padStart(2, '0')}}-01`;
  try {{
    cycleLwChart.timeScale().setVisibleRange({{ from: fromIso, to: maxIso }});
    const vr = cycleLwChart.timeScale().getVisibleLogicalRange();
    if (vr) updatePolicyCycleDelta(vr.from, vr.to);
  }} catch (e) {{
    cycleLwChart.timeScale().fitContent();
  }}
}}

function togglePolicyCycleBoxZoom(btnEl) {{
  cycleBoxZoom = !cycleBoxZoom;
  if (btnEl) btnEl.classList.toggle('tool-active', cycleBoxZoom);
  const plotEl = document.getElementById('policy-cycle-lw-chart');
  if (plotEl) plotEl.style.cursor = cycleBoxZoom ? 'crosshair' : 'grab';
  if (cycleLwChart) cycleLwChart.applyOptions({{ handleScroll: {{ pressedMouseMove: !cycleBoxZoom }} }});
}}

function resetPolicyCycleZoom() {{
  cycleBoxZoom = false;
  const btn = document.getElementById('cycle-boxzoom-btn');
  if (btn) btn.classList.remove('tool-active');
  const plotEl = document.getElementById('policy-cycle-lw-chart');
  if (plotEl) plotEl.style.cursor = 'grab';
  if (cycleLwChart) {{
    cycleLwChart.applyOptions({{ handleScroll: {{ pressedMouseMove: true }} }});
    cycleLwChart.timeScale().fitContent();
  }}
  const dBox = document.getElementById('policy-cycle-delta');
  if (dBox) dBox.classList.remove('active');
  document.querySelectorAll('#cycle-range-btns [data-range]').forEach(b => b.classList.toggle('active', b.getAttribute('data-range') === 'ALL'));
}}

function togglePolicyCycleSeries(idx) {{
  const target = cycleSeriesEntries[idx];
  if (!target) return;
  target.visible = !target.visible;
  target.series.applyOptions({{ visible: target.visible }});
  document.querySelectorAll('#policy-cycle-legend .lw-legend-pill').forEach((p, i) => {{
    p.classList.toggle('muted', !cycleSeriesEntries[i].visible);
  }});
}}

function soloPolicyCycleSeries(idx) {{
  const onlyThis = cycleSeriesEntries.every((e, i) => i === idx ? e.visible : !e.visible);
  cycleSeriesEntries.forEach((e, i) => {{
    e.visible = onlyThis ? true : (i === idx);
    e.series.applyOptions({{ visible: e.visible }});
  }});
  document.querySelectorAll('#policy-cycle-legend .lw-legend-pill').forEach((p, i) => {{
    p.classList.toggle('muted', !cycleSeriesEntries[i].visible);
  }});
}}

function updatePolicyCycleDelta(fromLogical, toLogical) {{
  const dBox = document.getElementById('policy-cycle-delta');
  const primary = cycleSeriesEntries.find(e => e.visible && e.data.length);
  if (!dBox || !primary) return;
  const i1 = Math.max(0, Math.min(primary.data.length - 1, Math.round(fromLogical)));
  const i2 = Math.max(0, Math.min(primary.data.length - 1, Math.round(toLogical)));
  if (i2 <= i1) return;
  const p1 = primary.data[i1];
  const p2 = primary.data[i2];
  const diffBps = Math.round((p2.value - p1.value) * 100);
  const sign = diffBps > 0 ? '+' : '';
  const col = diffBps >= 0 ? '#990f3d' : '#0d7680';
  dBox.innerHTML = `<span><strong>${{primary.label}} Δ (${{p1.time}} → ${{p2.time}})</strong>: ${{formatVal(p1.value, 2)}}% → ${{formatVal(p2.value, 2)}}% ` +
    `<strong style="color:${{col}}">(${{sign}}${{formatVal(diffBps, 0)}} bps)</strong></span>` +
    `<button type="button" class="lw-ctrl-btn" onclick="resetPolicyCycleZoom()">✕</button>`;
  dBox.classList.add('active');
}}

function exportPolicyCycleCSV() {{
  if (!cycleSeriesEntries.length) return;
  const datesSet = new Set();
  cycleSeriesEntries.forEach(e => e.data.forEach(p => datesSet.add(p.time)));
  const dates = Array.from(datesSet).sort();
  const header = ['Date', ...cycleSeriesEntries.map(e => `${{e.code}}_${{cycleMetric}}_pct`)];
  const maps = cycleSeriesEntries.map(e => new Map(e.data.map(p => [p.time, p.value])));
  const rows = [header.join(',')];
  dates.forEach(dt => {{
    rows.push([dt, ...maps.map(m => m.has(dt) ? m.get(dt) : '')].join(','));
  }});
  const blob = new Blob([rows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `policy_cycle_${{cycleCohort}}_${{cycleMetric}}.csv`;
  a.click();
}}

function exportPolicyCyclePNG() {{
  if (!cycleLwChart) return;
  try {{
    const canvas = cycleLwChart.takeScreenshot();
    const a = document.createElement('a');
    a.href = canvas.toDataURL('image/png');
    a.download = `policy_cycle_${{cycleCohort}}_${{cycleMetric}}.png`;
    a.click();
  }} catch (e) {{
    console.error(e);
  }}
}}

/* ==============================================================================
   High-DPI Interactive FT Canvas Charts (Real Rate Ranking, Taylor Rule, Dot Plot)
   ============================================================================== */
function setupHiDPICanvas(container, canvasId, heightPx) {{
  container.innerHTML = '';
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(360, container.clientWidth || 560);
  const h = Math.max(380, container.clientHeight || heightPx);
  const canvas = document.createElement('canvas');
  canvas.id = canvasId;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = w + 'px';
  canvas.style.height = h + 'px';
  canvas.style.display = 'block';
  container.appendChild(canvas);

  const tip = document.createElement('div');
  tip.style.cssText = 'position:absolute;pointer-events:none;background:rgba(255,253,250,0.96);border:1px solid #d9d2c7;border-radius:4px;padding:6px 10px;font-size:11px;line-height:1.4;box-shadow:0 2px 8px rgba(0,0,0,0.1);display:none;z-index:20;';
  container.appendChild(tip);

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  return {{ canvas, ctx, w, h, tip }};
}}

function exportCanvasCardPNG(canvasId, filename) {{
  const c = document.getElementById(canvasId);
  if (!c) return;
  const a = document.createElement('a');
  a.href = c.toDataURL('image/png');
  a.download = filename;
  a.click();
}}

function exportRealRateCSV() {{
  const rows = [['Code,Economy,Policy_Rate_Pct,CPI_YoY_Pct,Real_Policy_Rate_Pct']];
  REAL_RATE_DATA.forEach(d => rows.push(`${{d.code}},"${{d.name_en}}",${{d.policy_rate}},${{d.cpi}},${{d.real_rate}}`));
  const blob = new Blob([rows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'global_real_policy_rates.csv';
  a.click();
}}

function exportTaylorCSV() {{
  const rows = [['Code,Economy,Actual_Policy_Rate_Pct,Taylor_Implied_Rate_Pct,Policy_Gap_Pct,Stance']];
  TAYLOR_DATA.forEach(d => rows.push(`${{d.code}},"${{d.name_en}}",${{d.actual_rate}},${{d.taylor_rate}},${{d.policy_gap}},${{d.stance_label}}`));
  const blob = new Blob([rows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'taylor_rule_stance.csv';
  a.click();
}}

function initRealRateChart() {{
  const elem = document.getElementById('real-rate-plot');
  if (!elem) return;

  const sorted = [...REAL_RATE_DATA]; // descending from highest real rate to lowest
  const {{ canvas, ctx, w, h, tip }} = setupHiDPICanvas(elem, 'real-rate-canvas', 480);

  const padL = 158, padR = 58, padT = 16, padB = 38;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const vals = sorted.map(d => d.real_rate);
  const minX = Math.min(-2.5, Math.floor(Math.min(...vals) - 1));
  const maxX = Math.max(13.0, Math.ceil(Math.max(...vals) + 1.5));
  const xToPx = (v) => padL + ((v - minX) / (maxX - minX)) * plotW;

  ctx.fillStyle = '#FFFDFA';
  ctx.fillRect(0, 0, w, h);

  // Gridlines
  ctx.strokeStyle = '#e8e4df';
  ctx.lineWidth = 1;
  ctx.fillStyle = '#737c8c';
  ctx.font = '10.5px -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.textAlign = 'center';
  for (let gx = Math.ceil(minX / 2) * 2; gx <= maxX; gx += 2) {{
    const px = xToPx(gx);
    ctx.beginPath();
    ctx.moveTo(px, padT);
    ctx.lineTo(px, padT + plotH);
    ctx.stroke();
    ctx.fillText(`${{gx >= 0 ? '+' : ''}}${{gx}}%`, px, padT + plotH + 16);
  }}

  // Zero reference line
  const zeroPx = xToPx(0);
  ctx.strokeStyle = '#12151a';
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.moveTo(zeroPx, padT);
  ctx.lineTo(zeroPx, padT + plotH);
  ctx.stroke();

  const rowH = plotH / sorted.length;
  const barH = Math.max(10, rowH * 0.66);
  const hitBoxes = [];

  sorted.forEach((d, i) => {{
    const yCenter = padT + i * rowH + rowH / 2;
    const yTop = yCenter - barH / 2;
    const x0 = xToPx(0);
    const x1 = xToPx(d.real_rate);
    const bx = Math.min(x0, x1);
    const bw = Math.max(2, Math.abs(x1 - x0));

    const color = d.real_rate >= 2.0 ? '#0d7680' : (d.real_rate >= 0.0 ? '#364b61' : '#990f3d');
    ctx.fillStyle = color;
    ctx.fillRect(bx, yTop, bw, barH);

    // Y label
    ctx.fillStyle = '#12151a';
    ctx.font = '600 11px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.textAlign = 'right';
    const name = currentLang === 'zh' ? d.name_zh : d.name_en;
    ctx.fillText(`${{d.flag}} ${{name}} (${{d.code}})`, padL - 8, yCenter + 4);

    // Value label
    ctx.fillStyle = color;
    ctx.font = '700 10.5px ui-monospace, SFMono-Regular, monospace';
    ctx.textAlign = d.real_rate >= 0 ? 'left' : 'right';
    const valStr = `${{d.real_rate >= 0 ? '+' : ''}}${{formatVal(d.real_rate, 2)}}%`;
    ctx.fillText(valStr, d.real_rate >= 0 ? (x1 + 5) : (x1 - 5), yCenter + 3.5);

    hitBoxes.push({{ yTop: yCenter - rowH / 2, yBot: yCenter + rowH / 2, d }});
  }});

  canvas.onmousemove = (e) => {{
    const rect = canvas.getBoundingClientRect();
    const my = e.clientY - rect.top;
    const mx = e.clientX - rect.left;
    const hit = hitBoxes.find(b => my >= b.yTop && my <= b.yBot);
    if (!hit) {{
      tip.style.display = 'none';
      return;
    }}
    const d = hit.d;
    const name = currentLang === 'zh' ? d.name_zh : d.name_en;
    tip.innerHTML = `<strong>${{d.flag}} ${{name}} (${{d.code}})</strong><br>` +
      `${{currentLang === 'zh' ? '实际政策利率' : 'Real Policy Rate'}}: <strong>${{d.real_rate >= 0 ? '+' : ''}}${{formatVal(d.real_rate, 2)}}%</strong><br>` +
      `${{currentLang === 'zh' ? '名义政策利率' : 'Nominal Policy Rate'}}: ${{formatVal(d.policy_rate, 2)}}%<br>` +
      `${{currentLang === 'zh' ? '最新CPI通胀' : 'Headline CPI YoY'}}: ${{formatVal(d.cpi, 2)}}%`;
    tip.style.left = Math.min(w - 190, mx + 14) + 'px';
    tip.style.top = Math.max(8, my - 28) + 'px';
    tip.style.display = 'block';
  }};
  canvas.onmouseleave = () => {{ tip.style.display = 'none'; }};
}}

function initTaylorChart() {{
  const elem = document.getElementById('taylor-scatter-plot');
  if (!elem) return;

  const {{ canvas, ctx, w, h, tip }} = setupHiDPICanvas(elem, 'taylor-scatter-canvas', 480);
  const padL = 52, padR = 24, padT = 20, padB = 46;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const actuals = TAYLOR_DATA.map(d => d.actual_rate);
  const taylors = TAYLOR_DATA.map(d => d.taylor_rate);
  const minVal = Math.min(0, ...actuals, ...taylors);
  const maxVal = Math.ceil(Math.max(...actuals, ...taylors) + 2);

  const xToPx = (v) => padL + ((v - minVal) / (maxVal - minVal)) * plotW;
  const yToPx = (v) => padT + plotH - ((v - minVal) / (maxVal - minVal)) * plotH;

  ctx.fillStyle = '#FFFDFA';
  ctx.fillRect(0, 0, w, h);

  // Grid
  ctx.strokeStyle = '#e8e4df';
  ctx.lineWidth = 1;
  ctx.fillStyle = '#737c8c';
  ctx.font = '10.5px -apple-system, BlinkMacSystemFont, sans-serif';
  const step = maxVal > 25 ? 5 : 2;
  for (let gv = 0; gv <= maxVal; gv += step) {{
    const px = xToPx(gv);
    const py = yToPx(gv);
    ctx.beginPath(); ctx.moveTo(px, padT); ctx.lineTo(px, padT + plotH); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(padL, py); ctx.lineTo(padL + plotW, py); ctx.stroke();
    ctx.textAlign = 'center';
    ctx.fillText(`${{gv}}%`, px, padT + plotH + 16);
    ctx.textAlign = 'right';
    ctx.fillText(`${{gv}}%`, padL - 6, py + 3.5);
  }}

  // 45-degree Taylor Parity dashed line
  ctx.save();
  ctx.strokeStyle = '#9da8b6';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([5, 4]);
  ctx.beginPath();
  ctx.moveTo(xToPx(minVal), yToPx(minVal));
  ctx.lineTo(xToPx(maxVal), yToPx(maxVal));
  ctx.stroke();
  ctx.restore();

  // Axis titles
  ctx.fillStyle = '#364b61';
  ctx.font = '600 11px -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(currentLang === 'zh' ? '泰勒规则理论中性利率 (%)' : 'Taylor Rule Implied Benchmark (%)', padL + plotW / 2, h - 10);

  const pts = [];
  TAYLOR_DATA.forEach(d => {{
    const px = xToPx(d.taylor_rate);
    const py = yToPx(d.actual_rate);
    const col = d.policy_gap >= 1.0 ? '#0d7680' : (d.policy_gap <= -1.0 ? '#990f3d' : '#364b61');

    ctx.beginPath();
    ctx.arc(px, py, 6, 0, Math.PI * 2);
    ctx.fillStyle = col;
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = '#ffffff';
    ctx.stroke();

    ctx.fillStyle = '#12151a';
    ctx.font = '700 10px ui-monospace, SFMono-Regular, monospace';
    ctx.textAlign = 'center';
    ctx.fillText(d.code, px, py - 9);

    pts.push({{ px, py, d }});
  }});

  canvas.onmousemove = (e) => {{
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    let best = null, bestDist = 18;
    pts.forEach(p => {{
      const dist = Math.hypot(mx - p.px, my - p.py);
      if (dist < bestDist) {{ bestDist = dist; best = p; }}
    }});
    if (!best) {{ tip.style.display = 'none'; return; }}
    const d = best.d;
    const name = currentLang === 'zh' ? d.name_zh : d.name_en;
    tip.innerHTML = `<strong>${{d.flag}} ${{name}} (${{d.code}})</strong><br>` +
      `${{currentLang === 'zh' ? '实际政策利率' : 'Actual Policy Rate'}}: <strong>${{formatVal(d.actual_rate, 2)}}%</strong><br>` +
      `${{currentLang === 'zh' ? '泰勒中性推算' : 'Taylor Implied'}}: ${{formatVal(d.taylor_rate, 2)}}%<br>` +
      `${{currentLang === 'zh' ? '政策偏离度' : 'Stance Gap'}}: <strong>${{d.policy_gap >= 0 ? '+' : ''}}${{formatVal(d.policy_gap, 2)}}%</strong>`;
    tip.style.left = Math.min(w - 190, best.px + 12) + 'px';
    tip.style.top = Math.max(8, best.py - 32) + 'px';
    tip.style.display = 'block';
  }};
  canvas.onmouseleave = () => {{ tip.style.display = 'none'; }};
}}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {{
  initPolicyCycleLwChart();
  initRealRateChart();
  initTaylorChart();
}});
window.addEventListener('resize', () => {{
  if (document.getElementById('tab-realrate')?.classList.contains('active')) {{
    resizePolicyCycleLw();
    initRealRateChart();
    initTaylorChart();
  }}
}});
</script>
</body>
</html>
"""


def build() -> Path:
    """Compile and write policy_tracker.html in both output/ and root directories."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    html_content = build_policy_tracker_html()
    clean_html = "\n".join(line.rstrip() for line in html_content.splitlines()) + "\n"

    out_file = OUTPUT / "policy_tracker.html"
    out_file.write_text(clean_html, encoding="utf-8")
    print(f"Wrote {out_file} ({len(clean_html):,} bytes)")

    root_file = ROOT / "policy_tracker.html"
    root_file.write_text(clean_html, encoding="utf-8")
    print(f"Wrote {root_file} ({len(clean_html):,} bytes)")

    return out_file


if __name__ == "__main__":
    build()
