def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()



def _apply_transform(value: float, transform: str | None) -> float:
    if transform == "usd_trn":
        return value / 1_000_000_000_000
    if transform == "usd_mn_to_trn":
        return value / 1_000_000
    if transform == "usd_100mn_to_trn":
        return value / 10_000
    if transform == "usd_thousand_to_bn":
        return value / 1_000_000
    if transform == "cny_100mn_to_trn":
        return value / 10_000
    if transform == "cny_100mn_to_bn":
        return value / 10
    if transform == "cny_10k_to_bn":
        return value / 100_000
    if transform == "cny_yuan_to_trn":
        return value / 1_000_000_000_000
    if transform == "index_100_to_yoy":
        return value - 100
    if transform == "people_billion":
        return value / 1_000_000_000
    return value



def _parse_period_date(value: Any) -> str | None:
    if hasattr(value, "date"):
        value = value.date()
    if hasattr(value, "isoformat"):
        return value.isoformat()

    text = _clean_text(str(value))
    if not text or text.lower() in {"nan", "none", "nat"}:
        return None

    match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:\s+\d{1,2}:\d{2}:\d{2})?$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"

    match = re.match(r"^(\d{4})(\d{2})$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-01"

    match = re.match(r"^(\d{4})年(\d{1,2})月份$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-01"

    match = re.match(r"^(\d{4})-(\d{1,2})月$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-01"

    match = re.match(r"^(\d{4})年(\d{1,2})月$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-01"

    match = re.match(r"^(\d{4})年(\d{1,2})月(\d{1,2})日$", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"

    match = re.match(r"^(\d{4})年第(\d)(?:-(\d))?季度$", text)
    if match:
        quarter = int(match.group(3) or match.group(2))
        month = quarter * 3
        day = 31 if month in {3, 12} else 30
        return f"{int(match.group(1)):04d}-{month:02d}-{day:02d}"

    match = re.match(r"^(\d{4})[.\-/](\d{1,2})(?:[.\-/](\d{1,2}))?$", text)
    if match:
        day = int(match.group(3) or 1)
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{day:02d}"

    return None



def fetch_world_bank(spec: dict[str, Any]) -> dict[str, Any]:
    code = spec["series"]
    url = f"https://api.worldbank.org/v2/country/CHN/indicator/{code}"
    response = requests.get(url, params={"format": "json", "per_page": 20000}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    meta = payload[0] if isinstance(payload, list) and payload else {}
    rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
    observations: list[dict[str, Any]] = []
    for row in rows:
        raw_value = row.get("value")
        if raw_value is None:
            continue
        try:
            value = _apply_transform(float(raw_value), spec.get("transform"))
        except (TypeError, ValueError):
            continue
        observations.append({"date": str(row.get("date")), "value": value})
    observations.sort(key=lambda item: item["date"])
    return {
        **spec,
        "observations": observations,
        "provider_updated": meta.get("lastupdated", ""),
        "api_url": url,
    }



def fetch_imf_datamapper(spec: dict[str, Any]) -> dict[str, Any]:
    code = spec["series"]
    url = f"https://www.imf.org/external/datamapper/api/v1/{code}/CHN"
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    payload = response.json()
    country_values = ((payload.get("values") or {}).get(code) or {}).get("CHN") or {}
    observations = [
        {"date": str(year), "value": _apply_transform(float(value), spec.get("transform"))}
        for year, value in country_values.items()
        if value is not None and str(year).isdigit()
    ]
    observations.sort(key=lambda item: int(item["date"]))
    return {
        **spec,
        "observations": observations,
        "provider_updated": datetime.now(UTC).date().isoformat(),
        "api_url": url,
    }



def fetch_fred_graph(spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch a public FRED graph CSV without requiring a runtime API key."""
    code = spec["series"]
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    params = {"id": code}
    if spec.get("start_date"):
        params["cosd"] = str(spec["start_date"])
    response = requests.get(url, params=params, timeout=45)
    response.raise_for_status()
    observations: list[dict[str, Any]] = []
    for row in DictReader(StringIO(response.text)):
        raw_date = row.get("observation_date")
        raw_value = row.get(code)
        if not raw_date or raw_value in (None, "", "."):
            continue
        try:
            value = _apply_transform(float(raw_value), spec.get("transform"))
        except (TypeError, ValueError):
            continue
        observations.append({"date": raw_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": f"{url}?id={code}",
    }



def _fetch_akshare_frame(spec: dict[str, Any], cache: dict[str, Any] | None = None) -> Any:
    try:
        import akshare as ak  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("AKShare is not installed in the project environment.") from exc

    function_name = spec["function"]
    args = spec.get("args") or []
    kwargs = spec.get("kwargs") or {}
    cache_key = json.dumps({"function": function_name, "args": args, "kwargs": kwargs}, ensure_ascii=False, sort_keys=True)
    if cache is not None and cache_key in cache:
        frame = cache[cache_key]
    else:
        fetcher = getattr(ak, function_name)
        timeout_seconds = int(spec.get("timeout_seconds", 45))
        attempts = int(spec.get("retries", 2))
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                if timeout_seconds:
                    def _timeout_handler(signum: int, frame: Any) -> None:  # noqa: ARG001
                        raise TimeoutError(f"AKShare fetch timed out after {timeout_seconds}s for {function_name}")

                    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
                    signal.alarm(timeout_seconds)
                    try:
                        frame = fetcher(*args, **kwargs)
                    finally:
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, old_handler)
                else:
                    frame = fetcher(*args, **kwargs)
                break
            except Exception as exc:  # noqa: BLE001 - retry flaky upstream wrappers once before degrading.
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(2)
                else:
                    raise last_error
        if cache is not None:
            cache[cache_key] = frame
    return frame



def fetch_akshare_table(spec: dict[str, Any], cache: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is not installed in the project environment.") from exc

    frame = _fetch_akshare_frame(spec, cache)
    filter_column = spec.get("filter_column")
    if filter_column and spec.get("filter_value") is not None:
        frame = frame[frame[filter_column].astype(str) == str(spec["filter_value"])]
    date_column = spec["date_column"]
    value_column = spec.get("value_column")
    value_columns = spec.get("value_columns") or []
    observations: list[dict[str, Any]] = []

    for _, row in frame.iterrows():
        raw_date = row.get(date_column)
        if pd.isna(raw_date):
            continue
        if value_columns:
            raw_values = [row.get(column) for column in value_columns]
            if any(pd.isna(raw_value) for raw_value in raw_values):
                continue
            try:
                values = [float(raw_value) for raw_value in raw_values]
            except (TypeError, ValueError):
                continue
            operation = spec.get("value_operation", "sum")
            if operation == "difference":
                raw_value = values[0] - values[1]
            elif operation == "ratio":
                raw_value = values[0] / values[1] if values[1] else None
            else:
                raw_value = sum(values)
            if raw_value is None:
                continue
        else:
            raw_value = row.get(value_column)
            if pd.isna(raw_value):
                continue
        parsed_date = _parse_period_date(raw_date)
        if not parsed_date:
            continue
        try:
            value = _apply_transform(float(raw_value), spec.get("transform"))
        except (TypeError, ValueError):
            continue
        observations.append({"date": parsed_date, "value": value})

    observations.sort(key=lambda item: item["date"])
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": spec.get("source_url", ""),
    }



def fetch_akshare_wide_year_month(spec: dict[str, Any], cache: dict[str, Any] | None = None) -> dict[str, Any]:
    """Parse AKShare tables with month rows and year columns, e.g. CPCA."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is not installed in the project environment.") from exc

    frame = _fetch_akshare_frame(spec, cache)
    date_column = spec["date_column"]
    observations: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        month_text = _clean_text(str(row.get(date_column, "")))
        month_match = re.match(r"^(\d{1,2})月$", month_text)
        if not month_match:
            continue
        month = int(month_match.group(1))
        for column in frame.columns:
            year_match = re.match(r"^(\d{4})年$", str(column))
            if not year_match:
                continue
            raw_value = row.get(column)
            if pd.isna(raw_value):
                continue
            try:
                value = _apply_transform(float(raw_value), spec.get("transform"))
            except (TypeError, ValueError):
                continue
            observations.append({"date": f"{int(year_match.group(1)):04d}-{month:02d}-01", "value": value})

    observations.sort(key=lambda item: item["date"])
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": spec.get("source_url", ""),
    }



def fetch_eastmoney_industry_indicator(spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch Eastmoney's reusable industry-index API by stable INDICATOR_ID."""
    indicator_id = spec["indicator_id"]
    value_column = spec.get("value_column", "INDICATOR_VALUE")
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "sortColumns": "REPORT_DATE",
        "sortTypes": "-1",
        "pageSize": str(spec.get("page_size", 1000)),
        "pageNumber": "1",
        "reportName": "RPT_INDUSTRY_INDEX",
        "columns": "REPORT_DATE,INDICATOR_ID,INDICATOR_NAME,INDICATOR_VALUE,CHANGE_RATE,CHANGERATE_3M,CHANGERATE_6M,CHANGERATE_1Y,CHANGERATE_2Y,CHANGERATE_3Y",
        "filter": f'(INDICATOR_ID="{indicator_id}")',
        "source": "WEB",
        "client": "WEB",
    }
    response = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=45)
    response.raise_for_status()
    payload = response.json()
    rows = ((payload.get("result") or {}).get("data") or [])
    observations: list[dict[str, Any]] = []
    seen: set[tuple[str, float]] = set()
    for row in rows:
        parsed_date = _parse_period_date(row.get("REPORT_DATE"))
        raw_value = row.get(value_column)
        if not parsed_date or raw_value is None:
            continue
        try:
            value = _apply_transform(float(raw_value), spec.get("transform"))
        except (TypeError, ValueError):
            continue
        key = (parsed_date, value)
        if key in seen:
            continue
        seen.add(key)
        observations.append({"date": parsed_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": response.url,
    }



def _safe_rows() -> list[list[str]]:
    end = date.today()
    start = end - timedelta(days=365)
    response = requests.post(
        "https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do",
        data={"startDate": start.isoformat(), "endDate": end.isoformat(), "queryYN": "true"},
        timeout=45,
    )
    response.raise_for_status()
    rows: list[list[str]] = []
    for tr in re.findall(r'<tr[^>]*class="first"[^>]*>(.*?)</tr>', response.text, flags=re.S):
        cells = [
            _clean_text(re.sub(r"<.*?>", "", cell))
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)
        ]
        cells = [cell for cell in cells if cell]
        if len(cells) >= 3 and re.match(r"\d{4}-\d{2}-\d{2}", cells[0]):
            rows.append(cells)
    rows.sort(key=lambda item: item[0])
    return rows



def fetch_safe_midpoint(spec: dict[str, Any], rows: list[list[str]]) -> dict[str, Any]:
    column = 1 if spec["id"] == "usd_cny_midpoint" else 2
    observations: list[dict[str, Any]] = []
    for row in rows:
        try:
            value = float(row[column]) / 100.0
        except (IndexError, TypeError, ValueError):
            continue
        observations.append({"date": row[0], "value": value})
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": spec["source_url"],
    }



def fetch_pbc_card(card: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(card["url"], timeout=30)
    response.raise_for_status()
    text = re.sub(r"<[^>]+>", "\n", response.text)
    lines = [_clean_text(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    title = card["expected_title"]
    title_idx = next((i for i, line in enumerate(lines) if line == title), -1)
    value = "n/a"
    if title_idx >= 0:
        for line in lines[title_idx + 1 : title_idx + 14]:
            if re.match(r"^-?\d+(?:\.\d+)?(?:%|TN|BN|MN)?$", line, flags=re.I):
                value = line
                break
    update_idx = next((i for i, line in enumerate(lines) if line == "Latest Update"), -1)
    updated = ""
    if update_idx >= 0:
        for line in lines[update_idx + 1 : update_idx + 5]:
            if re.match(r"\d{2}/\d{2}/\d{4}", line):
                updated = line
                break
    return {**card, "value": value, "updated": updated or "n/a"}



def fetch_all(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    safe_rows: list[list[str]] | None = None
    akshare_cache: dict[str, Any] = {}
    series_list: list[dict[str, Any]] = []
    for spec in config.get("indicators", []):
        fetcher = spec.get("fetcher")

        def operation() -> dict[str, Any]:
            nonlocal safe_rows
            if fetcher == "world_bank":
                return fetch_world_bank(spec)
            if fetcher == "imf_datamapper":
                return fetch_imf_datamapper(spec)
            if fetcher == "fred_graph_csv":
                return fetch_fred_graph(spec)
            if fetcher == "akshare_table":
                return fetch_akshare_table(spec, akshare_cache)
            if fetcher == "eastmoney_api":
                return fetch_eastmoney(requests.Session(), spec)
            if fetcher == "nbs_api":
                try:
                    return fetch_nbs_api(requests.Session(), spec)
                except Exception as exc:
                    fallback = spec.get("fallback")
                    if fallback == "eastmoney_api":
                        print(f"Fallback triggered for {spec.get('id')}: {exc}")
                        return fetch_eastmoney(requests.Session(), spec)
                    elif fallback == "akshare_table":
                        print(f"Fallback triggered for {spec.get('id')}: {exc}")
                        return fetch_akshare_table(spec, akshare_cache)
                    raise exc
            if fetcher == "akshare_wide_year_month":
                return fetch_akshare_wide_year_month(spec, akshare_cache)
            if fetcher == "eastmoney_industry_indicator":
                return fetch_eastmoney_industry_indicator(spec)
            if fetcher == "safe_rmb_midpoint":
                if safe_rows is None:
                    safe_rows = _safe_rows()
                return fetch_safe_midpoint(spec, safe_rows)
            raise ValueError(f"Unknown fetcher: {fetcher}")

        try:
            series = guarded_source_call(
                country="CN",
                indicator_id=str(spec.get("id") or "unknown"),
                source_id=str(fetcher or "unknown"),
                operation=operation,
            )
        except Exception as exc:  # noqa: BLE001 - structured degradation is intentional.
            series = failure_series(spec, exc)
        series_list.append(validate_series(series))

    cards: list[dict[str, Any]] = []
    for card in config.get("latest_cards", []):
        try:
            cards.append(guarded_source_call(
                country="CN",
                indicator_id=str(card.get("id") or card.get("label_en") or "pbc_card"),
                source_id="pbc_card",
                operation=lambda card=card: fetch_pbc_card(card),
                record_empty=False,
            ))
        except Exception as exc:  # noqa: BLE001
            cards.append({**card, "value": "n/a", "updated": "n/a", "error": str(exc)})
    return series_list, cards



def _parse_date(value: str) -> date | None:
    value = _clean_text(str(value or ""))
    value = re.sub(r"\s+\[[^\]]+\]$", "", value).strip()
    quarter_match = re.match(r"^(\d{4})\s+Q([1-4])$", value, flags=re.I)
    if quarter_match:
        year = int(quarter_match.group(1))
        month = int(quarter_match.group(2)) * 3
        return date(year, month, monthrange(year, month)[1])
    quarter_range_match = re.match(
        r"^([A-Za-z]{3,9})\s+to\s+([A-Za-z]{3,9})\s+(\d{4})$",
        value,
        flags=re.I,
    )
    if quarter_range_match:
        year = int(quarter_range_match.group(3))
        month = MONTHS.get(quarter_range_match.group(2).lower())
        if month:
            return date(year, month, monthrange(year, month)[1])
    month_match = re.match(r"^(\d{4})\s+([A-Za-z]{3,9})$", value)
    if month_match:
        year = int(month_match.group(1))
        month = MONTHS.get(month_match.group(2).lower())
        if month:
            return date(year, month, 1)
    month_first_match = re.match(r"^([A-Za-z]{3,9})\s+(\d{4})$", value)
    if month_first_match:
        month = MONTHS.get(month_first_match.group(1).lower())
        if month:
            return date(int(month_first_match.group(2)), month, 1)
    for fmt, length in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            return datetime.strptime(value[:length], fmt).date()
        except ValueError:
            continue
    for fmt in ("%d %b %Y", "%d %B %Y", "%d %b %y", "%d/%m/%Y", "%b-%y", "%B-%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None



def fetch_fred(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    observations: list[dict[str, Any]]
    provider_updated: str
    used_api = False
    try:
        observations, provider_updated = _fred_api_observations(session, spec)
        used_api = bool(observations)
    except Exception:  # noqa: BLE001 - API key may be absent/invalid; graph CSV is the durable fallback.
        observations, provider_updated = [], ""
    if not observations:
        observations, provider_updated = _fred_graph_observations(session, spec)
    elif used_api:
        provider_updated = _fred_api_series_updated(session, str(spec["series"])) or provider_updated
    observations = _apply_transform(_start_filter(observations, spec.get("start_date")), spec)
    provider_updated = _provider_updated_date(provider_updated)
    return {
        **spec,
        "observations": observations,
        "provider_updated": provider_updated or (observations[-1]["date"] if observations else ""),
        "api_url": FRED_API_URL if os.environ.get("FRED_API_KEY") else FRED_GRAPH_URL,
    }



def fetch_ons_timeseries(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    path = _ons_path(spec)
    url = f"{ONS_TIMESERIES_BASE}{path}" if path.startswith("/") else path
    response = session.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=(4, 20))
    response.raise_for_status()
    payload = response.json()
    frequency = str(spec.get("frequency", "")).lower()
    rows_by_frequency = {
        "monthly": payload.get("months") or [],
        "quarterly": payload.get("quarters") or [],
        "annual": payload.get("years") or [],
    }
    if frequency not in rows_by_frequency:
        raise ValueError(
            f"ONS series {spec.get('series')!r} ({spec.get('id')!r}) declares unsupported "
            f"frequency {frequency!r}; expected one of {sorted(rows_by_frequency)}."
        )
    rows = rows_by_frequency[frequency]
    if not rows:
        # Do NOT silently fall back to whatever array the payload happens to
        # carry (e.g. "months" for a series that is actually quarterly) — that
        # produces a chart whose label ("monthly") contradicts its data. Fail
        # loudly so a mislabeled config gets caught at build time, not shipped
        # with a confident "verified" badge.
        available = sorted(key for key in ("months", "quarters", "years") if payload.get(key))
        raise ValueError(
            f"ONS series {spec.get('series')!r} ({spec.get('id')!r}) declares frequency "
            f"{frequency!r} but the ONS payload has no {frequency!r} observations at {url}; "
            f"payload only carries {available or ['none']}. Check the declared frequency "
            f"against the ONS dataset before relabeling or repointing this indicator."
        )
    observations: list[dict[str, Any]] = []
    provider_updated = ""
    for row in rows:
        raw_value = row.get("value")
        if raw_value in (None, "", "."):
            continue
        obs_date = _normalise_date(str(row.get("date") or row.get("label") or ""))
        if not obs_date:
            continue
        try:
            value = float(str(raw_value).replace(",", ""))
        except (TypeError, ValueError):
            continue
        provider_updated = str(row.get("updateDate") or provider_updated)
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    observations = _apply_transform(_start_filter(observations, spec.get("start_date")), spec)
    description = payload.get("description") or {}
    provider_updated = str(description.get("releaseDate") or provider_updated or "")
    if provider_updated:
        provider_updated = provider_updated[:10]
    return {
        **spec,
        "observations": observations,
        "provider_updated": provider_updated or (observations[-1]["date"] if observations else ""),
        "api_url": url,
        "current_value": str(description.get("number") or ""),
    }



def fetch_boe_iadb(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    series_code = str(spec["series"]).strip()
    params = {
        "csv.x": "yes",
        "Datefrom": _boe_date_param(spec.get("start_date")),
        "Dateto": "now",
        "SeriesCodes": series_code,
        "CSVF": "TN",
        "UsingCodes": "Y",
        "VPD": "Y",
        "VFD": "N",
    }
    response = session.get(BOE_IADB_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=(4, 20))
    response.raise_for_status()
    if "<html" in response.text[:200].lower():
        raise RuntimeError(f"BoE IADB rejected series code {series_code}.")
    rows = csv.DictReader(io.StringIO(response.text))
    observations: list[dict[str, Any]] = []
    for row in rows:
        raw_value = row.get(series_code)
        if raw_value in (None, "", "."):
            continue
        obs_date = _normalise_date(str(row.get("DATE") or ""))
        if not obs_date:
            continue
        try:
            value = float(str(raw_value).replace(",", ""))
        except (TypeError, ValueError):
            continue
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    observations = _apply_transform(_start_filter(observations, spec.get("start_date")), spec)
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": response.url,
    }



def fetch_boe_bank_rate(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    response = session.get(
        BOE_BANK_RATE_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        timeout=(4, 12),
    )
    response.raise_for_status()
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", response.text, flags=re.S | re.I)
    observations: list[dict[str, Any]] = []
    for row in rows:
        cells = [
            _clean_text(re.sub(r"<[^>]+>", " ", cell))
            for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S | re.I)
        ]
        if len(cells) < 2 or cells[0].lower().startswith("date"):
            continue
        obs_date = _parse_boe_short_date(cells[0])
        if not obs_date:
            continue
        try:
            value = float(cells[1].replace("%", ""))
        except ValueError:
            continue
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    observations = _start_filter(observations, spec.get("start_date"))
    current_match = re.search(r'<p class="stat-figure">([^<]+)</p>', response.text)
    current_value = _clean_text(current_match.group(1)) if current_match else ""
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": BOE_BANK_RATE_URL,
        "current_value": current_value,
    }



def fetch_govuk_road_fuel(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    csv_url = str(spec.get("csv_url") or "").strip()
    distribution_name = ""
    if not csv_url:
        csv_url, distribution_name = _govuk_distribution_url(session, spec, ".csv")
    response = session.get(csv_url, headers={"User-Agent": USER_AGENT}, timeout=(4, 20))
    response.raise_for_status()
    rows = csv.DictReader(io.StringIO(response.content.decode("utf-8-sig", errors="replace")))
    date_column = str(spec.get("date_column") or "Date")
    value_column = str(spec.get("value_column") or "")
    value_contains = str(spec.get("value_column_contains") or "").lower()
    observations: list[dict[str, Any]] = []
    for row in rows:
        if not value_column:
            value_column = next((name for name in row if value_contains and value_contains in name.lower()), "")
        if not value_column:
            raise ValueError("Road-fuel CSV value column could not be inferred.")
        obs_date = _normalise_date(str(row.get(date_column) or ""))
        raw_value = row.get(value_column)
        if not obs_date or raw_value in (None, "", "."):
            continue
        try:
            value = float(str(raw_value).replace(",", ""))
        except (TypeError, ValueError):
            continue
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    observations = _apply_transform(_start_filter(observations, spec.get("start_date")), spec)
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": csv_url,
        "distribution_name": distribution_name,
    }



def fetch_govuk_xlsx_table(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    xlsx_url = str(spec.get("xlsx_url") or "").strip()
    distribution_name = ""
    if not xlsx_url:
        xlsx_url, distribution_name = _govuk_distribution_url(session, spec, ".xlsx")
    content = _download_binary(session, xlsx_url)
    rows = _xlsx_sheet_rows(content, str(spec["sheet_name"]))
    date_column = str(spec.get("date_column") or "Period")
    value_column = str(spec["value_column"])
    header_index = -1
    date_index = -1
    value_index = -1
    for index, row in enumerate(rows):
        lowered = [str(item).strip().lower() for item in row]
        if date_column.lower() in lowered and value_column.lower() in lowered:
            header_index = index
            date_index = lowered.index(date_column.lower())
            value_index = lowered.index(value_column.lower())
            break
    if header_index < 0:
        raise ValueError(f"Columns {date_column!r}/{value_column!r} not found in XLSX.")

    observations: list[dict[str, Any]] = []
    for row in rows[header_index + 1 :]:
        if len(row) <= max(date_index, value_index):
            continue
        obs_date = _normalise_date(str(row[date_index]))
        raw_value = row[value_index]
        if not obs_date or raw_value in (None, "", "."):
            continue
        try:
            value = float(str(raw_value).replace(",", ""))
        except (TypeError, ValueError):
            continue
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    observations = _apply_transform(_start_filter(observations, spec.get("start_date")), spec)
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": xlsx_url,
        "distribution_name": distribution_name,
    }



def fetch_govuk_ods_table(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    ods_url = str(spec.get("ods_url") or "").strip()
    distribution_name = ""
    if not ods_url:
        ods_url, distribution_name = _govuk_distribution_url(session, spec, ".ods")
    content = _download_binary(session, ods_url)
    if not content.startswith(b"PK"):
        raise RuntimeError("GOV.UK ODS URL did not return a zipped ODS workbook.")
    rows = _ods_sheet_rows(content, str(spec["sheet_name"]))
    date_column = str(spec.get("date_column") or "Month and year")
    value_column = str(spec["value_column"])
    header_index = -1
    date_index = -1
    value_index = -1
    for index, row in enumerate(rows):
        lowered = [str(item).strip().lower() for item in row]
        if date_column.lower() in lowered and value_column.lower() in lowered:
            header_index = index
            date_index = lowered.index(date_column.lower())
            value_index = lowered.index(value_column.lower())
            break
    if header_index < 0:
        raise ValueError(f"Columns {date_column!r}/{value_column!r} not found in ODS.")
    observations = _table_observations(
        rows,
        spec,
        header_index=header_index,
        date_index=date_index,
        value_index=value_index,
    )
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": ods_url,
        "distribution_name": distribution_name,
    }



def fetch_ons_xlsx_table(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch a simple ONS xlsx worksheet with a Time period column and one value column."""
    xlsx_candidates = [(str(spec["xlsx_url"]), "configured")] if spec.get("xlsx_url") else _ons_distribution_candidates(
        session,
        spec,
        ".xlsx",
    )
    last_error: Exception | None = None
    for xlsx_url, distribution_name in xlsx_candidates:
        try:
            content = _download_binary(session, xlsx_url)
            if not content.startswith(b"PK"):
                raise RuntimeError("ONS xlsx candidate did not return an XLSX workbook.")
            rows = _xlsx_sheet_rows(content, str(spec["sheet_name"]))
            date_column = str(spec.get("date_column") or "Time period")
            value_column = str(spec["value_column"])
            header_index = -1
            date_index = -1
            value_index = -1
            for index, row in enumerate(rows):
                lowered = [str(item).strip().lower() for item in row]
                if date_column.lower() in lowered and value_column.lower() in lowered:
                    header_index = index
                    date_index = lowered.index(date_column.lower())
                    value_index = lowered.index(value_column.lower())
                    break
            if header_index < 0:
                raise ValueError(f"Columns {date_column!r}/{value_column!r} not found in ONS XLSX.")
            observations = _table_observations(
                rows,
                spec,
                header_index=header_index,
                date_index=date_index,
                value_index=value_index,
            )
            return {
                **spec,
                "observations": observations,
                "provider_updated": observations[-1]["date"] if observations else "",
                "api_url": xlsx_url,
                "distribution_name": distribution_name,
            }
        except Exception as exc:  # noqa: BLE001 - try visible dated ONS links if the current link is stale.
            last_error = exc
            continue
    raise last_error or RuntimeError("No ONS XLSX candidate could be parsed.")



def fetch_ons_horizontal_csv_table(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch an ONS CSV where multiple tables are laid out horizontally."""
    csv_candidates = [(str(spec["csv_url"]), "configured")] if spec.get("csv_url") else _ons_distribution_candidates(
        session,
        spec,
        ".csv",
    )
    table_title = str(spec["table_title_contains"]).lower()
    date_column = str(spec.get("date_column") or "Time period")
    value_column = str(spec["value_column"])
    last_error: Exception | None = None
    for csv_url, distribution_name in csv_candidates:
        try:
            response = session.get(csv_url, headers={"User-Agent": USER_AGENT}, timeout=(4, 20))
            response.raise_for_status()
            rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig", errors="replace"))))
            start_col = -1
            title_row_index = -1
            for row_index, row in enumerate(rows):
                for column_index, cell in enumerate(row):
                    if table_title in str(cell).lower():
                        start_col = column_index
                        title_row_index = row_index
                        break
                if start_col >= 0:
                    break
            if start_col < 0:
                raise ValueError(f"Table title containing {table_title!r} not found in ONS CSV.")

            header_index = -1
            date_index = -1
            value_index = -1
            for index in range(title_row_index + 1, min(title_row_index + 8, len(rows))):
                row = rows[index]
                if len(row) <= start_col:
                    continue
                lowered = [str(item).strip().lower() for item in row]
                if lowered[start_col] != date_column.lower():
                    continue
                for column_index in range(start_col + 1, len(lowered)):
                    if lowered[column_index] == value_column.lower():
                        header_index = index
                        date_index = start_col
                        value_index = column_index
                        break
                if header_index >= 0:
                    break
            if header_index < 0:
                raise ValueError(f"Columns {date_column!r}/{value_column!r} not found in ONS CSV.")
            observations = _table_observations(
                rows,
                spec,
                header_index=header_index,
                date_index=date_index,
                value_index=value_index,
            )
            return {
                **spec,
                "observations": observations,
                "provider_updated": observations[-1]["date"] if observations else "",
                "api_url": csv_url,
                "distribution_name": distribution_name,
            }
        except Exception as exc:  # noqa: BLE001 - try the next official ONS download candidate.
            last_error = exc
            continue
    raise last_error or RuntimeError("No ONS horizontal CSV candidate could be parsed.")



def fetch_obr_xlsx_row(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch one horizontal row from an OBR EFO workbook.

    OBR EFO tables often put forecast years across columns and indicator names
    down rows. This adapter keeps those fiscal forecast additions config-driven.
    """
    xlsx_url = str(spec.get("xlsx_url") or "").strip()
    if not xlsx_url:
        raise ValueError("OBR XLSX row fetcher requires xlsx_url.")
    content = _download_binary(session, xlsx_url)
    if not content.startswith(b"PK"):
        raise RuntimeError("OBR xlsx URL did not return an XLSX workbook.")
    rows = _xlsx_sheet_rows(content, str(spec["sheet_name"]))
    row_label = _clean_text(str(spec["row_label"])).lower()
    context = _clean_text(str(spec.get("context_above_contains") or "")).lower()
    target_index = -1
    for index, row in enumerate(rows):
        cleaned = [_clean_text(str(cell)).lower() for cell in row]
        if row_label not in cleaned:
            continue
        if context:
            above = " ".join(
                " ".join(_clean_text(str(cell)).lower() for cell in rows[above_index])
                for above_index in range(max(0, index - 8), index)
            )
            if context not in above:
                continue
        target_index = index
        break
    if target_index < 0:
        raise ValueError(f"OBR row {spec['row_label']!r} not found in {spec['sheet_name']!r}.")

    header_index = -1
    header_dates: dict[int, str] = {}
    for index in range(target_index - 1, -1, -1):
        candidates = {
            column_index: _normalise_obr_period(str(cell))
            for column_index, cell in enumerate(rows[index])
            if _normalise_obr_period(str(cell))
        }
        if len(candidates) >= 3:
            header_index = index
            header_dates = {column_index: value for column_index, value in candidates.items() if value}
            break
    if header_index < 0 or not header_dates:
        raise ValueError(f"Date header not found above OBR row {spec['row_label']!r}.")

    observations: list[dict[str, Any]] = []
    target_row = rows[target_index]
    for column_index, obs_date in header_dates.items():
        if column_index >= len(target_row):
            continue
        raw_value = target_row[column_index]
        if raw_value in (None, "", ".", "-", " - "):
            continue
        try:
            value = float(str(raw_value).replace(",", ""))
        except (TypeError, ValueError):
            continue
        observations.append({"date": obs_date, "value": value})
    observations.sort(key=lambda item: item["date"])
    observations = _apply_transform(_start_filter(observations, spec.get("start_date")), spec)
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"] if observations else "",
        "api_url": xlsx_url,
    }



def fetch_fred_us(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    if os.environ.get("FRED_API_KEY", "").strip():
        return fetch_fred(session, spec)

    last_error: Exception | None = None
    for read_timeout in (8, 16):
        try:
            observations, provider_updated = _fred_graph_observations_us(session, spec, read_timeout)
            if not observations:
                raise RuntimeError("FRED graph returned no observations.")
            if provider_updated:
                try:
                    provider_updated = parsedate_to_datetime(provider_updated).date().isoformat()
                except (TypeError, ValueError):
                    provider_updated = str(provider_updated)
            return {
                **spec,
                "observations": observations,
                "provider_updated": provider_updated or (observations[-1]["date"] if observations else ""),
                "api_url": FRED_GRAPH_URL,
            }
        except Exception as exc:  # noqa: BLE001 - retry with a larger read timeout.
            last_error = exc
    raise last_error or RuntimeError("FRED graph fetch failed.")



def _fetch_bls_batch(session: requests.Session, specs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    start_year = min(int(str(item.get("start_date", "1992-01-01"))[:4]) for item in specs)
    end_year = datetime.now(UTC).year
    series_ids = sorted({str(item["series"]) for item in specs})
    registration_key = os.environ.get("BLS_API_KEY", "").strip()
    observations_by_series: dict[str, dict[str, float]] = {series_id: {} for series_id in series_ids}

    # BLS public API range limits are tighter without a registration key. Keep
    # the unregistered path conservative so automated refreshes do not drop BED.
    chunk_years = 20 if registration_key else 10
    for chunk_start in range(start_year, end_year + 1, chunk_years):
        chunk_end = min(chunk_start + chunk_years - 1, end_year)
        payload_body: dict[str, Any] = {
            "seriesid": series_ids,
            "startyear": str(chunk_start),
            "endyear": str(chunk_end),
        }
        if registration_key:
            payload_body["registrationkey"] = registration_key

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = session.post(
                    BLS_API_URL,
                    json=payload_body,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                    timeout=(5, 30),
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("status") != "REQUEST_SUCCEEDED":
                    raise RuntimeError("; ".join(payload.get("message") or ["BLS API request failed."]))
                break
            except Exception as exc:  # noqa: BLE001 - retry transient BLS throttling/transport failures.
                last_error = exc
                if attempt < 2:
                    time.sleep(1.0 * (2 ** attempt))
        else:
            raise last_error or RuntimeError("BLS API request failed.")

        for series_payload in payload.get("Results", {}).get("series") or []:
            series_id = str(series_payload.get("seriesID", ""))
            if series_id not in observations_by_series:
                continue
            bucket = observations_by_series[series_id]
            for row in series_payload.get("data") or []:
                obs_date = _bls_period_to_date(str(row.get("year", "")), str(row.get("period", "")))
                value = _numeric(row.get("value"))
                if not obs_date or value is None:
                    continue
                bucket[obs_date] = value
        time.sleep(0.25)

    result = {
        series_id: [
            {"date": obs_date, "value": value}
            for obs_date, value in sorted(values.items())
        ]
        for series_id, values in observations_by_series.items()
    }
    _write_bls_bed_cache(result)
    return result



def fetch_bls_api(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    global BLS_BATCH_ERROR

    series_id = str(spec["series"])
    with BLS_LOCK:
        if series_id not in BLS_CACHE and not BLS_BATCH_ERROR:
            try:
                BLS_CACHE.update(_fetch_bls_batch(session, _bls_config_specs()))
            except Exception as exc:  # noqa: BLE001 - preserve one failure for all BLS specs in this run.
                BLS_BATCH_ERROR = str(exc)
        if BLS_BATCH_ERROR:
            cache_payload = _load_bls_bed_cache()
            observations = list((cache_payload.get("series") or {}).get(series_id) or [])
            if observations:
                cache_date = str(cache_payload.get("generated") or "")[:10]
                caveat_en = (
                    str(spec.get("caveat_en") or "").rstrip()
                    + " Live BLS API quota was unavailable in this run; rendering the last-good official BED cache."
                ).strip()
                caveat_zh = (
                    str(spec.get("caveat_zh") or "").rstrip()
                    + " 本次运行BLS实时API额度不可用；当前渲染最近一次验证成功的官方BED缓存。"
                ).strip()
                return {
                    **spec,
                    "observations": observations,
                    "provider_updated": cache_date or observations[-1]["date"],
                    "api_url": BLS_API_URL,
                    "caveat_en": caveat_en,
                    "caveat_zh": caveat_zh,
                }
            raise RuntimeError(BLS_BATCH_ERROR)
        observations = list(BLS_CACHE.get(series_id) or [])

    start_date = str(spec.get("start_date", ""))
    if start_date:
        observations = [item for item in observations if str(item["date"]) >= start_date]

    if not observations:
        raise RuntimeError(f"BLS API returned no observations for {series_id}.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": BLS_API_URL,
    }



def fetch_treasury_auctions(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "auction_date",
        "security_type",
        "total_accepted",
        "total_tendered",
        "bid_to_cover_ratio",
        "high_yield",
        "high_investment_rate",
    ]
    filters = [f"auction_date:gte:{spec.get('start_date', '2018-01-01')}", "total_accepted:gt:0"]
    security_types = list(spec.get("security_types") or [])
    if len(security_types) == 1:
        filters.append(f"security_type:eq:{security_types[0]}")
    elif security_types:
        filters.append(f"security_type:in:({','.join(security_types)})")

    rows: list[dict[str, Any]] = []
    page_number = 1
    total_pages = 1
    while page_number <= total_pages:
        response = session.get(
            TREASURY_AUCTIONS_URL,
            params={
                "fields": ",".join(fields),
                "filter": ",".join(filters),
                "page[size]": int(spec.get("page_size", 5000)),
                "page[number]": page_number,
                "sort": "auction_date",
            },
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=(5, 30),
        )
        response.raise_for_status()
        payload = response.json()
        rows.extend(payload.get("data") or [])
        total_pages = int(payload.get("meta", {}).get("total-pages") or page_number)
        page_number += 1

    aggregate = str(spec.get("aggregate", "monthly_sum"))
    metric = str(spec.get("metric", "total_accepted"))
    scale = float(spec.get("scale", 1))
    buckets: dict[str, dict[str, float]] = {}
    for row in rows:
        auction_date = str(row.get("auction_date") or "")
        if len(auction_date) < 7:
            continue
        month = f"{auction_date[:7]}-01"
        bucket = buckets.setdefault(month, {"value": 0.0, "count": 0.0, "numerator": 0.0, "denominator": 0.0})
        if aggregate == "monthly_weighted_bid_to_cover":
            numerator = _numeric(row.get("total_tendered"))
            denominator = _numeric(row.get("total_accepted"))
            if numerator is None or denominator in (None, 0):
                continue
            bucket["numerator"] += numerator
            bucket["denominator"] += denominator
        else:
            value = _numeric(row.get(metric))
            if value is None:
                continue
            bucket["value"] += value
            bucket["count"] += 1

    observations: list[dict[str, Any]] = []
    for month, bucket in sorted(buckets.items()):
        if aggregate == "monthly_weighted_bid_to_cover":
            denominator = bucket["denominator"]
            if denominator == 0:
                continue
            value = bucket["numerator"] / denominator
        elif aggregate == "monthly_average":
            count = bucket["count"]
            if count == 0:
                continue
            value = bucket["value"] / count
        else:
            value = bucket["value"]
        observations.append({"date": month, "value": value / scale})

    if not observations:
        raise RuntimeError("Treasury FiscalData returned no completed auction observations.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": TREASURY_AUCTIONS_URL,
    }




def fetch_sarb(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    """Fetch one SARB Web Indicators timeseries code.

    The bare ``/{code}`` form of this endpoint returns only the last 25
    observations, which is too short to chart, so the explicit date-range form
    is always used.
    """
    code = str(spec["series"])
    start_date = str(spec.get("start_date") or "1990-01-01")
    end_date = datetime.now(UTC).date().isoformat()
    url = f"{SARB_BASE}/{code}/{start_date}/{end_date}"
    response = session.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=(5, 45),
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError(f"SARB returned an unexpected payload for {code}.")

    frequency = str(spec.get("frequency") or "").strip().lower()
    observations: list[dict[str, Any]] = []
    for row in payload:
        period = str(row.get("Period") or "")[:10]
        raw_value = row.get("Value")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", period) or raw_value is None:
            continue
        if frequency == "monthly":
            # SARB stamps monthly readings with the last calendar day of the
            # reference month (e.g. "2026-07-31"); every other source in this
            # repo (FRED, IMF SDMX, e-Stat) stamps the first day instead. Align
            # to that convention so same-period observations from independent
            # sources share a date key for cross-source comparison.
            period = f"{period[:7]}-01"
        try:
            observations.append({"date": period, "value": float(raw_value)})
        except (TypeError, ValueError):
            continue
    observations.sort(key=lambda item: item["date"])
    if not observations:
        raise RuntimeError(f"SARB returned no observations for {code}.")
    return {
        **spec,
        "observations": observations,
        "provider_updated": observations[-1]["date"],
        "api_url": url,
    }




