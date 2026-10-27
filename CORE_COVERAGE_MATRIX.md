# Core 48 Coverage Matrix

Generated: 2026-10-27T23:58:57.911224+00:00

Legend: `V` verified, `W` watch, `L` low confidence, `S` substitute/low comparability, `-` missing.

| # | Pillar | Concept | HU | PL | CZ | RO | CN | EA | JP | ZA | UK | US | TR | HK | KR | TW |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `growth_demand` | `real_gdp_growth_qoq` Real GDP Growth, QoQ | V | V | V | V | - | V | W | L | V | V | V | V | W | V |
| 2 | `growth_demand` | `real_gdp_growth_yoy` Real GDP Growth, YoY | V | V | V | V | W | V | W | L | - | - | V | V | W | V |
| 3 | `growth_demand` | `nominal_gdp_growth` Nominal GDP Growth | - | - | - | - | W | - | W | L | V | V | - | - | - | - |
| 4 | `growth_demand` | `consumption_growth` Household Consumption Growth | - | - | - | - | W | V | - | - | V | W | V | - | - | V |
| 5 | `growth_demand` | `investment_growth` Investment Growth | W | W | W | W | W | V | W | L | V | V | V | - | W | V |
| 6 | `production_cycle` | `industrial_production_growth` Industrial Production Growth | V | V | V | V | W | V | L | S | V | V | V | V | W | - |
| 7 | `production_cycle` | `retail_sales_growth` Retail Sales Growth | V | V | V | V | W | V | L | L | V | V | V | W | W | - |
| 8 | `production_cycle` | `business_confidence` Business Confidence | V | V | V | V | W | L | W | W | W | V | V | - | W | - |
| 9 | `labour_household` | `unemployment_rate` Unemployment Rate | V | V | V | V | W | V | W | W | L | V | W | V | W | W |
| 10 | `labour_household` | `employment_growth` Employment Growth | V | V | V | V | - | V | W | W | W | V | - | - | W | - |
| 11 | `labour_household` | `participation_rate` Labour Force Participation | W | W | W | W | - | V | W | - | L | V | - | - | W | - |
| 12 | `labour_household` | `vacancies` Labour Demand / Vacancies | L | L | L | L | - | L | V | - | V | V | - | - | - | - |
| 13 | `labour_household` | `wage_growth` Wage Growth | V | V | V | V | - | L | L | - | V | V | - | W | - | - |
| 14 | `labour_household` | `real_income_growth` Real Household Income Growth | V | V | V | V | - | - | - | - | V | W | - | - | - | - |
| 15 | `prices_costs` | `headline_inflation` Headline Inflation | V | V | V | V | W | L | V | V | V | V | L | V | W | V |
| 16 | `prices_costs` | `core_inflation` Core Inflation | V | V | V | V | - | L | V | - | V | V | L | V | - | V |
| 17 | `prices_costs` | `services_inflation` Services Inflation | V | V | V | V | - | L | V | - | V | V | L | - | - | - |
| 18 | `prices_costs` | `goods_inflation` Goods Inflation | V | V | V | V | - | L | V | - | V | V | - | - | - | - |
| 19 | `prices_costs` | `producer_price_inflation` Producer Price Inflation | V | V | V | V | W | V | V | W | V | V | V | - | - | V |
| 20 | `prices_costs` | `wage_cost_inflation` Labour Cost Inflation | V | V | V | V | - | V | - | - | V | V | - | - | - | - |
| 21 | `prices_costs` | `inflation_expectations` Inflation Expectations | V | V | V | V | - | V | - | - | - | V | - | - | - | - |
| 22 | `housing_investment` | `house_price_growth` House Price Growth | V | V | V | V | L | V | L | L | L | V | L | L | L | - |
| 23 | `housing_investment` | `housing_activity` Housing Activity | - | - | - | - | W | L | L | - | W | V | - | - | - | - |
| 24 | `housing_investment` | `construction_activity` Construction Activity | V | V | V | V | W | V | - | - | L | V | V | V | - | - |
| 25 | `housing_investment` | `mortgage_rate` Mortgage Rate | W | W | W | W | - | W | - | - | V | W | - | - | - | - |
| 26 | `housing_investment` | `property_inventory` Property Inventory / Supply | - | - | - | - | - | - | - | - | - | V | - | - | - | - |
| 27 | `external_fx` | `current_account_gdp` Current Account, % GDP | W | W | W | W | W | L | L | L | V | V | - | - | W | W |
| 28 | `external_fx` | `trade_balance` Trade Balance | W | W | W | W | W | V | W | W | V | W | W | W | W | V |
| 29 | `external_fx` | `exports_growth` Exports Growth | - | - | - | - | W | V | W | W | V | W | V | W | W | V |
| 30 | `external_fx` | `imports_growth` Imports Growth | - | - | - | - | W | V | W | W | V | W | V | W | W | V |
| 31 | `external_fx` | `fx_spot` Spot Exchange Rate | V | V | V | V | W | V | W | V | V | V | V | W | W | W |
| 32 | `external_fx` | `reer` Real Effective Exchange Rate | W | W | W | W | L | V | L | L | L | V | - | W | W | W |
| 33 | `fiscal_sovereign` | `fiscal_balance_gdp` Fiscal Balance, % GDP | W | W | W | W | W | V | W | W | W | V | - | W | W | W |
| 34 | `fiscal_sovereign` | `primary_balance_gdp` Primary Balance, % GDP | W | W | W | W | - | W | W | W | - | - | - | - | W | - |
| 35 | `fiscal_sovereign` | `government_debt_gdp` Government Debt, % GDP | W | W | W | W | W | V | W | W | W | V | - | W | W | W |
| 36 | `fiscal_sovereign` | `government_interest_cost` Government Interest Cost | W | W | W | W | - | - | - | - | W | V | - | - | - | - |
| 37 | `fiscal_sovereign` | `sovereign_yield_10y` 10Y Sovereign Yield | V | V | V | V | - | V | W | V | V | V | - | - | W | W |
| 38 | `monetary_financial` | `policy_rate` Policy Rate | V | V | V | V | W | V | W | V | V | V | W | - | W | W |
| 39 | `monetary_financial` | `real_policy_rate` Real Policy Rate | L | L | L | L | - | - | - | - | - | - | - | - | - | - |
| 40 | `monetary_financial` | `broad_money_growth` Broad Money Growth | W | W | W | W | W | V | L | L | W | V | - | - | - | W |
| 41 | `monetary_financial` | `private_credit_growth` Private Credit Growth | W | W | W | W | W | V | L | L | W | V | L | L | L | W |
| 42 | `monetary_financial` | `bank_lending_rate` Bank Lending Rate | W | W | W | W | W | W | - | V | - | - | - | - | - | W |
| 43 | `monetary_financial` | `equity_return` Equity Market Return | W | W | W | W | W | - | W | - | W | - | - | - | - | - |
| 44 | `monetary_financial` | `yield_curve_slope` Yield Curve Slope | L | L | L | L | - | V | - | - | V | V | - | - | - | - |
| 45 | `monetary_financial` | `financial_conditions` Financial Conditions | - | - | - | - | - | V | - | - | - | V | - | - | - | - |
| 46 | `stability_structural` | `credit_gap` Credit-to-GDP Gap | L | L | L | L | - | - | - | - | - | - | - | - | - | - |
| 47 | `stability_structural` | `bank_capital_ratio` Bank Capital Ratio | W | W | W | W | - | V | L | L | - | - | L | L | L | - |
| 48 | `stability_structural` | `bank_npl_ratio` Bank NPL Ratio | W | W | W | W | - | V | L | L | - | - | L | L | L | - |

