# Base-Metals Follow-ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the base-metals and precious-metals pages these new series:
- accumulated long SHFE inventory history (copper, aluminium, zinc, nickel);
- the SHFE copper near-minus-third-month spread;
- COMEX gold and silver stocks;
- Chilean and Peruvian copper mine output.

The China refined-copper probe is recorded as a gap.

**Architecture:**
- **Accumulation:** a generic `accumulate: true` indicator flag. The data-first pipeline merges each successful fetch into `data/accumulated/<scope>_<id>.json`. That directory travels on the `data` branch, and `scripts/data_branch.sh` refuses a push that would shrink it.
- **Fetchers:** new metals sources live in a new module `src/country_primer/metals_adapters.py`, registered in `fetchers.py` with `module="metals_adapters"`. The module holds four fetchers: the SHFE calendar spread, COMEX stocks, BCCh, and MINEM.

**Tech Stack:**
- Python 3.12, requests, AKShare (Sina, Eastmoney), openpyxl.
- BCCh SieteRestWS, gob.pe.
- pytest; POSIX sh for `data_branch.sh`.

**Spec:** `docs/superpowers/specs/2026-11-05-base-metals-followups-design.md`

## Global Constraints

- **Real data only.** A failed or unparsable fetch raises. It never writes 0, a placeholder or an estimate (handoff D1).
- **Keys** are read from the environment or `.env.local`. They never appear in code, config, logs or error text: errors name the source and status only.
- **No licensed data:** no LME, no official CME stocks, no Platts/Argus.
- **Source grades:**
  - AKShare/Sina/Eastmoney series: `source_authority: public_wrapper`.
  - BCCh (Cochilco mirror): `official_mirror`.
  - MINEM: `official_primary`.
- **Bilingual config:** every new indicator carries `label_en`, `label_zh`, `unit`, `source_name`, `source_url`, `caveat_en`, `caveat_zh`.
- **Sessions:** a daily series drops today's date, which is a session still in progress (same rule as `fetch_cn_futures_main`).
- **Ordering:** 2.1 accumulation → 2.2 spread → 2.4 COMEX stocks → 2.5 China probe → Chile → 2.3 Peru.

## Decisions taken while planning (not in the spec)

- **Nickel inventory symbol.** The AKShare symbol for SHFE nickel stocks is `镍`, not `沪镍`. The latter raises `ValueError` (probed 2026-11-06).
- **Spread price.** The spread uses each contract's **settlement** price (`settle`), not the close: a thin third-month contract's last trade can be stale.
- **China refined copper (spec 2.5) is a gap.** The probe was done while planning (2026-11-06). Eastmoney `RPT_INDUSTRY_INDEX` holds 52 indicators over 14 months; metals appear only as price indices (`EMI00135902` copper, etc.). There is no output or trade series, and `like` filters are rejected (code 9501). Per the spec, record it as a gap; Task 7 updates the text.
- **Peru: two series from one workbook.** The MINEM workbook `S01.C01` holds annual copper totals since 2000 plus only the current year's months.
  - `peru_copper_output_annual`: 2000 to the last complete year.
  - `peru_copper_output`: monthly, `accumulate: true`.
  - Both are converted from TMF to kt to match Chile's unit.
- **Shrink guard.** `data_branch.sh push` refuses to drop dates from an accumulated file. The source keeps only about three months, so lost history cannot be refetched.

## Review Focus

1. **Push from a stale checkout.** A push from a checkout that skipped `make pull-data` must not shorten accumulated history on the `data` branch. The push is refused unless `ALLOW_ACCUMULATED_SHRINK=1` (Task 2).
2. **Corrupt or empty accumulated file.** If `data/accumulated/x.json` is corrupt or empty, the series falls back to last-known-good and the file is left untouched; it is never overwritten with a short window (Task 1).
3. **Spread roll timing.**
   - On the last trading day before the near contract's delivery month, the spread already uses the next pair.
   - In the current, incomplete month, no roll is inferred from "the latest date so far" (Task 3).
