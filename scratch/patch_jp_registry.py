import re
from pathlib import Path

path = Path("scripts/build_japan_dashboard.py")
text = path.read_text()

old_registry = """    registry = {
        "fred": lambda spec, cache: fetch_fred_us(requests.Session(), spec),
        "boj_flatfile": lambda spec, cache: fetch_boj_flatfile(requests.Session(), spec),
        "estat": lambda spec, cache: fetch_estat(requests.Session(), spec),
        "imf_datamapper": lambda spec, cache: fetch_imf_datamapper(requests.Session(), spec),
        "imf_sdmx": lambda spec, cache: fetch_imf_sdmx(requests.Session(), spec),
    }"""

new_registry = """    registry = {
        "fred": lambda spec, cache: _apply_transform(apply_scale(fetch_fred_us(requests.Session(), spec))),
        "boj_flatfile": lambda spec, cache: _apply_transform(apply_scale(fetch_boj_flatfile(requests.Session(), spec))),
        "estat": lambda spec, cache: _apply_transform(apply_scale(fetch_estat(requests.Session(), spec))),
        "imf_datamapper": lambda spec, cache: _apply_transform(fetch_imf_datamapper(requests.Session(), spec)),
        "imf_sdmx": lambda spec, cache: _apply_transform(fetch_imf_sdmx(requests.Session(), spec)),
    }"""

text = text.replace(old_registry, new_registry)
path.write_text(text)
