# JP/ZA Depth and Trust Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Japan and South Africa dashboards usable for single-country depth work by adding native official sources, fixing a quality model that currently ranks compiling authorities below third-hand mirrors, and surfacing provenance to the reader.

**Architecture:** Three layers, bottom-up. First the shared quality model in `src/country_primer/data_quality.py` learns to accept a declared authority and to stop penalising documented transforms. Then a new shared adapter module holds the fetchers, so builders stop importing fetchers from each other. Then the page renders the trust dimensions that were always computed but never shown, including a declared cross-check divergence indicator that doubles as a regression test on the new adapters.

**Tech Stack:** Python 3.12, `uv`, requests, PyYAML, Plotly, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-28-jp-za-depth-and-trust-design.md`

## Global Constraints

- Never fabricate, interpolate, or backfill a missing economic series. An unresolvable series stays a documented `data_gaps` entry.
- `make validate` must remain offline and deterministic. No live fetching in validation or tests; live probes belong in `make refresh-check`.
- Credentials live only in `.env.local`, loaded by `scripts/uv_project.sh`. Never in configs, HTML, JSON, tests, docs, or commit messages.
- The e-Stat adapter must degrade gracefully: absent `ESTAT_APP_ID`, its indicators fall back to their `data_gaps` entries and the build still succeeds.
- Run every command through `scripts/uv_project.sh run` or the project venv, never global Python.
- Valid `source_authority` values, exactly: `official_primary`, `official_mirror`, `public_wrapper`, `manual_curated`, `public_secondary`.
- After any change touching `data_quality.py`, rebuild via `make rebuild-ui` (snapshot-only, zero network) before comparing output.

## Resolved Identifiers (discovered 2026-08-28, do not re-derive)

**BOJ flat files** — `https://www.stat-search.boj.or.jp/info/<name>.zip`, each containing one same-named `.csv`, plain ASCII, wide format:
- Row 1: `,,,<period>,<period>,...` where period is `YYYYMM`
- Data rows: `<series_code>,<dataset_name>,<series_label>,<v1>,<v2>,...`
- `cgpi_m_en.zip` → `PRCG20_2200000000` = "[Producer Price Index] All commodities"

**e-Stat CPI** — `statsDataId=0004052037` (2025 base, history from 1970):
- `cdArea=00000` (全国 nationwide) — **required**; the default returns Tokyo ward area (13100)
- `cdTab=1` index, `cdTab=3` year-over-year (native, not derived)
- `cdCat01`: `0001` headline 総合 · `0161` core ex-fresh-food 生鮮食品を除く総合 · `0178` core-core ex-fresh-food-and-energy · `0202` goods 財 · `0220` services サービス
- Response: `GET_STATS_DATA.STATISTICAL_DATA.DATA_INF.VALUE`, rows of `{"@tab","@cat01","@area","@time","$"}`
- `@time` format `2026000808` → year = `[0:4]`, month = `[8:10]`

---

### Task 1: Accept a declared source authority

**Files:**
- Modify: `src/country_primer/data_quality.py:162-178` (`source_authority`), `:219`
- Test: `tests/test_data_quality.py`

**Interfaces:**
- Produces: `source_authority(source_name, source_url="", declared="") -> str`. Task 5, 6 and 9 rely on config-declared authority reaching this function.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_data_quality.py
from country_primer.data_quality import assess_series_quality, source_authority


def test_declared_authority_overrides_name_matching():
    assert source_authority("SARB Web API", "", "official_primary") == "official_primary"


def test_declared_authority_ignored_when_invalid():
    assert source_authority("FRED / OECD", "", "not_a_tier") == "official_mirror"


def test_native_sources_match_as_primary_without_declaration():
    for name in ("Bank of Japan flat file", "e-Stat API", "SARB Web API"):
        assert source_authority(name) == "official_primary", name


def test_declared_authority_flows_through_assessment():
    series = {
        "id": "cpi_inflation", "frequency": "monthly", "transform": "level",
        "source_name": "SARB Web API", "source_authority": "official_primary",
        "observations": [{"date": "2026-07-01", "value": 4.3}],
    }
    assert assess_series_quality(series)["source_authority"] == "official_primary"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `scripts/uv_project.sh run pytest tests/test_data_quality.py -k authority -v`
Expected: FAIL — `source_authority()` takes 2 positional arguments but 3 were given

- [ ] **Step 3: Implement**

In `src/country_primer/data_quality.py`, add above `source_authority`:

```python
VALID_SOURCE_AUTHORITIES = frozenset({
    "official_primary",
    "official_mirror",
    "public_wrapper",
    "manual_curated",
    "public_secondary",
})
```

Change the signature and add the declared branch plus the missing native tokens:

```python
def source_authority(source_name: object, source_url: object = "", declared: object = "") -> str:
    # A config author who validated the source declares its tier explicitly;
    # name matching is only the fallback for series that predate the field.
    declared_value = clean(declared).lower().replace(" ", "_")
    if declared_value in VALID_SOURCE_AUTHORITIES:
        return declared_value
    source = f"{clean(source_name)} {clean(source_url)}".lower()
    if any(token in source for token in ("manual", "curated", "tracker")):
        return "manual_curated"
    if any(token in source for token in ("akshare", "eastmoney", "sina", "yahoo", "stooq")):
        return "public_wrapper"
    if any(token in source for token in ("fred", "world bank", "imf", "bis", "oecd", "db.nomics")):
        return "official_mirror"
    if any(token in source for token in (
        "ons", "bank of england", "boe", "safe", "fiscaldata", "us treasury",
        "bls business", "eurostat", "ecb ", "cnb", "nbp", "mnb", "bnr",
        "bureau of economic analysis", "bea.gov", "bureau of labor statistics", "bls.gov",
        "federal reserve", "treasury.gov", "national bureau of statistics", "stats.gov.cn",
        "people's bank of china", "pbc.gov.cn", "pboc", "safe.gov.cn",
        "bank of japan", "boj", "stat-search.boj", "e-stat", "estat",
        "statistics bureau", "mhlw", "mlit", "meti",
        "sarb", "resbank", "south african reserve bank",
    )):
        return "official_primary"
    return "public_secondary"
```