4. **No BCCh key leak.** A BCCh network error must not leak the token into `source_health.json`, including when the token is not in `token=` form (Task 5).
5. **MINEM layout change.** If MINEM moves or renames the copper column, the parser raises a layout error and the page shows the old value as stale. It must never shift to another metal's column (Task 6).

---

### Task 1: Accumulation mechanism and SHFE stock series

**Files:**
- Create: `src/country_primer/accumulate.py`
- Modify: `src/country_primer/data_first_pipeline.py` (`fetch_one` inside `fetch_all`)
- Modify: `config/markets/base_metals.yaml` (three `shfe_*_stocks` entries, new `shfe_nickel_stocks`, inventories `report_logic_*`, `data_gaps` inventories item)
- Modify: `.gitignore` (add `data/accumulated/`)
- Test: `tests/test_accumulate.py`

**Interfaces:**
- Produces:
  - `ACCUMULATED_DIR: Path = ROOT / "data" / "accumulated"` (module constant; tests monkeypatch it).
  - `accumulated_path(scope: str, indicator_id: str, directory: Path | None = None) -> Path`. The file name is `f"{scope.lower()}_{indicator_id}.json"`.
  - `merge_observations(stored: list[dict], fresh: list[dict], revised_on: str) -> tuple[list[dict], list[dict]]`. Returns the merged observations, sorted by date with fresh values winning, and the new revision records `{"date", "previous", "value", "revised_on"}`, one for each date whose value changed.
  - `accumulate_series(series: dict, scope: str, today: date | None = None, directory: Path | None = None) -> dict`. It loads, merges and writes the file, then returns the series with merged `observations` and `accumulated_since` (the first stored date).
  - File schema: `{"schema_version": "accumulated-v1", "scope", "indicator_id", "source_name", "updated", "observations": [{"date","value"}], "revisions": [...]}`.

- [ ] **Step 1: Write the failing tests** in `tests/test_accumulate.py`:
  - `test_merge_keeps_old_dates_and_lets_fresh_values_win`:
    - stored `[2026-08-01:10, 2026-08-02:11]`, fresh `[2026-08-02:12, 2026-08-03:13]`, `revised_on="2026-11-06"`.
    - Merged equals `[08-01:10, 08-02:12, 08-03:13]`.
    - Revisions equal `[{"date":"2026-08-02","previous":11,"value":12,"revised_on":"2026-11-06"}]`.
  - `test_accumulate_series_writes_and_extends_history(tmp_path)`:
    - The first call with obs `[08-01, 08-02]` writes `base_shfe_copper_stocks.json` (`schema_version == "accumulated-v1"`).
    - A second call with `[08-02, 08-03]` returns three observations and `accumulated_since == "2026-08-01"`.
  - `test_empty_fetch_never_touches_the_file(tmp_path)`: after one write, a call with `observations: []` returns the series unchanged, and the file bytes are identical.
  - `test_corrupt_file_raises_and_is_preserved(tmp_path)`: with `{not json` written to the path, `accumulate_series` raises `RuntimeError` whose message names the file, and the file still reads `{not json`.
  - `test_pipeline_accumulates_flagged_specs(tmp_path, monkeypatch)`:
    - Monkeypatch `accumulate.ACCUMULATED_DIR` to `tmp_path`.
    - Run `fetch_all({"iso2": "BASE", "indicators": [spec_with_accumulate, spec_without]}, registry)`, where the registry returns fixed obs.
    - Only the flagged spec's file exists, and its returned series has `accumulated_since`.

- [ ] **Step 2: Run** `scripts/uv_project.sh run pytest -q tests/test_accumulate.py`. Expected: FAIL with `ModuleNotFoundError: country_primer.accumulate`.

- [ ] **Step 3: Implement `accumulate.py`.**
  - Write via a temp file in the same directory, then `os.replace`, so an interrupted run never leaves a half-written file.
  - `accumulate_series` returns the input unchanged when `series["observations"]` is empty.

- [ ] **Step 4: Hook the pipeline.** In `fetch_one`, after `series = {**spec, **series}` and only when `spec.get("accumulate")` and the series has observations, call `series = accumulate_series(series, country)` inside the existing `try`, so a `RuntimeError` becomes `failure_series(spec, exc)` like any fetch error.

