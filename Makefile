UV ?= scripts/uv_project.sh

.PHONY: setup doctor build-v4 data-catalog validate proxy-report publish-check publish clean

setup:
	$(UV) sync

doctor:
	$(UV) run python scripts/doctor_env.py

build-v4:
	$(UV) run python build_v4.py ALL
	$(UV) run python scripts/build_china_dashboard.py
	$(UV) run python scripts/build_uk_dashboard.py
	$(UV) run python scripts/build_us_dashboard.py

data-catalog:
	$(UV) run python scripts/data_source_catalog.py

validate:
	$(UV) run python -m py_compile build_v4.py src/country_primer/*.py scripts/*.py
	$(UV) run python -c "from pathlib import Path; import re; files=sorted(Path('output').glob('*_v4.html')); assert files; [print(p.name, len(re.findall(r'class=\"chart-cell chart-shell\" data-indicator-id=\"([^\"]+)\"', p.read_text())), p.read_text().count('<div class=\"charts\"></div>')) for p in files]"
	$(UV) run python -c "from pathlib import Path; text=Path('output/index.html').read_text(); assert '_v3.html' not in text; assert 'Macro Dashboard Archive' in text; assert '110/110' in text and '113/113' in text and '109/109' in text; assert 'china_2026Q2_v1.html' in text"
	$(UV) run python -c "from pathlib import Path; text=Path('output/index.html').read_text(); assert 'uk_2026Q2_v1.html' in text"
	$(UV) run python -c "from pathlib import Path; text=Path('output/index.html').read_text(); assert 'us_2026Q2_v1.html' in text; assert '7</strong><span>country dashboards' in text"
	$(UV) run python -c "from pathlib import Path; text=Path('index.html').read_text(); assert 'Macro Dashboard Archive' in text and 'output/china_2026Q2_v1.html' in text and 'output/uk_2026Q2_v1.html' in text and 'output/us_2026Q2_v1.html' in text"
	$(UV) run python -c "from pathlib import Path; import re; text=Path('output/china_2026Q2_v1.html').read_text(); assert 'China Dashboard' in text and '中国 Dashboard' in text; assert len(re.findall(r'class=\"chart-card', text)) >= 20; assert 'Official Data Gaps' in text"
	$(UV) run python -c "from pathlib import Path; import re; text=Path('output/uk_2026Q2_v1.html').read_text(); assert 'UK Dashboard' in text and '英国 Dashboard' in text; assert len(re.findall(r'class=\"chart-card', text)) >= 20; assert 'Official Data Gaps' in text"
	$(UV) run python -c "from pathlib import Path; import re; text=Path('output/us_2026Q2_v1.html').read_text(); assert 'US Dashboard' in text and '美国 Dashboard' in text; cards=len(re.findall(r'class=\"chart-card', text)); divs=re.findall(r'id=\"(chart-[^\"]+)\" class=\"plotly-chart\"', text); plots=re.findall(r'Plotly\\.newPlot\\(\"(chart-[^\"]+)\"', text); assert cards >= 120; assert cards == len(divs) == len(plots); assert len(divs) == len(set(divs)); assert set(divs) == set(plots); assert 'Official Data Gaps' in text"
	git diff --check

proxy-report:
	$(UV) run python scripts/proxy_report.py --details

publish-check:
	curl -L https://djiangwei.github.io/macro-dashboard/ | rg -n "v4 Framework|Hungary|macro-dashboard"
	curl -L https://djiangwei.github.io/macro-dashboard/output/index.html | rg -n "Macro Dashboard Archive|china_2026Q2_v1.html|110/110|113/113|109/109"
	curl -L https://djiangwei.github.io/macro-dashboard/output/hungary_2026Q2_v4.html | rg -n "Proxy / watch-list fills: 0|Source charts reused|chart-financial_stability-bank_car"
	curl -L https://djiangwei.github.io/macro-dashboard/output/china_2026Q2_v1.html | rg -n "China Dashboard|Official Data Gaps|chart-real_gdp_growth"
	curl -L https://djiangwei.github.io/macro-dashboard/output/uk_2026Q2_v1.html | rg -n "UK Dashboard|Official Data Gaps|chart-real_gdp_qoq"
	curl -L https://djiangwei.github.io/macro-dashboard/output/us_2026Q2_v1.html | rg -n "US Dashboard|Official Data Gaps|chart-real_gdp_growth|chart-real_gdp_per_capita_growth|chart-treasury_auction_total_accepted"

publish:
	@if [ -z "$(MSG)" ]; then echo 'Usage: make publish MSG="commit message"'; exit 2; fi
	scripts/publish_dashboard.sh "$(MSG)"

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
