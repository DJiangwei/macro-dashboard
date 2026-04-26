"""Assemble Plotly figures + commentary into a single HTML file."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import __version__

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(TEMPLATES)),
                       autoescape=select_autoescape(["html"]))


def fig_to_html(fig: go.Figure, div_id: str) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id)


def _markdown_lite(text: str) -> str:
    """Tiny markdown: **bold** → <strong>, paragraphs preserved."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def render_dashboard(
    country_meta: dict,
    peers: list[str],
    snapshot_tiles: list[dict],
    sections_payload: list[dict],
    out_path: Path,
    trade_section: dict | None = None,
) -> Path:
    env = _env()
    tpl = env.get_template("dashboard.html.j2")
    for s in sections_payload:
        if s.get("commentary"):
            s["commentary"] = _markdown_lite(s["commentary"])
    html = tpl.render(
        country=country_meta,
        peers=peers,
        snapshot_title="§1 Country Snapshot",
        snapshot_blurb="Structural parameters and context: economic size, sovereign rating, FX regime, central-bank mandate, and qualitative country background a PM needs to size up the opportunity set.",
        snapshot_tiles=snapshot_tiles,
        geo_context=country_meta.get("geo_context", ""),
        political_context=country_meta.get("political_context", ""),
        societal_context=country_meta.get("societal_context", ""),
        sections=sections_payload,
        trade_section=trade_section,
        cb_section=country_meta.get("central_bank_section"),
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        version=__version__,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    return out_path
