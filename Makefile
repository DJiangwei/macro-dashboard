UV ?= scripts/uv_project.sh

.PHONY: setup doctor build-v4 refresh-data rebuild-ui refresh-check data-catalog freshness-audit test validate proxy-report proxy-report-live publish-check publish clean

setup:
	$(UV) sync

doctor:
	$(UV) run python scripts/doctor_env.py

build-v4: refresh-data

refresh-data:
	COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python build_v4.py ALL
	COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_china_dashboard.py
	COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_uk_dashboard.py
	COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_us_dashboard.py
	COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_japan_dashboard.py
	COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_south_africa_dashboard.py
	$(UV) run python scripts/core_coverage_matrix.py
	$(UV) run python scripts/data_source_catalog.py
	$(UV) run python scripts/freshness_audit.py
	$(UV) run python scripts/build_dashboard_archive.py

rebuild-ui:
	COUNTRY_PRIMER_DATA_MODE=snapshot COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python build_v4.py ALL
	COUNTRY_PRIMER_DATA_MODE=snapshot COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_china_dashboard.py
	COUNTRY_PRIMER_DATA_MODE=snapshot COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_uk_dashboard.py
	COUNTRY_PRIMER_DATA_MODE=snapshot COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_us_dashboard.py
	COUNTRY_PRIMER_DATA_MODE=snapshot COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_japan_dashboard.py
	COUNTRY_PRIMER_DATA_MODE=snapshot COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_south_africa_dashboard.py
	$(UV) run python scripts/core_coverage_matrix.py
	$(UV) run python scripts/data_source_catalog.py
	$(UV) run python scripts/freshness_audit.py
	$(UV) run python scripts/build_dashboard_archive.py

refresh-check:
	$(UV) run python scripts/refresh_check.py

data-catalog:
	$(UV) run python scripts/data_source_catalog.py

freshness-audit:
	$(UV) run python scripts/freshness_audit.py

test:
	$(UV) run pytest -q

validate: test
	$(UV) run python scripts/validate_outputs.py
	$(UV) run python scripts/dashboard_consistency_check.py
	git diff --check

proxy-report:
	$(UV) run python scripts/proxy_report.py --details

proxy-report-live:
	$(UV) run python scripts/proxy_report.py --details --mode live

publish-check:
	curl -L https://djiangwei.github.io/macro-dashboard/ | rg -n "Macro Dashboard Archive|Hungary|dashboard_archive_summary.json"
	curl -L https://djiangwei.github.io/macro-dashboard/output/index.html | rg -n "Macro Dashboard Archive|china.html|japan.html|south_africa.html|uk.html|us.html"
	curl -L https://djiangwei.github.io/macro-dashboard/output/hungary.html | rg -n "Hungary Dashboard|Core 48|chart-financial_stability-bank_car"
	curl -L https://djiangwei.github.io/macro-dashboard/output/china.html | rg -n "China Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
	curl -L https://djiangwei.github.io/macro-dashboard/output/uk.html | rg -n "UK Dashboard|Core 48|Official Data Gaps|chart-real_gdp_qoq"
	curl -L https://djiangwei.github.io/macro-dashboard/output/us.html | rg -n "US Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
	curl -L https://djiangwei.github.io/macro-dashboard/output/japan.html | rg -n "Japan Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
	curl -L https://djiangwei.github.io/macro-dashboard/output/south_africa.html | rg -n "South Africa Dashboard|Core 48|Official Data Gaps|chart-real_gdp_growth"
	curl -L https://djiangwei.github.io/macro-dashboard/output/core_coverage_matrix.json | rg -n "core-coverage-v1|concept_count|priorities"
	curl -L https://djiangwei.github.io/macro-dashboard/output/source_health.json | rg -n "source-health-v1|circuit_breaker|countries"

publish:
	@if [ -z "$(MSG)" ]; then echo 'Usage: make publish MSG="commit message"'; exit 2; fi
	scripts/publish_dashboard.sh "$(MSG)"

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