Then at line 219 pass the declared value through:

```python
    authority = source_authority(
        series.get("source_name") or series.get("source"),
        series.get("source_url"),
        series.get("source_authority"),
    )
```

- [ ] **Step 4: Run tests**

Run: `scripts/uv_project.sh run pytest tests/test_data_quality.py -v`
Expected: PASS

- [ ] **Step 5: Declare authority on the SARB series**

In `config/south_africa_indicators.yaml`, add `source_authority: official_primary` to each of the 11 indicators with `fetcher: sarb`.

- [ ] **Step 6: Rebuild offline and confirm the reclassification**

```bash
make rebuild-ui
scripts/uv_project.sh run python -c "
import json, collections
d = json.load(open('output/south_africa_canonical_frame.json'))
print(collections.Counter((s.get('quality') or {}).get('source_authority') for s in d['series']))
"
```
Expected: zero `public_secondary`; the 11 SARB series now `official_primary`.

- [ ] **Step 7: Commit**

```bash
git add src/country_primer/data_quality.py tests/test_data_quality.py config/south_africa_indicators.yaml output/
git commit -m "fix: let indicator configs declare source authority"
```

---

### Task 2: Stop penalising documented transforms

**Files:**
- Modify: `src/country_primer/data_quality.py:274-280` (status gate)
- Test: `tests/test_data_quality.py`

**Interfaces:**
- Consumes: `source_authority(..., declared=...)` from Task 1.
- Produces: no signature change; `assess_series_quality(...)["status"]` may now return `verified` for `derivation == "derived"`.

- [ ] **Step 1: Write the failing test**

```python
def _series(**overrides):
    base = {
        "id": "core_cpi_inflation", "frequency": "monthly",
        "source_name": "e-Stat API", "source_authority": "official_primary",
        "observations": [{"date": "2026-07-01", "value": 1.7}],
    }
    base.update(overrides)
    return base


def test_declared_transform_can_still_be_verified(monkeypatch):
    import country_primer.data_quality as dq
    monkeypatch.setattr(dq, "DEFAULT_MAX_AGE_DAYS", {**dq.DEFAULT_MAX_AGE_DAYS, "monthly": 3650})
    result = dq.assess_series_quality(_series(transform="yoy_pct"), today=__import__("datetime").date(2026, 8, 1))
    assert result["derivation"] == "derived"
    assert result["status"] == "verified"


def test_substitute_is_still_not_verified(monkeypatch):
    import country_primer.data_quality as dq
    monkeypatch.setattr(dq, "DEFAULT_MAX_AGE_DAYS", {**dq.DEFAULT_MAX_AGE_DAYS, "monthly": 3650})
    result = dq.assess_series_quality(
        _series(transform="level", derivation="substitute"),
        today=__import__("datetime").date(2026, 8, 1),
    )
    assert result["status"] != "verified"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `scripts/uv_project.sh run pytest tests/test_data_quality.py -k verified -v`
Expected: FAIL — `assert 'watch' == 'verified'`

- [ ] **Step 3: Implement**

Replace the `verified` branch:

```python
    # A declared transform of an official series (YoY from an official index) is
    # normal macro practice, not a trust deduction. Substitutes standing in for a
    # different concept remain excluded via comparability.
    elif (
        authority == "official_primary"
        and derivation in {"observed", "derived"}
        and freshness == "current"
        and validation == "passed"
    ):
        status = "verified"
```

- [ ] **Step 4: Run tests**

Run: `scripts/uv_project.sh run pytest tests/test_data_quality.py -v`
Expected: PASS

- [ ] **Step 5: Rebuild offline and diff the quality distribution across all nine pages**

```bash
scripts/uv_project.sh run python -c "
import json, glob, collections
for p in sorted(glob.glob('output/*_canonical_frame.json')):
    d = json.load(open(p))
    c = collections.Counter((s.get('quality') or {}).get('status') for s in d.get('series', []))
    print(f'{p.split(\"/\")[-1]:36s} {dict(c)}')
" > /tmp/quality_before.txt
make rebuild-ui
scripts/uv_project.sh run python -c "
import json, glob, collections
for p in sorted(glob.glob('output/*_canonical_frame.json')):
    d = json.load(open(p))
    c = collections.Counter((s.get('quality') or {}).get('status') for s in d.get('series', []))
    print(f'{p.split(\"/\")[-1]:36s} {dict(c)}')
" > /tmp/quality_after.txt
diff /tmp/quality_before.txt /tmp/quality_after.txt
```
Expected: pills shift toward `verified` on pages with official-primary sources. **Review this diff before continuing** — no data changed, so every movement must be attributable to the scoring change.

- [ ] **Step 6: Commit**

```bash
git add src/country_primer/data_quality.py tests/test_data_quality.py output/
git commit -m "fix: allow documented transforms of official series to verify"
```

---

### Task 3: Guard pipeline outcomes, not just page structure

**Files:**
- Modify: `scripts/validate_outputs.py`
- Test: `tests/test_outputs.py`

**Interfaces:**
- Consumes: `validate_output_contract(root)` — existing.
- Produces: no new signature; adds assertions that later tasks rely on for safety.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_outputs.py
import json
import pytest
from validate_outputs import validate_output_contract, COUNTRY_FILES


def test_every_dashboard_produces_freshness_records():
    audit = json.loads(open("output/freshness_audit.json").read())
    dashboards = {r.get("dashboard") for r in audit.get("records", [])}
    assert len(dashboards) == len(COUNTRY_FILES), f"only {sorted(dashboards)} produced records"


def test_every_canonical_series_carries_trust_dimensions():
    import glob
    for path in glob.glob("output/*_canonical_frame.json"):
        for s in json.loads(open(path).read()).get("series", []):
            q = s.get("quality") or {}
            for field in ("source_authority", "freshness", "derivation"):
                assert q.get(field), f"{path}:{s.get('indicator_id')} missing {field}"
```

- [ ] **Step 2: Run test to verify it fails or passes for the right reason**

Run: `scripts/uv_project.sh run pytest tests/test_outputs.py -k "freshness_records or trust_dimensions" -v`
Expected: PASS if the 2026-08-28 freshness fix holds; if either fails, that is a real regression to fix before continuing.

