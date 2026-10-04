# Core 48 Coverage Matrix

Generated: 2026-10-04T20:10:27.746648+00:00

Legend: `V` verified, `W` watch, `L` low confidence, `S` substitute/low comparability, `-` missing.

| # | Pillar | Concept | HU | PL | CZ | RO | CN | JP | ZA | UK | US |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `growth_demand` | `real_gdp_growth_qoq` Real GDP Growth, QoQ | V | V | V | V | - | W | L | V | W |
| 2 | `growth_demand` | `real_gdp_growth_yoy` Real GDP Growth, YoY | V | V | V | V | W | W | L | - | - |
| 3 | `growth_demand` | `nominal_gdp_growth` Nominal GDP Growth | - | - | - | - | W | W | L | V | W |
| 4 | `growth_demand` | `consumption_growth` Household Consumption Growth | - | - | - | - | W | - | - | W | W |
| 5 | `growth_demand` | `investment_growth` Investment Growth | W | W | W | W | W | W | L | W | W |
| 6 | `production_cycle` | `industrial_production_growth` Industrial Production Growth | V | V | V | V | W | L | S | W | W |
| 7 | `production_cycle` | `retail_sales_growth` Retail Sales Growth | V | V | V | V | W | L | L | W | W |
| 8 | `production_cycle` | `business_confidence` Business Confidence | V | V | V | V | W | W | W | W | W |
| 9 | `labour_household` | `unemployment_rate` Unemployment Rate | V | V | V | V | W | W | L | L | W |
| 10 | `labour_household` | `employment_growth` Employment Growth | V | V | V | V | - | W | L | W | W |
| 11 | `labour_household` | `participation_rate` Labour Force Participation | W | W | W | W | - | W | - | L | W |
| 12 | `labour_household` | `vacancies` Labour Demand / Vacancies | L | L | L | L | - | - | - | V | W |
| 13 | `labour_household` | `wage_growth` Wage Growth | V | V | V | V | - | L | - | V | W |
| 14 | `labour_household` | `real_income_growth` Real Household Income Growth | W | W | W | W | - | - | - | V | W |
| 15 | `prices_costs` | `headline_inflation` Headline Inflation | V | V | V | V | W | W | W | V | W |
| 16 | `prices_costs` | `core_inflation` Core Inflation | V | V | V | V | - | - | - | V | W |
| 17 | `prices_costs` | `services_inflation` Services Inflation | V | V | V | V | - | - | - | V | W |
| 18 | `prices_costs` | `goods_inflation` Goods Inflation | V | V | V | V | - | - | - | V | W |
| 19 | `prices_costs` | `producer_price_inflation` Producer Price Inflation | V | V | V | V | W | - | W | W | W |
| 20 | `prices_costs` | `wage_cost_inflation` Labour Cost Inflation | V | V | V | V | - | - | - | V | W |
| 21 | `prices_costs` | `inflation_expectations` Inflation Expectations | V | V | V | V | - | - | - | - | W |
| 22 | `housing_investment` | `house_price_growth` House Price Growth | V | V | V | V | L | L | L | V | W |
| 23 | `housing_investment` | `housing_activity` Housing Activity | - | - | - | - | W | - | - | V | W |
| 24 | `housing_investment` | `construction_activity` Construction Activity | V | V | V | V | W | - | - | W | W |
| 25 | `housing_investment` | `mortgage_rate` Mortgage Rate | V | W | V | V | - | - | - | V | W |
| 26 | `housing_investment` | `property_inventory` Property Inventory / Supply | - | - | - | - | - | - | - | - | W |
| 27 | `external_fx` | `current_account_gdp` Current Account, % GDP | W | W | W | W | W | L | L | V | W |
| 28 | `external_fx` | `trade_balance` Trade Balance | W | W | W | W | W | L | L | V | W |
| 29 | `external_fx` | `exports_growth` Exports Growth | - | - | - | - | W | L | L | W | W |
| 30 | `external_fx` | `imports_growth` Imports Growth | - | - | - | - | W | L | L | W | W |
| 31 | `external_fx` | `fx_spot` Spot Exchange Rate | V | V | V | W | W | W | W | V | W |
| 32 | `external_fx` | `reer` Real Effective Exchange Rate | W | W | W | W | W | W | W | W | W |
| 33 | `fiscal_sovereign` | `fiscal_balance_gdp` Fiscal Balance, % GDP | W | W | W | W | W | W | W | L | W |
| 34 | `fiscal_sovereign` | `primary_balance_gdp` Primary Balance, % GDP | W | W | W | W | - | W | W | - | - |
| 35 | `fiscal_sovereign` | `government_debt_gdp` Government Debt, % GDP | W | W | W | W | W | W | W | L | L |
| 36 | `fiscal_sovereign` | `government_interest_cost` Government Interest Cost | W | W | W | W | - | - | - | W | W |
| 37 | `fiscal_sovereign` | `sovereign_yield_10y` 10Y Sovereign Yield | V | V | V | V | - | W | W | V | W |
| 38 | `monetary_financial` | `policy_rate` Policy Rate | V | V | V | V | W | W | W | V | W |
| 39 | `monetary_financial` | `real_policy_rate` Real Policy Rate | L | L | L | L | - | - | - | - | - |
| 40 | `monetary_financial` | `broad_money_growth` Broad Money Growth | W | W | W | W | W | W | W | V | W |
| 41 | `monetary_financial` | `private_credit_growth` Private Credit Growth | W | W | W | W | W | L | L | V | W |
| 42 | `monetary_financial` | `bank_lending_rate` Bank Lending Rate | V | V | V | V | - | - | W | - | - |
| 43 | `monetary_financial` | `equity_return` Equity Market Return | W | W | W | W | W | W | - | W | - |
| 44 | `monetary_financial` | `yield_curve_slope` Yield Curve Slope | L | L | L | L | - | - | - | - | W |
| 45 | `monetary_financial` | `financial_conditions` Financial Conditions | - | - | - | - | - | - | - | - | W |
| 46 | `stability_structural` | `credit_gap` Credit-to-GDP Gap | L | L | L | L | - | - | - | - | - |
| 47 | `stability_structural` | `bank_capital_ratio` Bank Capital Ratio | W | W | W | W | - | L | L | - | - |
| 48 | `stability_structural` | `bank_npl_ratio` Bank NPL Ratio | W | W | W | W | - | L | L | - | - |

