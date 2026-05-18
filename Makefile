UV ?= scripts/uv_project.sh

.PHONY: setup doctor build-v4 validate publish-check publish clean

setup:
	$(UV) sync

doctor:
	$(UV) run python scripts/doctor_env.py

build-v4:
	$(UV) run python build_v4.py ALL

validate:
	$(UV) run python -m py_compile build_v4.py src/country_primer/*.py scripts/doctor_env.py
	$(UV) run python -c "from pathlib import Path; import re; files=sorted(Path('output').glob('*_v4.html')); assert files; [print(p.name, len(re.findall(r'class=\"chart-cell chart-shell\" data-indicator-id=\"([^\"]+)\"', p.read_text())), p.read_text().count('<div class=\"charts\"></div>')) for p in files]"
	git diff --check

publish-check:
	curl -L https://djiangwei.github.io/macro-dashboard/ | rg -n "v4 Framework|Hungary|macro-dashboard"
	curl -L https://djiangwei.github.io/macro-dashboard/output/hungary_2026Q2_v4.html | rg -n "100/100|Source charts reused|chart-financial_stability-bank_car"

publish:
	@if [ -z "$(MSG)" ]; then echo 'Usage: make publish MSG="commit message"'; exit 2; fi
	scripts/publish_dashboard.sh "$(MSG)"

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