- [ ] **Step 3: Add the same assertions to the build gate**

In `scripts/validate_outputs.py`, inside `validate_output_contract`, before `return messages`:

```python
    audit = _load_json(output / "freshness_audit.json")
    audit_dashboards = {row.get("dashboard") for row in audit.get("records") or []}
    if len(audit_dashboards) != len(COUNTRY_FILES):
        raise AssertionError(
            f"Freshness audit covers {sorted(audit_dashboards)}, expected all {len(COUNTRY_FILES)} dashboards"
        )

    for name in DATA_FIRST_NAMES:
        canonical = _load_json(output / f"{name}_canonical_frame.json")
        for item in canonical.get("series") or []:
            quality = item.get("quality") or {}
            missing = [f for f in ("source_authority", "freshness", "derivation") if not quality.get(f)]
            if missing:
                raise AssertionError(f"{name}:{item.get('indicator_id')} missing quality fields {missing}")
            if quality.get("source_authority") == "public_secondary":
                raise AssertionError(
                    f"{name}:{item.get('indicator_id')} classified public_secondary; declare source_authority in config"
                )
    messages.append("pipeline outcome contract ok")
```

- [ ] **Step 4: Run the full gate**

Run: `make validate`
Expected: PASS, with a new `pipeline outcome contract ok` line.

- [ ] **Step 5: Commit**

```bash
git add scripts/validate_outputs.py tests/test_outputs.py
git commit -m "test: assert pipeline outcomes, not only page structure"
```

---

### Task 4: Extract a shared adapter module

**Files:**
- Create: `src/country_primer/adapters.py`
- Modify: `scripts/build_japan_dashboard.py` (remove `fetch_imf_sdmx`, `fetch_imf_datamapper`, `_sdmx_period_to_date`, `_imf_sdmx_rows`, `apply_scale`, and their module constants; import from the new module instead)
- Modify: `scripts/build_south_africa_dashboard.py` (import from the new module instead of from the Japan builder)
- Test: `tests/test_adapters.py`

**Interfaces:**
- Produces, all importable from `country_primer.adapters`:
  - `sdmx_period_to_date(value: str) -> str | None`
  - `fetch_imf_sdmx(session, spec: dict) -> dict`
  - `fetch_imf_datamapper(session, spec: dict) -> dict`
  - `apply_scale(series: dict) -> dict`
  - `USER_AGENT: str`
- Tasks 5 and 6 add their fetchers to this module.

**Why:** `build_south_africa_dashboard.py` currently imports fetchers from `build_japan_dashboard.py`. A builder importing a fetcher from another builder is the wrong dependency direction and blocks reuse.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adapters.py
import pytest


def test_adapters_module_exposes_the_shared_fetchers():
    from country_primer import adapters
    for name in ("fetch_imf_sdmx", "fetch_imf_datamapper", "apply_scale", "sdmx_period_to_date"):
        assert hasattr(adapters, name), name


def test_sdmx_period_parsing():
    from country_primer.adapters import sdmx_period_to_date
    assert sdmx_period_to_date("2026-M06") == "2026-06-01"
    assert sdmx_period_to_date("2025-Q3") == "2025-07-01"
    assert sdmx_period_to_date("2024") == "2024-01-01"
    assert sdmx_period_to_date("garbage") is None


def test_apply_scale_divides_and_is_a_noop_without_scale():
    from country_primer.adapters import apply_scale
    scaled = apply_scale({"scale": 1_000_000_000, "observations": [{"date": "2026-06-01", "value": 5e9}]})
    assert scaled["observations"][0]["value"] == 5.0
    same = {"observations": [{"date": "2026-06-01", "value": 42.0}]}
    assert apply_scale(same)["observations"][0]["value"] == 42.0


def test_builders_no_longer_import_fetchers_from_each_other():
    source = open("scripts/build_south_africa_dashboard.py").read()
    assert "from build_japan_dashboard import" not in source
```

- [ ] **Step 2: Run test to verify it fails**

Run: `scripts/uv_project.sh run pytest tests/test_adapters.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'country_primer.adapters'`

- [ ] **Step 3: Create the module**

Create `src/country_primer/adapters.py`. Move these verbatim from `scripts/build_japan_dashboard.py`: `IMF_SDMX_BASE`, `IMF_DATAMAPPER_BASE`, `USER_AGENT`, `IMF_SDMX_LOCK`, `IMF_SDMX_CACHE`, `_sdmx_period_to_date` (rename to public `sdmx_period_to_date`), `_imf_sdmx_rows`, `fetch_imf_sdmx`, `fetch_imf_datamapper`, `apply_scale`. Add the module docstring:

```python
"""Shared source adapters used by more than one country builder.

Fetchers live here rather than inside a builder so that a country page never
has to import from another country page.
"""
```

- [ ] **Step 4: Rewire both builders**

In `scripts/build_japan_dashboard.py` delete the moved code and add:

```python
from country_primer.adapters import (
    USER_AGENT,
    apply_scale,
    fetch_imf_datamapper,
    fetch_imf_sdmx,
)
```

In `scripts/build_south_africa_dashboard.py` replace the `from build_japan_dashboard import (...)` block with the same import.

- [ ] **Step 5: Run tests and rebuild offline**

Run: `scripts/uv_project.sh run pytest tests/test_adapters.py -v && make rebuild-ui && make validate`
Expected: PASS; chart counts unchanged at Japan 46, South Africa 51.

- [ ] **Step 6: Commit**

```bash
git add src/country_primer/adapters.py scripts/build_japan_dashboard.py scripts/build_south_africa_dashboard.py tests/test_adapters.py output/
git commit -m "refactor: move shared fetchers into country_primer.adapters"
```

---

### Task 5: BOJ flat-file adapter

**Files:**
- Modify: `src/country_primer/adapters.py`
- Create: `tests/fixtures/boj_cgpi_sample.csv`
- Modify: `config/japan_indicators.yaml`, `scripts/build_japan_dashboard.py`
- Test: `tests/test_adapters.py`

**Interfaces:**
- Consumes: `USER_AGENT` from Task 4.
- Produces:
  - `parse_boj_wide_csv(text: str, series_code: str) -> list[dict]` returning `[{"date": "YYYY-MM-01", "value": float}, ...]`
  - `fetch_boj_flatfile(session, spec: dict) -> dict` where `spec` needs `boj_file` (e.g. `"cgpi_m_en"`) and `series` (e.g. `"PRCG20_2200000000"`)

- [ ] **Step 1: Create the fixture**

```bash
mkdir -p tests/fixtures
scripts/uv_project.sh run python -c "
import io, zipfile, requests
r = requests.get('https://www.stat-search.boj.or.jp/info/cgpi_m_en.zip', timeout=120)
z = zipfile.ZipFile(io.BytesIO(r.content))
text = z.read('cgpi_m_en.csv').decode('ascii', 'replace').splitlines()
head = text[0].split(',')
keep = [l for l in text[1:] if l.startswith('PRCG20_2200000000')][:1]
open('tests/fixtures/boj_cgpi_sample.csv','w').write(
    ','.join(head[:8]) + '\n' + '\n'.join(','.join(l.split(',')[:8]) for l in keep) + '\n')
