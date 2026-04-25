"""Deterministic per-section macro commentary.

The structure follows the buy-side template: what the data shows → what's
driving it → what it means for positioning. Slot-filling is data-driven; if a
key indicator is missing, the section degrades to a shorter comment.
"""
from __future__ import annotations

import pandas as pd

from .fetch import Series
from .transform import latest_change, to_dataframe


def _fmt(v, pct: bool = False, dec: int = 1) -> str:
    if v is None:
        return "—"
    s = f"{v:+.{dec}f}" if pct else f"{v:.{dec}f}"
    return f"{s}%" if pct else s


def _direction(delta) -> str:
    if delta is None:
        return "broadly stable"
    if delta > 0.1:
        return "trending higher"
    if delta < -0.1:
        return "trending lower"
    return "broadly stable"


def comment_real_activity(country: str, series: dict[str, Series]) -> str:
    gdp = series.get("real_gdp_yoy")
    ip = series.get("industrial_production_yoy")
    un = series.get("unemployment_rate")
    parts: list[str] = []
    if gdp and gdp.available:
        lc = latest_change(to_dataframe(gdp))
        parts.append(f"Real GDP printed {_fmt(lc.get('value'), pct=True)} YoY in {lc.get('date','')[:7]}, "
                     f"{_direction(lc.get('delta'))} from the prior reading.")
    if ip and ip.available:
        lc = latest_change(to_dataframe(ip))
        parts.append(f"Industrial production at {_fmt(lc.get('value'), pct=True)} YoY signals the "
                     f"manufacturing pulse is {_direction(lc.get('delta'))}.")
    if un and un.available:
        lc = latest_change(to_dataframe(un))
        parts.append(f"Unemployment at {_fmt(lc.get('value'))}% — {_direction(lc.get('delta'))} — "
                     f"keeps wage-bargaining dynamics in focus.")
    if not parts:
        return f"Real-activity data for {country} is not available in the cache; refresh the prefetch step."
    parts.append("**Positioning:** the activity mix should anchor a view on the next central-bank step "
                 "and on the cyclicality of local equities.")
    return " ".join(parts)


def comment_prices_wages(country: str, series: dict[str, Series], target_band: tuple[float, float] | None) -> str:
    cpi = series.get("cpi_yoy")
    core = series.get("core_cpi_yoy")
    wage = series.get("avg_wage_yoy")
    parts: list[str] = []
    if cpi and cpi.available:
        lc = latest_change(to_dataframe(cpi))
        msg = f"Headline CPI at {_fmt(lc.get('value'), pct=True)} YoY ({lc.get('date','')[:7]})"
        if target_band:
            mid = sum(target_band) / 2
            gap = lc.get("value", 0) - mid
            msg += f", **{abs(gap):.1f}pp {'above' if gap > 0 else 'below'}** the target mid-point ({mid:.1f}%)"
        parts.append(msg + ".")
    if core and core.available:
        lc = latest_change(to_dataframe(core))
        parts.append(f"Core CPI at {_fmt(lc.get('value'), pct=True)} YoY shows the underlying-inflation "
                     f"trend is {_direction(lc.get('delta'))}.")
    if wage and wage.available:
        lc = latest_change(to_dataframe(wage))
        parts.append(f"Wage growth at {_fmt(lc.get('value'), pct=True)} YoY — second-round risks remain "
                     f"the swing factor for the policy path.")
    if not parts:
        return f"Price/wage data for {country} is not available in the cache."
    parts.append("**Positioning:** the gap between core inflation and the target band, and the "
                 "wage-CPI wedge, should drive the local-rates view.")
    return " ".join(parts)