- [ ] **Step 5: Config.** Make these changes in `base_metals.yaml`:
  - Add `accumulate: true` to `shfe_copper_stocks`, `shfe_aluminium_stocks` and `shfe_zinc_stocks`.
  - Add `shfe_nickel_stocks`, same shape as zinc, with `series: "镍"`, `label_en: "Nickel — SHFE Warehouse Stocks"` and `label_zh: "镍——上期所库存"`.
  - Replace the four caveats with:
    - `caveat_en`: "The source returns about the last three months; each refresh adds new days to a stored archive, so the history lengthens with every refresh (archive started November 2026)."
    - `caveat_zh`: "数据源仅返回约最近三个月；每次刷新把新数据并入存档，历史随之延长（存档始于2026年11月）。"
  - Inventories data gap:
    - `item_en`: "COMEX copper stocks"
    - `status_en`: "No free machine-readable COMEX copper source found (CME delivery reports unreachable; AKShare covers gold and silver only)."
    - Write matching zh text.
  - Add `data/accumulated/` to `.gitignore`.

- [ ] **Step 6: Run** `scripts/uv_project.sh run pytest -q tests/test_accumulate.py`, then `make validate`. Expected: both PASS.

- [ ] **Step 7: Commit:** "Accumulate short-window series; SHFE stocks keep their history"

### Task 2: Data branch carries accumulated files and refuses to shrink them

**Files:**
- Modify: `scripts/data_branch.sh` (`data_files`, `push`, new `files` subcommand)
- Create: `scripts/accumulated_guard.py` (stdlib only, so it runs under plain `python3` in CI)
- Test: `tests/test_data_branch.py`

**Interfaces:**
- Consumes: the Task 1 file schema (`observations[].date`).
- Produces:
  - `shrinking_files(branch_dir: Path, local_dir: Path) -> list[str]`: names of branch files that are missing locally or whose dates are not a subset of the local file's dates.
  - CLI `python3 scripts/accumulated_guard.py BRANCH_DIR LOCAL_DIR`: exits 1 and lists the names plus "run `make pull-data` first"; exits 0 when nothing would shrink.
  - `scripts/data_branch.sh files`: prints the file list that `push` would publish.

- [ ] **Step 1: Write the failing tests:**
  - `test_files_lists_accumulated_history(tmp_path)`: copy `scripts/data_branch.sh` to `tmp_path/scripts/`, then create `output/a.json`, `data/b.json` and `data/accumulated/base_x.json`. `sh scripts/data_branch.sh files` must print all three paths.
  - `test_guard_flags_missing_and_shortened_files(tmp_path)`:
    - branch has `x.json` (dates d1, d2) and `y.json` (d1);
    - local has `x.json` (d2, d3) and no `y.json`;
    - `shrinking_files` returns `["x.json", "y.json"]`.
  - `test_guard_passes_a_superset(tmp_path)`: local holds the branch dates plus newer ones, and the result is `[]`.

- [ ] **Step 2: Run** `scripts/uv_project.sh run pytest -q tests/test_data_branch.py`. Expected: FAIL. `files` prints the usage line and exits 2, and `accumulated_guard` is not importable.

- [ ] **Step 3: Implement.**
  - `data_files` adds `data/accumulated/*.json`.
  - `files)` prints `data_files`.
  - In `push`, right after `git worktree add`:
    ```sh
    if [ -d "$tmp/data/accumulated" ] && [ "${ALLOW_ACCUMULATED_SHRINK:-0}" != "1" ]; then
      python3 "$ROOT/scripts/accumulated_guard.py" "$tmp/data/accumulated" "$ROOT/data/accumulated"
    fi
    ```
  - `pull` needs no change: `git archive -- output data` already includes the subdirectory.

- [ ] **Step 4: Run** the same tests. Expected: PASS. Then run `make validate`.

- [ ] **Step 5: Docs.** In `docs/PAGES_DEPLOYMENT.md` and the HANDOFF option-C paragraph, add one line on `data/accumulated/`, the guard and `ALLOW_ACCUMULATED_SHRINK`.