print(open('tests/fixtures/boj_cgpi_sample.csv').read())
"
```

- [ ] **Step 2: Write the failing test**

```python
def test_parse_boj_wide_csv_reads_periods_from_the_header():
    from country_primer.adapters import parse_boj_wide_csv
    text = open("tests/fixtures/boj_cgpi_sample.csv").read()
    obs = parse_boj_wide_csv(text, "PRCG20_2200000000")
    assert obs, "expected observations for the all-commodities series"
    assert obs[0]["date"] == "2020-01-01"
    assert isinstance(obs[0]["value"], float)
    assert obs == sorted(obs, key=lambda o: o["date"])


def test_parse_boj_wide_csv_unknown_code_returns_empty():
    from country_primer.adapters import parse_boj_wide_csv
    text = open("tests/fixtures/boj_cgpi_sample.csv").read()
    assert parse_boj_wide_csv(text, "NOT_A_CODE") == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `scripts/uv_project.sh run pytest tests/test_adapters.py -k boj -v`
Expected: FAIL — cannot import name `parse_boj_wide_csv`

- [ ] **Step 4: Implement**

Append to `src/country_primer/adapters.py`:

```python
BOJ_FLATFILE_BASE = "https://www.stat-search.boj.or.jp/info"


def parse_boj_wide_csv(text: str, series_code: str) -> list[dict[str, Any]]:
    """Parse a BOJ flat file. Row 1 holds YYYYMM periods from column 4 onward;
    each data row is `code,dataset,label,v1..vN`."""
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    periods = rows[0][3:]
    for row in rows[1:]:
        if not row or row[0].strip() != series_code:
            continue
        observations: list[dict[str, Any]] = []
        for period, raw in zip(periods, row[3:]):
            period = period.strip()
            if len(period) != 6 or not period.isdigit():
                continue
            try:
                value = float(str(raw).strip())
            except (TypeError, ValueError):
                continue
            observations.append({"date": f"{period[:4]}-{period[4:6]}-01", "value": value})
        observations.sort(key=lambda item: item["date"])
        return observations
    return []


def fetch_boj_flatfile(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    name = str(spec["boj_file"])
    url = f"{BOJ_FLATFILE_BASE}/{name}.zip"
    response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=(5, 120))
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        member = next((n for n in archive.namelist() if n.endswith(".csv")), None)
        if member is None:
            raise RuntimeError(f"BOJ archive {name}.zip contains no CSV.")
        text = archive.read(member).decode("ascii", "replace")
    observations = parse_boj_wide_csv(text, str(spec["series"]))
    start_date = str(spec.get("start_date") or "")
    if start_date:
        observations = [o for o in observations if o["date"] >= start_date]
    if not observations:
        raise RuntimeError(f"BOJ {name} returned no observations for {spec['series']}.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": url,
    }
```

Add `import zipfile` to the module imports (`csv`, `io`, `requests`, `Any` are already present from Task 4).

- [ ] **Step 5: Run tests**

Run: `scripts/uv_project.sh run pytest tests/test_adapters.py -k boj -v`
Expected: PASS

- [ ] **Step 6: Wire the indicator and the fetcher branch**

In `config/japan_indicators.yaml`, add to `prices_costs` and remove the matching `data_gaps` entry for the corporate goods price index:

```yaml
  - id: producer_price_inflation
    section: prices_costs
    label_en: "Corporate Goods Price Index, YoY"
    label_zh: "企业物价指数同比"
    unit: "% y/y"
    transform: "yoy_pct"
    fetcher: boj_flatfile
    boj_file: "cgpi_m_en"
    series: "PRCG20_2200000000"
    source_name: "Bank of Japan / Corporate Goods Price Index"
    source_authority: official_primary
    source_url: "https://www.stat-search.boj.or.jp/info/dload_en.html"
    frequency: "monthly"
    start_date: "1995-01-01"
    caveat_en: "Domestic producer prices for all commodities, 2020 base. Derived year-over-year from the published index."
    caveat_zh: "全部商品的国内生产者价格，2020年基准。由公布指数派生的同比增速。"
```

In `scripts/build_japan_dashboard.py`, import `fetch_boj_flatfile` and add to `_fetch_one`:

```python
        if fetcher == "boj_flatfile":
            return _apply_transform(apply_scale(fetch_boj_flatfile(session, spec)))
```

- [ ] **Step 7: Build live and verify**

```bash
set -a && . ./.env.local && set +a
COUNTRY_PRIMER_SKIP_ARCHIVE=1 scripts/uv_project.sh run python scripts/build_japan_dashboard.py
scripts/uv_project.sh run python -c "
import json; s=json.load(open('output/japan_dashboard_summary.json'))
print('charts', s['charts'], 'gaps', s['data_gaps'], 'unavailable', s['unavailable'])"
```
Expected: charts 47, one fewer gap, `unavailable` empty.

- [ ] **Step 8: Commit**

