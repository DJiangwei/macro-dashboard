import yaml

with open("config/framework_v2.yaml") as f:
    framework = yaml.safe_load(f)

jp_map = {
    "headline_inflation": ["cpi_inflation_estat", "cpi_inflation"],
    "services_inflation": ["services_inflation"],
    "goods_inflation": ["goods_inflation"],
    "core_inflation": ["core_inflation", "core_core_inflation"],
    "producer_price_inflation": ["producer_price_inflation"],
    "house_price_growth": ["house_price_growth"],
    "nominal_gdp_growth": ["nominal_gdp_growth"],
    "real_gdp_growth_qoq": ["real_gdp_growth"],
    "real_gdp_growth_yoy": ["real_gdp_yoy"],
    "investment_growth": ["gfcf_growth"],
    "government_consumption": ["government_consumption_growth"],
    "industrial_production_growth": ["industrial_production_growth", "manufacturing_production_growth"],
    "capacity_utilization": ["capacity_utilisation"],
    "business_confidence": ["business_confidence"],
    "leading_indicator": ["composite_leading_indicator"],
    "retail_sales_growth": ["retail_sales_growth"],
    "unemployment_rate": ["unemployment_rate"],
    "participation_rate": ["participation_rate"],
    "employment_growth": ["employment_growth"],
    "wage_growth": ["manufacturing_earnings_growth"],
    "trade_balance": ["goods_trade_balance"],
    "exports_growth": ["goods_exports_growth"],
    "imports_growth": ["goods_imports_growth"],
    "current_account_gdp": ["current_account_gdp"],
    "fx_spot": ["usd_jpy"],
    "reer": ["reer"],
    "government_debt_gdp": ["government_debt_gdp"],
    "fiscal_balance_gdp": ["fiscal_balance_gdp"],
    "primary_balance_gdp": ["primary_balance_gdp"],
    "sovereign_yield_10y": ["sovereign_yield_10y"],
    "policy_rate": ["policy_rate"],
    "interbank_rate_3m": ["interbank_3m"],
    "broad_money_growth": ["broad_money_growth"],
    "private_credit_growth": ["private_credit_gdp", "bank_credit_gdp"],
    "equity_return": ["equity_index"],
    "bank_capital_ratio": ["bank_capital_ratio"],
    "bank_npl_ratio": ["bank_npl_ratio"]
}

za_map = {
    "headline_inflation": ["cpi_inflation"],
    "producer_price_inflation": ["ppi_inflation"],
    "house_price_growth": ["house_price_growth"],
    "nominal_gdp_growth": ["nominal_gdp_growth"],
    "real_gdp_growth_qoq": ["real_gdp_growth"],
    "real_gdp_growth_yoy": ["real_gdp_yoy"],
    "investment_growth": ["gfcf_growth"],
    "industrial_production_growth": ["manufacturing_production_growth"],
    "capacity_utilization": ["capacity_utilisation"],
    "leading_indicator": ["composite_leading_indicator"],
    "retail_sales_growth": ["retail_sales_growth"],
    "unemployment_rate": ["unemployment_rate"],
    "trade_balance": ["goods_trade_balance"],
    "exports_growth": ["goods_exports_growth"],
    "imports_growth": ["goods_imports_growth"],
    "current_account_gdp": ["current_account_gdp"],
    "fx_spot": ["zar_usd"],
    "reer": ["reer"],
    "government_debt_gdp": ["government_debt_gdp"],
    "fiscal_balance_gdp": ["fiscal_balance_gdp"],
    "primary_balance_gdp": ["primary_balance_gdp"],
    "sovereign_yield_10y": ["sovereign_yield_10y"],
    "policy_rate": ["policy_rate"],
    "interbank_rate_3m": ["interbank_3m"],
    "broad_money_growth": ["broad_money_growth"],
    "private_credit_growth": ["private_credit_gdp"],
    "bank_lending_rate": ["prime_lending_rate"],
    "bank_capital_ratio": ["bank_capital_ratio"],
    "bank_npl_ratio": ["bank_npl_ratio"]
}

for item in framework["concepts"]:
    c_id = item["id"]
    if c_id in jp_map:
        if "JP" not in item["mappings"]:
            item["mappings"]["JP"] = []
        for val in jp_map[c_id]:
            if val not in item["mappings"]["JP"]:
                item["mappings"]["JP"].append(val)
    if c_id in za_map:
        if "ZA" not in item["mappings"]:
            item["mappings"]["ZA"] = []
        for val in za_map[c_id]:
            if val not in item["mappings"]["ZA"]:
                item["mappings"]["ZA"].append(val)

with open("config/framework_v2.yaml", "w") as f:
    yaml.dump(framework, f, sort_keys=False)
