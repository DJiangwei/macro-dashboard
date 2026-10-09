import re
from pathlib import Path

path = Path("scripts/build_south_africa_dashboard.py")
text = path.read_text()

old_registry = """    registry = {
        "fred": lambda spec, cache: fetch_fred_us(requests.Session(), spec),
        "sarb": lambda spec, cache: fetch_sarb(requests.Session(), spec),
        "resbank_api": lambda spec, cache: fetch_resbank_api(requests.Session(), spec),
        "statssa_excel": lambda spec, cache: fetch_statssa_excel(requests.Session(), spec),
        "imf_datamapper": lambda spec, cache: fetch_imf_datamapper(spec),
        "imf_sdmx": lambda spec, cache: fetch_imf_sdmx(spec),
    }"""

new_registry = """    registry = {
        "fred": lambda spec, cache: _apply_transform(apply_scale(fetch_fred_us(requests.Session(), spec))),
        "sarb": lambda spec, cache: _apply_transform(fetch_sarb(requests.Session(), spec)),
        "imf_datamapper": lambda spec, cache: _apply_transform(fetch_imf_datamapper(requests.Session(), spec)),
        "imf_sdmx": lambda spec, cache: _apply_transform(apply_scale(fetch_imf_sdmx(requests.Session(), spec))),
    }"""

text = text.replace(old_registry, new_registry)
path.write_text(text)