```bash
git add src/country_primer/adapters.py tests/ config/japan_indicators.yaml scripts/build_japan_dashboard.py output/
git commit -m "feat: add BOJ flat-file adapter and Japan producer prices"
```

---

### Task 6: e-Stat adapter and the Japan CPI family

**Files:**
- Modify: `src/country_primer/adapters.py`
- Create: `tests/fixtures/estat_cpi_sample.json`
- Modify: `config/japan_indicators.yaml`, `scripts/build_japan_dashboard.py`, `.env.example`, `README.md`
- Test: `tests/test_adapters.py`

**Interfaces:**
- Produces:
  - `estat_time_to_date(value: str) -> str | None` — `"2026000808"` → `"2026-08-01"`
  - `fetch_estat(session, spec: dict) -> dict`; `spec` needs `stats_data_id`, `estat_tab`, `estat_cat01`, optional `estat_area` (default `"00000"`)
  - Raises `EstatCredentialMissing` when `ESTAT_APP_ID` is absent.

- [ ] **Step 1: Create the fixture**

```bash
set -a && . ./.env.local && set +a
scripts/uv_project.sh run python -c "
import os, json, requests
r = requests.get('https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData',
  params={'appId': os.environ['ESTAT_APP_ID'], 'statsDataId': '0004052037',
          'cdTab': '3', 'cdCat01': '0161', 'cdArea': '00000', 'limit': 24},
  timeout=(10, 240))
d = r.json()
vals = d['GET_STATS_DATA']['STATISTICAL_DATA']['DATA_INF']['VALUE']
json.dump({'GET_STATS_DATA': {'RESULT': {'STATUS': 0},
  'STATISTICAL_DATA': {'DATA_INF': {'VALUE': vals}}}},
  open('tests/fixtures/estat_cpi_sample.json','w'), ensure_ascii=False, indent=2)
print('rows:', len(vals))"
```
The fixture contains no credential — verify with `grep -c ESTAT tests/fixtures/estat_cpi_sample.json` returning 0.

- [ ] **Step 2: Write the failing test**

```python
def test_estat_time_parsing():
    from country_primer.adapters import estat_time_to_date
    assert estat_time_to_date("2026000808") == "2026-08-01"
    assert estat_time_to_date("2026000707") == "2026-07-01"
    assert estat_time_to_date("1970000000") is None


def test_estat_value_rows_parse_into_observations():
    import json
    from country_primer.adapters import estat_observations
    payload = json.load(open("tests/fixtures/estat_cpi_sample.json"))
    obs = estat_observations(payload)
    assert obs
    assert all(o["date"][4] == "-" and isinstance(o["value"], float) for o in obs)
    assert obs == sorted(obs, key=lambda o: o["date"])


def test_estat_without_credential_raises_a_typed_error(monkeypatch):
    from country_primer.adapters import EstatCredentialMissing, fetch_estat
    monkeypatch.delenv("ESTAT_APP_ID", raising=False)
    with pytest.raises(EstatCredentialMissing):
        fetch_estat(None, {"stats_data_id": "0004052037", "estat_tab": "3", "estat_cat01": "0161"})
```

- [ ] **Step 3: Run test to verify it fails**

Run: `scripts/uv_project.sh run pytest tests/test_adapters.py -k estat -v`
Expected: FAIL — cannot import name `estat_time_to_date`

- [ ] **Step 4: Implement**

Append to `src/country_primer/adapters.py`:

```python
ESTAT_BASE = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"


class EstatCredentialMissing(RuntimeError):
    """Raised when ESTAT_APP_ID is absent so the caller can fall back to a gap."""


def estat_time_to_date(value: str) -> str | None:
    """e-Stat encodes monthly periods as YYYY00MMMM; month is the last two digits."""
    text = str(value or "").strip()
    if len(text) != 10 or not text.isdigit():
        return None
    year, month = text[:4], text[8:10]
    if not ("01" <= month <= "12"):
        return None
    return f"{year}-{month}-01"


def estat_observations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = (
        payload.get("GET_STATS_DATA", {})
        .get("STATISTICAL_DATA", {})
        .get("DATA_INF", {})
        .get("VALUE")
    ) or []
    observations: list[dict[str, Any]] = []
    for row in rows:
        obs_date = estat_time_to_date(row.get("@time"))
        if not obs_date:
            continue
        try:
            observations.append({"date": obs_date, "value": float(row.get("$"))})
        except (TypeError, ValueError):
            continue
    observations.sort(key=lambda item: item["date"])
    return observations


def fetch_estat(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    app_id = os.environ.get("ESTAT_APP_ID", "").strip()
    if not app_id:
        raise EstatCredentialMissing("ESTAT_APP_ID is not set.")
    params = {
        "appId": app_id,
        "statsDataId": str(spec["stats_data_id"]),
        "cdTab": str(spec["estat_tab"]),
        "cdCat01": str(spec["estat_cat01"]),
        # Nationwide. Omitting this returns the Tokyo ward area, not Japan.
        "cdArea": str(spec.get("estat_area") or "00000"),
    }
    # e-Stat free-text search times out; narrow id lookups still need a long read.
    response = session.get(ESTAT_BASE, params=params, timeout=(10, 240))
    response.raise_for_status()
    payload = response.json()
    status = payload.get("GET_STATS_DATA", {}).get("RESULT", {}).get("STATUS")
    if status != 0:
        raise RuntimeError(f"e-Stat returned STATUS={status} for {spec['stats_data_id']}.")
    observations = estat_observations(payload)
    start_date = str(spec.get("start_date") or "")
    if start_date:
        observations = [o for o in observations if o["date"] >= start_date]
    if not observations:
        raise RuntimeError(f"e-Stat returned no observations for {spec['stats_data_id']}.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": ESTAT_BASE,
    }
```

Add `import os` if not already present.

- [ ] **Step 5: Run tests**

Run: `scripts/uv_project.sh run pytest tests/test_adapters.py -k estat -v`
Expected: PASS

- [ ] **Step 6: Wire graceful degradation into the builder**

In `scripts/build_japan_dashboard.py`, import `EstatCredentialMissing` and `fetch_estat`, add the branch, and skip cleanly when the key is absent:

