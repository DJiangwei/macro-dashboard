import sys

with open("src/country_primer/adapters.py", "r") as f:
    content = f.read()

new_func = """def fetch_estat(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
    app_id = os.environ.get("ESTAT_APP_ID", "").strip()
    if not app_id:
        raise EstatCredentialMissing("ESTAT_APP_ID is not set.")
    params = {
        "appId": app_id,
        "statsDataId": str(spec["stats_data_id"]),
    }
    for key in ["cdTab", "cdCat01", "cdCat02", "cdCat03", "cdArea"]:
        spec_key = "estat_" + key.replace("cd", "").lower()
        if spec_key in spec:
            params[key] = str(spec[spec_key])
            
    # e-Stat free-text search times out; narrow id lookups still need a long read.
    response = session.get(ESTAT_BASE, params=params, timeout=(10, 240))"""

content = content.replace("""def fetch_estat(session: requests.Session, spec: dict[str, Any]) -> dict[str, Any]:
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
    response = session.get(ESTAT_BASE, params=params, timeout=(10, 240))""", new_func)

with open("src/country_primer/adapters.py", "w") as f:
    f.write(content)
