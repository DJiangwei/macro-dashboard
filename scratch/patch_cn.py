import re

with open("scripts/build_china_dashboard.py") as f:
    text = f.read()

new_registry = """    import requests
    from src.country_primer.adapters import fetch_eastmoney, fetch_nbs_api
    registry = {
        "world_bank": lambda spec, cache: fetch_world_bank(spec),
        "imf_datamapper": lambda spec, cache: fetch_imf_datamapper(spec),
        "fred_graph": lambda spec, cache: fetch_fred_graph(spec),
        "akshare_table": lambda spec, cache: fetch_akshare_table(spec, cache),
        "akshare_wide_year_month": lambda spec, cache: fetch_akshare_wide_year_month(spec, cache),
        "eastmoney_industry_indicator": lambda spec, cache: fetch_eastmoney_industry_indicator(spec),
        "safe_midpoint": lambda spec, cache: fetch_safe_midpoint(spec, cache.setdefault("safe_rows", [])),
        "pbc_card": lambda spec, cache: fetch_pbc_card(spec),
        "eastmoney_api": lambda spec, cache: fetch_eastmoney(requests.Session(), spec),
        "nbs_api": lambda spec, cache: fetch_nbs_api(requests.Session(), spec),
    }"""

text = re.sub(r'    registry = \{.*?"pbc_card": lambda spec, cache: fetch_pbc_card\(spec\),\n    \}', new_registry, text, flags=re.S)

with open("scripts/build_china_dashboard.py", "w") as f:
    f.write(text)
