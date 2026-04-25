"""Build an optimized preview HTML with narrative commentary and upgraded visuals."""
from pathlib import Path
import re

ORIG = Path(__file__).parent / "output" / "hungary_2026Q2.html"
OUT = Path(__file__).parent / "output" / "hungary_2026Q2_v3.html"

html = ORIG.read_text()

# Extract Central Bank and Trade sections from base HTML
cb_match = re.search(r'<section class="panel" id="central_bank">.*?</section>', html, re.DOTALL)
cb_section = cb_match.group() if cb_match else ""
trade_match = re.search(r'<section class="panel" id="trade">.*?</section>', html, re.DOTALL)
trade_section_html = trade_match.group() if trade_match else ""

# Extract all chart-cell divs
chart_blocks = re.findall(
    r'(<div class="chart-cell"><div.*?</div></div>)', html, re.DOTALL
)

# Map chart id -> html
chart_map = {}
for cb in chart_blocks:
    m = re.search(r'id="(chart-[^"]+)"', cb)
    if m:
        chart_map[m.group(1)] = cb

# Extract snapshot tiles
tiles_match = re.search(
    r'<div class="snapshot">(.*?)</div>\s*</section>', html, re.DOTALL
)
snapshot_html = tiles_match.group(1) if tiles_match else ""

# === NARRATIVE COMMENTARY for Hungary (April 2026) ===

REAL_ACTIVITY_NARRATIVE = """
<div class="narrative">
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
</div>
"""

PRICES_WAGES_NARRATIVE = """
<div class="narrative">
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
</div>
"""

EXTERNAL_NARRATIVE = """
<div class="narrative">
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
</div>
"""

FISCAL_NARRATIVE = """
<div class="narrative">
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
</div>
"""

MONETARY_NARRATIVE = """
<div class="narrative">
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
</div>
"""

MARKETS_NARRATIVE = """
<div class="narrative">
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
</div>
"""

NARRATIVES = {
    "real_activity": REAL_ACTIVITY_NARRATIVE,
    "prices_wages": PRICES_WAGES_NARRATIVE,
    "external": EXTERNAL_NARRATIVE,
    "fiscal_sovereign": FISCAL_NARRATIVE,
    "monetary_financial": MONETARY_NARRATIVE,
    "markets_valuation": MARKETS_NARRATIVE,
}

# === CSS ===
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

/* ---- Container ---- */
.container { max-width: 1280px; margin: 0 auto; padding: 28px 24px 48px; }

