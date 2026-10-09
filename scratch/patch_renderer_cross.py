import re
from pathlib import Path

path = Path("src/country_primer/page_renderer.py")
text = path.read_text()

old_code = """    apply_quality_assessments(series_list)
    html = render_html(config, series_list, extra_cards or [], summary_key_ids)"""

new_code = """    apply_quality_assessments(series_list)

    cross_checks = evaluate_cross_checks(config, series_list)
    checks_by_id = {}
    for check in cross_checks:
        for side in (check["primary"], check["secondary"]):
            checks_by_id[side] = check
    for item in series_list:
        item["cross_check"] = checks_by_id.get(item["id"])

    html = render_html(config, series_list, extra_cards or [], summary_key_ids)"""

text = text.replace(old_code, new_code)
path.write_text(text)