## Country Summary

| Country | Covered | Verified | Watch | Low | Substitute | Missing |
|---|---:|---:|---:|---:|---:|---:|
| HU | 41/48 | 22 | 15 | 4 | 0 | 7 |
| PL | 41/48 | 21 | 16 | 4 | 0 | 7 |
| CZ | 41/48 | 22 | 15 | 4 | 0 | 7 |
| RO | 41/48 | 21 | 16 | 4 | 0 | 7 |
| CN | 25/48 | 0 | 24 | 1 | 0 | 23 |
| JP | 29/48 | 0 | 18 | 11 | 0 | 19 |
| ZA | 28/48 | 0 | 12 | 15 | 1 | 20 |
| UK | 37/48 | 20 | 13 | 4 | 0 | 11 |
| US | 40/48 | 0 | 39 | 1 | 0 | 8 |

## Priority Gaps

Priority is explicit and reproducible: pillar macro-value weight x10, plus 5 points per missing country and 2 per weak implementation.

| Rank | Concept | Pillar | Score | Missing | Weak |
|---:|---|---|---:|---|---|
| 1 | `financial_conditions` Financial Conditions | `monetary_financial` | 90 | HU, PL, CZ, RO, CN, JP, ZA, UK | - |
| 2 | `real_policy_rate` Real Policy Rate | `monetary_financial` | 83 | CN, JP, ZA, UK, US | HU, PL, CZ, RO |
| 3 | `consumption_growth` Household Consumption Growth | `growth_demand` | 80 | HU, PL, CZ, RO, JP, ZA | - |
| 4 | `yield_curve_slope` Yield Curve Slope | `monetary_financial` | 78 | CN, JP, ZA, UK | HU, PL, CZ, RO |
| 5 | `nominal_gdp_growth` Nominal GDP Growth | `growth_demand` | 72 | HU, PL, CZ, RO | ZA |
| 6 | `inflation_expectations` Inflation Expectations | `prices_costs` | 70 | CN, JP, ZA, UK | - |
| 7 | `property_inventory` Property Inventory / Supply | `housing_investment` | 70 | HU, PL, CZ, RO, CN, JP, ZA, UK | - |
| 8 | `bank_lending_rate` Bank Lending Rate | `monetary_financial` | 70 | CN, JP, UK, US | - |
| 9 | `core_inflation` Core Inflation | `prices_costs` | 65 | CN, JP, ZA | - |
| 10 | `services_inflation` Services Inflation | `prices_costs` | 65 | CN, JP, ZA | - |
| 11 | `goods_inflation` Goods Inflation | `prices_costs` | 65 | CN, JP, ZA | - |
| 12 | `wage_cost_inflation` Labour Cost Inflation | `prices_costs` | 65 | CN, JP, ZA | - |
| 13 | `exports_growth` Exports Growth | `external_fx` | 64 | HU, PL, CZ, RO | JP, ZA |
| 14 | `imports_growth` Imports Growth | `external_fx` | 64 | HU, PL, CZ, RO | JP, ZA |
| 15 | `vacancies` Labour Demand / Vacancies | `labour_household` | 63 | CN, JP, ZA | HU, PL, CZ, RO |
| 16 | `real_gdp_growth_yoy` Real GDP Growth, YoY | `growth_demand` | 62 | UK, US | ZA |
| 17 | `housing_activity` Housing Activity | `housing_investment` | 60 | HU, PL, CZ, RO, JP, ZA | - |
| 18 | `equity_return` Equity Market Return | `monetary_financial` | 60 | ZA, US | - |
| 19 | `real_gdp_growth_qoq` Real GDP Growth, QoQ | `growth_demand` | 57 | CN | ZA |
| 20 | `real_income_growth` Real Household Income Growth | `labour_household` | 55 | CN, JP, ZA | - |
| 21 | `producer_price_inflation` Producer Price Inflation | `prices_costs` | 55 | JP | - |
| 22 | `private_credit_growth` Private Credit Growth | `monetary_financial` | 54 | - | JP, ZA |
| 23 | `credit_gap` Credit-to-GDP Gap | `stability_structural` | 53 | CN, JP, ZA, UK, US | HU, PL, CZ, RO |
| 24 | `investment_growth` Investment Growth | `growth_demand` | 52 | - | ZA |

This matrix measures comparable concept coverage, not raw chart count. Country-specific deep-dive charts do not fill a Core 48 slot unless the framework mapping is explicit.