```python
        if fetcher == "estat":
            return _apply_transform(apply_scale(fetch_estat(session, spec)))
```

and in `_fetch_one`, before the generic handler:

```python
    except EstatCredentialMissing as exc:
        # No credential is a configuration state, not a source failure: leave the
        # indicator unavailable so it renders as a documented gap.
        series = {**spec, "observations": [], "quality_status": "unavailable",
                  "quality_notes": [f"Requires ESTAT_APP_ID: {exc}"]}
```

- [ ] **Step 7: Add the four CPI indicators**

In `config/japan_indicators.yaml` add to `prices_costs`, using `tab: "3"` so the year-over-year rate is taken natively rather than derived. Repeat this block for each, changing only `id`, labels, and `estat_cat01`:

| id | `estat_cat01` | label_en |
|---|---|---|
| `core_inflation` | `0161` | Core CPI ex-Fresh Food, YoY |
| `core_core_inflation` | `0178` | Core-Core CPI ex-Fresh Food & Energy, YoY |
| `goods_inflation` | `0202` | Goods CPI, YoY |
| `services_inflation` | `0220` | Services CPI, YoY |

```yaml
  - id: core_inflation
    section: prices_costs
    label_en: "Core CPI ex-Fresh Food, YoY"
    label_zh: "核心CPI（剔除生鲜食品）同比"
    unit: "% y/y"
    fetcher: estat
    stats_data_id: "0004052037"
    estat_tab: "3"
    estat_cat01: "0161"
    estat_area: "00000"
    series: "0004052037/3/0161/00000"
    source_name: "e-Stat / Statistics Bureau CPI"
    source_authority: official_primary
    source_url: "https://www.e-stat.go.jp/en/dbview?sid=0004052037"
    frequency: "monthly"
    start_date: "1995-01-01"
    caveat_en: "The BoJ's policy reference measure. Year-over-year is published directly by the Statistics Bureau, not derived here. Nationwide, 2025 base."
    caveat_zh: "日银政策参考口径。同比由总务省统计局直接公布，非本页派生。全国口径，2025年基准。"
```

Remove the now-closed entries from `data_gaps`, and update the `prices_costs` `report_logic_en`/`report_logic_zh` to describe the native e-Stat path.

- [ ] **Step 8: Document the credential**

Append to `.env.example`:

```
# e-Stat (Japan Statistics Bureau) application ID. Register at
# https://www.e-stat.go.jp/en/api/ . Unlocks Japan core CPI, services and goods
# CPI. Absent, those indicators render as documented gaps.
ESTAT_APP_ID=
```

Add the matching row to the README credential table.

- [ ] **Step 9: Build live and verify**

```bash
set -a && . ./.env.local && set +a
COUNTRY_PRIMER_SKIP_ARCHIVE=1 scripts/uv_project.sh run python scripts/build_japan_dashboard.py
scripts/uv_project.sh run python -c "
import json, collections
d=json.load(open('output/japan_canonical_frame.json'))
print(collections.Counter((s.get('quality') or {}).get('status') for s in d['series']))"
```
Expected: charts 51; `verified` appears on the Japan page for the first time.

- [ ] **Step 10: Verify graceful degradation**

Run: `env -u ESTAT_APP_ID scripts/uv_project.sh run python scripts/build_japan_dashboard.py`
Expected: build succeeds; the four e-Stat indicators are absent rather than the build failing.

- [ ] **Step 11: Commit**

```bash
git add src/country_primer/adapters.py tests/ config/japan_indicators.yaml scripts/build_japan_dashboard.py .env.example README.md output/
git commit -m "feat: add e-Stat adapter and native Japan core/services/goods CPI"
```

---

### Task 7: Cross-check divergence computation

**Files:**
- Create: `src/country_primer/cross_checks.py`
- Modify: `config/south_africa_indicators.yaml`, `config/japan_indicators.yaml`
- Modify: `scripts/build_south_africa_dashboard.py`, `scripts/build_japan_dashboard.py`
- Test: `tests/test_cross_checks.py`

**Interfaces:**
- Produces: `evaluate_cross_checks(config: dict, series_list: list[dict]) -> list[dict]`, each result being
  `{"concept", "primary", "secondary", "label_en", "n_common", "latest_diff", "max_abs_diff", "n_breaches", "last_breach_date", "tolerance", "status"}`
  where `status` is `agree` | `minor` | `diverged` | `insufficient`.
- Task 8 asserts on these; Task 9 renders them.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cross_checks.py
from country_primer.cross_checks import evaluate_cross_checks

CONFIG = {"cross_checks": [{
    "concept": "headline_inflation", "primary": "a", "secondary": "b",
    "tolerance": 0.15, "label_en": "A vs B",
}]}


def _series(sid, points):
    return {"id": sid, "observations": [{"date": d, "value": v} for d, v in points],
            "frequency": "monthly", "transform": "level"}


def test_agreeing_sources_report_agree():
    series = [_series("a", [("2026-06-01", 4.3), ("2026-07-01", 5.0)]),
              _series("b", [("2026-06-01", 4.31), ("2026-07-01", 5.02)])]
    result = evaluate_cross_checks(CONFIG, series)[0]
    assert result["n_common"] == 2
    assert result["n_breaches"] == 0
    assert result["status"] == "agree"


def test_breach_beyond_tolerance_reports_diverged():
    series = [_series("a", [("2026-06-01", 4.3), ("2026-07-01", 5.0)]),
              _series("b", [("2026-06-01", 4.31), ("2026-07-01", 5.9)])]
    result = evaluate_cross_checks(CONFIG, series)[0]
    assert result["n_breaches"] == 1
    assert result["last_breach_date"] == "2026-07-01"
    assert result["status"] == "diverged"
    assert round(result["latest_diff"], 2) == -0.90


def test_no_overlap_reports_insufficient():
    series = [_series("a", [("2026-06-01", 4.3)]), _series("b", [("2025-01-01", 4.0)])]
    assert evaluate_cross_checks(CONFIG, series)[0]["status"] == "insufficient"