## Country Summary

| Country | Covered | Verified | Watch | Low | Substitute | Missing |
|---|---:|---:|---:|---:|---:|---:|
| HU | 41/48 | 21 | 16 | 4 | 0 | 7 |
| PL | 41/48 | 21 | 16 | 4 | 0 | 7 |
| CZ | 41/48 | 21 | 16 | 4 | 0 | 7 |
| RO | 41/48 | 21 | 16 | 4 | 0 | 7 |
| CN | 26/48 | 0 | 24 | 2 | 0 | 22 |
| EA | 41/48 | 29 | 3 | 9 | 0 | 7 |
| JP | 35/48 | 6 | 18 | 11 | 0 | 13 |
| ZA | 28/48 | 5 | 10 | 12 | 1 | 20 |
| UK | 38/48 | 24 | 9 | 5 | 0 | 10 |
| US | 40/48 | 34 | 6 | 0 | 0 | 8 |
| TR | 22/48 | 12 | 3 | 7 | 0 | 26 |
| HK | 20/48 | 7 | 9 | 4 | 0 | 28 |
| KR | 25/48 | 0 | 21 | 4 | 0 | 23 |
| TW | 21/48 | 10 | 11 | 0 | 0 | 27 |

## Priority Gaps

Priority is explicit and reproducible: pillar macro-value weight x10, plus 5 points per missing country and 2 per weak implementation.

