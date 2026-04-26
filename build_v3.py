"""Build v3 preview HTML for HU, PL, CZ, RO — parametrized from base HTML with
country-specific narratives, KPI ribbon, snapshot prose, and country-switcher nav.

Usage:
  python build_v3.py HU    # Hungary only
  python build_v3.py PL    # Poland only
  python build_v3.py CZ    # Czechia only
  python build_v3.py RO    # Romania only
  python build_v3.py ALL   # all four
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).parent
OUTPUT = ROOT / "output"

# ── Shared CSS (same as Hungary v3) ──────────────────────────────────────────

CSS = """
:root {
  --bg: #f4f5f7;
  --fg: #1a1f36;
  --muted: #6b7280;
  --primary: #0f3b5e;
  --primary-light: #1a5680;
  --accent: #b8860b;
  --danger: #c62828;
  --success: #2e7d32;
  --border: #e2e4e9;
  --card: #ffffff;
  --card-alt: #f8f9fb;
  --highlight: #e8f0fe;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
  --radius: 8px;
  --radius-sm: 5px;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0;
  background: var(--bg); color: var(--fg);
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  font-size: 14px; line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
/* ---- Top Navigation Bar ---- */
.topbar {
  background: var(--primary);
  color: #fff;
  padding: 10px 32px;
  display: flex; align-items: center; justify-content: space-between;
  font-size: 12px; letter-spacing: 0.3px;
  position: sticky; top: 0; z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.topbar .brand { font-weight: 700; font-size: 15px; letter-spacing: -0.2px; }
.topbar .brand span { color: #ffd966; }
.topbar .meta-item { opacity: 0.85; margin-left: 20px; }
.topbar a { color: #ffd966; text-decoration: none; }
.topbar a:hover { text-decoration: underline; }
/* ---- Country Switcher ---- */
.country-nav { display: flex; gap: 4px; align-items: center; }
.country-nav .nav-link {
  color: rgba(255,255,255,0.7); text-decoration: none;
  padding: 4px 12px; border-radius: 4px; font-size: 12px;
  font-weight: 500; transition: all 0.15s;
  border: 1px solid rgba(255,255,255,0.2);
}
.country-nav .nav-link:hover {
  background: rgba(255,255,255,0.15); color: #fff;
  border-color: rgba(255,255,255,0.4);
}
.country-nav .nav-link.active {
  background: #ffd966; color: var(--primary); border-color: #ffd966;
  font-weight: 700;
}
.nav-separator { color: rgba(255,255,255,0.3); margin: 0 2px; }
.container { max-width: 1280px; margin: 0 auto; padding: 28px 24px 48px; }
header {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  border-radius: var(--radius);
  padding: 28px 32px; margin-bottom: 24px;
  color: #fff;
  box-shadow: var(--shadow-md);
}
header h1 {
  margin: 0; font-size: 26px; font-weight: 700; letter-spacing: -0.3px;
}
header .subtitle {
  font-size: 14px; opacity: 0.85; margin-top: 6px;
}
header .meta-row {
  display: flex; gap: 24px; margin-top: 14px; flex-wrap: wrap;
}
header .meta-chip {
  background: rgba(255,255,255,0.12); border-radius: 20px;
  padding: 4px 14px; font-size: 12px;
  backdrop-filter: blur(4px);
}
header .meta-chip strong { color: #ffd966; }
/* ---- KPI Ribbon ---- */
.kpi-ribbon {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 12px; margin-bottom: 24px;
}
.kpi-card {
  background: var(--card); border-radius: var(--radius);
  padding: 16px 20px;
  border-left: 4px solid var(--primary);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s;
}
.kpi-card:hover { box-shadow: var(--shadow-md); }
.kpi-card.warn { border-left-color: var(--accent); }
.kpi-card.danger { border-left-color: var(--danger); }
.kpi-card .kpi-label {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px;
  color: var(--muted); margin-bottom: 4px;
}
.kpi-card .kpi-value { font-size: 22px; font-weight: 700; color: var(--fg); }
.kpi-card .kpi-sub {
  font-size: 11px; color: var(--muted); margin-top: 2px;
}
.kpi-delta-up { color: var(--success) !important; font-weight: 600; }
.kpi-delta-down { color: var(--danger) !important; font-weight: 600; }
/* ---- Snapshot ---- */
.snapshot-panel {
  background: var(--card); border-radius: var(--radius);
  padding: 20px 24px; margin-bottom: 24px;
  box-shadow: var(--shadow-sm); border: 1px solid var(--border);
}
.snapshot-panel h2 {
  margin: 0 0 4px 0; font-size: 17px; color: var(--primary); font-weight: 600;
}
.snapshot-panel .blurb { color: var(--muted); font-size: 12.5px; margin-bottom: 20px; }
.snapshot-prose {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}
.snapshot-subsection {
  background: var(--card-alt); border-radius: var(--radius-sm);
  padding: 18px 20px; border: 1px solid var(--border);
}
.snapshot-subsection h3 {
  margin: 0 0 10px 0; font-size: 13px; color: var(--primary);
  font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase;
  border-bottom: 1px solid var(--border); padding-bottom: 8px;
}
.snapshot-subsection p {
  margin: 0; font-size: 13px; line-height: 1.7; color: var(--fg);
}
.snapshot-subsection strong {
  color: var(--primary); font-weight: 600;
}
/* ---- Section Panels ---- */
section.panel {
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 24px 28px; margin-bottom: 24px;
  box-shadow: var(--shadow-sm);
}
section.panel h2 {
  margin: 0 0 4px 0; font-size: 18px; color: var(--primary);
  font-weight: 600; letter-spacing: -0.2px;
  display: flex; align-items: center; gap: 10px;
}
section.panel h2 .section-badge {
  font-size: 11px; background: var(--highlight); color: var(--primary);
  padding: 2px 10px; border-radius: 12px; font-weight: 500;
  letter-spacing: 0.3px;
}
section.panel .blurb { color: var(--muted); font-size: 13px; margin-bottom: 20px; }
/* ---- Charts Grid ---- */
.charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(540px, 1fr));
  gap: 16px; margin-bottom: 20px;
}
.chart-cell {
  min-height: 400px; height: 400px;
  border: 1px solid var(--border); border-radius: var(--radius-sm);
  background: #fff; overflow: hidden;
  transition: box-shadow 0.2s;
}
.chart-cell:hover { box-shadow: 0 2px 10px rgba(0,0,0,0.06); }
.chart-cell .plotly-graph-div { height: 100% !important; }
/* ---- Narrative Commentary ---- */
.narrative {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  margin-top: 20px;
}
.narrative-header {
  background: var(--primary);
  color: #fff;
  padding: 10px 18px;
  display: flex; align-items: center; justify-content: space-between;
  font-size: 12px;
}
.narrative-label { font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; }
.narrative-date { opacity: 0.75; }
.narrative-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px; padding: 20px 24px;
  background: var(--card-alt);
}
.narrative-col h4 {
  margin: 0 0 10px 0; font-size: 13.5px; color: var(--primary);
  font-weight: 600; border-bottom: 1px solid var(--border);
  padding-bottom: 6px;
}
.narrative-col p { margin: 0 0 10px 0; font-size: 13px; color: var(--fg); line-height: 1.65; }
.narrative-col li {
  font-size: 13px; margin-bottom: 8px; color: var(--fg); line-height: 1.55;
  padding-left: 2px;
}
.narrative-col ul { margin: 0; padding-left: 18px; }
.narrative-footer {
  background: var(--highlight);
  padding: 14px 24px;
  font-size: 13px; color: var(--primary);
  border-top: 1px solid var(--border);
  line-height: 1.6;
}
.narrative-footer strong { color: var(--primary); }
/* ---- TOC ---- */
.toc {
  display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 24px;
}
.toc a {
  background: var(--card); border: 1px solid var(--border);
  color: var(--primary); text-decoration: none;
  padding: 6px 14px; border-radius: 20px; font-size: 12.5px;
  font-weight: 500; transition: all 0.15s;
}
.toc a:hover {
  background: var(--primary); color: #fff; border-color: var(--primary);
}
/* ---- Footer ---- */
footer {
  margin-top: 36px; padding: 32px 0 16px;
  border-top: 1px solid var(--border); text-align: center;
}
footer .disclaimer {
  color: var(--muted); font-size: 11px; max-width: 700px;
  margin: 12px auto 0; line-height: 1.55;
}
footer .attribution { color: var(--muted); font-size: 11px; }
/* ---- Context & Trade Cards ---- */
.context-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 14px; margin-top: 18px;
}
.context-card {
  background: var(--card-alt); border: 1px solid var(--border);
  border-radius: var(--radius-sm); overflow: hidden;
}
.context-card-header {
  background: var(--primary); color: #fff; padding: 8px 14px;
  font-size: 12px; font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase;
}
.context-card-body {
  padding: 12px 14px; font-size: 13px; line-height: 1.65; color: var(--fg);
  white-space: pre-line;
}
.trade-card-body table {
  width: 100%; border-collapse: collapse; font-size: 12px;
}
.trade-card-body th {
  text-align: left; padding: 4px 6px; border-bottom: 1px solid var(--border);
  color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: 0.3px;
}
.trade-card-body td { padding: 4px 6px; border-bottom: 1px solid #f0f1f3; }
.tile { background: var(--card-alt); border: 1px solid var(--border);
  border-radius: 4px; padding: 12px 16px; }
.tile .k { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }
.tile .v { font-size: 16px; font-weight: 600; margin-top: 2px; color: var(--fg); }
/* ---- Responsive ---- */
@media (max-width: 900px) {
  .narrative-body { grid-template-columns: 1fr; }
  .charts { grid-template-columns: 1fr; }
  .kpi-ribbon { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .kpi-ribbon { grid-template-columns: 1fr; }
  header .meta-row { flex-direction: column; gap: 6px; }
}
"""

# ── Section config (shared across countries) ─────────────────────────────────

SECTION_CHART_MAP = {
    "real_activity": [
        "chart-real_activity-real_gdp_yoy-1",
        "chart-real_activity-industrial_production_yoy-2",
        "chart-real_activity-retail_sales_yoy-3",
        "chart-real_activity-unemployment_rate-4",
    ],
    "prices_wages": [
        "chart-prices_wages-cpi_yoy-5",
        "chart-prices_wages-core_cpi_yoy-6",
        "chart-prices_wages-ppi_yoy-7",
        "chart-prices_wages-avg_wage_yoy-8",
    ],
    "external": [
        "chart-external-current_account_pct_gdp-9",
        "chart-external-trade_balance-10",
        "chart-external-fx_reserves-11",
        "chart-external-reer-12",
    ],
    "fiscal_sovereign": [
        "chart-fiscal_sovereign-fiscal_balance_pct_gdp-13",
        "chart-fiscal_sovereign-gov_debt_pct_gdp-14",
        "chart-fiscal_sovereign-sov_yield_10y-15",
    ],
    "monetary_financial": [
        "chart-monetary_financial-policy_rate-16",
        "chart-monetary_financial-m3_yoy-17",
        "chart-monetary_financial-private_credit_yoy-18",
        "chart-monetary_financial-fx_vs_eur-19",
    ],
    "markets_valuation": [
        "chart-markets_valuation-equity_index-20",
        "chart-markets_valuation-equity_yoy-21",
    ],
}

SECTION_TITLES = {
    "real_activity": ("§2 Real Activity", "coincident"),
    "prices_wages": ("§3 Prices & Wages", "forward-looking"),
    "external": ("§4 External Sector", "structural"),
    "fiscal_sovereign": ("§5 Fiscal & Sovereign", "risk factor"),
    "monetary_financial": ("§6 Monetary & Financial", "policy anchor"),
    "markets_valuation": ("§7 Markets & Valuation", "price signal"),
}

SECTION_BLURBS = {
    "real_activity": "Growth decomposition: GDP, industrial production, retail sales, and labour market — separating cyclical momentum from structural drags and identifying the dominant growth engine.",
    "prices_wages": "Inflation dynamics: headline and core CPI trends, producer price pipeline, and the wage-growth impulse that will determine the central bank's terminal rate.",
    "external": "Balance of payments: current account trajectory, trade balance, FX reserve adequacy, and real exchange rate misalignment vs fair value.",
    "fiscal_sovereign": "Sovereign creditworthiness: fiscal balance path, debt stock dynamics, and the term premium the market demands for bearing duration risk.",
    "monetary_financial": "Policy stance: the base rate relative to Taylor-implied neutral, credit transmission channels, and the FX fair-value anchor.",
    "markets_valuation": "Equity valuation: headline index level and momentum, relative to CEE peers and to the macro fundamentals mapped in sections 2–6.",
}

SECTION_ORDER = ["real_activity", "prices_wages", "external", "fiscal_sovereign", "monetary_financial", "markets_valuation"]

# ── Country-specific data ────────────────────────────────────────────────────

COUNTRY_DATA = {}


# ═══ HUNGARY ═══
COUNTRY_DATA["HU"] = {
    "code": "HU",
    "name": "Hungary",
    "iso": "HUF",
    "cb": "MNB",
    "gen_date": "2026-04-26",
    "peers": "PL, CZ, RO",
    "rating": "BBB− / Baa3 / BBB",
    "fxregime": "Free Float",
    "inftarget": "3.0% ±1pp CPI",
    "equity_index": "BUX",
    "subtitle": "Comprehensive country primer with macro narratives and forward-looking positioning views",
    "kpi_html": """<!-- KPI Ribbon -->
<div class="kpi-ribbon">
  <div class="kpi-card">
    <div class="kpi-label">Real GDP (YoY)</div>
    <div class="kpi-value">+0.5%</div>
    <div class="kpi-sub"><span class="kpi-delta-down">Decelerating</span> · Q4 2025</div>
  </div>
  <div class="kpi-card warn">
    <div class="kpi-label">Headline CPI (YoY)</div>
    <div class="kpi-value">3.3%</div>
    <div class="kpi-sub">Above 3.0% target midpoint · Dec 2025</div>
  </div>
  <div class="kpi-card danger">
    <div class="kpi-label">Fiscal Balance</div>
    <div class="kpi-value">−4.7%</div>
    <div class="kpi-sub"><span class="kpi-delta-down">of GDP</span> · 2025</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Current Account</div>
    <div class="kpi-value">+1.3%</div>
    <div class="kpi-sub"><span class="kpi-delta-up">Surplus</span> · of GDP 2025</div>
  </div>
  <div class="kpi-card warn">
    <div class="kpi-label">Policy Rate</div>
    <div class="kpi-value">6.25%</div>
    <div class="kpi-sub">Real rate ~300bp · MNB on hold</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">10Y HGB Yield</div>
    <div class="kpi-value">7.10%</div>
    <div class="kpi-sub">~250bp over CEE peers · Apr 2026</div>
  </div>
</div>""",
    "snapshot_prose": """    <div class="snapshot-subsection">
      <h3>Economy</h3>
      <p>Hungary is a <strong>$215 bn economy</strong> (2024 nominal GDP) with a population of <strong>9.6 million</strong> and GDP per capita of <strong>$22,400</strong>. The industrial base is concentrated in <strong>automotive &amp; EV batteries, electronics &amp; ICT, pharmaceuticals, food processing, and business services</strong>. Top trading partners are <strong>Germany, Austria, China, Italy, and Romania</strong> — reflecting deep integration into German-speaking supply chains alongside growing Asian linkages.</p>
    </div>

    <div class="snapshot-subsection">
      <h3>Institutional Framework</h3>
      <p>The <strong>Magyar Nemzeti Bank (MNB)</strong> operates a <strong>free float</strong> FX regime with a formal inflation target of <strong>3.0% &plusmn;1pp</strong>. Hungary is an EU and NATO member (since 2004) but <strong>not a euro-area member</strong> — the HUF floats independently and monetary policy is set domestically. The sovereign carries a <strong>BBB&minus; (S&amp;P) / Baa3 (Moody&rsquo;s) / BBB (Fitch)</strong> rating — one notch above high yield, with a negative outlook risk if fiscal consolidation stalls.</p>
    </div>

    <div class="snapshot-subsection">
      <h3>Market Access</h3>
      <p>The benchmark <strong>BUX equity index</strong> (OTP Bank ~25% weight, ~&euro;14bn market cap) trades at a forward P/E of ~7.2x — a <strong>30–40% discount</strong> to CEE peers (WIG20 ~10.5x, PX ~12.0x) reflecting the political risk premium. The <strong>10-year HGB yields ~7.1%</strong>, offering the highest EUR-denominated carry in the EU but with a ~250bp spread over CEE peers that signals the market&rsquo;s fiscal credibility concern. The <strong>EURHUF at ~365</strong> (April 2026) is roughly in line with REER-based fair value estimates of 360–370.</p>
    </div>""",
    "narratives": {
        "real_activity": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">Q1 2026 assessment</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Hungary's economy is <strong>stuck in a low-growth equilibrium</strong>. Real GDP printed just +0.5% YoY
      in Q4 2025, a sharp deceleration from the 1.5%+ pace of early 2024. The culprit is not domestic demand —
      real wages are growing at 6%+ as inflation normalises — but <strong>external demand</strong>. Germany, which
      absorbs ~27% of Hungarian exports, has been flatlining for six quarters. Industrial production at −1.4% YoY
      confirms the manufacturing recession, concentrated in the automotive supply chain (batteries, ICE powertrains).
      The unemployment rate has drifted up to 4.8% from a trough of 3.8%, though this partly reflects rising
      participation, not outright job destruction.</p>
      <p>Retail sales tell a more constructive story — volumes are positive, driven by real wage gains. The economy
      is <strong>bifurcated</strong>: an export-manufacturing sector in recession alongside a domestic services sector
      still growing at trend.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>EU funds release</strong> — the Tisza government's ability to unlock the €20bn+ in suspended
        RRF and cohesion funds is the single largest catalyst. Expect a political agreement in H2 2026, but
        disbursement won't hit the real economy until 2027.</li>
        <li><strong>German IP cycle</strong> — watch IFO expectations and German PMI new orders. Hungary's
        manufacturing PMI has been sub-50 for 18 of the last 21 months; a German recovery is the necessary
        condition for a turn.</li>
        <li><strong>Fiscal impulse</strong> — the 2026 budget implies a widening deficit ahead of the election
        cycle. The risk is a pro-cyclical fiscal expansion just as the output gap closes, forcing MNB to keep
        rates higher for longer.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The growth mix favours domestic-facing equities (banks, telcos) over
    exporters (auto suppliers, manufacturers). In rates, the weak growth print argues for eventual MNB cuts,
    but sticky services CPI and fiscal risk keep the front-end elevated. The HUF is caught between CA surplus
    support and EU-funds uncertainty — range-bound with a dovish tilt if funds materialise.
  </div>
</div>""",
        "prices_wages": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Hungary's disinflation has been <strong>the CEE region's standout success</strong> — headline CPI collapsed
      from 25.7% in Q1 2023 to 3.3% by end-2025, now just 0.3pp above the MNB's 3.0% target midpoint and well
      within the ±1pp tolerance band. The drivers were mechanical: energy base effects, administered price
      normalisation, and a 450bp demand compression from the 2022−23 rate shock.</p>
      <p>But the composition matters. <strong>Core CPI at 1.4%</strong> signals genuine underlying disinflation —
      goods prices are flat or falling, and even services inflation is moderating. PPI has been in deflation for
      12+ months, pointing to a further CPI grind lower over H1 2026. The uncomfortable number is
      <strong>wage growth at 9.3% YoY</strong>. While real wages are only recovering ground lost in 2022−23,
      the pace sits ~4pp above the sum of productivity growth (trend ~1.5%) and the inflation target (3.0%).
      This is the textbook definition of second-round risk that keeps MNB hawks awake.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Wage-CPI wedge</strong> — the 9.3% YoY wage print vs 3.3% CPI means real wages are rising
        ~6%. If this persists through the 2026 wage round (January−March settlements), services inflation will
        re-accelerate by H2. This is the MNB's stated red line.</li>
        <li><strong>Administered price adjustments</strong> — the Tisza government has signalled utility price
        reforms. If electricity/gas caps are lifted mid-2026, expect a one-off 1.5−2.0pp bump to headline.</li>
        <li><strong>Forint passthrough</strong> — EURHUF at 365 is 8% weaker than the 2024 average of ~395.
        A further 5% depreciation would add ~0.6pp to CPI within two quarters via the import channel.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The disinflation trend buys MNB room to cut, but wage stickiness
    caps the cutting cycle at ~5.00−5.25% (from 6.25% currently). The front end of the HGB curve is pricing
    ~75bp of cuts over 12 months — roughly fair. The tail risk is that wage data forces MNB to hold at 6.25%
    through year-end, which would trigger a front-end rates rally as cuts get priced out. Receive 2y HGB
    vs pay 2y Bund expresses this view cleanly.
  </div>
</div>""",
        "external": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Hungary's external position is <strong>structurally improving but underappreciated</strong>. The current
      account swung from a −8.1% GDP deficit at the energy-price peak (2022) to a +1.3% surplus in 2025 — a
      ~9pp adjustment in three years. The drivers: energy import bill normalisation (gas prices down ~70% from
      the panic), auto exports ramping (new BMW/EV battery capacity), and domestic demand compression during
      the inflation shock.</p>
      <p>The REER has been depreciating gently (latest ~114, down from ~120 in 2023), restoring competitiveness
      lost during the 2021−22 inflation overshoot. But the EURHUF has been volatile — from ~380 in mid-2024
      to ~412 during the Q4 risk-off, then back to ~365 as EU fund optimism built. FX reserves at ~€46bn cover
      4.5 months of imports, adequate but not generous by CEE standards (Czechia holds ~€140bn for a similar
      import base).</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>EU transfers</strong> — the 2021−27 RRF + Cohesion envelope for Hungary is ~€36bn, of which
        only ~€5bn has arrived. Each €5bn tranche released adds ~0.8% of GDP to the financial account and tends
        to strengthen HUF by 2−3%.</li>
        <li><strong>Energy terms of trade</strong> — Hungary's gas storage is at 65% (vs 80% EU average). A cold
        Q4 2026 winter or Russia-Ukraine transit disruption would widen the import bill. The LNG terminal in
        Krk (Croatia) provides partial diversification but at a premium.</li>
        <li><strong>Tourism recovery</strong> — 2025 tourism receipts hit a record, contributing ~2% of GDP.
        Budapest remains underpriced vs Prague/Vienna on a quality-adjusted basis; further growth is likely.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The CA surplus provides a structural HUF bid that was absent in
    2021−23. EURHUF fair value on a FEER/REER basis is probably 360−370 — not far from spot. The tail event:
    a comprehensive EU funds deal unlocks a move to 340−350. The risk event: no deal + energy shock pushes
    EURHUF back to 400+. Position for HUF strength via 6m EURHUF put spreads (360/345) funded by selling
    410 calls — asymmetric payoff to the EU funds catalyst.
  </div>
</div>""",
        "fiscal_sovereign": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Hungary's fiscal position is <strong>the primary macro vulnerability</strong>. The 2025 deficit printed
      at −4.7% of GDP, well above the 3.9% target and above the 3% Maastricht reference. This marks the 5th
      consecutive year above 4%. The overshoot was driven by: pre-election spending (family benefits, pension
      13th-month payments), energy subsidies, and rising interest costs as the stock of HGB debt reprices.</p>
      <p>Gross debt at 74.6% of GDP is trending higher and sits ~20pp above the CEE peer average (CZ ~43%, RO
      ~49%). The interest bill is now ~4.5% of GDP — the highest in the EU — with an average maturity of only
      ~4.5 years, meaning fiscal accounts are highly sensitive to the MNB rate path. The 10y HGB yield at 7.1%
      includes a ~250bp spread over the CEE average, reflecting the market's fiscal credibility discount.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Tisza fiscal plan</strong> — this is the known unknown. The new government inherits a
        structural deficit and will need to choose between consolidation (IMF/WB advice) and expansion
        (political temptation post-election). The 2026 budget is due by June; the deficit target will be
        the first test of market credibility.</li>
        <li><strong>Rating trajectory</strong> — all three agencies have Hungary at BBB-/Baa3, one notch
        above junk. Moody's next review is September 2026. A negative outlook from any agency would trigger
        forced selling from IG-only mandates (~$3−5bn of HGB outflows).</li>
        <li><strong>Debt composition</strong> — ~25% of HGB stock is FX-denominated, mostly EUR. HUF
        depreciation directly increases the debt/GDP ratio via the revaluation channel. This is the
        self-reinforcing mechanism that makes HUF a crisis currency in risk-off episodes.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The 250bp HGB spread over CEE peers compensates for genuine fiscal
    risk, but at 7.1% the 10y offers the highest carry in the EU. The trade: long 10y HGB vs pay 10y Bund
    (350bp spread) works if EU funds unlock and Tisza delivers a credible consolidation plan. But size the
    position for a potential Moody's downgrade — the tail is a move to 8.5−9.0% in a risk-off. Stop on a
    spread widening through 400bp.
  </div>
</div>""",
        "monetary_financial": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The MNB delivered one of the most aggressive tightening cycles in EM history (6.0% → 18.0% in 2022),
      followed by a cautious easing cycle that brought the base rate to <strong>6.25% by early 2026</strong>.
      The real policy rate — deflated by headline CPI — is ~300bp, among the highest in the EM universe. By
      any Taylor-rule estimate, policy is restrictive.</p>
      <p>The transmission mechanism is working: private credit growth is anaemic at +1.2% YoY (negative in real
      terms), M3 growth is subdued, and the housing market has cooled. But the MNB has paused the cutting cycle
      since January 2026, explicitly citing wage data and HUF stability as the binding constraints. The minutes
      show a 5−4 split on the last hold decision, with the minority favouring a 25bp cut. The EURHUF at ~365
      is ~8% firmer than the 2024 average, giving the MNB room to cut without triggering HUF weakness — but
      they are being deliberately cautious to preserve credibility after losing it in 2021−22.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>MNB May meeting (22 May)</strong> — the market prices a ~60% probability of a 25bp cut.
        The decision hinges on the March wage print (due 21 May). A wage print below 8.5% likely triggers a
        cut; above 9.5% means an extended hold.</li>
        <li><strong>Forward guidance evolution</strong> — MNB dropped the "patient, cautious" language in
        February. If the May statement shifts to "data-dependent easing," expect the market to price an
        additional 50bp of cuts into the H2 strip within 48 hours.</li>
        <li><strong>NBH vs NBP vs CNB</strong> — NBP is on hold at 5.75%, CNB at 4.00%. The MNB-NBP spread
        at 50bp is tight by historical standards; if NBP cuts first (July), the HUF/PLN cross could widen 3−5%
        as carry compression bites.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> HUF carry trade (long HUF vs EUR or CHF) earns ~300bp annualised at
    current rates — attractive in a world of converging DM rates. But the trade is politically fragile: any
    EU funds setback or rating downgrade triggers 5−8% HUF depreciation that wipes out a year of carry in
    a week. Size carry positions accordingly. We prefer expressing the view through the front end: receive
    2y HGB FRA (FRA 6x12) to capture the cutting cycle without the HUF spot risk.
  </div>
</div>""",
        "markets_valuation": """<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The BUX at 41,610 (−2.9% YoY) is <strong>underperforming CEE peers</strong> (WIG20 +5.4%, PX +3.1%)
      and broader EM equities (MSCI EM +6.2%). The underperformance reflects a concentrated set of domestic
      headwinds: political transition uncertainty, EU fund impasse, and the HUF's volatility keeping foreign
      investors at bay. OTP Bank (~25% of BUX, ~€14bn market cap) is the bellwether — it trades at a P/B of
      ~0.9x and trailing P/E of ~6.5x, both at the low end of the 5-year range.</p>
      <p>The valuation case is not subtle: BUX forward P/E of ~7.2x compares to WIG20 at ~10.5x and PX at
      ~12.0x. The discount reflects a political risk premium of ~30−40%. If EU funds unlock, historical
      mean-reversion implies 25−35% upside for the BUX over 12−18 months. But the market has been waiting
      for this catalyst since 2022.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>OTP Bank Q1 earnings (16 May)</strong> — net interest margin trajectory is the key metric.
        If NIM compression slows (consensus: 3.85% vs 4.05% QoQ), it signals the rate cycle peak is
        translating to earnings stability. OTP also has substantial CIS exposure (Ukraine, Russia) that adds
        a geopolitical overlay few CEE banks carry.</li>
        <li><strong>EU funds catalyst</strong> — the binary event. An RRF tranche release adds ~1.2% of GDP
        to the investment pipeline within 3 quarters. The BUX historically rallies 5−8% in the month following
        a positive EU funds announcement.</li>
        <li><strong>Foreign ownership</strong> — foreign ownership of BUX free float has fallen from ~55%
        (2019) to ~35% (2026). When the catalyst arrives, the rebalancing flow into an under-owned,
        under-valued index would be explosive — thin liquidity amplifies moves in both directions.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The BUX is a high-convexity bet on Hungary's political economy
    normalising. We see three ways to express it: (1) long OTP Bank equity vs short WIG20 banks — captures
    the relative valuation gap while hedging CEE regional risk; (2) BUX December 2026 calls, strike 45,000 —
    cheap vol with a defined catalyst window; (3) for the cautious — long 10y HGB (carry) and wait for equity
    entry confirmation on the first EU tranche release. Position sizing: this is a 2−3% of NAV trade, not a
    10% conviction bet. The binary EU funds risk means sizing for the scenario where nothing happens for
    another 12 months.
  </div>
</div>""",
    },
}

# ═══ POLAND ═══
COUNTRY_DATA["PL"] = {
    "name": "Poland",
    "iso": "PLN",
    "cb": "NBP",
    "gen_date": "2026-04-26",
    "peers": "HU, CZ, RO",
    "rating": "A− / A2 / A−",
    "fxregime": "Free Float",
    "inftarget": "2.5% ±1pp CPI",
    "equity_index": "WIG20",
    "subtitle": "Comprehensive country primer with macro narratives and forward-looking positioning views",
    "kpi_html": """
  <div class="kpi-ribbon">
    <div class="kpi-card">
      <div class="kpi-label">Real GDP (YoY)</div>
      <div class="kpi-value">+2.8%</div>
      <div class="kpi-sub"><span class="kpi-delta-up">CEE leader</span> · Q4 2025</div>
    </div>
    <div class="kpi-card warn">
      <div class="kpi-label">Headline CPI (YoY)</div>
      <div class="kpi-value">4.5%</div>
      <div class="kpi-sub">Above 2.5% target · Dec 2025</div>
    </div>
    <div class="kpi-card warn">
      <div class="kpi-label">Fiscal Balance</div>
      <div class="kpi-value">−5.1%</div>
      <div class="kpi-sub"><span class="kpi-delta-down">of GDP</span> · 2025</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Current Account</div>
      <div class="kpi-value">+0.8%</div>
      <div class="kpi-sub"><span class="kpi-delta-up">Surplus</span> · of GDP 2025</div>
    </div>
    <div class="kpi-card warn">
      <div class="kpi-label">Policy Rate</div>
      <div class="kpi-value">5.75%</div>
      <div class="kpi-sub">Real rate ~1.25% · NBP on hold</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">10Y PLN Yield</div>
      <div class="kpi-value">5.90%</div>
      <div class="kpi-sub">~130bp over Bund · Apr 2026</div>
    </div>
  </div>""",
    "snapshot_prose": """
    <div class="snapshot-subsection">
      <h3>Economy</h3>
      <p>Poland is the <strong>largest CEE economy at $845 bn</strong> (2024 nominal GDP) with a population of <strong>36.8 million</strong> and GDP per capita of <strong>$23,000</strong>. It was the only EU economy to avoid recession during the 2008 GFC and again outperformed during COVID. The industrial base spans <strong>automotive parts &amp; assembly (Europe's largest auto-parts exporter), consumer electronics, IT services, food processing, and coal/energy</strong>. Top trading partners are <strong>Germany, Czechia, France, the UK, and the Netherlands</strong>. Poland benefits from a large internal market, diversified export structure, and a structurally tight labour market (unemployment &lt;4%) that supports domestic demand.</p>
    </div>
    <div class="snapshot-subsection">
      <h3>Institutional Framework</h3>
      <p>The <strong>Narodowy Bank Polski (NBP)</strong> operates a <strong>free float</strong> FX regime with a formal inflation target of <strong>2.5% &plusmn;1pp</strong>. Poland is an EU and NATO member since 2004 but <strong>not a euro-area member</strong> — the PLN floats independently. Sovereign credit rating stands at <strong>A&minus; (S&amp;P) / A2 (Moody&rsquo;s) / A&minus; (Fitch)</strong> — the strongest in CEE, reflecting Poland's diversified economy, manageable debt (~50% GDP), and large FX reserves (~€170bn). EU RRF funds (~€60bn) have been partially unlocked under the Tusk government.</p>
    </div>
    <div class="snapshot-subsection">
      <h3>Market Access</h3>
      <p>The benchmark <strong>WIG20 index</strong> trades at a forward P/E of ~10.5x — roughly in line with EM Europe peers. The <strong>10-year PLN government bond yields ~5.9%</strong>, offering ~130bp over Bunds — a tight spread that reflects Poland's rating advantage and deep local institutional base (pension funds, insurers). The <strong>EURPLN at ~4.30</strong> (April 2026) is close to the 5-year average. Poland has the deepest and most liquid capital markets in CEE — Warsaw Stock Exchange is the region's primary listing venue with ~€200bn market cap across all listed companies.</p>
    </div>""",
    "narratives": {
        "real_activity": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">Q1 2026 assessment</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Poland is the <strong>CEE growth outperformer</strong> — real GDP expanded ~2.8% YoY in 2025, roughly double the CEE-4 average. The growth model is uniquely balanced: <strong>domestic consumption</strong> (real wage growth of 4%+ with unemployment at a structural low of 2.9%), <strong>robust investment</strong> (EU-funds fuelled infrastructure and defence spending at 4%+ of GDP), and <strong>resilient exports</strong> despite the German manufacturing recession. Industrial production is running at +2.1% YoY — modest but positive, in contrast to the contraction seen in Hungary and Czechia.</p>
      <p>The secret sauce is <strong>economic scale and diversification</strong>. Poland's 37mn population provides a domestic demand buffer that smaller CEE economies lack. The services sector (IT outsourcing, shared services, logistics) has been growing at 5%+, absorbing labour shed from manufacturing. This multi-engine growth model is rare in CEE and is the structural reason Poland commands the region's highest sovereign rating.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>German spillovers</strong> — Poland is less exposed than Czechia or Hungary (exports to DE are ~27% of total vs 31% for CZ), but a prolonged German stagnation would eventually drag on manufacturing employment. Watch PMI new export orders.</li>
        <li><strong>Defence spending multiplier</strong> — Poland is spending ~4.2% of GDP on defence (NATO's highest share), with a large domestic procurement component. This is a sustained fiscal impulse that flows through construction, manufacturing, and technology sectors.</li>
        <li><strong>Labour supply constraint</strong> — with unemployment at 2.9%, the binding constraint on growth is not demand but labour supply. The Tusk government has liberalised work permits for non-EU migrants (mainly Ukraine, Belarus, India), but political sensitivity is rising.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Poland's growth premium over CEE peers (~150bp of GDP) justifies the tighter sovereign spread. Long PLN assets vs CZK or HUF on a growth-divergence thesis, but be mindful that Poland's larger fiscal deficit partially offsets the growth advantage in the rates space. We prefer expressing the growth view through equity (WIG20 banks + industrials) rather than rates.
  </div>
</div>""",
        "prices_wages": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Poland's inflation at <strong>4.5% CPI</strong> is the highest in CEE-4, stubbornly above the NBP's 2.5% target despite significant progress from the 18.4% peak in 2023. The stickiness comes from <strong>two domestic sources</strong>: (1) services inflation running at ~6.5% YoY, driven by wage passthrough in a labour-scarce economy, and (2) administered energy prices — the previous government's energy shield was partially unwound in H2 2025, adding ~1.5pp to headline. Core CPI ex-energy and food at 3.8% tells a more constructive story but remains above target.</p>
      <p>Wage growth at <strong>11.2% YoY</strong> is the region's highest in nominal terms. In real terms (~6.7%), it's fuelling consumption but keeping services inflation elevated. The NBP's own analysis suggests the NAIRU is around 3.5% — with unemployment at 2.9%, the economy is operating beyond full employment. This is a structural inflation impulse that rate cuts cannot address.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Energy price liberalisation</strong> — the Tusk government faces a choice: extend the energy shield (fiscally costly, ~1.5% GDP) or let it expire and accept a one-off CPI bump of ~1.0-1.5pp. The decision will determine whether CPI converges to ~3.5% or stays at ~5% through 2026.</li>
        <li><strong>Wage round Q1 2026</strong> — the January-March wage settlement season is critical. If the 2026 round lands above 9% (vs 11.2% in 2025), it signals moderation; if it accelerates, the NBP may need to hike.</li>
        <li><strong>NBP communication shift</strong> — Governor Glapiński has shifted from "rates on hold indefinitely" to "data dependent." The market is pricing a 25bp cut by Q4 2026. This is optimistic; we see the first cut in Q1 2027.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The NBP-NBH rate spread (5.75% vs 6.25%) is 50bp in Poland's favour but doesn't compensate for the inflation differential. Short PLN vs HUF in FX space — the NBP will be the last CEE central bank to cut, supporting PLN carry, but the sticky inflation means front-end rates have asymmetric upside risk. Consider receiving 2y PLN FRA vs paying 2y HUF.
  </div>
</div>""",
        "external": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Poland's external position is <strong>broadly balanced</strong> — the current account registered a small surplus of +0.8% GDP in 2025, a marked improvement from the -2.5% deficit in 2022. The improvement was driven by: (1) terms-of-trade recovery as energy import prices normalised, (2) strong services exports (IT, transport, shared services) running a ~+5% GDP surplus, and (3) EU transfer inflows (~3% GDP annually) that structurally support the current account.</p>
      <p>The REER has been relatively stable, appreciating only ~3% from the 2020 average — far less than CZK or HUF, reflecting the NBP's reluctance to allow PLN strength to erode export competitiveness. FX reserves at <strong>€170bn</strong> are the largest in CEE in absolute terms, covering ~7 months of imports — more than adequate by any metric. The NBP has also built a 420-tonne gold position (~13% of reserves), the largest in the region.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>EU fund inflows</strong> — the RRF disbursement schedule implies €12-15bn of inflows in 2026. Each €5bn tranche tends to strengthen PLN by 1-2%, other things equal. The cumulative flow could push EURPLN from 4.30 to 4.15.</li>
        <li><strong>Energy dependence</strong> — Poland still relies on coal for ~70% of electricity generation. The energy transition (offshore wind, nuclear, LNG import infrastructure) is capital-intensive and will require sustained equipment imports — a structural drag on the trade balance over the medium term.</li>
        <li><strong>Geopolitical risk premium</strong> — Poland's eastern-flank exposure means PLN carries a geopolitical risk premium that CZK and HUF do not. This premium compresses during risk-on and widens sharply during risk-off. The option-implied EURPLN vol is ~1.5x EURCZK vol.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The PLN is structurally undervalued on a FEER basis (fair value ~4.10-4.20 EURPLN). EU fund inflows and the NBP's hawkish hold provide a steady appreciation bias of 2-3% per annum. But the geopolitical risk premium means short PLN positions are dangerous in risk-off — this is a carry-and-convergence trade that requires patience and position discipline. 12m EURPLN forwards at 4.25 offer an attractive entry.
  </div>
</div>""",
        "fiscal_sovereign": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Poland's fiscal position is <strong>deteriorating from a position of relative strength</strong>. The 2025 general government deficit printed at -5.1% of GDP, the widest since the COVID year of 2020. The drivers: (1) defence spending at 4.2% of GDP (~PLN 160bn, up from 2.2% in 2021), (2) the energy price shield (~1.5% GDP cost), and (3) social transfers (expanded child benefit, 13th/14th pension payments). These are mostly permanent, not cyclical.</p>
      <p>However, gross debt at <strong>~50% of GDP</strong> is well below the EU average (~83%) and the Maastricht 60% threshold. The debt stock is predominantly PLN-denominated (~73%) with a stable domestic investor base (Polish pension funds and insurers hold ~55% of outstanding government bonds). The 10y yield at 5.9% represents a spread of only ~130bp over Bunds — the tightest in CEE — reflecting Poland's A- rating and the market's confidence in debt sustainability.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>EDP timeline</strong> — Poland is in the EU's Excessive Deficit Procedure (like most EU states post-COVID). The fiscal adjustment path required by Brussels is ~0.5% GDP per year. Meeting this while sustaining defence spending will require tax measures or spending cuts elsewhere — politically difficult in the pre-election period (presidential election 2025, parliamentary 2027).</li>
        <li><strong>Defence spending trajectory</strong> — the government has committed to maintaining defence spending above 3% of GDP through 2030. If funded through debt rather than revenue, this adds ~1-1.5pp to the deficit annually. The rating agencies are watching — a failure to consolidate outside defence could trigger a negative outlook.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Poland's tight sovereign spread is built on the rating advantage and the deep domestic bid for PLN government bonds. The risk is a slow-burn fiscal deterioration that erodes the rating buffer over 2-3 years. We're not at the point of shorting POLGBs — the domestic bid is too deep — but the spread compression trade (long POLGB vs Bund) has run its course. Neutral duration, with a bias to receive in 2y where NBP expectations are mispriced.
  </div>
</div>""",
        "monetary_financial": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The NBP hiked aggressively (0.1% → 6.75% in 2021-22) but has been <strong>the most reluctant CEE central bank to ease</strong>. The reference rate has been held at <strong>5.75%</strong> since October 2023, with only a token 25bp cut in September 2023 that was partially reversed. Governor Glapiński's rhetoric has been consistently hawkish, emphasising the inflation risks from fiscal expansion, wage growth, and energy price normalisation.</p>
      <p>With headline CPI at 4.5% and the reference rate at 5.75%, the <strong>ex-ante real rate is only ~1.25%</strong> — the lowest in CEE-4. This is not particularly restrictive by historical standards, which is why the NBP feels no urgency to cut. Private credit growth is healthy at +4.5% YoY, M3 growth is running at 7%, and the banking sector is well-capitalised (CAR ~19%). The transmission mechanism is functioning, but the economy is growing through the restrictive stance.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>First cut timing</strong> — the market prices a 25bp cut by Q4 2026. We see Q1 2027 as more realistic. The NBP wants to see CPI below 3.5% and wage growth below 8% before easing. Neither condition is likely met before end-2026.</li>
        <li><strong>NBP vs NBP (Poland vs Hungary)</strong> — Poland's NBP and Hungary's MNB are on diverging paths. MNB is closer to cutting (real rate ~300bp, growth weak). The NBP-MNB spread could widen from the current 50bp to 100bp+, supporting PLN vs HUF.</li>
        <li><strong>Glapiński succession</strong> — the Governor's term runs to 2028, but political pressure from the Tusk government is a background risk. Any move to curtail NBP independence (unlikely but not impossible) would trigger a sharp PLN sell-off.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The NBP's hawkish hold supports PLN carry trades. Long PLN vs EUR earns ~200bp annualised (5.75% vs 3.25% ECB depo) with an appreciation tailwind from EU funds. The position is crowded — BIS data shows speculative PLN positioning at the 70th percentile — but the fundamentals support it. Size for a 5% stop; the geopolitical risk premium can re-price violently.
  </div>
</div>""",
        "markets_valuation": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The <strong>WIG20 at ~2,450 (+5.4% YoY)</strong> is the best-performing CEE equity benchmark, driven by bank re-rating (PKO BP, Pekao, Santander BP — combined ~40% of index) and strong earnings from the IT/tech sector (CD Projekt, Allegro). The WIG20 forward P/E of ~10.5x is in line with the 10-year median but at a discount to DM Europe (~13x) — the discount reflects the geopolitical risk premium, not fundamentals.</p>
      <p>The structural story is Poland's deepening capital markets. The Warsaw Stock Exchange (GPW) has been the CEE region's primary equity venue, with total market cap of ~€200bn across the main and NewConnect markets. Foreign ownership of the free float is ~40% (down from ~55% in 2017), with domestic pension funds and retail investors filling the gap — a stabilising force in risk-off episodes. The banking sector is the earnings engine: Polish banks trade at ~1.3x P/B with ROE of ~14%.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Bank earnings peak?</strong> — NIM compression is beginning as the rate cycle turns. Q4 2025 NIM averaged 3.65%, down from 3.85% a year earlier. If the NBP cuts in H2 2026 (not our base case but the market's), bank earnings face a headwind. Defensive rotation into insurers (PZU) and utilities (PGE) would follow.</li>
        <li><strong>IPO pipeline</strong> — the Tusk government has signalled interest in listing minority stakes in state-owned enterprises. A successful IPO (e.g., PGE Renewables, PKP Cargo spin-off) would deepen the market and attract passive inflows.</li>
        <li><strong>Geopolitical discount</strong> — Poland's equity risk premium (ERP) is ~7.5%, roughly 200bp above DM Europe. If the security situation stabilises (NATO commitment credible, Ukraine ceasefire durable), 100bp of ERP compression implies ~12% index upside.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> WIG20 offers the best risk/reward in CEE equities. The combination of GDP growth leadership, deep capital markets, A- rating, and a diversified sector mix (banks, tech, energy, retail) makes Poland the core CEE equity allocation. Long WIG20 vs short BUX expresses the growth/fiscal divergence cleanly. December 2026 WIG20 calls at 2,600 strike offer cheap optionality on the ERP compression narrative.
  </div>
</div>""",
    },
}

# ═══ CZECHIA ═══
COUNTRY_DATA["CZ"] = {
    "name": "Czechia",
    "iso": "CZK",
    "cb": "CNB",
    "gen_date": "2026-04-26",
    "peers": "HU, PL, RO",
    "rating": "AA− / Aa3 / AA−",
    "fxregime": "Managed Float",
    "inftarget": "2.0% ±1pp CPI",
    "equity_index": "PX",
    "subtitle": "Comprehensive country primer with macro narratives and forward-looking positioning views",
    "kpi_html": """
  <div class="kpi-ribbon">
    <div class="kpi-card">
      <div class="kpi-label">Real GDP (YoY)</div>
      <div class="kpi-value">+1.1%</div>
      <div class="kpi-sub"><span class="kpi-delta-down">Below trend</span> · Q4 2025</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Headline CPI (YoY)</div>
      <div class="kpi-value">2.6%</div>
      <div class="kpi-sub">Within 2.0% ±1pp band · Dec 2025</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Fiscal Balance</div>
      <div class="kpi-value">−2.2%</div>
      <div class="kpi-sub"><span class="kpi-delta-up">Best in CEE-4</span> · 2025</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Current Account</div>
      <div class="kpi-value">+2.8%</div>
      <div class="kpi-sub"><span class="kpi-delta-up">Strong surplus</span> · of GDP 2025</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Policy Rate</div>
      <div class="kpi-value">4.00%</div>
      <div class="kpi-sub">Real rate ~1.4% · CNB cutting cycle</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">10Y CZK Yield</div>
      <div class="kpi-value">4.20%</div>
      <div class="kpi-sub">~40bp under PLN · Apr 2026</div>
    </div>
  </div>""",
    "snapshot_prose": """
    <div class="snapshot-subsection">
      <h3>Economy</h3>
      <p>Czechia is a <strong>$345 bn economy</strong> (2024 nominal GDP) with a population of <strong>10.9 million</strong> and the <strong>highest GDP per capita in CEE at $31,600</strong> (PPP-adjusted above Italy and Spain). The economy is the most manufacturing-intensive in the EU, centred on <strong>automotive OEM &amp; supply chain (&Scaron;koda/VW, Hyundai, Toyota), machinery &amp; precision engineering, electronics, and beer &amp; beverages</strong>. Top trading partners are <strong>Germany, Slovakia, Poland, France, and Austria</strong> — Czechia is the most deeply integrated into German supply chains of any CEE economy, making it a leveraged play on the German industrial cycle.</p>
    </div>
    <div class="snapshot-subsection">
      <h3>Institutional Framework</h3>
      <p>The <strong>&Ccaron;esk&aacute; n&aacute;rodn&iacute; banka (CNB)</strong> operates a <strong>managed float</strong> FX regime with a formal inflation target of <strong>2.0% &plusmn;1pp</strong>. Czechia is an EU and NATO member since 2004 but <strong>not a euro-area member</strong>. Sovereign credit rating stands at <strong>AA&minus; (S&amp;P) / Aa3 (Moody&rsquo;s) / AA&minus; (Fitch)</strong> — the highest in CEE, reflecting fiscal conservatism (debt ~43% GDP), a persistent current account surplus, and the deepest capital stock per capita in the region. The CNB is the most transparent CEE central bank, publishing its own interest-rate forecast path.</p>
    </div>
    <div class="snapshot-subsection">
      <h3>Market Access</h3>
      <p>The benchmark <strong>PX index</strong> (~1,600) trades at a forward P/E of ~12.0x — a premium to CEE peers reflecting Czechia's AA- rating. The PX is dominated by banks (Erste, Komer&ccaron;n&iacute; banka — ~45% weight) and utilities (&Ccaron;EZ — ~20% weight), giving it a defensive, dividend-heavy character. The <strong>10-year CZK government bond yields ~4.2%</strong> — below PLN and HGB yields, consistent with the rating hierarchy. The <strong>EURCZK at ~25.0</strong> (April 2026) is ~8% weaker than the pre-COVID average of ~25.5, reflecting the CNB's aggressive rate cuts and a terms-of-trade drag from energy imports.</p>
    </div>""",
    "narratives": {
        "real_activity": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">Q1 2026 assessment</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Czechia is <strong>stuck in a shallow-growth equilibrium</strong>. Real GDP expanded just +1.1% YoY in Q4 2025, the weakest in CEE-4. The economy is being dragged down by its own structural strength: <strong>manufacturing is ~25% of GDP</strong> (highest in the EU), and the German manufacturing recession has hit Czech industry disproportionately. Industrial production at -2.0% YoY reflects the auto supply chain — &Scaron;koda/VW alone represents ~5% of GDP and ~10% of exports. The order-book-to-shipment ratio is at its lowest since 2020.</p>
      <p>But the domestic economy is holding up better than the headline suggests. <strong>Unemployment at 2.6%</strong> (EU's lowest) means the labour market is a structural support — anyone who wants a job has one. Real wages are growing ~4% as inflation normalises, and household consumption contributed positively to GDP in every quarter of 2025. The problem is investment: corporates are deferring capex decisions amid German uncertainty and the CNB's cutting cycle has not yet translated into a credit recovery.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>German IFO cycle</strong> — Czechia's PMI has been sub-50 for 24 of the last 27 months. The single variable that matters is German manufacturing orders. A sustained IFO expectations recovery above 95 would be the signal to go long Czech assets.</li>
        <li><strong>&Scaron;koda EV transition</strong> — &Scaron;koda is investing €5.6bn in electrification (2024-28), with three new EV models launching in 2025-26. Success or failure of these launches will determine the trajectory of 10% of Czech exports over the next decade.</li>
        <li><strong>CNB easing transmission</strong> — the CNB has cut 300bp from the peak (7.0% → 4.0%) but private credit growth remains negative in real terms. The transmission lag suggests the growth impulse from easing hits in H2 2026 at the earliest.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Czechia is a high-beta play on the German industrial cycle. If Germany recovers, CZK and Czech equities outperform CEE peers by 5-8% within 6 months. If Germany flatlines, Czech assets underperform. We'd size a long CZK vs EUR position as a call option on German recovery — define the risk with a tight stop at EURCZK 25.50. In equities, long PX banks (Erste) vs short DAX auto represents a relative-value expression of the same theme with less directionality.
  </div>
</div>""",
        "prices_wages": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Czechia has achieved <strong>the softest landing in CEE</strong> on the inflation front. Headline CPI at <strong>2.6% YoY</strong> is within the CNB's 2.0% ±1pp tolerance band, down from a peak of 18.0% in early 2023. The disinflation was textbook: energy base effects accounted for ~70% of the decline, with the remaining 30% from genuine demand compression via the 2021-23 rate shock. Core CPI at 2.3% is the lowest in CEE.</p>
      <p>The CNB's early and aggressive cutting cycle (7.0% → 4.0% since December 2023) was predicated on this disinflation success. But wage growth at <strong>7.4% YoY</strong> in a 2.6% unemployment economy raises the question of whether the easing was premature. The CNB's own forecast sees CPI grinding to 2.0% by mid-2026, but the wage impulse and the closed output gap argue for inflation settling closer to 2.5-3.0% — within band but above target midpoint.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>CNB terminal rate debate</strong> — the market prices the terminal rate at 3.25% (75bp more cuts). The CNB staff forecast implies 3.50%. The risk is that the terminal rate lands at 3.75-4.00% — services inflation at 3.8% and 7%+ wages don't justify a sub-3.5% policy rate.</li>
        <li><strong>Housing market re-acceleration</strong> — Prague property prices, which fell ~10% during the rate-hiking cycle, have stabilised and are beginning to rise again as mortgage rates fall below 4.5%. A renewed housing boom would flow through to imputed rents (~10% of CPI basket) and keep core CPI elevated.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The CZK rates market is pricing too much easing — 75bp of cuts vs our forecast of 25-50bp. Receive 2y CZK FRAs vs pay 2y EUR to express the view that the CNB terminal rate is higher than priced. In FX, the CNB cutting cycle has weakened CZK from 24.0 to 25.0 — a lot of bad news is priced. If the cutting cycle ends sooner than expected, EURCZK could reprice to 24.50.
  </div>
</div>""",
        "external": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Czechia runs a <strong>persistent current account surplus</strong> — +2.8% of GDP in 2025, the largest in CEE-4. This is a structural feature: the manufacturing export engine (vehicles, machinery) generates a ~+8% GDP goods surplus, which more than offsets the income deficit (dividend and profit repatriation by foreign-owned firms). The trade surplus with Germany alone (~€15bn annually) is roughly 4% of Czech GDP.</p>
      <p>FX reserves at <strong>€140bn</strong> are the largest relative to GDP in the EU (~40% of GDP), a legacy of the 2013-17 EURCZK floor. The CNB has been running this massive reserve position at a negative carry (~200bp, funding short-CZK liabilities against long-EUR assets), generating mark-to-market volatility but providing an unassailable defence against CZK speculative attacks. The REER has depreciated ~5% from its 2023 peak, restoring competitiveness lost during the inflation overshoot.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Reserve divestment?</strong> — Governor Michl has signalled an intention to reduce the FX reserve stock gradually. Any CNB FX sales (EURCZK buying) would weaken CZK. But the practical scope is limited — the market would interpret aggressive sales as a policy error.</li>
        <li><strong>Auto export cycle</strong> — Czech auto exports are ~8% of GDP. A 10% decline in German car registrations translates to a ~0.8% GDP drag on Czechia. The EV transition adds structural uncertainty — the Czech supply chain is ICE-optimised.</li>
        <li><strong>Energy dependence</strong> — Czechia has largely weaned itself off Russian gas (LNG via Dutch/German terminals, Norwegian pipeline gas), but remains energy-import dependent. The terms-of-trade drag from the 2022-23 energy shock has largely reversed.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The CA surplus is a structural CZK bid, but it's offset by the CNB's dovish stance and the negative carry on the FX reserve position. CZK is not a clean carry trade. We prefer expressing Czech external strength through the sovereign credit (long CZGBs vs HGBs at a ~300bp spread pickup on a AA- vs BBB- basis). The CZK is a range trade: buy at 25.20, sell at 24.50.
  </div>
</div>""",
        "fiscal_sovereign": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Czechia is <strong>the fiscal champion of CEE</strong>. The 2025 general government deficit printed at just -2.2% of GDP, the narrowest in CEE-4 and below the 3% Maastricht reference. The SPOLU coalition government under PM Fiala has delivered on fiscal consolidation: the deficit has halved from -5.1% in 2021 through a combination of tax increases (corporate income tax, windfall tax on banks/energy) and spending restraint.</p>
      <p>Gross debt at <strong>~43% of GDP</strong> is the lowest in the EU and well below the Maastricht 60% threshold. The debt is predominantly CZK-denominated (~90%), with a stable domestic investor base. The 10y yield at 4.2% represents a spread of only ~40bp under Poland — remarkable given Czechia's two-notch rating advantage. The tight spread is partly technical: the CZGB market is smaller and less liquid than POLGBs, limiting foreign participation.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>ANO fiscal policy</strong> — if ANO wins the 2025 parliamentary election (polls suggest it's likely), fiscal policy could shift toward expansion. Babi&scaron;'s platform is light on detail but heavy on spending promises (pension hikes, infrastructure). Markets are not pricing this risk.</li>
        <li><strong>Defence spending ramp</strong> — Czechia has committed to 2% of GDP defence spending (NATO target), up from 1.3% in 2023. The incremental ~0.7% GDP cost is manageable from the current fiscal position but adds to the structural deficit.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> CZGBs at 4.2% offer the best risk-adjusted carry in CEE sovereign credit. The AA- rating, 43% debt/GDP, and persistent CA surplus make this the regional safe haven. Long 10y CZGBs vs 10y HGBs at a ~290bp spread — the rating differential (5 notches) vs the spread differential is not fully priced. The primary risk is an ANO-driven fiscal expansion; monitor election polls closely.
  </div>
</div>""",
        "monetary_financial": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The CNB has been <strong>the most aggressive cutter in CEE</strong>, bringing the policy rate from 7.0% to <strong>4.00%</strong> in a series of 50bp and 25bp steps since December 2023. The cutting cycle was data-dependent and well-communicated — the CNB's published forecast path (a transparency practice unique in CEE) guided market expectations effectively. The real policy rate at ~1.4% is approaching the CNB's estimate of neutral (roughly 3.0-3.5% nominal, or ~1.0% real).</p>
      <p>The transmission mechanism is working but with lags. Mortgage rates have fallen from ~6.5% to ~4.5%, driving a tentative housing market recovery. But <strong>private credit growth at +2.1% YoY</strong> remains anaemic — corporations are not borrowing because they're not investing, not because credit is expensive. The CNB faces the classic pushing-on-a-string problem: rate cuts can't force firms to invest when German demand is absent. M3 growth at 5.5% is healthy but not expansionary.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Terminal rate landing zone</strong> — CNB staff analysis puts the neutral rate at 3.0-3.5%. We think 3.75% is more realistic given the tight labour market and wage growth. The next 2-3 meetings (25bp cuts expected at each) will define the terminal rate debate.</li>
        <li><strong>FX passthrough risk</strong> — CZK has weakened from 24.0 to 25.0 during the cutting cycle. A further move to 25.50+ (from EURCZK buying by corporates, energy importers, or the CNB's reserve operations) would add ~0.3pp to CPI via import prices. This is a self-limiting mechanism on cuts.</li>
        <li><strong>CNB vs ECB</strong> — the CNB-ECB spread has compressed from 300bp to 75bp. If the CNB cuts further and the ECB holds, the carry attraction of CZK diminishes, potentially weakening CZK further.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The CNB cutting cycle is approaching its end. Front-end CZK rates are pricing 75bp more cuts; we see 25-50bp. Receive 2y CZK vs pay 2y EUR — the CNB will stop cutting before the market thinks, and the ECB will cut more than the market thinks. In FX, EURCZK at 25.0 is close to fair value on a rate-differential basis. Range trade with a hawkish CNB tilt.
  </div>
</div>""",
        "markets_valuation": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The <strong>PX index at ~1,600 (+3.1% YoY)</strong> has been a middling performer in CEE — better than BUX (-2.9%) but lagging WIG20 (+5.4%). The PX is a concentrated, defensive index: <strong>Erste Bank and Komer&ccaron;n&iacute; banka (~45% weight combined)</strong> and <strong>&Ccaron;EZ (~20% weight)</strong> dominate, giving the index a financials + utilities tilt with a ~5% dividend yield — the highest in CEE. The forward P/E of ~12.0x is a premium to WIG20 (~10.5x) and BUX (~7.2x), justified by the AA- sovereign rating and the earnings stability of the dominant constituents.</p>
      <p>The PX is effectively a <strong>bond proxy with an equity kicker</strong>. Erste and KB trade at P/B of ~1.2x and ~1.5x respectively, with ROEs of ~13-15% — these are well-run, profitable banks in a consolidated market. &Ccaron;EZ, the dominant utility, generates stable cash flows from nuclear and coal generation but faces a structural transition risk as carbon costs rise and renewable investment needs escalate.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Erste Bank CEE exposure</strong> — Erste generates ~50% of revenue outside Czechia (mainly Austria, Romania, Slovakia, Hungary). It's a diversified CEE financials play rather than a pure Czech bet. Watch the Romanian and Hungarian NIM trajectory.</li>
        <li><strong>&Ccaron;EZ nuclear tender</strong> — the government's plan to build a new nuclear reactor (Dukovany II, ~€7bn) is the largest infrastructure project in Czech history. &Ccaron;EZ is the designated developer but the financing structure (government guarantees, PPAs) is unresolved. A favourable resolution would be a significant positive catalyst.</li>
        <li><strong>Dividend sustainability</strong> — PX's ~5% yield is the index's main attraction. Erste and KB have payout ratios of ~50-60%, sustainable from earnings. &Ccaron;EZ's dividend is more volatile (linked to power prices). Monitor for any cut risk if power prices decline further.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The PX is a defensive, income-oriented allocation — not a growth bet. Long PX vs short DAX expresses the view that Czech banks will benefit from CNB rate stability while German auto/manufacturing faces structural headwinds. The 5% dividend yield provides a cushion in a sideways market. For growth exposure, look to Poland; for deep value, look to Hungary; for income and safety, Czechia is the destination.
  </div>
</div>""",
    },
}

# ═══ ROMANIA ═══
COUNTRY_DATA["RO"] = {
    "name": "Romania",
    "iso": "RON",
    "cb": "BNR",
    "gen_date": "2026-04-26",
    "peers": "HU, PL, CZ",
    "rating": "BBB− / Baa3 / BBB−",
    "fxregime": "Managed Float",
    "inftarget": "2.5% ±1pp CPI",
    "equity_index": "BET",
    "subtitle": "Comprehensive country primer with macro narratives and forward-looking positioning views",
    "kpi_html": """
  <div class="kpi-ribbon">
    <div class="kpi-card">
      <div class="kpi-label">Real GDP (YoY)</div>
      <div class="kpi-value">+2.2%</div>
      <div class="kpi-sub"><span class="kpi-delta-up">Above CEE avg</span> · Q4 2025</div>
    </div>
    <div class="kpi-card warn">
      <div class="kpi-label">Headline CPI (YoY)</div>
      <div class="kpi-value">5.1%</div>
      <div class="kpi-sub">Highest in CEE-4 · Dec 2025</div>
    </div>
    <div class="kpi-card danger">
      <div class="kpi-label">Fiscal Balance</div>
      <div class="kpi-value">−6.3%</div>
      <div class="kpi-sub"><span class="kpi-delta-down">EDP procedure</span> · 2025</div>
    </div>
    <div class="kpi-card danger">
      <div class="kpi-label">Current Account</div>
      <div class="kpi-value">−6.8%</div>
      <div class="kpi-sub"><span class="kpi-delta-down">Twin deficit</span> · of GDP 2025</div>
    </div>
    <div class="kpi-card warn">
      <div class="kpi-label">Policy Rate</div>
      <div class="kpi-value">6.50%</div>
      <div class="kpi-sub">Real rate ~1.4% · BNR on hold</div>
    </div>
    <div class="kpi-card danger">
      <div class="kpi-label">10Y RON Yield</div>
      <div class="kpi-value">7.50%</div>
      <div class="kpi-sub">Highest in EU · Apr 2026</div>
    </div>
  </div>""",
    "snapshot_prose": """
    <div class="snapshot-subsection">
      <h3>Economy</h3>
      <p>Romania is a <strong>$370 bn economy</strong> (2024 nominal GDP) with a population of <strong>19.0 million</strong> and GDP per capita of <strong>$19,500</strong> — the lowest in CEE-4 but converging rapidly (PPP-adjusted ~75% of EU average, up from ~50% in 2010). The industrial base is concentrated in <strong>automotive components &amp; wire harnesses (Dacia/Renault, Ford, Continental), IT services &amp; software outsourcing (fastest-growing tech sector in the EU), oil &amp; gas (OMV Petrom, Black Sea offshore), and agri-food (EU's largest maize and sunflower producer)</strong>. Top trading partners are <strong>Germany, Italy, France, Hungary, and Bulgaria</strong>.</p>
    </div>
    <div class="snapshot-subsection">
      <h3>Institutional Framework</h3>
      <p>The <strong>Banca Na&tcedil;ional&abreve; a Rom&acirc;niei (BNR)</strong> operates a <strong>managed float</strong> (de facto crawl vs EUR) with a formal inflation target of <strong>2.5% &plusmn;1pp</strong>. Romania is an EU and NATO member since 2007 and achieved partial Schengen accession (air/sea) in 2024. Sovereign credit rating stands at <strong>BBB&minus; (S&amp;P) / Baa3 (Moody&rsquo;s) / BBB&minus; (Fitch)</strong> — the lowest in CEE-4, reflecting Romania's <strong>twin deficit vulnerability (fiscal deficit ~6% GDP, current account deficit ~7% GDP)</strong>. Governor Mugur Is&abreve;rescu (since 1990) is the world's longest-serving central bank governor and the institutional anchor of Romanian macro stability.</p>
    </div>
    <div class="snapshot-subsection">
      <h3>Market Access</h3>
      <p>The benchmark <strong>BET index</strong> (~18,000) trades at a forward P/E of ~8.5x — the lowest in CEE-4, with a ~6% dividend yield that reflects the risk premium. The BET is dominated by banks (BT, BRD — ~35% weight), energy (OMV Petrom, Romgaz — ~25% weight), and utilities. The <strong>10-year RON government bond yields ~7.5%</strong> — the highest in the EU — offering ~180bp over HGBs and ~320bp over Bunds. The <strong>EURRON at ~4.97</strong> (April 2026) has been remarkably stable, reflecting the BNR's managed-float regime and the anchoring effect of Governor Is&abreve;rescu's credibility.</p>
    </div>""",
    "narratives": {
        "real_activity": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">Q1 2026 assessment</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Romania grew at <strong>+2.2% YoY in 2025</strong> — respectable, above the CEE-4 average, and driven by a <strong>consumption boom</strong> that is both the economy's strength and its vulnerability. Real wage growth of 7%+ (public sector wage hikes of 15%+ in 2024-25, minimum wage increases) is fuelling retail sales (+5.3% YoY) but widening the trade deficit as consumption sucks in imports. Industrial production is flat (+0.5% YoY) — the manufacturing sector is not participating in the consumption boom, which is import-heavy.</p>
      <p>The growth model is <strong>unsustainably tilted toward consumption over investment</strong>. Gross fixed capital formation is only ~22% of GDP (vs ~27% in Czechia and Hungary), held back by weak EU fund absorption (~60% vs 85%+ in Poland) and policy unpredictability. The IT services sector (+12% YoY, ~6% of GDP) is the structural growth star — Romania now has more tech workers per capita than any other EU country — but it's not large enough to offset the twin deficit drag from consumption-led growth.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Fiscal consolidation impact</strong> — the EDP requires deficit reduction of ~0.5% GDP/year. If the government implements consolidation through tax increases (VAT, income tax) rather than spending cuts, the consumption engine stalls. A 1pp VAT hike would add ~1.5pp to CPI and subtract ~0.5pp from GDP.</li>
        <li><strong>EU fund absorption</strong> — Romania has €29bn in RRF + cohesion funds allocated. Absorption capacity, not funding availability, is the binding constraint. The government's administrative reform agenda is critical to unlocking this growth driver.</li>
        <li><strong>Neptune Deep FID</strong> — OMV Petrom's Black Sea gas project (Neptune Deep, ~€4bn investment) is the largest FDI project in Romanian history. Final investment decision is expected mid-2026; a positive FID would transform Romania's energy trade balance and add ~0.5% to GDP during construction.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Romania's growth is the most fragile in CEE-4 — high nominal growth masks deep structural imbalances. Long ROMGBs only if you believe the BNR can manage the twin deficit adjustment without a disruptive FX move. We prefer expressing the growth view through equity (BET banks + energy) rather than rates or FX. The consumption story supports retail and bank earnings; the twin deficit risk caps ROMGB duration appetite.
  </div>
</div>""",
        "prices_wages": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Romania has <strong>the worst inflation problem in CEE</strong>. Headline CPI at <strong>5.1% YoY</strong> is the highest in CEE-4, more than double the BNR's 2.5% target midpoint and well outside the ±1pp tolerance band. The inflation is not primarily imported — it's <strong>homegrown and fiscal in origin</strong>. Public sector wage hikes of 15%+ (2024) and 10%+ (2025), combined with 15%+ minimum wage increases and pension indexation of 13%+, have injected massive demand stimulus into an economy already operating near capacity.</p>
      <p>Core CPI at <strong>4.8%</strong> tells the story — this is not about energy base effects (those have fully washed out). It's about services inflation at 7.2%, driven by labour costs in a tight labour market (unemployment ~5.4%, but structural — skills mismatch is severe). The BNR's policy rate at 6.50% gives a real rate of only ~1.4%, which is barely restrictive given the inflation composition. PPI is running at +3.2% YoY — the pipeline is not deflationary as in Hungary or Czechia.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Fiscal-driven inflation</strong> — Romania's inflation is a fiscal phenomenon, not a monetary one. The BNR can hold rates at 6.50% indefinitely, but as long as the government is running a 6%+ deficit fuelled by wage and pension hikes, CPI will stay elevated. Fiscal consolidation is the necessary condition for disinflation, not rate policy.</li>
        <li><strong>Exchange-rate passthrough</strong> — at ~40%, Romania has the highest FX passthrough in CEE. The BNR's managed float (de facto EURRON stability around 4.97) is the inflation anchor. If the leu comes under pressure (from twin deficit financing concerns), the passthrough adds 2pp to CPI for every 5% depreciation.</li>
        <li><strong>2026 wage round</strong> — the government has signalled a smaller public sector increase (~5%) and minimum wage moderation. If delivered, this is the first sign of demand-side disinflation. If not, CPI stays at 5%+ through 2027.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Romanian inflation is a short ROMGBs trade masquerading as a rates view. Real yields are barely positive, and the inflation risk premium is underpriced at 7.5% nominal. Pay 2y RON IRS vs receive 2y PLN — the inflation divergence between Romania (fiscal-driven, sticky) and Poland (energy-driven, fading) is not priced. In FX, the BNR's managed float makes EURRON a low-vol carry trade until it isn't — the twin deficit means the tail risk is a 10%+ depreciation, not a gradual move.
  </div>
</div>""",
        "external": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Romania's external position is <strong>the most vulnerable in CEE</strong>. The current account deficit printed at -6.8% of GDP in 2025, the widest in the EU. The deficit is structural: (1) a goods trade deficit of ~-8% GDP, as the consumption boom pulls in imports (electronics, vehicles, consumer goods) while manufacturing exports stagnate; (2) a primary income deficit of ~-2.5% GDP from profit repatriation by foreign-owned firms; partially offset by (3) a services surplus of +2.5% GDP (IT, transport) and (4) remittances from the 4mn-strong diaspora (~€6bn/yr, ~1.2% GDP).</p>
      <p>The financing of the CA deficit is increasingly <strong>dependent on EU transfers and portfolio flows</strong> rather than stable FDI. Net FDI has fallen from ~3% GDP (2016-19) to ~1.5% GDP (2024-25), reflecting policy unpredictability and the perception of a deteriorating business environment. FX reserves at €63bn cover ~4.5 months of imports — adequate but on the low side given the twin deficit structure. The BNR's managed float has kept EURRON remarkably stable at ~4.97, but this stability is purchased at the cost of reserve depletion during risk-off episodes.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>External financing gap</strong> — Romania needs to finance a ~€25bn CA deficit annually. If EU fund inflows slow or portfolio investors turn cautious (Romania was downgraded to BBB- by S&P in 2024), the financing gap pressures RON. The BNR would be forced to choose between FX intervention (reserve drawdown) and rate hikes.</li>
        <li><strong>Neptune Deep impact</strong> — if FID is taken in 2026, first gas is expected 2028-29. At peak production (~10 bcm/yr), it would reduce Romania's gas import bill by ~€2bn/yr (~0.5% GDP), a meaningful but not transformative external adjustment.</li>
        <li><strong>Rating agency calendar</strong> — Moody's next review is October 2026. A negative outlook (currently stable at Baa3) would increase Romania's funding costs and potentially trigger EM index exclusion fears. The investment-grade floor is fragile.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Romania's external vulnerability is the most under-priced risk in CEE. The BNR's managed float has suppressed EURRON vol to ~3% — absurdly low for a twin-deficit economy with a BBB- rating. Long EURRON vol via 6m strangles (5.00/5.10) is cheap insurance against a balance-of-payments shock. In rates, the CA deficit argues for a higher risk premium on ROMGBs — the 7.5% 10y yield is fair, not cheap.
  </div>
</div>""",
        "fiscal_sovereign": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>Romania's fiscal position is <strong>the worst in the EU outside of crisis cases</strong>. The 2025 general government deficit printed at -6.3% of GDP, well above the 3% Maastricht reference and the worst in CEE-4. Romania has been in the Excessive Deficit Procedure (EDP) since 2020 and has missed every fiscal target since. The drivers are structural: (1) a pro-cyclical public wage policy (wages are ~12% of GDP, up from 9% in 2019), (2) pension costs (~10% of GDP) following a 13%+ indexation in 2024, and (3) weak revenue collection — Romania's tax-to-GDP ratio is ~27%, the lowest in the EU (EU average ~41%).</p>
      <p>Gross debt at <strong>~53% of GDP</strong> is moderate relative to the EU average (~83%), but it's rising fast — from 35% in 2019 to 53% in 2025, an 18pp increase in 6 years. The debt stock is roughly 50% RON-denominated and 50% EUR-denominated — the high FX share makes debt dynamics sensitive to RON depreciation. The 10y yield at 7.5% reflects the market's sober assessment: the ~320bp spread over Bunds is the widest in the EU, and the ~180bp spread over HGBs reflects Romania's weaker fiscal fundamentals vs Hungary.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>EDP compliance</strong> — the European Commission's spring 2026 assessment will judge Romania's progress on fiscal consolidation. A negative assessment could trigger the suspension of EU cohesion funds (~€3-5bn/yr), which would immediately widen the financing gap and pressure RON.</li>
        <li><strong>Pension reform</strong> — the pension system is the structural fiscal problem. The pension-to-GDP ratio is rising ~0.5pp/yr due to demographics and discretionary indexation. The World Bank and IMF have recommended a shift to a points-based indexation formula; the PSD-PNL coalition has resisted. This is the political economy fault line.</li>
        <li><strong>Election cycle risk</strong> — the 2024-25 elections saw a strong far-right showing (~32%), introducing a new political risk premium. A far-right government (unlikely but not impossible in the next cycle) would struggle to access EU funds, pushing Romania toward a balance-of-payments crisis.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> Romania is the highest-risk, highest-carry trade in CEE sovereign credit. At 7.5%, the 10y ROMGB offers the highest nominal yield in the EU, but the 320bp Bund spread compensates for genuine crisis risk. This is a trade for specialists — size for a potential 150bp spread widening in a stress scenario. Long ROMGBs vs short HGBs if you believe the BNR/Is&abreve;rescu anchor holds; avoid if you think the twin deficit dynamic is unsustainable. We're neutral — the carry is tempting but the risk of a fiscal-financial spiral (RON depreciation → higher debt/GDP → rating downgrade → capital outflows) is non-trivial.
  </div>
</div>""",
        "monetary_financial": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The BNR has been <strong>the most conservative central bank in CEE</strong> — it hiked to 7.0% (from 1.25%) during 2021-23 and has cut only 50bp to <strong>6.50%</strong>, the highest policy rate in CEE-4. Governor Mugur Is&abreve;rescu's institutional DNA (he managed Romania's 1990s hyperinflation stabilisation) shapes the BNR's hawkish bias. With CPI at 5.1%, the real policy rate is only ~1.4% — barely restrictive. The BNR's own analysis suggests the neutral rate is 4.0-4.5% nominal, implying the current stance is only moderately tight.</p>
      <p>The transmission mechanism is partially impaired by the <strong>managed float</strong>. The BNR's FX management keeps EURRON at ~4.97, suppressing the exchange-rate channel of monetary transmission. This forces the BNR to rely more heavily on the credit channel, which is weakened by: (1) high financial euroisation (~35% of bank deposits and ~30% of loans are EUR-denominated), (2) a relatively shallow capital market, and (3) state-owned banks (~15% of system assets) that are less responsive to the policy rate. Private credit growth at +6.1% YoY is the highest in CEE — the consumption boom is being financed.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>BNR cutting cycle</strong> — the market prices a first 25bp cut in Q3 2026. We think this is too optimistic — the BNR won't cut with CPI above 4.5% and a 6%+ fiscal deficit. First cut in Q1 2027 is more realistic, and only if fiscal consolidation is delivered.</li>
        <li><strong>Is&abreve;rescu succession</strong> — the Governor's term runs to 2029 (he will be 80). His eventual departure is the single largest institutional risk for Romanian macro stability. The succession process (Parliament appoints) will be highly politicised. Markets will react negatively to any candidate perceived as insufficiently hawkish or politically pliant.</li>
        <li><strong>Euroisation risk</strong> — the high share of EUR-denominated credit means the BNR's policy rate has less traction on ~30% of the credit stock. It also means RON depreciation directly increases debt-service burdens for unhedged EUR borrowers — a financial-stability constraint on FX flexibility.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The BNR's hawkish hold supports RON carry trades (long RON vs EUR earns ~325bp annualised at current rates). But this is a classic carry trade — the risk is a 10% FX move that wipes out 3 years of carry in a month. The BNR's managed float reduces the probability of this tail event but doesn't eliminate it. We prefer expressing the BNR view through the front end: receive 2y RON FRA to capture the delayed cutting cycle without the FX risk. EURRON vol is too cheap relative to the fundamental tail risk — long 6m EURRON strangles are a positive-carry hedge.
  </div>
</div>""",
        "markets_valuation": """
<div class="narrative">
  <div class="narrative-header">
    <span class="narrative-label">Macro Narrative</span>
    <span class="narrative-date">April 2026</span>
  </div>
  <div class="narrative-body">
    <div class="narrative-col">
      <h4>What's Happened</h4>
      <p>The <strong>BET index at ~18,000 (+8.2% YoY)</strong> has been the best-performing CEE equity benchmark, driven by: (1) bank earnings benefiting from the consumption boom and high nominal rates (BT, BRD — combined ~35% of index, ROEs of 18-22%), (2) energy sector re-rating (OMV Petrom, Romgaz — ~25% weight) on higher oil/gas prices and Neptune Deep optionality, and (3) the ~6% dividend yield attracting income-seeking flows in a low-rate DM world. The forward P/E of ~8.5x is the lowest in CEE — a 40% discount to WIG20.</p>
      <p>But the discount is not irrational. It reflects: (1) the twin deficit macro risk — in a balance-of-payments stress, the BET would be the first CEE equity market to sell off, (2) low free float and liquidity (~€30bn total market cap, ~35% free float, daily turnover ~€10-15mn), and (3) corporate governance concerns at state-owned enterprises. The BET is a high-beta, high-risk, high-return proposition — it works in a constructive EM risk environment and gets crushed in risk-off.</p>
    </div>
    <div class="narrative-col">
      <h4>What to Watch</h4>
      <ul>
        <li><strong>Banca Transilvania (TLV) — the growth story</strong> — TLV is Romania's largest bank (~20% market share), trading at P/B ~2.2x with ROE ~22%. It has been consolidating the Romanian banking market through acquisitions (OTP Romania, Idea Bank). If Romania achieves a soft landing on the twin deficits, TLV is the primary equity beneficiary.</li>
        <li><strong>OMV Petrom & Neptune Deep</strong> — Petrom (~8% BET weight) is a binary option on the Neptune Deep FID. If the project proceeds (mid-2026 decision), Petrom's production profile doubles by 2030 and the stock re-rates 30-40%. If it's delayed/cancelled, the stock trades as a declining E&P company.</li>
        <li><strong>EM index upgrade?</strong> — FTSE Russell currently classifies Romania as a Frontier Market. An upgrade to Secondary Emerging Market status (possible by 2028 if market depth and corporate governance improve) would trigger ~$500mn of passive inflows — significant for a ~€30bn market.</li>
      </ul>
    </div>
  </div>
  <div class="narrative-footer">
    <strong>Market Implication:</strong> The BET is the highest-conviction long in CEE equities IF you can tolerate the twin deficit tail risk. Long BET banks (TLV) vs short HGB banks (OTP) captures the consumption-growth divergence while hedging the fiscal risk (OTP benefits from HUF weakness, TLV from RON stability). The 6% dividend yield provides a cushion. Position size: this is a 1-2% of NAV trade — the twin deficit makes it structurally higher-risk than WIG20 or PX. For the cautious, long ROMGBs at 7.5% with a tight stop offers similar carry with less convexity.
  </div>
</div>""",
    },
}


# ── Build logic ───────────────────────────────────────────────────────────────

def build_v3(country_code: str) -> Path:
    data = COUNTRY_DATA[country_code]
    iso_lower = country_code.lower()
    # Map to base HTML filename
    name_map = {"HU": "hungary", "PL": "poland", "CZ": "czechia", "RO": "romania"}
    base_name = name_map[country_code]
    base_path = OUTPUT / f"{base_name}_2026Q2.html"
    out_path = OUTPUT / f"{base_name}_2026Q2_v3.html"

    html = base_path.read_text()

    # Extract chart blocks
    chart_blocks = re.findall(
        r'(<div class="chart-cell"><div.*?</div></div>)', html, re.DOTALL
    )
    chart_map = {}
    for cb in chart_blocks:
        m = re.search(r'id="(chart-[^"]+)"', cb)
        if m:
            chart_map[m.group(1)] = cb

    # Extract CB and Trade sections
    cb_match = re.search(r'<section class="panel" id="central_bank">.*?</section>', html, re.DOTALL)
    cb_section = cb_match.group() if cb_match else ""
    trade_match = re.search(r'<section class="panel" id="trade">.*?</section>', html, re.DOTALL)
    trade_section_html = trade_match.group() if trade_match else ""

    # Build section panels with narratives
    sections_html = ""
    for sec_id in SECTION_ORDER:
        title, badge = SECTION_TITLES[sec_id]
        blurb = SECTION_BLURBS[sec_id]
        chart_ids = SECTION_CHART_MAP[sec_id]
        narrative = data["narratives"].get(sec_id, "")

        charts_html = ""
        for cid in chart_ids:
            if cid in chart_map:
                charts_html += f'<div class="chart-cell">{chart_map[cid]}</div>\n'

        sections_html += f"""
<section class="panel" id="{sec_id}">
  <h2>{title} <span class="section-badge">{badge}</span></h2>
  <div class="blurb">{blurb}</div>
  <div class="charts">{charts_html}</div>
  {narrative}
</section>
"""

    # Plotly JS
    plotly_js = re.search(r'<script src="https://cdn.plot.ly/plotly-2\.32\.0\.min\.js"></script>', html)
    plotly_tag = plotly_js.group(0) if plotly_js else '<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>'

    # Build country switcher nav
    all_countries = [
        ("HU", "Hungary", "hungary_2026Q2_v3.html"),
        ("PL", "Poland", "poland_2026Q2_v3.html"),
        ("CZ", "Czechia", "czechia_2026Q2_v3.html"),
        ("RO", "Romania", "romania_2026Q2_v3.html"),
    ]
    nav_links = []
    for cc, cname, cfile in all_countries:
        cls = 'nav-link active' if cc == country_code else 'nav-link'
        nav_links.append(f'<a href="{cfile}" class="{cls}">{cc}</a>')
    country_nav = "\n    " + "\n    ".join(nav_links)

    final_html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{data["name"]} — Macro Dashboard (Narrative Edition)</title>
{plotly_tag}
<style>{CSS}</style>
</head>
<body>

<div class="topbar">
  <a href="index.html" style="text-decoration:none;color:inherit;"><div class="brand">Country Primer <span>v3</span></div></a>
  <div class="country-nav">
    {country_nav}
  </div>
  <div>
    <span class="meta-item">{data["name"]} · {data["iso"]} · {data["cb"]}</span>
  </div>
</div>

<div class="container">

<header>
  <h1>{data["name"]} — Macro Dashboard</h1>
  <div class="subtitle">{data["subtitle"]}</div>
  <div class="meta-row">
    <div class="meta-chip">Framework: <strong>IMF FPP × GS Indicators × Buy-side PM</strong></div>
    <div class="meta-chip">Rating: <strong>{data["rating"]}</strong></div>
    <div class="meta-chip">FX Regime: <strong>{data["fxregime"]}</strong></div>
    <div class="meta-chip">Target: <strong>{data["inftarget"]}</strong></div>
  </div>
</header>

{data["kpi_html"]}

<!-- TOC -->
<div class="toc">
  <a href="#snapshot">§1 Snapshot</a>
  <a href="#real_activity">§2 Real Activity</a>
  <a href="#prices_wages">§3 Prices & Wages</a>
  <a href="#external">§4 External</a>
  <a href="#fiscal_sovereign">§5 Fiscal & Sovereign</a>
  <a href="#monetary_financial">§6 Monetary & Financial</a>
  <a href="#markets_valuation">§7 Markets & Valuation</a>
</div>

<!-- Snapshot -->
<div class="snapshot-panel" id="snapshot">
  <h2>§1 Country Snapshot</h2>
  <div class="blurb">Structural parameters that set the frame: economic size, sovereign rating, FX regime, the central bank's mandate, and qualitative country context. These are the slow-moving variables against which the cyclical sections below should be read.</div>
  <div class="snapshot-prose">
    {data["snapshot_prose"]}
  </div>
</div>

""" + cb_section + trade_section_html + f"""

<!-- Chart Sections with Narrative Commentary -->
{sections_html}

<footer>
  <div class="attribution">
    Country Primer v3 · Data via openecon-data MCP, ECB, Eurostat, World Bank, Yahoo Finance · Charts: Plotly
  </div>
  <div class="disclaimer">
    <strong>Disclaimer:</strong> This is a research artefact produced for analytical purposes, not investment advice.
    All positioning views expressed are illustrative of the analytical framework and should not be construed as
    trade recommendations. Past performance does not guarantee future results. Macro narratives reflect the
    author's assessment as of the generation date and may change without notice.
  </div>
</footer>

</div>
</body>
</html>
"""

    out_path.write_text(final_html)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_v3.py {HU|PL|CZ|RO|ALL}")
        sys.exit(1)

    target = sys.argv[1].upper()
    if target == "ALL":
        targets = ["HU", "PL", "CZ", "RO"]
    elif target in COUNTRY_DATA:
        targets = [target]
    else:
        print(f"Unknown country: {target}. Use HU, PL, CZ, RO, or ALL")
        sys.exit(1)

    for cc in targets:
        path = build_v3(cc)
        print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
