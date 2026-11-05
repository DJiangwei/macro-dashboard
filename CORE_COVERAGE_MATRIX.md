# Core 48 Coverage Matrix

Generated: 2026-11-05T08:05:22.115339+00:00

Legend: `V` verified, `W` watch, `L` low confidence, `S` substitute/low comparability, `-` missing.

| # | Pillar | Concept | HU | PL | CZ | RO | CN | EA | JP | ZA | UK | US | TR | HK | KR | TW | IN | KZ | UZ | EG | NG |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `growth_demand` | `real_gdp_growth_qoq` Real GDP Growth, QoQ | V | V | V | V | - | V | W | L | W | V | W | W | W | W | - | - | - | - | - |
| 2 | `growth_demand` | `real_gdp_growth_yoy` Real GDP Growth, YoY | V | V | V | V | W | V | W | L | - | - | V | W | W | W | W | W | W | W | W |
| 3 | `growth_demand` | `nominal_gdp_growth` Nominal GDP Growth | - | - | - | - | - | - | W | L | - | V | - | - | - | - | - | - | - | - | - |
| 4 | `growth_demand` | `consumption_growth` Household Consumption Growth | - | - | - | - | W | V | - | - | W | V | V | - | - | W | W | W | W | W | - |
| 5 | `growth_demand` | `investment_growth` Investment Growth | W | W | W | W | W | V | W | L | W | V | V | - | W | W | W | W | W | W | - |
| 6 | `production_cycle` | `industrial_production_growth` Industrial Production Growth | V | V | V | V | W | V | L | S | V | V | V | W | W | - | W | - | - | - | W |
| 7 | `production_cycle` | `retail_sales_growth` Retail Sales Growth | V | V | V | V | W | V | L | L | V | V | V | W | W | - | - | - | - | - | - |
| 8 | `production_cycle` | `business_confidence` Business Confidence | V | V | V | V | W | L | W | W | W | V | V | - | W | - | - | - | - | - | - |
| 9 | `labour_household` | `unemployment_rate` Unemployment Rate | V | V | V | V | W | V | W | W | L | V | V | V | W | W | W | W | W | W | W |
| 10 | `labour_household` | `employment_growth` Employment Growth | V | V | V | V | - | V | W | W | W | V | - | - | W | - | - | - | - | - | - |
| 11 | `labour_household` | `participation_rate` Labour Force Participation | W | W | W | W | - | V | W | - | L | V | W | - | W | - | W | W | W | W | W |
| 12 | `labour_household` | `vacancies` Labour Demand / Vacancies | L | L | L | L | - | L | V | - | V | W | - | - | - | - | - | - | - | - | - |
| 13 | `labour_household` | `wage_growth` Wage Growth | V | V | V | V | - | L | L | - | V | V | - | W | - | - | - | - | - | - | - |
| 14 | `labour_household` | `real_income_growth` Real Household Income Growth | V | V | V | V | - | - | - | - | - | V | - | - | - | - | - | - | - | - | - |
| 15 | `prices_costs` | `headline_inflation` Headline Inflation | V | V | V | V | W | V | V | V | V | V | W | V | W | V | L | W | W | W | L |
| 16 | `prices_costs` | `core_inflation` Core Inflation | V | V | V | V | - | V | V | - | V | V | V | V | - | V | - | - | - | - | - |
| 17 | `prices_costs` | `services_inflation` Services Inflation | V | V | V | V | - | V | V | - | V | V | V | - | - | - | - | - | - | - | - |
| 18 | `prices_costs` | `goods_inflation` Goods Inflation | V | V | V | V | - | V | V | - | V | V | - | - | - | - | - | - | - | - | - |
| 19 | `prices_costs` | `producer_price_inflation` Producer Price Inflation | V | V | V | V | W | V | V | V | V | V | V | - | V | V | - | - | - | - | - |
| 20 | `prices_costs` | `wage_cost_inflation` Labour Cost Inflation | V | V | V | V | - | V | - | - | V | W | - | - | - | - | - | - | - | - | - |
| 21 | `prices_costs` | `inflation_expectations` Inflation Expectations | V | V | V | V | - | V | - | - | - | V | - | - | - | - | - | - | - | - | - |
| 22 | `housing_investment` | `house_price_growth` House Price Growth | V | V | V | V | - | V | L | L | L | W | L | - | - | - | L | - | - | - | - |
| 23 | `housing_investment` | `housing_activity` Housing Activity | - | - | - | - | W | L | L | - | W | V | - | - | - | - | - | - | - | - | - |
| 24 | `housing_investment` | `construction_activity` Construction Activity | V | V | V | V | W | V | - | - | L | V | V | W | - | V | - | - | - | - | - |
| 25 | `housing_investment` | `mortgage_rate` Mortgage Rate | V | V | V | V | - | V | - | - | V | W | - | - | - | - | - | - | - | - | - |
| 26 | `housing_investment` | `property_inventory` Property Inventory / Supply | - | - | - | - | - | - | - | - | - | V | - | - | - | - | - | - | - | - | - |
| 27 | `external_fx` | `current_account_gdp` Current Account, % GDP | W | W | W | W | W | L | L | L | V | W | W | W | W | W | W | W | W | W | W |
| 28 | `external_fx` | `trade_balance` Trade Balance | W | W | W | W | W | V | W | W | V | W | W | V | W | W | W | W | W | L | W |
| 29 | `external_fx` | `exports_growth` Exports Growth | - | - | - | - | W | V | W | W | W | W | V | V | - | W | W | - | - | - | - |
| 30 | `external_fx` | `imports_growth` Imports Growth | - | - | - | - | W | V | W | W | W | W | V | V | - | W | W | - | - | - | - |
| 31 | `external_fx` | `fx_spot` Spot Exchange Rate | V | V | V | V | W | V | W | V | V | V | V | W | W | W | W | V | W | L | V |
| 32 | `external_fx` | `reer` Real Effective Exchange Rate | W | W | W | W | L | V | L | L | L | V | W | W | W | W | L | W | W | W | W |
| 33 | `fiscal_sovereign` | `fiscal_balance_gdp` Fiscal Balance, % GDP | W | W | W | W | W | V | W | W | W | V | W | W | W | W | W | W | W | W | W |
| 34 | `fiscal_sovereign` | `primary_balance_gdp` Primary Balance, % GDP | W | W | W | W | - | W | W | W | - | - | W | - | W | - | W | W | W | W | W |
| 35 | `fiscal_sovereign` | `government_debt_gdp` Government Debt, % GDP | W | W | W | W | W | V | W | W | W | V | W | W | W | W | W | W | W | W | W |
| 36 | `fiscal_sovereign` | `government_interest_cost` Government Interest Cost | W | W | W | W | - | - | - | - | W | V | - | - | - | - | - | - | - | - | - |
| 37 | `fiscal_sovereign` | `sovereign_yield_10y` 10Y Sovereign Yield | V | V | V | V | W | V | W | V | V | V | - | - | W | W | - | - | - | - | - |
| 38 | `monetary_financial` | `policy_rate` Policy Rate | V | V | V | V | W | V | V | V | V | V | V | V | V | V | V | L | L | L | L |
| 39 | `monetary_financial` | `real_policy_rate` Real Policy Rate | W | W | W | W | W | V | W | V | V | W | W | W | W | V | L | L | L | L | L |
| 40 | `monetary_financial` | `broad_money_growth` Broad Money Growth | W | W | W | W | W | V | L | L | V | V | - | - | - | V | - | W | W | W | W |
| 41 | `monetary_financial` | `private_credit_growth` Private Credit Growth | W | W | W | W | - | V | L | L | V | V | L | L | L | V | - | W | W | W | L |
| 42 | `monetary_financial` | `bank_lending_rate` Bank Lending Rate | V | V | V | W | W | V | - | V | - | - | V | - | - | V | - | - | L | L | L |
| 43 | `monetary_financial` | `equity_return` Equity Market Return | W | W | W | W | W | - | W | - | W | - | V | - | V | W | W | - | - | - | - |
| 44 | `monetary_financial` | `yield_curve_slope` Yield Curve Slope | L | L | L | L | W | V | W | - | V | V | - | - | W | W | - | - | - | - | - |
| 45 | `monetary_financial` | `financial_conditions` Financial Conditions | - | - | - | - | - | V | - | - | - | V | - | - | - | - | - | - | - | - | - |
| 46 | `stability_structural` | `credit_gap` Credit-to-GDP Gap | L | L | L | L | W | W | W | - | L | L | - | - | L | - | W | - | - | - | - |
| 47 | `stability_structural` | `bank_capital_ratio` Bank Capital Ratio | W | W | W | W | - | W | L | L | - | - | L | L | L | - | - | L | L | - | L |
| 48 | `stability_structural` | `bank_npl_ratio` Bank NPL Ratio | W | W | W | W | - | W | L | L | - | - | L | L | L | W | - | L | L | - | L |

