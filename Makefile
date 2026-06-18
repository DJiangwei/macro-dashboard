UV ?= scripts/uv_project.sh

.PHONY: setup doctor build-v4 data-catalog freshness-audit validate proxy-report publish-check publish clean

setup:
	$(UV) sync

doctor:
	$(UV) run python scripts/doctor_env.py

build-v4:
	COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python build_v4.py ALL
	COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_china_dashboard.py
	COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_uk_dashboard.py
	COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_us_dashboard.py
	$(UV) run python scripts/build_dashboard_archive.py

data-catalog:
	$(UV) run python scripts/data_source_catalog.py

freshness-audit:
	$(UV) run python scripts/freshness_audit.py

validate:
	$(UV) run python -m py_compile build_v4.py src/country_primer/*.py scripts/*.py
	$(UV) run python -c "from pathlib import Path; import re; files=sorted(Path('output').glob('*_v4.html')); assert files; [print(p.name, len(re.findall(r'class=\"chart-cell chart-shell\" data-indicator-id=\"([^\"]+)\"', p.read_text())), p.read_text().count('<div class=\"charts\"></div>')) for p in files]"
	$(UV) run python -c "from pathlib import Path; text=Path('output/index.html').read_text(); assert '_v3.html' not in text; assert 'Macro Dashboard Archive' in text; assert '110/110' in text and '113/113' in text and '109/109' in text; assert 'china_2026Q2_v1.html' in text"
	$(UV) run python -c "from pathlib import Path; text=Path('output/index.html').read_text(); assert 'uk_2026Q2_v1.html' in text"
	$(UV) run python -c "from pathlib import Path; text=Path('output/index.html').read_text(); assert 'us_2026Q2_v1.html' in text; assert '7</strong><span>country dashboards' in text"
	$(UV) run python -c "from pathlib import Path; text=Path('index.html').read_text(); assert 'Macro Dashboard Archive' in text and 'output/china_2026Q2_v1.html' in text and 'output/uk_2026Q2_v1.html' in text and 'output/us_2026Q2_v1.html' in text and 'output/dashboard_archive_summary.json' in text"
	$(UV) run python -c "from pathlib import Path; import json; data=json.loads(Path('output/dashboard_archive_summary.json').read_text()); assert len(data['cards']) == 7; assert all('charts' in c and 'file' in c for c in data['cards'])"
	$(UV) run python -c "from pathlib import Path; import re; text=Path('output/china_2026Q2_v1.html').read_text(); assert 'China Dashboard' in text and '中国 Dashboard' in text; cards=len(re.findall(r'class=\"chart-card', text)); divs=re.findall(r'id=\"(chart-[^\"]+)\" class=\"plotly-chart\"', text); plots=re.findall(r'Plotly\\.newPlot\\(\"(chart-[^\"]+)\"', text); assert cards >= 96; assert cards == len(divs) == len(plots); assert len(divs) == len(set(divs)); assert set(divs) == set(plots); assert 'Official Data Gaps' in text; assert all(token in text for token in ['Series: TRESEGCNM052N', 'Series: QCNN628BIS', 'Series: QCNR628BIS', 'Series: DEXCHUS', 'Series: RBCNBIS', 'Series: IR3TIB01CNM156N', 'Series: SPASTT01CNM661N', 'Series: macro_china_cpi:全国-同比增长', 'Series: macro_china_ppi:当月同比增长', 'Series: macro_china_pmi:制造业-指数', 'Series: macro_china_money_supply:M2同比增长', 'Series: macro_china_new_financial_credit:当月', 'Series: macro_china_lpr:LPR1Y', 'Series: macro_china_gdzctz:同比增长', 'Series: macro_china_gyzjz:同比增长', 'Series: macro_china_consumer_goods_retail:同比增长', 'Series: macro_china_society_electricity:全社会用电量同比', 'Series: macro_china_shrzgm:社会融资规模增量', 'Series: macro_china_shibor_all:O/N-定价', 'Series: macro_china_reserve_requirement_ratio:大型金融机构-调整后', 'Series: macro_china_hgjck:当月出口额-同比增长', 'Series: macro_china_new_house_price:北京:新建商品住宅价格指数-同比', 'Series: macro_china_xfzxx:消费者信心指数-指数值', 'Series: macro_china_foreign_exchange_gold:国家外汇储备', 'Series: macro_china_czsr:累计-同比增长', 'Series: macro_china_enterprise_boom_index:企业景气指数-指数', 'Series: macro_china_freight_index:波罗的海综合运价指数BDI', 'Series: macro_china_cpi:全国-环比增长', 'Series: macro_china_cpi:城市-同比增长', 'Series: macro_china_cpi:农村-同比增长', 'Series: macro_china_qyspjg:总指数-同比增长', 'Series: macro_china_qyspjg:煤油电-同比增长', 'Series: macro_china_agricultural_product:最新值', 'Series: macro_china_commodity_price_index:最新值', 'Series: macro_china_energy_index:最新值', 'Series: macro_china_lpi_index:最新值', 'Series: macro_china_passenger_load_factor:客座率', 'Series: macro_china_hgjck:当月出口额-金额', 'Series: macro_china_hgjck:当月出口额-金额-当月进口额-金额', 'Series: macro_china_stock_market_cap:市价总值-上海+市价总值-深圳', 'Series: macro_china_market_margin_sh:融资融券余额', 'Series: macro_china_market_margin_sz:融资融券余额', 'Series: macro_china_national_tax_receipts:税收收入合计', 'Series: macro_china_construction_index:最新值', 'Series: car_market_total_cpca:狭义乘用车:零售', 'Series: car_market_fuel_cpca:整体市场', 'Series: car_market_fuel_cpca:销量占比-ICE-NEV:NEV', 'Series: car_market_total_cpca:狭义乘用车:出口', 'Series: macro_china_central_bank_balance:总资产', 'Series: macro_china_central_bank_balance:外汇', 'Series: macro_china_central_bank_balance:对其他存款性公司债权', 'Series: macro_china_central_bank_balance:储备货币'])"
	$(UV) run python -c "from pathlib import Path; import json; data=json.loads(Path('output/china_dashboard_summary.json').read_text()); keys={item['id'] for item in data.get('key_series_latest', [])}; assert data['charts'] >= 96; assert 'passenger_vehicle_retail_cpca' in keys and 'new_energy_vehicle_share_cpca' in keys and 'pbc_total_assets_akshare' in keys and 'pbc_reserve_money_akshare' in keys"
	$(UV) run python -c "from pathlib import Path; import re; text=Path('output/uk_2026Q2_v1.html').read_text(); assert 'UK Dashboard' in text and '英国 Dashboard' in text; assert len(re.findall(r'class=\"chart-card', text)) >= 87; assert 'Official Data Gaps' in text"
	$(UV) run python -c "from pathlib import Path; import json; data=json.loads(Path('output/uk_dashboard_summary.json').read_text()); keys={item['id'] for item in data.get('key_series_latest', [])}; assert 'bank_rate' in keys and 'real_gdp_qoq' in keys and 'cpi_yoy' in keys"
	$(UV) run python -c "from pathlib import Path; text=Path('output/uk_2026Q2_v1.html').read_text(); assert all(token in text for token in ['Series: IHYQ', 'Series: YBHA', 'Series: ABJR', 'Series: NPQT', 'Series: IKBK', 'Series: IKBL', 'Series: MGRZ', 'Series: LF2S', 'Series: D7NN', 'Series: D7NM', 'Series: D7G8', 'Series: D7GT', 'Series: AA6H', 'Series: CRXX', 'Series: NRJS', 'Series: ONS RTI SA:Payrolled employees', 'Series: ONS RTI SA:Median of pay growth', 'Series: HMRC MPT:Residential_monthly:UK seasonally adjusted', 'Series: HMRC MPT:Non-residential_monthly:UK seasonally adjusted', 'Series: L55O', 'Series: L5P7', 'Series: JW2O', 'Series: KAU3'])"
	$(UV) run python -c "from pathlib import Path; import re; text=Path('output/us_2026Q2_v1.html').read_text(); assert 'US Dashboard' in text and '美国 Dashboard' in text; cards=len(re.findall(r'class=\"chart-card', text)); divs=re.findall(r'id=\"(chart-[^\"]+)\" class=\"plotly-chart\"', text); plots=re.findall(r'Plotly\\.newPlot\\(\"(chart-[^\"]+)\"', text); assert cards >= 120; assert cards == len(divs) == len(plots); assert len(divs) == len(set(divs)); assert set(divs) == set(plots); assert 'Official Data Gaps' in text"
	$(UV) run python -c "from pathlib import Path; import json; data=json.loads(Path('output/us_dashboard_summary.json').read_text()); keys={item['id'] for item in data.get('key_series_latest', [])}; assert 'daily_fed_funds' in keys and 'effective_fed_funds' not in keys; assert '(2026-05-01)' not in data.get('fed_funds_latest', '')"
	$(UV) run python scripts/dashboard_consistency_check.py
	git diff --check

proxy-report:
	$(UV) run python scripts/proxy_report.py --details

publish-check:
	curl -L https://djiangwei.github.io/macro-dashboard/ | rg -n "Macro Dashboard Archive|Hungary|dashboard_archive_summary.json"
	curl -L https://djiangwei.github.io/macro-dashboard/output/index.html | rg -n "Macro Dashboard Archive|china_2026Q2_v1.html|110/110|113/113|109/109"
	curl -L https://djiangwei.github.io/macro-dashboard/output/hungary_2026Q2_v4.html | rg -n "Proxy / watch-list fills: 0|Source charts reused|chart-financial_stability-bank_car"
	curl -L https://djiangwei.github.io/macro-dashboard/output/china_2026Q2_v1.html | rg -n "China Dashboard|Official Data Gaps|chart-real_gdp_growth"
	curl -L https://djiangwei.github.io/macro-dashboard/output/uk_2026Q2_v1.html | rg -n "UK Dashboard|Official Data Gaps|chart-real_gdp_qoq"
	curl -L https://djiangwei.github.io/macro-dashboard/output/us_2026Q2_v1.html | rg -n "US Dashboard|Official Data Gaps|BED API quota|chart-real_gdp_growth|chart-real_gdp_per_capita_growth|chart-treasury_auction_total_accepted|chart-tic_foreign_treasury_net_transactions|chart-adp_private_payrolls_change"

publish:
	@if [ -z "$(MSG)" ]; then echo 'Usage: make publish MSG="commit message"'; exit 2; fi
	scripts/publish_dashboard.sh "$(MSG)"

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