- [ ] **Step 6: Commit:** "Data branch: sync accumulated history and refuse pushes that shrink it"

### Task 3: SHFE copper near-minus-third-month spread

**Files:**
- Create: `src/country_primer/metals_adapters.py`
- Modify: `src/country_primer/fetchers.py`: register `"cn_futures_calendar_spread": FetcherDef("fetch_cn_futures_calendar_spread", SPEC, RAW, "SHFE near minus third-month settle via Sina/AKShare", "metals_adapters")`
- Modify: `config/markets/base_metals.yaml` (new indicator in `china_futures`)
- Test: `tests/test_metals_adapters.py`

**Interfaces:**
- Produces:
  - `calendar_spread(settles: dict[str, dict[str, float]], start: str, today: str) -> list[dict]`. `settles` maps contract `YYMM` to `{date: settle}`; the result is `[{"date","value"}]` with value = settle(near) − settle(near+2 months).
  - `contract_months(start: str, today: str, ahead: int = 3) -> list[str]`: the `YYMM` codes from start's month to today's month + `ahead`.
  - `fetch_cn_futures_calendar_spread(spec: dict) -> dict`, with spec keys `series` (product code, e.g. `CU`) and `start_date`.

- [ ] **Step 1: Write the failing tests** (pure function, synthetic settles). Contracts 2601–2605 trade on 2025-12-29, 12-30, 12-31, 2026-01-02, 01-30, 02-02 and 02-09; `today="2026-02-10"`.
  - `test_spread_uses_near_and_third_month`: on 2025-12-30, value = s2601 − s2603.
  - `test_spread_rolls_on_last_trading_day_before_delivery_month`:
    - on 2025-12-31 (last December trading day in the data), value = s2602 − s2604;
    - on 2026-01-30 (last January day), value = s2603 − s2605.
  - `test_current_month_is_not_rolled_early`: 2026-02-09 is the latest date, but February is incomplete, so near stays 2603; value = s2603 − s2605.
  - `test_days_missing_a_leg_are_skipped`: delete s2603 on 12-30, and 12-30 is absent from the output.
  - `test_contract_months_span_start_to_three_ahead`: `contract_months("2025-11-15", "2026-01-20") == ["2511","2512","2601","2602","2603","2604"]`.

- [ ] **Step 2: Run** `scripts/uv_project.sh run pytest -q tests/test_metals_adapters.py`. Expected: FAIL (module missing).

- [ ] **Step 3: Implement `calendar_spread`.**
  - `L(m)` is the last trading day of calendar month `m` across all contracts, and is defined only for months before `today`'s month. A month that has not ended, or the month containing `today`, has `L(m) = +∞`.
  - Contract `M` is near on day `d` when it is the smallest `M` with `d < L(M − 1 month)`.
  - `L` is computed from all dates in the data, including dates before `start`. A past month with no trading days at all gives `L = −∞`.
  - Days are `start ≤ d < today`.

- [ ] **Step 4: Implement `fetch_cn_futures_calendar_spread`.**
  - For each code from `contract_months`, call `ak.futures_zh_daily_sina(symbol=f"{product}{yymm}")` through `adapters._call_with_timeout(..., timeout_seconds=30, label=...)`, reading columns `date` and `settle`.
  - A contract that errors or returns no rows is skipped. If the spread is empty, raise `RuntimeError`.
  - Return `api_url="https://finance.sina.com.cn/futuremarket/"` and `provider_updated` set to the last date.

- [ ] **Step 5: Run the tests.** Expected: PASS. Then do a live check:

  ```sh
  scripts/uv_project.sh run python -c "from country_primer.metals_adapters import fetch_cn_futures_calendar_spread as f; s=f({'series':'CU','start_date':'2024-01-01'}); print(len(s['observations']), s['observations'][-3:])"
  ```

  Expected: ≥ 400 observations, the latest dated before today, and values within ±5000 CNY/t.