| Rank | Concept | Pillar | Score | Missing | Weak |
|---:|---|---|---:|---|---|
| 1 | `financial_conditions` Financial Conditions | `monetary_financial` | 110 | HU, PL, CZ, RO, CN, JP, ZA, UK, TR, HK, KR, TW | - |
| 2 | `real_policy_rate` Real Policy Rate | `monetary_financial` | 108 | CN, EA, JP, ZA, UK, US, TR, HK, KR, TW | HU, PL, CZ, RO |
| 3 | `nominal_gdp_growth` Nominal GDP Growth | `growth_demand` | 97 | HU, PL, CZ, RO, EA, TR, HK, KR, TW | ZA |
| 4 | `property_inventory` Property Inventory / Supply | `housing_investment` | 95 | HU, PL, CZ, RO, CN, EA, JP, ZA, UK, TR, HK, KR, TW | - |
| 5 | `yield_curve_slope` Yield Curve Slope | `monetary_financial` | 93 | CN, JP, ZA, TR, HK, KR, TW | HU, PL, CZ, RO |
| 6 | `consumption_growth` Household Consumption Growth | `growth_demand` | 90 | HU, PL, CZ, RO, JP, ZA, HK, KR | - |
| 7 | `inflation_expectations` Inflation Expectations | `prices_costs` | 90 | CN, JP, ZA, UK, TR, HK, KR, TW | - |
| 8 | `wage_cost_inflation` Labour Cost Inflation | `prices_costs` | 85 | CN, JP, ZA, TR, HK, KR, TW | - |
| 9 | `equity_return` Equity Market Return | `monetary_financial` | 85 | EA, ZA, US, TR, HK, KR, TW | - |
| 10 | `goods_inflation` Goods Inflation | `prices_costs` | 82 | CN, ZA, TR, HK, KR, TW | EA |
| 11 | `vacancies` Labour Demand / Vacancies | `labour_household` | 80 | CN, ZA, TR, HK, KR, TW | HU, PL, CZ, RO, EA |
| 12 | `real_income_growth` Real Household Income Growth | `labour_household` | 80 | CN, EA, JP, ZA, TR, HK, KR, TW | - |
| 13 | `bank_lending_rate` Bank Lending Rate | `monetary_financial` | 80 | JP, UK, US, TR, HK, KR | - |
| 14 | `services_inflation` Services Inflation | `prices_costs` | 79 | CN, ZA, HK, KR, TW | EA, TR |
| 15 | `housing_activity` Housing Activity | `housing_investment` | 79 | HU, PL, CZ, RO, ZA, TR, HK, KR, TW | EA, JP |
| 16 | `credit_gap` Credit-to-GDP Gap | `stability_structural` | 78 | CN, EA, JP, ZA, UK, US, TR, HK, KR, TW | HU, PL, CZ, RO |
| 17 | `government_interest_cost` Government Interest Cost | `fiscal_sovereign` | 70 | CN, EA, JP, ZA, TR, HK, KR, TW | - |
| 18 | `wage_growth` Wage Growth | `labour_household` | 69 | CN, ZA, TR, KR, TW | EA, JP |
| 19 | `core_inflation` Core Inflation | `prices_costs` | 69 | CN, ZA, KR | EA, TR |
| 20 | `broad_money_growth` Broad Money Growth | `monetary_financial` | 69 | TR, HK, KR | JP, ZA |
| 21 | `participation_rate` Labour Force Participation | `labour_household` | 67 | CN, ZA, TR, HK, TW | UK |
| 22 | `mortgage_rate` Mortgage Rate | `housing_investment` | 65 | CN, JP, ZA, TR, HK, KR, TW | - |
| 23 | `real_gdp_growth_yoy` Real GDP Growth, YoY | `growth_demand` | 62 | UK, US | ZA |
| 24 | `employment_growth` Employment Growth | `labour_household` | 60 | CN, TR, HK, TW | - |

This matrix measures comparable concept coverage, not raw chart count. Country-specific deep-dive charts do not fill a Core 48 slot unless the framework mapping is explicit.