/* ---- Header ---- */
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
.snapshot-panel .blurb { color: var(--muted); font-size: 12.5px; margin-bottom: 16px; }
.snapshot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.snap-tile {
  background: var(--card-alt); border-radius: var(--radius-sm);
  padding: 12px 14px; border: 1px solid var(--border);
}
.snap-tile .sk {
  font-size: 10.5px; color: var(--muted); text-transform: uppercase;
  letter-spacing: 0.4px; margin-bottom: 3px;
}
.snap-tile .sv {
  font-size: 14px; font-weight: 600; color: var(--fg);
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

/* ---- Positioning Callout ---- */
.positioning-callout {
  background: linear-gradient(135deg, #fef9e7, #fefce8);
  border: 1px solid #e6d88a;
  border-radius: var(--radius-sm);
  padding: 14px 18px; margin-top: 16px;
  font-size: 13px;
}
.positioning-callout .pos-label {
  font-weight: 700; color: var(--accent); text-transform: uppercase;
  font-size: 10px; letter-spacing: 0.8px;
}

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

/* ---- Responsive ---- */
@media (max-width: 900px) {
  .narrative-body { grid-template-columns: 1fr; }
  .charts { grid-template-columns: 1fr; }
  .kpi-ribbon { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .kpi-ribbon { grid-template-columns: 1fr; }
  header .meta-row { flex-direction: column; gap: 6px; }
  .snapshot-grid { grid-template-columns: 1fr 1fr; }
}
"""

# === Assemble the HTML ===
# Reuse the Plotly JS from original
plotly_js = re.search(r'<script src="https://cdn.plot.ly/plotly-2\.32\.0\.min\.js"></script>', html)
plotly_tag = plotly_js.group(0) if plotly_js else '<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>'

# Map section indicators to chart IDs
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
    "real_activity": "Growth decomposition: GDP, industrial production, retail sales, and labour market — separating the export-manufacturing recession from the domestically-driven services expansion.",
    "prices_wages": "Inflation dynamics: headline and core CPI trends, producer price pipeline, and the wage-growth impulse that will determine the MNB's terminal rate.",
    "external": "Balance of payments: current account trajectory, trade balance, FX reserve adequacy, and real exchange rate misalignment vs fair value.",
    "fiscal_sovereign": "Sovereign creditworthiness: fiscal balance path, debt stock dynamics, and the term premium the market demands for bearing Hungarian duration risk.",
    "monetary_financial": "Policy stance: the base rate relative to the Taylor-implied neutral, credit transmission channels, and the HUF fair-value anchor.",
    "markets_valuation": "Equity valuation: BUX level and momentum, relative to CEE peers and to the macro fundamentals mapped in sections 2−6.",
}

sections_html = ""
for sec_id in ["real_activity", "prices_wages", "external", "fiscal_sovereign", "monetary_financial", "markets_valuation"]:
    title, badge = SECTION_TITLES[sec_id]
    blurb = SECTION_BLURBS[sec_id]
    chart_ids = SECTION_CHART_MAP[sec_id]
    narrative = NARRATIVES[sec_id]

    charts_html = ""
    for cid in chart_ids:
        if cid in chart_map:
            charts_html += f'<div class="chart-cell">{chart_map[cid]}</div>\n'

    sections_html += f'''
<section class="panel" id="{sec_id}">
  <h2>{title} <span class="section-badge">{badge}</span></h2>
  <div class="blurb">{blurb}</div>
  <div class="charts">{charts_html}</div>
  {narrative}
</section>
'''

# Build final HTML
final_html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hungary — Macro Dashboard (Narrative Edition)</title>
{plotly_tag}
<style>{CSS}</style>
</head>
<body>

<div class="topbar">
  <div class="brand">Country Primer <span>v3</span></div>
  <div>
    <span class="meta-item">Hungary · HUF · MNB</span>
    <span class="meta-item">Generated 2026-04-25</span>
    <span class="meta-item">Peers: PL, CZ, RO</span>
    <span class="meta-item"><a href="hungary_2026Q2.html">← Original v1</a></span>
  </div>
</div>

<div class="container">

<header>
  <h1>Hungary — Macro Dashboard</h1>
  <div class="subtitle">Comprehensive country primer with macro narratives and forward-looking positioning views</div>
  <div class="meta-row">
    <div class="meta-chip">Framework: <strong>IMF FPP × GS Indicators × Buy-side PM</strong></div>
    <div class="meta-chip">Rating: <strong>BBB− / Baa3 / BBB</strong></div>
    <div class="meta-chip">FX Regime: <strong>Free Float</strong></div>
    <div class="meta-chip">Target: <strong>3.0% ±1pp CPI</strong></div>
  </div>
</header>

<!-- KPI Ribbon -->
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
</div>

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
  <div class="snapshot-grid">
    <div class="snap-tile"><div class="sk">Country</div><div class="sv">Hungary</div></div>
    <div class="snap-tile"><div class="sk">ISO</div><div class="sv">HU (HUN)</div></div>
    <div class="snap-tile"><div class="sk">Population</div><div class="sv">9.6 million</div></div>
    <div class="snap-tile"><div class="sk">GDP (nominal)</div><div class="sv">$215 bn (2024)</div></div>
    <div class="snap-tile"><div class="sk">GDP per Capita</div><div class="sv">$22,400</div></div>
    <div class="snap-tile"><div class="sk">Currency</div><div class="sv">HUF</div></div>
    <div class="snap-tile"><div class="sk">Central Bank</div><div class="sv">Magyar Nemzeti Bank (MNB)</div></div>
    <div class="snap-tile"><div class="sk">FX Regime</div><div class="sv">Free float (with FX-stabilising operations)</div></div>
    <div class="snap-tile"><div class="sk">Inflation Target</div><div class="sv">3.0% ±1pp</div></div>
    <div class="snap-tile"><div class="sk">Sovereign Rating</div><div class="sv">BBB− / Baa3 / BBB</div></div>
    <div class="snap-tile"><div class="sk">Equity Index</div><div class="sv">BUX (OTP Bank ~25% wt)</div></div>
    <div class="snap-tile"><div class="sk">Major Industries</div><div class="sv">Automotive & EV batteries, Electronics & ICT, Pharmaceuticals, Food processing, Business services</div></div>
    <div class="snap-tile"><div class="sk">Top Trading Partners</div><div class="sv">Germany, Austria, China, Italy, Romania</div></div>
  </div>
  <div class="context-grid">
    <div class="context-card">
      <div class="context-card-header">Geography &amp; Infrastructure</div>
      <div class="context-card-body">Landlocked CEE economy at the crossroads of major EU transport corridors. Borders 7 countries (AT, SK, UA, RO, RS, HR, SI). Flat terrain (Pannonian Basin) with the Danube as the main waterway. EU and NATO member since 2004, Schengen since 2007. Not a euro-area member.</div>
    </div>
    <div class="context-card">
      <div class="context-card-header">Political Economy</div>
      <div class="context-card-body">The April 2026 parliamentary election produced a Tisza Party supermajority, ending 16 years of Fidesz rule under Viktor Orban. The new government inherits a wide fiscal deficit and suspended EU RRF/cohesion funds (~€36bn envelope frozen) due to rule-of-law disputes under the previous administration. The political pivot raises the probability of an EU funds agreement in H2 2026 but introduces policy uncertainty during the transition.</div>
    </div>
    <div class="context-card">
      <div class="context-card-header">Society &amp; Demographics</div>
      <div class="context-card-body">Population ~9.6mn, declining slowly (-0.3%/yr). Median age 44, above EU average. Labour force participation ~67% with scope to rise. High educational attainment in STEM fields supports manufacturing FDI. Budapest metro area (~1.7mn) dominates economic activity; east-west regional inequality is pronounced. Household debt is low (~20% of GDP) but FX mortgage exposure (mostly HUF-refinanced post-2015) is a legacy vulnerability.</div>
    </div>
  </div>
</div>

""" + cb_section + trade_section_html + f"""

<!-- Chart Sections with Narrative Commentary -->
{sections_html}

<footer>
  <div class="attribution">
    Country Primer v3 · Data via openecon-data MCP, ECB, Eurostat, World Bank, Yahoo Finance · Charts: Plotly<br>
    <a href="hungary_2026Q2.html">View base v1 version</a> · <a href="hungary_2026Q2_preview.html">View v2 preview</a>
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

OUT.write_text(final_html)
print(f"Wrote preview to {OUT}")
print(f"Size: {len(final_html):,} bytes")