- [ ] **Step 6: Config.** Add to `china_futures`:
  - `id: shfe_copper_calendar_spread`, `view: deep`
  - `label_en: "Copper — SHFE Near minus Third-Month Spread"`, `label_zh: "铜——上期所近月减第三月价差"`
  - `unit: CNY/t`, `frequency: daily`, `start_date: 2024-01-01`, `source_authority: public_wrapper`
  - `source_name: "SHFE contract settlements via Sina/AKShare"`, `source_url: "https://finance.sina.com.cn/futuremarket/"`
  - `caveat_en`: "Settlement of the nearest contract minus the contract two months later; positive = backwardation. The pair rolls on the last trading day before the near contract's delivery month."
  - `caveat_zh`: "最近合约结算价减其后第二个月合约结算价；正值为现货升水（backwardation）。在近月合约进入交割月前的最后一个交易日换月。"
  - Add `shfe_aluminium_calendar_spread` (`series: AL`, same wording with 铝/Aluminium) only after the copper live check in Step 5 passes.

- [ ] **Step 7: Run** `make validate` (expected PASS), then commit: "Base metals: SHFE copper and aluminium calendar spreads"

### Task 4: COMEX gold and silver stocks on the precious-metals page

**Files:**
- Modify: `src/country_primer/metals_adapters.py`, `src/country_primer/fetchers.py`: register `"comex_inventory": FetcherDef("fetch_comex_inventory", SPEC, RAW, "COMEX warehouse stocks via AKShare", "metals_adapters")`.
- Modify: `config/markets/precious_metals.yaml` (new section `inventories`, two indicators)
- Test: `tests/test_metals_adapters.py`

**Interfaces:**
- Produces:
  - `comex_observations(frame, today: str) -> list[dict]`: reads the column whose name ends in `-吨`, keeps dates before `today`, and drops non-numeric or non-positive values.
  - `fetch_comex_inventory(spec: dict) -> dict`, where `series` is the AKShare symbol `黄金` or `白银`.

- [ ] **Step 1: Write the failing test** `test_comex_observations_reads_tonnes_and_drops_today`:
  - Build a pandas frame with columns `序号, 日期, COMEX黄金库存量-吨, COMEX黄金库存量-盎司` and rows 2026-11-03 (719.26), 2026-11-04 (715.29) and 2026-11-06 (700.0).
  - With `today="2026-11-06"`, the result is `[{"date":"2026-11-03","value":719.26},{"date":"2026-11-04","value":715.29}]`.
  - A frame without a `-吨` column raises `ValueError`.
- [ ] **Step 2: Run** the test. Expected: FAIL (function missing).
- [ ] **Step 3: Implement** both functions. The fetch goes through `adapters._call_with_timeout` with a 60 s timeout. Use `api_url="https://www.cmegroup.com/clearing/operations-and-deliveries/nymex-delivery-notices.html"`.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Config.**
  - Add section `inventories`:
    - `title_en: "Exchange Inventories"`, `title_zh: "交易所库存"`
    - `report_logic_en: "COMEX registered plus eligible gold and silver stocks, in tonnes."`, `report_logic_zh: "COMEX黄金与白银库存（注册仓单加合格库存），单位吨。"`
  - Add `comex_gold_stocks` (`series: "黄金"`, `label_en: "Gold — COMEX Stocks"`, `label_zh: "黄金——COMEX库存"`) and `comex_silver_stocks` (`白银`, Silver/白银).
  - Both use `unit: t`, `frequency: daily`, `source_authority: public_wrapper`, `source_name: "COMEX stocks via AKShare"`.
  - Caveat: "Daily COMEX warehouse stocks compiled by AKShare from CME reports; history starts November 2021." / "AKShare据CME报告整理的COMEX每日库存；历史始于2021年11月。"
- [ ] **Step 6: Run** `make validate` (expected PASS), then commit: "Precious metals: COMEX gold and silver stocks"

### Task 5: Chilean copper mine output from the BCCh API

**Files:**
- Modify: `src/country_primer/metals_adapters.py`, `src/country_primer/fetchers.py`: register `"bcch_series": FetcherDef("fetch_bcch_series", SPEC, RAW, "Banco Central de Chile SieteRestWS (BCCH_API_TOKEN)", "metals_adapters")`.
- Modify: `src/country_primer/source_health.py` (`SECRET_ENV_NAMES` += `"BCCH_API_TOKEN"`)
- Modify: `.github/workflows/scheduled_refresh.yml` (refresh step env `BCCH_API_TOKEN: ${{ secrets.BCCH_API_TOKEN }}`)
- Modify: `config/markets/base_metals.yaml` (new section `mine_supply` placed before `monthly_benchmarks`; indicator; data gap text)
- Test: `tests/test_metals_adapters.py`, `tests/test_source_health.py`

