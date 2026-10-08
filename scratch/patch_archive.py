with open("scripts/build_dashboard_archive.py", "r") as f:
    text = f.read()

text = text.replace("<th>Composite</th><th>Growth</th>", "<th>Cyclical</th><th>Structural</th><th>Growth</th>")

old_row = """        <td><span class="score-pill {_status_class(regime.get('composite_score'))}">{escape(str(regime.get('composite_score', 'n/a')))}</span><em>{escape(str(regime.get('composite_label', 'n/a')))}</em></td>"""
new_row = """        <td><span class="score-pill {_status_class(regime.get('cyclical_score'))}">{escape(str(regime.get('cyclical_score', 'n/a')))}</span><em>{escape(str(regime.get('composite_label', 'n/a')))}</em></td>
        <td><span class="score-pill {_status_class(regime.get('structural_score'))}">{escape(str(regime.get('structural_score', 'n/a')))}</span></td>"""

text = text.replace(old_row, new_row)

with open("scripts/build_dashboard_archive.py", "w") as f:
    f.write(text)
