import re

with open("scripts/build_uk_dashboard.py") as f:
    text = f.read()

# Replace the broken UK registry
new_registry = """    import requests
    from country_primer.adapters import (
        fetch_fred, fetch_ons_timeseries, fetch_boe_iadb, fetch_boe_bank_rate,
        fetch_govuk_road_fuel, fetch_govuk_xlsx_table, fetch_govuk_ods_table,
        fetch_ons_xlsx_table, fetch_ons_horizontal_csv_table, fetch_obr_xlsx_row
    )
    registry = {
        "fred": lambda spec, cache: fetch_fred(requests.Session(), spec),
        "ons_timeseries": lambda spec, cache: fetch_ons_timeseries(requests.Session(), spec),
        "boe_iadb": lambda spec, cache: fetch_boe_iadb(requests.Session(), spec),
        "boe_bank_rate": lambda spec, cache: fetch_boe_bank_rate(requests.Session(), spec),
        "govuk_road_fuel": lambda spec, cache: fetch_govuk_road_fuel(requests.Session(), spec),
        "govuk_xlsx_table": lambda spec, cache: fetch_govuk_xlsx_table(requests.Session(), spec),
        "govuk_ods_table": lambda spec, cache: fetch_govuk_ods_table(requests.Session(), spec),
        "ons_xlsx_table": lambda spec, cache: fetch_ons_xlsx_table(requests.Session(), spec),
        "ons_horizontal_csv_table": lambda spec, cache: fetch_ons_horizontal_csv_table(requests.Session(), spec),
        "obr_xlsx_row": lambda spec, cache: fetch_obr_xlsx_row(requests.Session(), spec),
    }"""

text = re.sub(r'    registry = \{.*?    \}', new_registry, text, flags=re.S)

with open("scripts/build_uk_dashboard.py", "w") as f:
    f.write(text)
