import ast
import os
import glob
from collections import defaultdict

scripts = glob.glob("scripts/build_*_dashboard.py")

# We want to identify the exact functions to move.
# build_china_dashboard.py:
# _parse_period_date, _apply_transform, fetch_world_bank, fetch_imf_datamapper, fetch_fred_graph, fetch_akshare_table, fetch_akshare_wide_year_month, fetch_eastmoney_industry_indicator, fetch_safe_midpoint, fetch_pbc_card
china_funcs = ["_parse_period_date", "_apply_transform", "fetch_world_bank", "fetch_imf_datamapper", "fetch_fred_graph", "fetch_akshare_table", "fetch_akshare_wide_year_month", "fetch_eastmoney_industry_indicator", "fetch_safe_midpoint", "fetch_pbc_card"]

# build_us_dashboard.py:
# _parse_obs_date, _lag_for_frequency, _lookup_base, _apply_transform, fetch_fred_us, fetch_bls_api, fetch_treasury_auctions
us_funcs = ["_parse_obs_date", "_lag_for_frequency", "_lookup_base", "_apply_transform", "fetch_fred_us", "fetch_bls_api", "fetch_treasury_auctions"]

# build_uk_dashboard.py:
# shift_calendar_periods, _parse_date, _apply_transform, fetch_fred, fetch_ons_timeseries, fetch_boe_iadb, fetch_boe_bank_rate, fetch_govuk_road_fuel, fetch_govuk_xlsx_table, fetch_govuk_ods_table, fetch_ons_xlsx_table, fetch_ons_horizontal_csv_table, fetch_obr_xlsx_row
uk_funcs = ["shift_calendar_periods", "_parse_date", "_apply_transform", "fetch_fred", "fetch_ons_timeseries", "fetch_boe_iadb", "fetch_boe_bank_rate", "fetch_govuk_road_fuel", "fetch_govuk_xlsx_table", "fetch_govuk_ods_table", "fetch_ons_xlsx_table", "fetch_ons_horizontal_csv_table", "fetch_obr_xlsx_row"]

# build_south_africa_dashboard.py:
# fetch_sarb
za_funcs = ["fetch_sarb"]

# build_japan_dashboard.py: None

def extract_funcs(filename, func_names, rename_map=None):
    if rename_map is None: rename_map = {}
    with open(filename) as f:
        source = f.read()
    
    tree = ast.parse(source)
    extracted = []
    
    class Rewriter(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id in rename_map:
                node.id = rename_map[node.id]
            return node
        def visit_FunctionDef(self, node):
            if node.name in rename_map:
                node.name = rename_map[node.name]
            self.generic_visit(node)
            return node

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in func_names:
            Rewriter().visit(node)
            extracted.append(ast.unparse(node))
            
    return "\n\n".join(extracted)

china_rename = {"_apply_transform": "_apply_china_transform"}
us_rename = {"_apply_transform": "_apply_us_transform"}
uk_rename = {"_apply_transform": "_apply_uk_transform"}

china_code = extract_funcs("scripts/build_china_dashboard.py", china_funcs, china_rename)
us_code = extract_funcs("scripts/build_us_dashboard.py", us_funcs, us_rename)
uk_code = extract_funcs("scripts/build_uk_dashboard.py", uk_funcs, uk_rename)
za_code = extract_funcs("scripts/build_south_africa_dashboard.py", za_funcs, {})

with open("src/country_primer/adapters.py", "a") as f:
    f.write("\n\n" + us_code)
    f.write("\n\n" + uk_code)
    f.write("\n\n" + china_code)
    f.write("\n\n" + za_code)

print("Done appending to adapters.py")