def test_missing_member_is_skipped_not_crashed():
    assert evaluate_cross_checks(CONFIG, [_series("a", [("2026-06-01", 4.3)])]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `scripts/uv_project.sh run pytest tests/test_cross_checks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'country_primer.cross_checks'`

- [ ] **Step 3: Implement**

Create `src/country_primer/cross_checks.py`:

```python
"""Compare two independent publication paths for the same concept.

This is primarily a regression test on the adapters: if a parser mis-scales a
series or selects the wrong column, the paired source diverges immediately.
"""
from __future__ import annotations

from typing import Any

DEFAULT_TOLERANCE = 0.15
MINOR_MULTIPLE = 2.0


def _by_date(series: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for item in series.get("observations") or []:
        try:
            out[str(item["date"])] = float(item["value"])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def evaluate_cross_checks(config: dict[str, Any], series_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(item.get("id")): item for item in series_list}
    results: list[dict[str, Any]] = []
    for pair in config.get("cross_checks") or []:
        primary = by_id.get(str(pair.get("primary")))
        secondary = by_id.get(str(pair.get("secondary")))
        if not primary or not secondary:
            continue
        tolerance = float(pair.get("tolerance") or DEFAULT_TOLERANCE)
        left, right = _by_date(primary), _by_date(secondary)
        common = sorted(set(left) & set(right))
        diffs = [(d, left[d] - right[d]) for d in common]
        breaches = [(d, v) for d, v in diffs if abs(v) > tolerance]
        max_abs = max((abs(v) for _, v in diffs), default=0.0)
        if not diffs:
            status = "insufficient"
        elif breaches:
            status = "diverged"
        elif max_abs > tolerance / MINOR_MULTIPLE:
            status = "minor"
        else:
            status = "agree"
        results.append({
            "concept": str(pair.get("concept") or ""),
            "primary": str(pair.get("primary")),
            "secondary": str(pair.get("secondary")),
            "label_en": str(pair.get("label_en") or ""),
            "n_common": len(common),
            "latest_diff": diffs[-1][1] if diffs else None,
            "max_abs_diff": max_abs,
            "n_breaches": len(breaches),
            "last_breach_date": breaches[-1][0] if breaches else "",
            "tolerance": tolerance,
            "status": status,
        })
    return results
```

- [ ] **Step 4: Run tests**

Run: `scripts/uv_project.sh run pytest tests/test_cross_checks.py -v`
Expected: PASS

- [ ] **Step 5: Declare the pairs**

In `config/south_africa_indicators.yaml`, at top level:

```yaml
cross_checks:
  - concept: headline_inflation
    primary: cpi_inflation          # SARB, compiling authority
    secondary: cpi_inflation_imf    # IMF SDMX, independent path
    tolerance: 0.15
    label_en: "SARB vs IMF headline CPI"
```

In `config/japan_indicators.yaml`, after Task 6 adds the e-Stat headline series (`estat_cat01: "0001"`, id `cpi_inflation_estat`):

```yaml
cross_checks:
  - concept: headline_inflation
    primary: cpi_inflation_estat    # e-Stat, compiling authority
    secondary: cpi_inflation        # IMF SDMX, independent path
    tolerance: 0.15
    label_en: "e-Stat vs IMF headline CPI"
```

Add `cpi_inflation_estat` to `config/japan_indicators.yaml` using the Task 6 block with `estat_cat01: "0001"`.

- [ ] **Step 6: Write results into both summaries**

In each builder's `build()`, after `apply_quality_assessments(series_list)`:

```python
    from country_primer.cross_checks import evaluate_cross_checks
    summary["cross_checks"] = evaluate_cross_checks(config, series_list)
```
placed with the other `summary[...]` assignments.

- [ ] **Step 7: Build both live and inspect**

```bash
set -a && . ./.env.local && set +a
COUNTRY_PRIMER_SKIP_ARCHIVE=1 scripts/uv_project.sh run python scripts/build_japan_dashboard.py
COUNTRY_PRIMER_SKIP_ARCHIVE=1 scripts/uv_project.sh run python scripts/build_south_africa_dashboard.py
scripts/uv_project.sh run python -c "
import json
for n in ('japan','south_africa'):
    for c in json.load(open(f'output/{n}_dashboard_summary.json')).get('cross_checks', []):
        print(n, c['label_en'], c['status'], 'n=', c['n_common'], 'max=', round(c['max_abs_diff'], 4))"
```
Expected: both `agree` or `minor`. **A `diverged` result here means an adapter bug — investigate before continuing.**

- [ ] **Step 8: Commit**

```bash
git add src/country_primer/cross_checks.py tests/test_cross_checks.py config/ scripts/ output/
git commit -m "feat: add cross-check divergence between publication paths"
```

---

### Task 8: Fail the build on divergence

**Files:**
- Modify: `scripts/validate_outputs.py`
- Test: `tests/test_outputs.py`

**Interfaces:**
- Consumes: `summary["cross_checks"]` from Task 7.

- [ ] **Step 1: Write the failing test**

```python
def test_cross_checks_are_present_and_within_tolerance():
    import json
    for name in ("japan", "south_africa"):
        summary = json.loads(open(f"output/{name}_dashboard_summary.json").read())
        checks = summary.get("cross_checks")
        assert checks, f"{name} declares no cross-checks"
        bad = [c for c in checks if c["status"] == "diverged"]
        assert not bad, f"{name} cross-checks diverged: {[c['label_en'] for c in bad]}"
```

- [ ] **Step 2: Run test**

Run: `scripts/uv_project.sh run pytest tests/test_outputs.py -k cross_check -v`
Expected: PASS after Task 7

- [ ] **Step 3: Add to the build gate**

In `validate_output_contract`, inside the `for name in DATA_FIRST_NAMES:` loop:

```python
        for check in summary.get("cross_checks") or []:
            if check.get("status") == "diverged":
                raise AssertionError(
                    f"{name} cross-check '{check.get('label_en')}' diverged: "
                    f"{check.get('n_breaches')} breaches beyond {check.get('tolerance')}, "
                    f"latest {check.get('last_breach_date')}"
                )
```

- [ ] **Step 4: Run the gate**

Run: `make validate`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/validate_outputs.py tests/test_outputs.py
git commit -m "test: fail the build when paired sources diverge"
```

---

### Task 9: Render the trust surface

**Files:**
- Modify: `scripts/build_china_dashboard.py` (`_chart_html`, `CSS`) — shared by all data-first pages
- Modify: `scripts/build_japan_dashboard.py`, `scripts/build_south_africa_dashboard.py` (page header)
- Test: `tests/test_chart_readouts.py`

**Interfaces:**
- Consumes: `series["data_quality"]["source_authority"|"freshness"]` from Tasks 1–2, `summary["cross_checks"]` from Task 7.

- [ ] **Step 1: Write the failing test**

```python
def test_chart_cards_show_source_authority_and_freshness():
    html = open("output/japan.html").read()
    assert 'class="authority-chip"' in html
    assert "official primary" in html or "official mirror" in html
    assert 'class="freshness-chip"' in html


def test_page_header_shows_provenance_mix():
    html = open("output/japan.html").read()
    assert "native official" in html


def test_cross_check_line_renders_on_paired_charts():
    html = open("output/south_africa.html").read()
    assert "cross-check" in html.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `scripts/uv_project.sh run pytest tests/test_chart_readouts.py -k "authority or provenance or cross_check" -v`
Expected: FAIL — `assert 'class="authority-chip"' in html`

- [ ] **Step 3: Render the chips**

In `scripts/build_china_dashboard.py`, `_chart_html`, replace the single `quality` pill block with:

```python
    quality_data = series.get("data_quality") or {}
    authority = escape(str(quality_data.get("source_authority", "")).replace("_", " "))
    freshness = escape(str(quality_data.get("freshness", "")).replace("_", " "))
    quality = escape(series.get("quality_status", "unchecked").replace("_", " "))
    chips = (
        f'<span class="quality-pill">{quality}</span>'
        f'<span class="authority-chip">{authority}</span>'
        f'<span class="freshness-chip">{freshness}</span>'
    )
```
and substitute `{chips}` where `<span class="quality-pill">{quality}</span>` was.

Add to `CSS`:

```css
.authority-chip, .freshness-chip {
  font-size: 11px; letter-spacing: .02em; padding: 2px 7px; border-radius: 999px;
  border: 1px solid rgba(23,19,16,0.16); color: var(--muted, #63574e); margin-left: 6px;
}
.authority-chip { background: rgba(63,111,80,0.10); }
.freshness-chip { background: rgba(54,75,97,0.10); }
.cross-check { font-size: 12px; color: #63574e; margin-top: 4px; }
.cross-check.diverged { color: #9d3d2e; }
```

- [ ] **Step 4: Render the provenance header**

In both new builders' `render_html`, add a chip alongside the existing `meta-chip` row:

```python
    authority_mix = collections.Counter(
        (item.get("data_quality") or {}).get("source_authority")
        for item in series_list if item.get("observations")
    )
    native = authority_mix.get("official_primary", 0)
    mirror = authority_mix.get("official_mirror", 0)
```
then in the f-string meta row:

```html
      <span class="meta-chip">{native} <span data-lang="en">native official</span><span data-lang="zh">原生官方</span> · {mirror} <span data-lang="en">mirror</span><span data-lang="zh">镜像</span></span>
```
Add `import collections` to each builder.

- [ ] **Step 5: Render the cross-check line**

In both builders, build a lookup before `_sections_html` and pass it through, appending under the chart footer for either member of a pair:

```python
    checks_by_id: dict[str, dict] = {}
    for check in evaluate_cross_checks(config, series_list):
        for side in (check["primary"], check["secondary"]):
            checks_by_id[side] = check
```
and in `_chart_html`, when the series id is present:

```python
    cross = (series.get("cross_check") or {})
    cross_html = ""
    if cross:
        ok = cross["status"] in {"agree", "minor"}
        mark = "✓ Agrees with" if ok else "⚠ Diverges from"
        detail = (f"{cross['n_common']} common periods · max gap {cross['max_abs_diff']:.2f}"
                  if ok else
                  f"latest gap {cross['latest_diff']:.2f} ({cross['last_breach_date']}) · "
                  f"{cross['n_breaches']} of {cross['n_common']} beyond {cross['tolerance']}")
        cls = "cross-check" if ok else "cross-check diverged"
        cross_html = f'<p class="{cls}">{mark} {escape(cross["label_en"])} · {escape(detail)}</p>'
```
Attach `series["cross_check"] = checks_by_id.get(series["id"])` in `build()` before rendering, and insert `{cross_html}` after the `<footer>` block.

- [ ] **Step 6: Rebuild and run tests**

```bash
set -a && . ./.env.local && set +a
COUNTRY_PRIMER_SKIP_ARCHIVE=1 scripts/uv_project.sh run python scripts/build_japan_dashboard.py
COUNTRY_PRIMER_SKIP_ARCHIVE=1 scripts/uv_project.sh run python scripts/build_south_africa_dashboard.py
scripts/uv_project.sh run pytest tests/test_chart_readouts.py -v
```
Expected: PASS

- [ ] **Step 7: Full build and gate**

Run: `make refresh-data && make validate`
Expected: PASS across all nine pages.

- [ ] **Step 8: Commit**

```bash
git add scripts/ tests/ output/ index.html
git commit -m "feat: surface source authority, freshness, and cross-checks on charts"
```

---

## Follow-on work, deliberately out of this plan

- **Additional e-Stat tables** — job-to-applicant ratio (MHLW), housing starts (MLIT), household consumption. The adapter and the discovery procedure exist after Task 6; each needs its own `statsDataId` and `cdCat01` resolved via `getStatsList` → `getMetaInfo` before it can be specified without placeholders.
- **IMF BOP / IIP / MFS_ODC expansion** for both countries. The seam is confirmed live through 2026-Q1 (`CAB`, `CABXEF`, `CKAB`, `ANPNFA`, `D1`…) but the indicator codes are not yet resolved.
- **BOJ SPPI, monthly BoP, Flow of Funds** — the adapter from Task 5 handles them; each needs its series codes read out of the relevant ZIP.
- **Eskom** — blocked, see spec E6. Revisit only if a documented API appears.
- **Vintage and revision tracking (P3)** — the agreed next spec.
