"""Plotly chart factory. All charts return a Plotly Figure with a source-attribution footer."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go

from .catalog import load_yaml
from .fetch import Series
from .transform import to_dataframe

_CFG = load_yaml("chart_templates.yaml")
DEF = _CFG["defaults"]
COLORS = _CFG["colors"]
FOOTER = _CFG["footer"]

def _footer_text(s: Series) -> str:
    footer = FOOTER["template"].format(
        source=s.source or "-",
        series_id=s.series_id or "-",
        last_update=s.last_update or "-",
        fetched=s.fetched or datetime.utcnow().strftime("%Y-%m-%d"),
    )
    status = getattr(s, "quality_status", "") or ""
    notes = getattr(s, "quality_notes", []) or []
    if status in {"watch", "low_confidence"} and notes:
        note = notes[0]
        footer += (
            "<br><span style='color:#8a593d'>Data note: "
            f"{note}</span>"
        )
    elif status == "verified":
        footer += " · Quality checked"
    elif status == "unavailable" and notes:
        footer += (
            "<br><span style='color:#9d3d2e'>Data unavailable: "
            f"{notes[0]}</span>"
        )
    return footer


def _apply_layout(fig: go.Figure, title: str, footer: str, ytitle: str = "") -> go.Figure:
    fig.update_layout(
        template=DEF["template"],
        title={"text": title, "x": 0.01, "xanchor": "left", "font": {"size": 14}},
        height=DEF["height"],
        margin=DEF["margin"],
        font={"family": DEF["font_family"], "size": DEF["font_size"]},
        hovermode=DEF["hovermode"],
        legend={"orientation": "h", "y": -0.18, "x": 0},
        yaxis={"title": ytitle, "gridcolor": "#eee", "automargin": True},
        xaxis={"gridcolor": "#eee", "autorange": True, "type": "date"},
        annotations=[{
            "text": footer,
            "xref": "paper", "yref": "paper",
            "x": 0, "y": -0.32,
            "xanchor": "left", "yanchor": "top",
            "showarrow": False,
            "font": {"size": FOOTER["font_size"], "color": FOOTER["color"]},
        }],
    )
    return fig


def _add_latest_marker(fig: go.Figure, df: pd.DataFrame, color: str,
                       value_fmt: str = "{:.1f}") -> None:
    """Mark the latest data point with a dot + value annotation in the top-right area."""
    if df.empty:
        return
    last_date = df.index[-1]
    last_val = float(df["value"].iloc[-1])
    fig.add_trace(go.Scatter(
        x=[last_date], y=[last_val],
        mode="markers", marker={"size": 9, "color": color,
                                "line": {"width": 1.5, "color": "white"}},
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_annotation(
        x=last_date, y=last_val,
        text=f"<b>{value_fmt.format(last_val)}</b><br>"
             f"<span style='font-size:9px;color:#666'>{last_date.strftime('%b %Y')}</span>",
        showarrow=True, arrowhead=0, ax=20, ay=-25,
        font={"size": 11, "color": color},
        bgcolor="rgba(255,255,255,0.85)", bordercolor=color, borderwidth=1,
        borderpad=3,
    )


def unavailable_chart(title: str, note: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=f"Data unavailable<br><span style='font-size:10px;color:#999'>{note}</span>",
                       xref="paper", yref="paper", x=0.5, y=0.5,
                       showarrow=False, font={"size": 13, "color": "#999"})
    fig.update_layout(template=DEF["template"], height=DEF["height"],
                      margin=DEF["margin"], title=title,
                      xaxis={"visible": False}, yaxis={"visible": False})
    return fig


def _val_fmt(unit: str) -> str:
    u = (unit or "").lower()
    if "index" in u and "%" not in u:
        return "{:,.1f}"
    if "usd" in u or "eur" in u or "bn" in u or "mn" in u:
        return "{:,.1f}"
    if "%" in u:
        return "{:+.1f}%"
    return "{:.2f}"


def line(s: Series, title: str | None = None, ytitle: str = "") -> go.Figure:
    if not s.available or not s.observations:
        return unavailable_chart(title or s.label, s.note or "no data")
    df = to_dataframe(s)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["value"], mode="lines",
                             name=s.country, line={"color": COLORS["primary"], "width": 2.2}))
    _add_latest_marker(fig, df, COLORS["primary"], _val_fmt(s.unit))
    return _apply_layout(fig, title or s.label, _footer_text(s), ytitle or s.unit)


def bar(s: Series, title: str | None = None, ytitle: str = "") -> go.Figure:
    if not s.available or not s.observations:
        return unavailable_chart(title or s.label, s.note or "no data")
    df = to_dataframe(s)
    colors = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in df["value"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df.index, y=df["value"], name=s.country, marker_color=colors))
    _add_latest_marker(fig, df,
                       COLORS["positive"] if df["value"].iloc[-1] >= 0 else COLORS["negative"],
                       _val_fmt(s.unit))
    return _apply_layout(fig, title or s.label, _footer_text(s), ytitle or s.unit)


def peer_overlay(primary: Series, peers: list[Series], title: str | None = None,
                 ytitle: str = "") -> go.Figure:
    if not primary.available or not primary.observations:
        return unavailable_chart(title or primary.label, primary.note or "no primary data")
    fig = go.Figure()
    palette = COLORS["peer_palette"]
    for i, p in enumerate(peers):
        if not p.available or not p.observations:
            continue
        dfp = to_dataframe(p)
        fig.add_trace(go.Scatter(x=dfp.index, y=dfp["value"], mode="lines",
                                 name=p.country,
                                 line={"color": palette[i % len(palette)], "width": 1.4, "dash": "dot"},
                                 opacity=0.85))
    df = to_dataframe(primary)
    fig.add_trace(go.Scatter(x=df.index, y=df["value"], mode="lines",
                             name=f"{primary.country} (primary)",
                             line={"color": COLORS["primary"], "width": 2.6}))
    _add_latest_marker(fig, df, COLORS["primary"], _val_fmt(primary.unit))
    footer = _footer_text(primary)
    if peers:
        peer_srcs = sorted({p.source for p in peers if p.available})
        if peer_srcs and not all(s == primary.source for s in peer_srcs):
            footer += " · Peers: " + ", ".join(peer_srcs)
    return _apply_layout(fig, title or primary.label, footer,
                         ytitle or primary.unit)


def pct_gdp_dual(pct_series: Series, abs_series: Series,
                 title: str | None = None, ytitle_pct: str = "% of GDP",
                 ytitle_abs: str = "") -> go.Figure:
    """Dual-axis chart: % of GDP (left, line) + absolute value (right, bars)."""
    if not pct_series.available or not pct_series.observations:
        return unavailable_chart(title or pct_series.label, pct_series.note or "no data")

    df_pct = to_dataframe(pct_series)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_pct.index, y=df_pct["value"], mode="lines+markers",
        name=f"{pct_series.country} % GDP",
        line={"color": COLORS["primary"], "width": 2.4},
        marker={"size": 6, "color": COLORS["primary"]},
        yaxis="y1",
    ))
    _add_latest_marker(fig, df_pct, COLORS["primary"], _val_fmt(pct_series.unit))

    if abs_series.available and abs_series.observations:
        df_abs = to_dataframe(abs_series)
        abs_color = COLORS["peer_palette"][2]
        fig.add_trace(go.Bar(
            x=df_abs.index, y=df_abs["value"],
            name=f"{abs_series.country} (abs)",
            marker_color=abs_color, opacity=0.55,
            yaxis="y2",
        ))
        abs_label = abs_series.unit or ytitle_abs
    else:
        abs_label = ""

    footer = _footer_text(pct_series)
    if abs_series.available:
        footer += " · Abs: " + _footer_text(abs_series)

    fig.update_layout(
        template=DEF["template"],
        title={"text": title or pct_series.label, "x": 0.01, "xanchor": "left", "font": {"size": 14}},
        height=DEF["height"],
        margin=DEF["margin"],
        font={"family": DEF["font_family"], "size": DEF["font_size"]},
        hovermode=DEF["hovermode"],
        legend={"orientation": "h", "y": -0.22, "x": 0},
        yaxis={"title": ytitle_pct, "gridcolor": "#eee", "automargin": True},
        yaxis2={"title": abs_label, "overlaying": "y", "side": "right",
                "showgrid": False, "automargin": True},
        xaxis={"gridcolor": "#eee", "autorange": True, "type": "date"},
        annotations=[{
            "text": footer,
            "xref": "paper", "yref": "paper",
            "x": 0, "y": -0.40,
            "xanchor": "left", "yanchor": "top",
            "showarrow": False,
            "font": {"size": FOOTER["font_size"], "color": FOOTER["color"]},
        }],
    )
    return fig


def with_target_band(fig: go.Figure, lo: float, hi: float, label: str = "Target band") -> go.Figure:
    fig.add_hrect(y0=lo, y1=hi, fillcolor=COLORS["band_fill"], line_width=0,
                  annotation_text=label, annotation_position="top left",
                  annotation={"font": {"size": 10, "color": COLORS["primary"]}})
    return fig


def trade_partner_bars(partners: list[tuple[str, float, float]], title: str,
                       value_label: str = "Trade Value, USD bn",
                       share_label: str = "Share of Total, %") -> go.Figure:
    """Horizontal bar chart for top trade partners with value + share bars."""
    if not partners:
        return unavailable_chart(title, "no trade partner data")
    names = [p[0] for p in partners][::-1]
    values = [p[1] for p in partners][::-1]
    shares = [p[2] for p in partners][::-1]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=values, y=names, orientation="h",
        name="Value (USD bn)",
        marker_color=COLORS["primary"], opacity=0.85,
        text=[f"${v:.1f}bn" for v in values],
        textposition="outside", textfont={"size": 11, "color": COLORS["primary"]},
        hovertemplate="%{y}: $%{x:.1f} bn<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[s * max(values) / max(shares) if max(shares) > 0 else 0 for s in shares],
        y=names, mode="markers+text",
        name="Share %",
        marker={"size": 8, "color": COLORS["secondary"]},
        text=[f"{s:.1f}%" for s in shares],
        textposition="middle right", textfont={"size": 10, "color": COLORS["secondary"]},
        xaxis="x2", hoverinfo="skip",
    ))

    fig.update_layout(
        template=DEF["template"],
        title={"text": title, "x": 0.01, "xanchor": "left", "font": {"size": 14}},
        height=max(320, len(partners) * 38),
        margin={"l": 100, "r": 60, "t": 50, "b": 50},
        font={"family": DEF["font_family"], "size": DEF["font_size"]},
        hovermode="y unified",
        legend={"orientation": "h", "y": -0.12, "x": 0},
        xaxis={"title": value_label, "gridcolor": "#eee", "side": "top"},
        xaxis2={"title": share_label, "overlaying": "x", "side": "bottom",
                "showgrid": False, "range": [0, max(shares) * 1.15 if shares else 100]},
        barmode="group",
    )
    return fig


def trade_product_bars(products: list[tuple[str, float]], title: str,
                       is_export: bool = True) -> go.Figure:
    """Horizontal bar chart for top traded products."""
    if not products:
        return unavailable_chart(title, "no product data")
    names = [p[0] for p in products][::-1]
    values = [p[1] for p in products][::-1]
    color = COLORS["positive"] if is_export else COLORS["negative"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=values, y=names, orientation="h",
        marker_color=color, opacity=0.85,
        text=[f"{v:.1f}%" for v in values],
        textposition="outside", textfont={"size": 11, "color": color},
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        template=DEF["template"],
        title={"text": title, "x": 0.01, "xanchor": "left", "font": {"size": 14}},
        height=max(280, len(products) * 36),
        margin={"l": 220, "r": 50, "t": 50, "b": 40},
        font={"family": DEF["font_family"], "size": DEF["font_size"]},
        hovermode="y unified",
        xaxis={"title": "% of Total", "gridcolor": "#eee", "side": "top"},
        showlegend=False,
    )
    return fig