**Interfaces:**
- Consumes: `energy_adapters._require_key`, `energy_adapters._get_json` (raises with source and status only).
- Produces:
  - `BCCH_URL = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"`.
  - `bcch_observations(payload: dict) -> list[dict]`. If `Codigo != 0`, it raises `RuntimeError(f"BCCh returned code {Codigo}: {Descripcion}")`. It maps `indexDateString` `dd-mm-yyyy` → `yyyy-mm-dd` and keeps only `statusCode == "OK"` rows with a finite numeric `value`.
  - `fetch_bcch_series(spec: dict) -> dict`, with params `token`, `function=GetSeries`, `timeseries=spec["series"]` and `firstdate=spec["start_date"]`.

- [ ] **Step 1: Write the failing tests:**
  - `test_bcch_observations_parses_ok_rows_only`:
    - Input `{"Codigo":0,"Series":{"Obs":[{"indexDateString":"01-07-2026","value":"444.1","statusCode":"OK"},{"indexDateString":"01-08-2026","value":"NaN","statusCode":"ND"}]}}`.
    - Result: `[{"date":"2026-07-01","value":444.1}]`.
  - `test_bcch_error_code_raises_without_details`: `{"Codigo":-5,"Descripcion":"Invalid username or password"}` raises `RuntimeError` matching `"code -5"`.
  - In `tests/test_source_health.py`, `test_bcch_token_is_redacted_outside_query_strings(monkeypatch)`: set env `BCCH_API_TOKEN="bcchsecret12345"`; then `_safe_message("params {'token': 'bcchsecret12345'}")` must not contain `bcchsecret12345`.
- [ ] **Step 2: Run** the tests. Expected: FAIL. The two BCCh parser tests fail because the function is missing. The redaction test fails because the token survives: it is not in `token=` form and not yet in `SECRET_ENV_NAMES`.
- [ ] **Step 3: Implement** the parser and the fetcher, add the name to `SECRET_ENV_NAMES`, and add the workflow env line.
- [ ] **Step 4: Run** the tests (expected: PASS). Then run a live check through `scripts/uv_project.sh run python -c ...` for `F034.PCUM.FLU.COCHILCO.Z.0.M` from 2000-01-01. Expected: 320+ monthly observations, the last ≥ 2026-08-01, values between 300 and 600.
- [ ] **Step 5: Config.**
  - Add section `mine_supply`:
    - `title_en: "Mine Supply"`, `title_zh: "矿山供给"`
    - `report_logic_en: "Copper mine output of the two largest producers: Chile (Cochilco, via the central bank) and Peru (Ministry of Energy and Mines)."`, `report_logic_zh: "两大产铜国的铜矿产量：智利（Cochilco，经央行数据库）与秘鲁（能源矿业部）。"`
  - Add indicator `chile_copper_output`:
    - `label_en: "Chile — Copper Mine Output"`, `label_zh: "智利——铜矿产量"`, `unit: kt`
    - `fetcher: bcch_series`, `series: F034.PCUM.FLU.COCHILCO.Z.0.M`, `frequency: monthly`, `start_date: 2000-01-01`
    - `source_authority: official_mirror`, `source_name: "Cochilco via Banco Central de Chile (BDE)"`, `source_url: "https://si3.bcentral.cl/siete"`
    - `caveat_en`: "Monthly mine output in thousand tonnes of fine copper, compiled by Cochilco and published in the central bank's statistics database; seasonal, compare with the same month a year earlier."
    - `caveat_zh`: "Cochilco编制、智利央行统计库发布的月度铜矿产量（千吨精铜）；有季节性，宜与上年同月比较。"
  - Data gap `monthly_benchmarks` "Mine supply…": drop Chile and Peru, keep "Indonesian nickel, TC/RC and ICSG balances".