## Country Summary

| Country | Covered | Verified | Watch | Low | Substitute | Missing |
|---|---:|---:|---:|---:|---:|---:|
| HU | 41/48 | 23 | 15 | 3 | 0 | 7 |
| PL | 41/48 | 23 | 15 | 3 | 0 | 7 |
| CZ | 41/48 | 23 | 15 | 3 | 0 | 7 |
| RO | 41/48 | 22 | 16 | 3 | 0 | 7 |
| CN | 27/48 | 0 | 26 | 1 | 0 | 21 |
| EA | 43/48 | 34 | 4 | 5 | 0 | 5 |
| JP | 38/48 | 7 | 20 | 11 | 0 | 10 |
| ZA | 29/48 | 7 | 9 | 12 | 1 | 19 |
| UK | 38/48 | 20 | 12 | 6 | 0 | 10 |
| US | 42/48 | 32 | 9 | 1 | 0 | 6 |
| TR | 31/48 | 17 | 10 | 4 | 0 | 17 |
| HK | 22/48 | 7 | 12 | 3 | 0 | 26 |
| KR | 27/48 | 3 | 20 | 4 | 0 | 21 |
| TW | 26/48 | 9 | 17 | 0 | 0 | 22 |
| IN | 21/48 | 1 | 16 | 4 | 0 | 27 |
| KZ | 19/48 | 1 | 14 | 4 | 0 | 29 |
| UZ | 20/48 | 0 | 15 | 5 | 0 | 28 |
| EG | 18/48 | 0 | 13 | 5 | 0 | 30 |
| NG | 19/48 | 1 | 11 | 7 | 0 | 29 |