def comment_external(country: str, series: dict[str, Series]) -> str:
    ca = series.get("current_account_pct_gdp")
    reer = series.get("reer")
    fx = series.get("fx_reserves")
    parts: list[str] = []
    if ca and ca.available:
        lc = latest_change(to_dataframe(ca))
        parts.append(f"Current account at {_fmt(lc.get('value'), pct=True)} of GDP "
                     f"({lc.get('date','')[:4]}) — {'surplus' if lc.get('value', 0) > 0 else 'deficit'}.")
    if reer and reer.available:
        lc = latest_change(to_dataframe(reer))
        parts.append(f"REER {_direction(lc.get('delta'))} (latest {_fmt(lc.get('value'))}); "
                     f"competitiveness pressure is the key implication.")
    if fx and fx.available:
        lc = latest_change(to_dataframe(fx))
        parts.append(f"FX reserves at {_fmt(lc.get('value'), dec=0)}; reserve adequacy backstops the "
                     f"FX regime.")
    if not parts:
        return f"External-sector data for {country} is not available in the cache."
    parts.append("**Positioning:** persistent CA dynamics + REER drift map directly to FX-spot fair value.")
    return " ".join(parts)


def comment_fiscal(country: str, series: dict[str, Series]) -> str:
    bal = series.get("fiscal_balance_pct_gdp")
    debt = series.get("gov_debt_pct_gdp")
    yld = series.get("sov_yield_10y")
    parts: list[str] = []
    if bal and bal.available:
        lc = latest_change(to_dataframe(bal))
        parts.append(f"Fiscal balance at {_fmt(lc.get('value'), pct=True)} of GDP ({lc.get('date','')[:4]}).")
    if debt and debt.available:
        lc = latest_change(to_dataframe(debt))
        parts.append(f"Gross debt at {_fmt(lc.get('value'))} % of GDP — {_direction(lc.get('delta'))}.")
    if yld and yld.available:
        lc = latest_change(to_dataframe(yld))
        parts.append(f"10-year sovereign yield at {_fmt(lc.get('value'))}%; the term-premium tells you "
                     f"how the market is pricing fiscal risk.")
    if not parts:
        return f"Fiscal/sovereign data for {country} is not available in the cache."
    parts.append("**Positioning:** twin-deficit dynamics + 10y level frame the long-end duration call.")
    return " ".join(parts)


def comment_monetary(country: str, series: dict[str, Series]) -> str:
    pol = series.get("policy_rate")
    cred = series.get("private_credit_yoy")
    fx = series.get("fx_vs_eur")
    parts: list[str] = []
    if pol and pol.available:
        lc = latest_change(to_dataframe(pol))
        parts.append(f"Policy rate at {_fmt(lc.get('value'))}%, {_direction(lc.get('delta'))}.")
    if cred and cred.available:
        lc = latest_change(to_dataframe(cred))
        parts.append(f"Private credit growth {_fmt(lc.get('value'), pct=True)} YoY signals the "
                     f"transmission channel is {_direction(lc.get('delta'))}.")
    if fx and fx.available:
        lc = latest_change(to_dataframe(fx))
        parts.append(f"EUR-cross at {_fmt(lc.get('value'), dec=2)} — {'weaker' if (lc.get('delta') or 0) > 0 else 'firmer'} "
                     f"local currency vs the prior print.")
    if not parts:
        return f"Monetary/financial data for {country} is not available in the cache."
    parts.append("**Positioning:** real policy rate + FX trend define the carry-vs-FX-risk balance.")
    return " ".join(parts)


def comment_markets(country: str, series: dict[str, Series]) -> str:
    eq = series.get("equity_index")
    eq_yoy = series.get("equity_yoy")
    parts: list[str] = []
    if eq and eq.available:
        lc = latest_change(to_dataframe(eq))
        parts.append(f"Headline equity index at {_fmt(lc.get('value'), dec=0)} ({lc.get('date','')[:7]}).")
    if eq_yoy and eq_yoy.available:
        df = to_dataframe(eq_yoy)
        if len(df) >= 13:
            yoy_val = (df["value"].iloc[-1] / df["value"].iloc[-13] - 1) * 100
            parts.append(f"YoY return {_fmt(yoy_val, pct=True)} — frames the local risk-asset beta.")
    if not parts:
        return f"Markets data for {country} is not available in the cache."
    parts.append("**Positioning:** combine with §6 monetary stance to assess if equities are pricing "
                 "the policy path correctly.")
    return " ".join(parts)


COMMENTERS = {
    "real_activity": comment_real_activity,
    "external": comment_external,
    "fiscal_sovereign": comment_fiscal,
    "monetary_financial": comment_monetary,
    "markets_valuation": comment_markets,
}