- [ ] **Step 6: Run** `make validate` (expected PASS), then commit: "Base metals: Chilean copper mine output from the BCCh API"

### Task 6: Peruvian copper output from MINEM

**Files:**
- Modify: `src/country_primer/metals_adapters.py`, `src/country_primer/fetchers.py`: register `"minem_copper": FetcherDef("fetch_minem_copper", CACHE, RAW, "MINEM metallic production workbook (S01.C01)", "metals_adapters")`.
- Modify: `config/markets/base_metals.yaml` (two indicators in `mine_supply`)
- No committed fixture file: a test helper `_minem_workbook(copper_header="COBRE\nCopper", unit="TMF\nFTM") -> bytes` builds the workbook with openpyxl, mirroring the probed layout: sheet `S01.C01`; header row with first cell `PERIODO\nPeriod`, then `COBRE\nCopper`, `ORO*\nGold`; a unit row `TMF\nFTM`; year rows `2024` and `2025`; a YTD row `2026\n(Ene-Ago)\n(Jan-Aug)`; month rows `Ene. / Jan.` and `Feb. / Feb.`.
- Test: `tests/test_metals_adapters.py`

**Interfaces:**
- Produces:
  - `MINEM_COLLECTION_URL = "https://www.gob.pe/institucion/minem/colecciones/6-boletin-estadistico-minero"`.
  - `latest_minem_release(collection_html: str) -> str`: the path `/institucion/minem/informes-publicaciones/<id>-cuadros-estadisticos-mineros-prepublicacion-del-bem-<mes>-<año>` with the highest numeric id.
  - `minem_workbook_url(publication_html: str) -> str`: the `https://cdn.www.gob.pe/...xlsx` link whose path contains `s01-produccion-minera-metalica`.
  - `parse_minem_copper(content: bytes) -> dict[str, list[dict]]`, returning `{"annual": [...], "monthly": [...]}` in kt.
  - `fetch_minem_copper(spec: dict, cache: dict) -> dict`, where `spec["measure"]` is `"annual"` or `"monthly"`. The parse is cached in `cache["minem_copper"]` so both indicators share one download.

- [ ] **Step 1: Write the failing tests:**
  - `test_latest_release_picks_highest_prepublication_id`: given HTML with links `…/8604205-cuadros-…-julio-2026`, `…/8737012-boletin-estadistico-minero-agosto-2026` and `…/8736267-cuadros-…-agosto-2026`, the result ends with `8736267-cuadros-estadisticos-mineros-prepublicacion-del-bem-agosto-2026`.
  - `test_workbook_url_picks_metallic_production`: of two cdn links (`s01-produccion-minera-metalica…xlsx?v=1`, `s04-exportaciones…xlsx?v=1`), the s01 one is returned.
  - `test_parse_reads_copper_column_by_header`:
    - From the fixture (copper values 2024: 2736237.1, 2025: 2765994.5, Jan: 226465.1, Feb: 223285.3; gold values different), annual equals `[{"date":"2024-01-01","value":2736.2371},{"date":"2025-01-01","value":2765.9945}]` (approx) and monthly equals `[{"date":"2026-01-01",…226.4651},{"date":"2026-02-01",…223.2853}]`.
    - The YTD row is in neither list.
  - `test_parse_rejects_a_moved_copper_column`: rename the header `COBRE\nCopper` to `ZINC\nZinc`. The parser raises `ValueError` matching `"COBRE"`, and no observation from the other column is returned.
  - `test_parse_rejects_a_non_tonne_unit`: set the unit cell to `kgf\nfkg`, which raises `ValueError` matching `"TMF"`.
- [ ] **Step 2: Run** the tests. Expected: FAIL (functions missing).
- [ ] **Step 3: Implement.** Spanish month map: `Ene 1, Feb 2, Mar 3, Abr 4, May 5, Jun 6, Jul 7, Ago 8, Set 9, Sep 9, Oct 10, Nov 11, Dic 12`, matched on the label's first three letters. Rules:
  - The current year comes from the YTD row: a leading 4-digit year whose cell also contains `(`.
  - Month rows after it belong to that year.
  - Plain 4-digit year rows are annual.
  - Fetch with `USER_AGENT` from `energy_adapters`, with timeouts `(5, 60)`.