## Priority Gaps

Priority is explicit and reproducible: pillar macro-value weight x10, plus 5 points per missing country and 2 per weak implementation.

| Rank | Concept | Pillar | Score | Missing | Weak |
|---:|---|---|---:|---|---|
| 1 | `financial_conditions` Financial Conditions | `monetary_financial` | 135 | HU, PL, CZ, RO, CN, JP, ZA, UK, TR, HK, KR, TW, IN, KZ, UZ, EG, NG | - |
| 2 | `nominal_gdp_growth` Nominal GDP Growth | `growth_demand` | 132 | HU, PL, CZ, RO, CN, EA, UK, TR, HK, KR, TW, IN, KZ, UZ, EG, NG | ZA |
| 3 | `property_inventory` Property Inventory / Supply | `housing_investment` | 120 | HU, PL, CZ, RO, CN, EA, JP, ZA, UK, TR, HK, KR, TW, IN, KZ, UZ, EG, NG | - |
| 4 | `inflation_expectations` Inflation Expectations | `prices_costs` | 115 | CN, JP, ZA, UK, TR, HK, KR, TW, IN, KZ, UZ, EG, NG | - |
| 5 | `real_income_growth` Real Household Income Growth | `labour_household` | 110 | CN, EA, JP, ZA, UK, TR, HK, KR, TW, IN, KZ, UZ, EG, NG | - |
| 6 | `wage_cost_inflation` Labour Cost Inflation | `prices_costs` | 110 | CN, JP, ZA, TR, HK, KR, TW, IN, KZ, UZ, EG, NG | - |
| 7 | `vacancies` Labour Demand / Vacancies | `labour_household` | 105 | CN, ZA, TR, HK, KR, TW, IN, KZ, UZ, EG, NG | HU, PL, CZ, RO, EA |
| 8 | `goods_inflation` Goods Inflation | `prices_costs` | 105 | CN, ZA, TR, HK, KR, TW, IN, KZ, UZ, EG, NG | - |
| 9 | `housing_activity` Housing Activity | `housing_investment` | 104 | HU, PL, CZ, RO, ZA, TR, HK, KR, TW, IN, KZ, UZ, EG, NG | EA, JP |
| 10 | `services_inflation` Services Inflation | `prices_costs` | 100 | CN, ZA, HK, KR, TW, IN, KZ, UZ, EG, NG | - |
| 11 | `yield_curve_slope` Yield Curve Slope | `monetary_financial` | 98 | ZA, TR, HK, IN, KZ, UZ, EG, NG | HU, PL, CZ, RO |
| 12 | `consumption_growth` Household Consumption Growth | `growth_demand` | 95 | HU, PL, CZ, RO, JP, ZA, HK, KR, NG | - |
| 13 | `government_interest_cost` Government Interest Cost | `fiscal_sovereign` | 95 | CN, EA, JP, ZA, TR, HK, KR, TW, IN, KZ, UZ, EG, NG | - |
| 14 | `wage_growth` Wage Growth | `labour_household` | 94 | CN, ZA, TR, KR, TW, IN, KZ, UZ, EG, NG | EA, JP |
| 15 | `bank_lending_rate` Bank Lending Rate | `monetary_financial` | 91 | JP, UK, US, HK, KR, IN, KZ | UZ, EG, NG |
| 16 | `core_inflation` Core Inflation | `prices_costs` | 90 | CN, ZA, KR, IN, KZ, UZ, EG, NG | - |
| 17 | `mortgage_rate` Mortgage Rate | `housing_investment` | 90 | CN, JP, ZA, TR, HK, KR, TW, IN, KZ, UZ, EG, NG | - |
| 18 | `equity_return` Equity Market Return | `monetary_financial` | 90 | EA, ZA, US, HK, KZ, UZ, EG, NG | - |
| 19 | `employment_growth` Employment Growth | `labour_household` | 85 | CN, TR, HK, TW, IN, KZ, UZ, EG, NG | - |
| 20 | `exports_growth` Exports Growth | `external_fx` | 85 | HU, PL, CZ, RO, KR, KZ, UZ, EG, NG | - |
| 21 | `imports_growth` Imports Growth | `external_fx` | 85 | HU, PL, CZ, RO, KR, KZ, UZ, EG, NG | - |
| 22 | `real_gdp_growth_qoq` Real GDP Growth, QoQ | `growth_demand` | 82 | CN, IN, KZ, UZ, EG, NG | ZA |
| 23 | `producer_price_inflation` Producer Price Inflation | `prices_costs` | 80 | HK, IN, KZ, UZ, EG, NG | - |
| 24 | `house_price_growth` House Price Growth | `housing_investment` | 80 | CN, HK, KR, TW, KZ, UZ, EG, NG | JP, ZA, UK, TR, IN |

This matrix measures comparable concept coverage, not raw chart count. Country-specific deep-dive charts do not fill a Core 48 slot unless the framework mapping is explicit.
