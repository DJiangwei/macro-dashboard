UV ?= scripts/uv_project.sh

.PHONY: setup doctor golden-diff build-v4 refresh-data rebuild-ui refresh-check refresh-scheduled refresh-quick ci-summary data-catalog freshness-audit chart-studio my-dashboard policy-tracker enrich-data test validate proxy-report proxy-report-live publish-check publish clean

setup:
	$(UV) sync

doctor:
	$(UV) run python scripts/doctor_env.py

build-v4: refresh-data

refresh-data:
	$(UV) run python scripts/refresh_bis_policy_snapshot.py
	COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python build_v4.py ALL
	COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_scope.py --all
	$(UV) run python scripts/enrich_macro_data_quality.py
	$(UV) run python scripts/enrich_cee_inflation_deepdive.py
	$(UV) run python scripts/enrich_us_inflation_deepdive.py
	$(UV) run python scripts/real_deepdives.py
	$(MAKE) rebuild-ui

rebuild-ui:
	$(UV) run python scripts/enrich_macro_data_quality.py
	$(UV) run python scripts/enrich_cee_inflation_deepdive.py
	$(UV) run python scripts/enrich_us_inflation_deepdive.py
	$(UV) run python scripts/real_deepdives.py
	COUNTRY_PRIMER_DATA_MODE=snapshot COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python build_v4.py ALL
	COUNTRY_PRIMER_DATA_MODE=snapshot COUNTRY_PRIMER_SKIP_ARCHIVE=1 $(UV) run python scripts/build_scope.py --all
	$(UV) run python scripts/core_coverage_matrix.py
	$(UV) run python scripts/data_source_catalog.py
	$(UV) run python scripts/freshness_audit.py
	$(UV) run python scripts/build_dashboard_archive.py
	$(UV) run python scripts/macro_workbench.py
	$(UV) run python scripts/build_chart_studio.py
	$(UV) run python scripts/build_my_dashboard.py
	$(UV) run python scripts/build_policy_tracker.py

golden-diff:
	$(UV) run python scripts/golden_diff.py

refresh-check:
	$(UV) run python scripts/refresh_check.py

refresh-scheduled:
	$(UV) run python scripts/run_scheduled_refresh.py --mode auto

refresh-quick:
	$(UV) run python scripts/run_scheduled_refresh.py --mode quick

ci-summary:
	$(UV) run python scripts/ci_step_summary.py

data-catalog:
	$(UV) run python scripts/data_source_catalog.py

freshness-audit:
	$(UV) run python scripts/freshness_audit.py

chart-studio:
	$(UV) run python scripts/build_chart_studio.py

my-dashboard:
	$(UV) run python scripts/build_my_dashboard.py

policy-tracker:
	$(UV) run python scripts/build_policy_tracker.py

enrich-data:
	$(UV) run python scripts/enrich_macro_data_quality.py
	$(UV) run python scripts/enrich_cee_inflation_deepdive.py
	$(UV) run python scripts/enrich_us_inflation_deepdive.py
	$(UV) run python scripts/real_deepdives.py

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
	$(UV) run python scripts/publish_smoke.py

publish:
	@if [ -z "$(MSG)" ]; then echo 'Usage: make publish MSG="commit message"'; exit 2; fi
	scripts/publish_dashboard.sh "$(MSG)"

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
