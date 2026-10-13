# Global Macro Workbench Intelligence Briefing

**Generated**: 2026-10-13 | **Coverage**: 10 Economies (US, EA, UK, JP, CN, ZA, PL, CZ, HU, RO)

---

## 1. Global Macro Regime Board

| Country | Cyclical | Structural | Composite | Growth Assessment | Inflation Assessment | Policy Stance | Data Quality |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :---: |
| **Hungary (HU)** | 58.8 | 43.3 | **mixed** | moderate expansion | near-target inflation | restrictive stance | 54.3 (needs data review) |
| **Poland (PL)** | 61.2 | 45.0 | **mixed** | above-trend expansion | above-target inflation | neutral-moderate stance | 61.3 (usable with watch-list) |
| **Czechia (CZ)** | 65.0 | 58.3 | **mixed** | moderate expansion | near-target inflation | neutral-moderate stance | 52.0 (needs data review) |
| **Romania (RO)** | 30.0 | 46.7 | **defensive** | contraction | inflation pressure | restrictive stance | 50.7 (needs data review) |
| **China (CN)** | 67.5 | 46.7 | **mixed** | above-trend expansion | disinflation risk | neutral-moderate stance | 38.3 (needs data review) |
| **Euro Area (EA)** | 60.0 | 61.7 | **mixed** | stall-speed growth | near-target inflation | neutral-moderate stance | 55.5 (needs data review) |
| **Japan (JP)** | 56.2 | 56.7 | **mixed** | stall-speed growth | near-target inflation | accommodative stance | 45.6 (needs data review) |
| **South Africa (ZA)** | 55.0 | 53.3 | **mixed** | moderate expansion | above-target inflation | restrictive stance | 43.4 (needs data review) |
| **United Kingdom (UK)** | 57.1 | 53.3 | **mixed** | moderate expansion | above-target inflation | neutral-moderate stance | 48.1 (needs data review) |
| **United States (US)** | 51.2 | 43.3 | **defensive** | moderate expansion | above-target inflation | neutral-moderate stance | 58.7 (needs data review) |

---

## 2. Central Bank Policy Stance & Taylor Rule Monitor

Theoretical rate benchmark calculated as $i^* = r^* + \pi + 0.5(\pi - \pi^*) + 0.5(y - y^*)$ with $r^* \pm 50\text{ bps}$ sensitivity band.

| Economy / Institution | Policy Rate | Inflation (Target) | Neutral $r^*$ | Taylor Benchmark (Range) | Policy Gap | Stance Label |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **HU** (MNB) | **6.25%** | 1.80% (3.0%) | 1.80% | **2.75%** (2.25% ~ 3.25%) | **+3.50%** | *substantially restrictive* |
| **PL** (NBP) | **3.75%** | 3.50% (2.5%) | 1.50% | **5.90%** (5.40% ~ 6.40%) | **-2.15%** | *substantially accommodative* |
| **CZ** (CNB) | **3.50%** | 1.50% (2.0%) | 1.20% | **2.35%** (1.85% ~ 2.85%) | **+1.15%** | *moderately restrictive* |
| **RO** (BNR) | **6.50%** | 6.30% (2.5%) | 2.00% | **8.70%** (8.20% ~ 9.20%) | **-2.20%** | *substantially accommodative* |
| **CN** (PBC) | **3.00%** | 0.80% (3.0%) | 1.50% | **1.55%** (1.05% ~ 2.05%) | **+1.45%** | *moderately restrictive* |
| **EA** (ECB) | **2.50%** | 2.00% (2.0%) | 0.50% | **2.50%** (2.00% ~ 3.00%) | **0.00%** | *calibrated / neutral* |
| **JP** (Bank of Japan) | **0.98%** | 1.96% (2.0%) | 0.00% | **1.91%** (1.41% ~ 2.41%) | **-0.93%** | *moderately accommodative* |
| **ZA** (SARB) | **7.25%** | 4.40% (4.5%) | 2.50% | **7.12%** (6.62% ~ 7.62%) | **+0.13%** | *calibrated / neutral* |
| **UK** (Bank of England) | **3.75%** | 3.10% (2.0%) | 1.25% | **4.49%** (3.99% ~ 4.99%) | **-0.74%** | *moderately accommodative* |
| **US** (Federal Reserve) | **3.88%** | 3.01% (2.0%) | 1.00% | **4.61%** (4.11% ~ 5.11%) | **-0.73%** | *moderately accommodative* |

---

## 3. Cross-Country Synchronization (36-Month Rolling Correlation)

- **Nominal Cycle (Headline CPI Inflation)**:
  - Highly coupled core: US vs. Euro Area (**0.94**), US vs. UK (**0.87**), Euro Area vs. UK (**0.96**).
  - Independent domestic price cycle: China vs. US (**0.64**), China vs. Euro Area (**0.56**).
- **Real Business Cycle (Industrial Production)**:
  - Transatlantic industrial linkage: US vs. Euro Area (**0.49**), US vs. UK (**0.5**).
  - Manufacturing divergence: China vs. US (**0.21**), Japan vs. US (**0.44**).

---

## 4. Priority Data Quality & Maintenance Backlog

| Code | Section | Item | Priority | Action Hint |
| :---: | :--- | :--- | :---: | :--- |
| **CN** | `activity_production` | NBS monthly industrial production, services output index, electricity consumption, rail freight, industrial profits, and PMI series | **HIGH** | Prefer native official APIs or AKShare-wrapped structured endpoints; avoid manual proxy fills. |
| **CN** | `consumption` | NBS retail sales, online retail sales, household survey, auto sales, and consumer confidence | **HIGH** | Prefer native official APIs or AKShare-wrapped structured endpoints; avoid manual proxy fills. |
| **CN** | `investment` | NBS fixed asset investment by sector and project pipeline | **HIGH** | Prefer native official APIs or AKShare-wrapped structured endpoints; avoid manual proxy fills. |
| **CN** | `prices` | NBS monthly CPI, core CPI, PPI, agriculture prices, and trade price indices | **HIGH** | Prefer native official APIs or AKShare-wrapped structured endpoints; avoid manual proxy fills. |
| **CN** | `real_estate` | NBS property investment, floor-space starts/completions/sales, 70-city price index, land transactions, and inventory | **HIGH** | Prefer native official APIs or AKShare-wrapped structured endpoints; avoid manual proxy fills. |
| **EA** | `prices_costs` | Dutch TTF natural gas front-month benchmark futures | **HIGH** | Prefer FRED, Federal Reserve, BLS/Census/BEA, FiscalData, or Treasury source APIs. |
| **EA** | `production_cycle` | HCOB Eurozone Manufacturing and Services Flash PMIs | **HIGH** | Check licensing before rendering; vendor surveys should stay as official gaps unless source-safe. |
| **JP** | `housing_property` | Housing starts and mortgage rates | **HIGH** | Prefer ONS, BoE IADB, HMRC/GOV.UK, OBR, or DESNZ endpoints before mirrors. |
| **JP** | `labour_wages` | Job-to-applicant ratio and shunto wage settlements | **HIGH** | Prefer FRED, Federal Reserve, BLS/Census/BEA, FiscalData, or Treasury source APIs. |
| **JP** | `prices_costs` | CPI by COICOP division (food, housing, transport, and the other CP01-CP12 categories) | **HIGH** | Prefer ONS, BoE IADB, HMRC/GOV.UK, OBR, or DESNZ endpoints before mirrors. |