- [ ] **Step 4: Run** the tests (expected: PASS). Then run a live check of both measures. Expected:
  - annual 2000–2025, with 2025 ≈ 2766 kt;
  - monthly ≥ 8 points for 2026, January ≈ 226 kt.
- [ ] **Step 5: Config** in `mine_supply`. Both indicators use `fetcher: minem_copper`, `source_authority: official_primary`, `source_name: "MINEM, Boletín Estadístico Minero (cuadros estadísticos)"` and `source_url: MINEM_COLLECTION_URL`.
  - `peru_copper_output`:
    - `measure: monthly`, `accumulate: true`, `frequency: monthly`, `unit: kt`
    - `label_en: "Peru — Copper Mine Output"`, `label_zh: "秘鲁——铜矿产量"`
    - `caveat_en`: "Monthly output in thousand tonnes of fine copper from MINEM's statistical tables. Each release lists only the current year's months, so history accumulates from 2026; the latest month is preliminary and may be revised."
    - `caveat_zh`: "能源矿业部统计表中的月度铜产量（千吨精铜）。每期只列当年各月，因此历史从2026年起累积；最新月份为初值，可能修订。"
  - `peru_copper_output_annual`:
    - `measure: annual`, `frequency: annual`, `unit: kt`, `view: deep`
    - `label_en: "Peru — Copper Mine Output (annual)"`, `label_zh: "秘鲁——铜矿产量（年度）"`
    - `caveat_en`: "Calendar-year totals from the same table; the current partial year is excluded."
    - `caveat_zh`: "取自同一张表的年度合计；不含当年未完成年份。"
- [ ] **Step 6: Run** `make validate` (expected PASS), then commit: "Base metals: Peruvian copper output from MINEM"

### Task 7: China probe record, docs, data and live check

**Files:**
- Modify: `config/markets/base_metals.yaml` (`china_demand` data gap)
- Modify: `docs/HANDOFF.md` (§6 item 3 status, §7 source notes for BCCh, MINEM, COMEX stocks and the spread)
- Modify: `PROJECT_LESSONS.md`
- Modify: the spec, setting its status line to "已实施（2026-11-06）"

- [ ] **Step 1: China gap text.** Set `status_en`:

  > "NBS is not reachable from this environment. Eastmoney's industry-indicator table (RPT_INDUSTRY_INDEX) was searched on 2026-11-06: it carries metal price indices only, no refined output or product trade."

  Write matching zh text.
- [ ] **Step 2: Docs.**
  - HANDOFF §6 item 3: list what shipped and what remains: China refined copper, Indonesian nickel, and the aluminium spread if Task 3 deferred it.
  - HANDOFF §7: one row each for BCCh (token, `Codigo -5` on a bad token, HTTP 200), MINEM (`S01.C01` layout, release discovery) and Sina contracts (`settle`, expired contracts still served).
  - `PROJECT_LESSONS.md`: one line on accumulation and the shrink guard.
- [ ] **Step 3: Verify.**
  - Run `make validate`, then `make golden-diff`. Expected: differences only in the BASE and PRECIOUS pages and their summaries, plus catalog/freshness files.
  - Run `scripts/uv_project.sh run python scripts/source_health_report.py`: no new failures for BASE or PRECIOUS.
- [ ] **Step 4: Ship.**
  - Commit and open the PR. Merge it when CI is green (project rule).
  - Then dispatch `Scheduled Macro Data Refresh & Publish` with `country=BASE`, then `country=PRECIOUS`. This uses the CI secret, which proves `BCCH_API_TOKEN` is set there.
- [ ] **Step 5: Live check.**
  - The run conclusions are `success`.
  - The `data` branch contains `data/accumulated/base_shfe_copper_stocks.json`.
  - The live `output/base_metals_canonical_frame.json` and `output/precious_metals_canonical_frame.json` contain the new ids with observations.
  - `scripts/publish_smoke.py --version <data sha>` passes.
