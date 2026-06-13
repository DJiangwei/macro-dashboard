# Eco Harness Source Review

Generated from the local reference files provided by the user:

- `eco_harness_skill.md`
- `eco_harness_README.md`

This note records how the Eco Data API Harness should inform this repo. It is a source-evaluation memo, not an instruction to install the harness wholesale.

## Decision

Do not install the full `app/eco_harness/` package into this dashboard now.

The dashboard already has a lighter typed-config and per-source-adapter architecture. Installing the full harness would add heavy optional dependencies (`akshare`, `wbgapi`, `dbnomics`, `opensdmx`, `boj-api`, `fredapi`) while duplicating existing fetchers. More importantly, the harness contains convenience methods that explicitly use proxies, such as mapping ISM manufacturing PMI to industrial production. That conflicts with this dashboard's current data policy: do not render fabricated or convenience proxies when a native source has not been validated.

Use the harness as a candidate-source map and interface-design reference:

- Keep every rendered series tied to a visible `source_name`, `source_url`, `series`, `frequency`, and caveat.
- Normalize successful fetches into date/value observations before chart generation.
- Gate API-key sources through ignored local environment variables, never committed keys.
- Prefer official native endpoints for release-sensitive country work before aggregator mirrors.
- Treat aggregator libraries as discovery or fallback tools, not as automatic authority.

## Source Assessment

| Harness source | Applies to | Current decision | Reason |
|---|---|---|---|
| FRED | US, some UK mirrors | Accepted where already used | FRED is a durable public backbone, especially for US official mirror series. For UK, native ONS/BoE remains preferred for release-sensitive data. |
| US Treasury FiscalData | US | Accepted | Already used for completed Treasury auction results. It is official, no-key, reproducible, and better than generic mirrors for auction data. |
| EIA Open Data | US energy | Candidate, not automatic | Useful for oil, gas, and energy macro channels if the direct EIA v2 endpoint is validated and `EIA_API_KEY` is available in `.env.local`. Do not commit keys. |
| AKShare | China | Candidate only | It can expose China-native macro data, but it wraps varied upstream providers and can change schemas. Use only behind an optional adapter with strict source labels, freshness checks, and no silent replacement of official NBS/PBOC/SAFE endpoints. |
| World Bank WDI | China and structural/global series | Accepted as lagged structural/annual data | Already used for China annual national-account, demographic, and structural series. It is not adequate for tactical monthly China macro data. |
| DBnomics | Global/OECD/IMF/BIS discovery | Candidate only | Useful for finding public datasets, but provider-specific definitions and freshness must still be validated before rendering. |
| OECD SDMX | UK/global candidates | Candidate only | Useful for public leading/survey data, but UK release-sensitive series should continue to prefer ONS/BoE. |
| ECB/Eurostat SDMX | CE4 and euro-area context | Accepted where native coverage is validated | CE4 already uses Eurostat-heavy official data. Future additions should preserve source-level validation. |
| Bank of Japan | Japan only | Out of current scope | Relevant if a Japan page is added later. |

## China Implications

The harness correctly identifies China as the area with the largest opportunity for source improvement, but AKShare should not be wired directly into production charts without validation. The priority order remains:

1. Official NBS/PBOC/SAFE/Customs/SAFE endpoints when reproducible from this runtime.
2. Official English or Chinese release pages parsed into stable date/value series.
3. Multilateral annual series such as World Bank WDI or IMF WEO for structural context.
4. AKShare as an optional helper only after endpoint provenance, schema, latest date, and failure behavior are documented.

Current China dashboard behavior is intentionally conservative. It renders WDI/IMF/SAFE/PBC data that can be fetched reproducibly and lists monthly NBS/PBOC gaps instead of filling them with proxies.

## UK Implications

The harness does not materially improve UK data quality versus the repo's current ONS/BoE path. For UK:

- Continue using ONS time-series JSON for GDP, output, labour, prices, fiscal, and household-sector indicators.
- Continue using Bank of England IADB for Bank Rate, SONIA, gilt yields, sterling, money, credit, and mortgage channels.
- Keep FRED/OECD/BIS/IMF only for concepts where no better native public UK endpoint has been validated, such as BIS REER or IMF reserve mirrors.
- Do not replace ONS/BoE with generic DBnomics/OECD fetches just because they are easier.

## US Implications

The US page is already aligned with the strongest parts of the harness:

- FRED is the main public backbone for US official mirrors.
- BLS direct API is used for selected BED series.
- Treasury FiscalData is used for auction quantities and bid-to-cover.

Potential future upgrades:

- Add direct EIA energy charts only where they improve over existing FRED official mirrors and can be refreshed with `EIA_API_KEY`.
- Consider direct BEA/Census adapters only if they provide freshness, detail, or metadata that FRED does not.
- Keep vendor-controlled series such as ISM, Conference Board, Redbook, and proprietary GS indicators as explicit data gaps unless a license-safe endpoint is validated.

## Implementation Notes For Future Agents

- Do not commit `FRED_API_KEY`, `EIA_API_KEY`, or any `.env.local` values.
- Do not add `akshare`, `dbnomics`, `opensdmx`, or `fredapi` to `pyproject.toml` merely because the harness recommends them.
- Before adding a new dependency, prove that the existing `requests`-based adapter approach cannot fetch the needed official endpoint.
- Before charting a new series, record its source, frequency, latest observation, definition caveat, and quality status in config/catalog output.
- If a candidate endpoint fails from this runtime, keep it in `data_gaps` with the failure mode instead of rendering a proxy.
